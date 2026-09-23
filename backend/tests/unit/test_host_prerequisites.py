from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "setup_host_prerequisites.sh"


def _write_command(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(f"#!/usr/bin/env bash\n{body}\n")
    path.chmod(0o755)


def _run_script(
    tmp_path: Path,
    *,
    os_name: str,
    java_version: str | None,
    include_python: bool = True,
    mode: str = "--check",
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_command(bin_dir, "uname", f"printf '%s\\n' '{os_name}'")
    if include_python:
        _write_command(
            bin_dir,
            "python3",
            "if [[ \"${1:-}\" == '-c' && \"${2:-}\" == *platform* ]]; then "
            "printf '%s\\n' '3.12.0'; fi",
        )
    else:
        _write_command(bin_dir, "python3", "exit 1")
    if java_version is not None:
        _write_command(
            bin_dir,
            "java",
            "printf '%s\\n' 'Picked up JAVA_TOOL_OPTIONS: -Dfile.encoding=UTF-8' >&2; "
            f"printf '%s\\n' 'openjdk version \"{java_version}\"' >&2",
        )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["bash", str(SCRIPT), mode],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_check_accepts_linux_with_python_and_java_17(tmp_path: Path) -> None:
    result = _run_script(tmp_path, os_name="Linux", java_version="17.0.12")

    assert result.returncode == 0
    assert "Host OS: Linux" in result.stdout
    assert "Bootstrap Python: 3.12.0" in result.stdout
    assert "Java: 17.0.12" in result.stdout


def test_check_accepts_macos_and_ignores_java_tool_options_notice(tmp_path: Path) -> None:
    result = _run_script(tmp_path, os_name="Darwin", java_version="21.0.4")

    assert result.returncode == 0
    assert "Host OS: Darwin" in result.stdout
    assert "Java: 21.0.4" in result.stdout


def test_check_rejects_java_older_than_17(tmp_path: Path) -> None:
    result = _run_script(tmp_path, os_name="Linux", java_version="11.0.24")

    assert result.returncode == 70
    assert "ENVIRONMENT_FAILURE: Java 17 or newer is required." in result.stderr


def test_check_rejects_missing_python(tmp_path: Path) -> None:
    result = _run_script(
        tmp_path,
        os_name="Linux",
        java_version="17.0.12",
        include_python=False,
    )

    assert result.returncode == 70
    assert "ENVIRONMENT_FAILURE: python3 with the venv module is required." in result.stderr


def test_install_is_idempotent_when_prerequisites_are_ready(tmp_path: Path) -> None:
    result = _run_script(
        tmp_path,
        os_name="Linux",
        java_version="17.0.12",
        mode="--install",
    )

    assert result.returncode == 0
    assert "Host OS: Linux" in result.stdout


def test_check_rejects_windows_native(tmp_path: Path) -> None:
    result = _run_script(tmp_path, os_name="Windows_NT", java_version="17.0.12")

    assert result.returncode == 70
    assert "supported hosts are Linux (including WSL2) and macOS" in result.stderr


def test_check_rejects_other_posix_hosts(tmp_path: Path) -> None:
    result = _run_script(tmp_path, os_name="FreeBSD", java_version="17.0.12")

    assert result.returncode == 70
    assert "supported hosts are Linux (including WSL2) and macOS" in result.stderr
