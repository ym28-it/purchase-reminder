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
    os_name: str = "Linux",
    python_version: str = "3.14.7",
    uv_version: str = "0.12.18",
    java_version: str = "17.0.12",
    missing_tool: str = "",
    include_mise: bool = True,
    install_fails: bool = False,
    mode: str = "--check",
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    install_log = tmp_path / "mise-install.log"
    _write_command(bin_dir, "uname", f"printf '%s\\n' '{os_name}'")

    if include_mise:
        _write_command(
            bin_dir,
            "mise",
            """case "${1:-}" in
  --version)
    printf '%s\\n' 'mise 2026.9.12'
    ;;
  install)
    printf '%s\\n' "$*" > "$FAKE_MISE_INSTALL_LOG"
    [[ "$FAKE_MISE_INSTALL_FAILS" != 'true' ]]
    ;;
  which)
    [[ "${2:-}" != "$FAKE_MISE_MISSING_TOOL" ]] || exit 1
    printf '/mise/%s/bin/%s\\n' "${2:-unknown}" "${2:-unknown}"
    ;;
  exec)
    shift
    [[ "${1:-}" == '--' ]] && shift
    case "${1:-}" in
      python) printf '%s\\n' "$FAKE_PYTHON_VERSION" ;;
      uv) printf 'uv %s\\n' "$FAKE_UV_VERSION" ;;
      java) printf 'openjdk version "%s"\\n' "$FAKE_JAVA_VERSION" >&2 ;;
      *) exit 1 ;;
    esac
    ;;
  *) exit 1 ;;
esac""",
        )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "FAKE_MISE_INSTALL_LOG": str(install_log),
            "FAKE_MISE_INSTALL_FAILS": str(install_fails).lower(),
            "FAKE_MISE_MISSING_TOOL": missing_tool,
            "FAKE_PYTHON_VERSION": python_version,
            "FAKE_UV_VERSION": uv_version,
            "FAKE_JAVA_VERSION": java_version,
        }
    )
    return subprocess.run(
        ["bash", str(SCRIPT), mode],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_check_accepts_mise_managed_toolchain(tmp_path: Path) -> None:
    result = _run_script(tmp_path)

    assert result.returncode == 0
    assert "Host OS: Linux" in result.stdout
    assert "mise: mise 2026.9.12" in result.stdout
    assert "Python: 3.14.7" in result.stdout
    assert "uv: uv 0.12.18" in result.stdout
    assert "Java: 17.0.12" in result.stdout


def test_install_requests_only_environment_gate_tools(tmp_path: Path) -> None:
    result = _run_script(tmp_path, mode="--install")

    assert result.returncode == 0
    assert (tmp_path / "mise-install.log").read_text() == "install python uv java\n"


def test_install_failure_is_environment_failure(tmp_path: Path) -> None:
    result = _run_script(tmp_path, mode="--install", install_fails=True)

    assert result.returncode == 70
    assert "mise failed to install" in result.stderr


def test_check_rejects_missing_mise(tmp_path: Path) -> None:
    result = _run_script(tmp_path, include_mise=False)

    assert result.returncode == 70
    assert "ENVIRONMENT_FAILURE: mise is required." in result.stderr


def test_check_rejects_uninstalled_tool(tmp_path: Path) -> None:
    result = _run_script(tmp_path, missing_tool="java")

    assert result.returncode == 70
    assert "java is not installed for this repository" in result.stderr


def test_check_rejects_wrong_python_version(tmp_path: Path) -> None:
    result = _run_script(tmp_path, python_version="3.14.0rc2")

    assert result.returncode == 70
    assert "expected Python 3.14.7, found 3.14.0rc2" in result.stderr


def test_check_rejects_wrong_uv_version(tmp_path: Path) -> None:
    result = _run_script(tmp_path, uv_version="0.8.0")

    assert result.returncode == 70
    assert "expected uv 0.12.18, found uv 0.8.0" in result.stderr


def test_check_rejects_java_older_than_17(tmp_path: Path) -> None:
    result = _run_script(tmp_path, java_version="11.0.24")

    assert result.returncode == 70
    assert "expected Java 17 or newer, found 11.0.24" in result.stderr


def test_check_accepts_macos(tmp_path: Path) -> None:
    result = _run_script(tmp_path, os_name="Darwin")

    assert result.returncode == 0
    assert "Host OS: Darwin" in result.stdout


def test_check_rejects_windows_native(tmp_path: Path) -> None:
    result = _run_script(tmp_path, os_name="Windows_NT")

    assert result.returncode == 70
    assert "supported hosts are Linux (including WSL2) and macOS" in result.stderr
