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
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn
from urllib.parse import unquote, urlparse
from xml.sax.saxutils import escape

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
DYNAMODB_LOCAL_GROUP_ID = "software.amazon.dynamodb"
DYNAMODB_LOCAL_ARTIFACT_ID = "DynamoDBLocal"
DYNAMODB_LOCAL_MAIN_CLASS = "software.amazon.dynamodb.services.local.main.ServerRunner"
MAVEN_DEPENDENCY_PLUGIN_GROUP_ID = "org.apache.maven.plugins"
MAVEN_DEPENDENCY_PLUGIN_ARTIFACT_ID = "maven-dependency-plugin"


class EnvironmentSetupError(RuntimeError):
    """An environment failure that must not be classified as a test failure."""


@dataclass(frozen=True)
class DynamoDBLocalRuntime:
    version: str
    dependency_plugin_version: str
    pom_path: Path


def _fail(message: str) -> NoReturn:
    raise EnvironmentSetupError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_runtime(pom_path: Path) -> DynamoDBLocalRuntime:
    try:
        root = ET.parse(pom_path).getroot()
        namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
        properties = root.find("m:properties", namespace)
        if properties is None:
            _fail(f"Maven properties are missing from {pom_path}")
        version = properties.findtext("m:dynamodb-local.version", namespaces=namespace)
        plugin_version = properties.findtext(
            "m:maven-dependency-plugin.version", namespaces=namespace
        )
        if not version or not plugin_version:
            _fail(f"pinned Maven dependency versions are missing from {pom_path}")

        dependency_found = any(
            dependency.findtext("m:groupId", namespaces=namespace) == DYNAMODB_LOCAL_GROUP_ID
            and dependency.findtext("m:artifactId", namespaces=namespace)
            == DYNAMODB_LOCAL_ARTIFACT_ID
            and dependency.findtext("m:version", namespaces=namespace)
            == "${dynamodb-local.version}"
            for dependency in root.findall("m:dependencies/m:dependency", namespace)
        )
        if not dependency_found:
            _fail(f"pinned DynamoDB Local dependency is missing from {pom_path}")
        return DynamoDBLocalRuntime(version, plugin_version, pom_path)
    except (OSError, ET.ParseError) as error:
        _fail(f"invalid Maven runtime POM {pom_path}: {error}")


def _run_java_version(java: str) -> str:
    try:
        result = subprocess.run(
            [java, "-version"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError) as error:
        _fail(f"unable to execute Java: {error}")
    output = (result.stdout + result.stderr).strip()
    # JAVA_TOOL_OPTIONS makes the JVM print a "Picked up ..." notice before the version line.
    match = re.search(r'^.*version "(\d+).*$', output, re.MULTILINE)
    if result.returncode != 0 or match is None:
        _fail(f"unable to determine Java version: {output}")
    if int(match.group(1)) < MINIMUM_JAVA_MAJOR:
        _fail(f"Java {MINIMUM_JAVA_MAJOR} or newer is required: {output}")
    return match.group(0)


def _maven_environment(cache_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("MAVEN_ARGS", "MAVEN_OPTS", "MVNW_REPOURL", "MVNW_VERBOSE"):
        environment.pop(name, None)
    environment["MAVEN_USER_HOME"] = str(cache_root / "maven-user-home")
    return environment


def _write_maven_proxy_settings(cache_root: Path) -> Path | None:
    proxy_value = (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
    )
    if not proxy_value:
        return None

    parsed = urlparse(proxy_value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        _fail("HTTP proxy URL is invalid for Maven")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as error:
        _fail(f"HTTP proxy port is invalid for Maven: {error}")

    non_proxy_hosts = (
        os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or "localhost,127.0.0.1"
    )
    non_proxy_hosts = "|".join(
        value.strip() for value in non_proxy_hosts.split(",") if value.strip()
    )
    credentials = ""
    if parsed.username is not None:
        credentials += f"      <username>{escape(unquote(parsed.username))}</username>\n"
    if parsed.password is not None:
        credentials += f"      <password>{escape(unquote(parsed.password))}</password>\n"

    settings = (
        '<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"\n'
        '          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        '          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0 '
        'https://maven.apache.org/xsd/settings-1.0.0.xsd">\n'
        "  <proxies>\n"
        "    <proxy>\n"
        "      <id>environment-proxy</id>\n"
        "      <active>true</active>\n"
        f"      <protocol>{escape(parsed.scheme)}</protocol>\n"
        f"      <host>{escape(parsed.hostname)}</host>\n"
        f"      <port>{port}</port>\n"
        f"{credentials}"
        f"      <nonProxyHosts>{escape(non_proxy_hosts)}</nonProxyHosts>\n"
        "    </proxy>\n"
        "  </proxies>\n"
        "</settings>\n"
    )
    cache_root.mkdir(parents=True, exist_ok=True)
    settings_path = cache_root / f".maven-settings-{uuid.uuid4().hex}.xml"
    try:
        settings_path.write_text(settings, encoding="utf-8")
        settings_path.chmod(0o600)
    except OSError as error:
        settings_path.unlink(missing_ok=True)
        _fail(f"unable to create temporary Maven settings: {error}")
    return settings_path


def _run_maven(
    repository_root: Path,
    cache_root: Path,
    arguments: list[str],
    *,
    timeout: int,
) -> str:
    wrapper = repository_root / "mvnw"
    if not wrapper.is_file():
        _fail(f"Maven Wrapper is missing: {wrapper}")

    settings_path = _write_maven_proxy_settings(cache_root)
    command = ["sh", str(wrapper)]
    if settings_path is not None:
        command.extend(["-s", str(settings_path)])
    command.extend(arguments)
    try:
        result = subprocess.run(
            command,
            cwd=repository_root,
            env=_maven_environment(cache_root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        _fail(f"unable to execute Maven Wrapper: {error}")
    finally:
        if settings_path is not None:
            settings_path.unlink(missing_ok=True)

    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        tail = "\n".join(output.splitlines()[-20:])
        _fail(f"Maven command failed with exit {result.returncode}: {tail}")
    return output


def _run_maven_version(repository_root: Path, cache_root: Path) -> str:
    output = _run_maven(repository_root, cache_root, ["--version"], timeout=120)
    first_line = output.splitlines()[0] if output else ""
    if not first_line.startswith("Apache Maven "):
        _fail(f"unable to determine Maven version: {output}")
    return first_line


def _read_dynamodb_version(java: str, dependencies: Path) -> str:
    try:
        result = subprocess.run(
            [
                java,
                "-cp",
                str(dependencies / "*"),
                DYNAMODB_LOCAL_MAIN_CLASS,
                "-version",
            ],
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


def _dependencies_complete(runtime: DynamoDBLocalRuntime, dependencies: Path) -> bool:
    jar = dependencies / f"{DYNAMODB_LOCAL_ARTIFACT_ID}-{runtime.version}.jar"
    native_libraries = (
        list(dependencies.glob("libsqlite4java-*.so"))
        + list(dependencies.glob("libsqlite4java-*.dylib"))
        + list(dependencies.glob("sqlite4java-*.dll"))
    )
    return jar.is_file() and bool(native_libraries)


def _resolve_maven_dependencies(
    runtime: DynamoDBLocalRuntime,
    repository_root: Path,
    cache_root: Path,
    destination: Path,
) -> None:
    plugin = (
        f"{MAVEN_DEPENDENCY_PLUGIN_GROUP_ID}:"
        f"{MAVEN_DEPENDENCY_PLUGIN_ARTIFACT_ID}:"
        f"{runtime.dependency_plugin_version}:copy-dependencies"
    )
    local_repository = cache_root / "maven-repository"
    _run_maven(
        repository_root,
        cache_root,
        [
            "-q",
            "-B",
            "-ntp",
            "-f",
            str(runtime.pom_path),
            f"-Dmaven.repo.local={local_repository}",
            plugin,
            f"-DoutputDirectory={destination}",
            "-DincludeScope=runtime",
        ],
        timeout=300,
    )


def _prepare_distribution(
    runtime: DynamoDBLocalRuntime,
    repository_root: Path,
    cache_root: Path,
    java: str,
) -> Path:
    version_root = cache_root / runtime.version
    dependencies = version_root / "dependencies"
    marker = version_root / "maven-resolved.json"
    pom_sha256 = _sha256(runtime.pom_path)
    expected_marker = {
        "coordinate": (f"{DYNAMODB_LOCAL_GROUP_ID}:{DYNAMODB_LOCAL_ARTIFACT_ID}:{runtime.version}"),
        "pom_sha256": pom_sha256,
    }

    marker_matches = False
    try:
        marker_matches = json.loads(marker.read_text(encoding="utf-8")) == expected_marker
    except OSError, json.JSONDecodeError:
        pass

    if not marker_matches or not _dependencies_complete(runtime, dependencies):
        version_root.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".dependencies-", dir=version_root))
        try:
            _resolve_maven_dependencies(runtime, repository_root, cache_root, temporary)
            if not _dependencies_complete(runtime, temporary):
                _fail("Maven resolved an incomplete DynamoDB Local runtime")
            if dependencies.exists():
                shutil.rmtree(dependencies)
            temporary.replace(dependencies)
            marker_temporary = marker.with_suffix(f".{uuid.uuid4().hex}.tmp")
            marker_temporary.write_text(
                json.dumps(expected_marker, indent=2) + "\n", encoding="utf-8"
            )
            marker_temporary.replace(marker)
        except OSError as error:
            _fail(f"unable to cache Maven dependencies: {error}")
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)

    actual_version = _read_dynamodb_version(java, dependencies)
    if actual_version != runtime.version:
        _fail(f"DynamoDB Local version mismatch: expected {runtime.version}, got {actual_version}")
    return dependencies


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


def _run(arguments: argparse.Namespace) -> int:
    repository_root = Path(__file__).resolve().parents[2]
    pom_path = repository_root / "tools" / "java-runtime" / "pom.xml"
    cache_root = repository_root / ".cache" / "dynamodb-local"
    java = shutil.which("java")
    if java is None:
        _fail("Java is not installed")

    process: subprocess.Popen[bytes] | None = None
    log_file = None
    try:
        java_version = _run_java_version(java)
        maven_version = _run_maven_version(repository_root, cache_root)
        runtime = _load_runtime(pom_path)
        dependencies = _prepare_distribution(runtime, repository_root, cache_root, java)
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
        log_path = cache_root / runtime.version / "logs" / f"{session_id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = log_path.open("wb")
        process = subprocess.Popen(
            [
                java,
                f"-Djava.library.path={dependencies}",
                "-cp",
                str(dependencies / "*"),
                DYNAMODB_LOCAL_MAIN_CLASS,
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
        print(f"Maven version: {maven_version}", flush=True)
        print(
            "Dependency coordinate: "
            f"{DYNAMODB_LOCAL_GROUP_ID}:{DYNAMODB_LOCAL_ARTIFACT_ID}:{runtime.version}",
            flush=True,
        )
        print(f"Runtime POM SHA-256: {_sha256(runtime.pom_path)}", flush=True)
        print(f"DynamoDB Local version: {runtime.version}", flush=True)
        print(f"API ready check: PASS ({environment['DYNAMODB_ENDPOINT_URL']})", flush=True)
        print(f"Test table: {environment['DYNAMODB_TABLE_NAME']}", flush=True)
        print(f"DynamoDB Local PID: {process.pid}", flush=True)

        child = subprocess.run(arguments.command, env=environment, check=False)
        print(f"Child command exit: {child.returncode}", flush=True)
        return child.returncode
    finally:
        try:
            if process is not None:
                _stop_process(process)
                print(f"DynamoDB Local stopped: PID {process.pid}", flush=True)
        finally:
            if log_file is not None:
                log_file.close()


def main() -> int:
    try:
        return _run(_parse_arguments())
    except (EnvironmentSetupError, OSError) as error:
        print(f"ENVIRONMENT_FAILURE: {error}", file=sys.stderr)
        return ENVIRONMENT_FAILURE_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
