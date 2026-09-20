"""Run a child command against a pinned, temporary DynamoDB Local process."""

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn
from urllib.error import URLError
from urllib.request import urlopen

from scripts.dynamodb_test_environment import (
    DEFAULT_LOCAL_PORT,
    DUMMY_CREDENTIAL,
    TEST_TABLE_PREFIX,
    EnvironmentContractError,
    clear_dynamodb_caches,
    get_test_dynamodb_resource,
    recreate_test_table,
)

MINIMUM_JAVA_MAJOR = 17
READY_TIMEOUT_SECONDS = 30
ENVIRONMENT_FAILURE_EXIT = 70


class EnvironmentSetupError(RuntimeError):
    """An environment failure that must not be classified as a test failure."""


@dataclass(frozen=True)
class DynamoDBLocalLock:
    version: str
    download_url: str
    sha256: str


def _fail(message: str) -> NoReturn:
    raise EnvironmentSetupError(message)


def _load_lock(path: Path) -> DynamoDBLocalLock:
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
        return DynamoDBLocalLock(
            version=values["version"],
            download_url=values["download_url"],
            sha256=values["sha256"],
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        _fail(f"invalid lock file {path}: {error}")


def _run_java_version(java: str) -> str:
    try:
        result = subprocess.run(
            [java, "-version"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError) as error:
        _fail(f"unable to execute Java: {error}")
    output = (result.stdout + result.stderr).strip()
    match = re.search(r'version "(\d+)', output)
    if result.returncode != 0 or match is None:
        _fail(f"unable to determine Java version: {output}")
    if int(match.group(1)) < MINIMUM_JAVA_MAJOR:
        _fail(f"Java {MINIMUM_JAVA_MAJOR} or newer is required: {output}")
    return output.splitlines()[0]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_sha256(path: Path, expected: str) -> None:
    actual = _sha256(path)
    if actual != expected:
        _fail(f"checksum mismatch for {path}: expected {expected}, got {actual}")


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.{uuid.uuid4().hex}.tmp")
    try:
        with urlopen(url, timeout=60) as response, temporary.open("wb") as file:
            shutil.copyfileobj(response, file)
        temporary.replace(destination)
    except (OSError, URLError) as error:
        temporary.unlink(missing_ok=True)
        _fail(f"DynamoDB Local download failed: {error}")


def _extract_archive(archive: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        with tarfile.open(archive, mode="r:gz") as bundle:
            bundle.extractall(temporary, filter="data")
        if not (temporary / "DynamoDBLocal.jar").is_file():
            _fail("DynamoDBLocal.jar is missing from the verified archive")
        if not (temporary / "DynamoDBLocal_lib").is_dir():
            _fail("DynamoDBLocal_lib is missing from the verified archive")
        if destination.exists():
            shutil.rmtree(destination)
        temporary.replace(destination)
    except (OSError, tarfile.TarError) as error:
        _fail(f"DynamoDB Local extraction failed: {error}")
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _read_dynamodb_version(java: str, jar: Path) -> str:
    try:
        result = subprocess.run(
            [java, "-jar", str(jar), "-version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        _fail(f"unable to read DynamoDB Local version: {error}")
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        _fail(f"unable to read DynamoDB Local version: {output}")
    match = re.search(r"(\d+\.\d+\.\d+)", output)
    if match is None:
        _fail(f"unrecognized DynamoDB Local version output: {output}")
    return match.group(1)


def _prepare_distribution(
    lock: DynamoDBLocalLock,
    cache_root: Path,
    java: str,
) -> tuple[Path, Path]:
    version_root = cache_root / lock.version
    archive = version_root / "dynamodb_local.tar.gz"
    distribution = version_root / "distribution"
    if not archive.exists():
        _download(lock.download_url, archive)
    _verify_sha256(archive, lock.sha256)
    if not distribution.exists():
        _extract_archive(archive, distribution)

    jar = distribution / "DynamoDBLocal.jar"
    library = distribution / "DynamoDBLocal_lib"
    if not jar.is_file() or not library.is_dir():
        _fail("cached DynamoDB Local distribution is incomplete")
    actual_version = _read_dynamodb_version(java, jar)
    if actual_version != lock.version:
        _fail(f"DynamoDB Local version mismatch: expected {lock.version}, got {actual_version}")
    return jar, library


def _assert_port_available(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            _fail(f"DynamoDB Local port {port} is already in use: {error}")


def _sanitized_environment(port: int, session_id: str) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("AWS_")}
    environment.update(
        {
            "DYNAMODB_ENDPOINT_URL": f"http://127.0.0.1:{port}",
            "DYNAMODB_LOCAL_PORT": str(port),
            "DYNAMODB_TABLE_NAME": f"{TEST_TABLE_PREFIX}{session_id}",
            "AWS_ACCESS_KEY_ID": DUMMY_CREDENTIAL,
            "AWS_SECRET_ACCESS_KEY": DUMMY_CREDENTIAL,
            "AWS_DEFAULT_REGION": "ap-northeast-1",
            "AWS_EC2_METADATA_DISABLED": "true",
        }
    )
    return environment


def _wait_until_ready(process: subprocess.Popen[bytes], environment: dict[str, str]) -> None:
    previous = os.environ.copy()
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    last_error: Exception | None = None
    try:
        os.environ.clear()
        os.environ.update(environment)
        clear_dynamodb_caches()
        while time.monotonic() < deadline:
            if process.poll() is not None:
                _fail(f"DynamoDB Local exited during readiness check ({process.returncode})")
            try:
                dynamodb = get_test_dynamodb_resource()
                dynamodb.meta.client.list_tables(Limit=1)
                table_name = environment["DYNAMODB_TABLE_NAME"]
                recreate_test_table(dynamodb, table_name)
                return
            except EnvironmentContractError as error:
                _fail(f"DynamoDB Local safety check failed: {error}")
            except Exception as error:  # SDK transport errors vary by botocore version.
                last_error = error
                time.sleep(0.25)
        _fail(f"DynamoDB Local API readiness timed out: {last_error}")
    finally:
        clear_dynamodb_caches()
        os.environ.clear()
        os.environ.update(previous)


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10)
    except ProcessLookupError, subprocess.TimeoutExpired:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    if arguments.command[:1] == ["--"]:
        arguments.command = arguments.command[1:]
    if not arguments.command:
        parser.error("a child command is required after --")
    return arguments


def main() -> int:
    arguments = _parse_arguments()
    repository_root = Path(__file__).resolve().parents[2]
    lock_path = repository_root / "backend" / "dynamodb-local.lock.json"
    cache_root = repository_root / ".cache" / "dynamodb-local"
    java = shutil.which("java")
    if java is None:
        print("ENVIRONMENT_FAILURE: Java is not installed", file=sys.stderr)
        return ENVIRONMENT_FAILURE_EXIT

    process: subprocess.Popen[bytes] | None = None
    log_file = None
    try:
        java_version = _run_java_version(java)
        lock = _load_lock(lock_path)
        jar, library = _prepare_distribution(lock, cache_root, java)
        try:
            port = (
                arguments.port
                if arguments.port is not None
                else int(os.environ.get("DYNAMODB_LOCAL_PORT", DEFAULT_LOCAL_PORT))
            )
        except ValueError as error:
            _fail(f"invalid DYNAMODB_LOCAL_PORT: {error}")
        if not 1 <= port <= 65535:
            _fail(f"invalid DynamoDB Local port: {port}")
        _assert_port_available(port)

        session_id = uuid.uuid4().hex
        environment = _sanitized_environment(port, session_id)
        log_path = cache_root / lock.version / "logs" / f"{session_id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = log_path.open("wb")
        process = subprocess.Popen(
            [
                java,
                f"-Djava.library.path={library}",
                "-jar",
                str(jar),
                "-inMemory",
                "-sharedDb",
                "-port",
                str(port),
                "-disableTelemetry",
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        print(f"DynamoDB Local log: {log_path}", flush=True)
        _wait_until_ready(process, environment)
        print(f"Java version: {java_version}", flush=True)
        print(f"Distribution checksum: {lock.sha256}", flush=True)
        print(f"DynamoDB Local version: {lock.version}", flush=True)
        print(f"API ready check: PASS ({environment['DYNAMODB_ENDPOINT_URL']})", flush=True)
        print(f"Test table: {environment['DYNAMODB_TABLE_NAME']}", flush=True)
        print(f"DynamoDB Local PID: {process.pid}", flush=True)

        child = subprocess.run(arguments.command, env=environment, check=False)
        print(f"Child command exit: {child.returncode}", flush=True)
        return child.returncode
    except EnvironmentSetupError as error:
        print(f"ENVIRONMENT_FAILURE: {error}", file=sys.stderr)
        if process is not None and log_file is not None:
            log_file.flush()
        return ENVIRONMENT_FAILURE_EXIT
    finally:
        if process is not None:
            _stop_process(process)
            print(f"DynamoDB Local stopped: PID {process.pid}", flush=True)
        if log_file is not None:
            log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
