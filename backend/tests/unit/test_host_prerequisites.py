from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "setup_host_prerequisites.sh"
MISE_WRAPPER = REPO_ROOT / "bin" / "mise"
MISE_CONFIG = REPO_ROOT / "mise.toml"


def _write_command(bin_dir: Path, name: str, body: str) -> Path:
    path = bin_dir / name
    path.write_text(f"#!/usr/bin/env bash\n{body}\n")
    path.chmod(0o755)
    return path


def _run_script(
    tmp_path: Path,
    *,
    os_name: str = "Linux",
    python_version: str = "3.14.7",
    pinned_python_version: str = "3.14.7",
    uv_version: str = "0.12.18",
    java_version: str = "17.0.12",
    missing_tool: str = "",
    include_wrapper: bool = True,
    include_python: bool = True,
    install_fails: bool = False,
    python_install_fails: bool = False,
    mode: str = "--check",
) -> subprocess.CompletedProcess[str]:
    fake_repo = tmp_path / "repo"
    script_dir = fake_repo / "scripts"
    wrapper_dir = fake_repo / "bin"
    command_dir = tmp_path / "commands"
    python_dir = fake_repo / ".mise" / "uv-python" / "cpython-3.14.7" / "bin"
    script_dir.mkdir(parents=True)
    wrapper_dir.mkdir()
    command_dir.mkdir()
    python_dir.mkdir(parents=True)
    fake_script = script_dir / SCRIPT.name
    shutil.copy2(SCRIPT, fake_script)
    (fake_repo / ".python-version").write_text(f"{pinned_python_version}\n")
    install_log = tmp_path / "install.log"
    _write_command(command_dir, "uname", f"printf '%s\\n' '{os_name}'")
    fake_python = python_dir / "python3.14"
    if include_python:
        _write_command(
            python_dir,
            fake_python.name,
            "printf '%s\\n' \"$FAKE_PYTHON_VERSION\"",
        )

    if include_wrapper:
        _write_command(
            wrapper_dir,
            "mise",
            """case "${1:-}" in
  --version)
    printf '%s\\n' 'mise 2026.9.12'
    ;;
  install)
    printf 'mise %s\\n' "$*" >> "$FAKE_INSTALL_LOG"
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
      uv)
        case "${2:-}" in
          --version) printf 'uv %s\\n' "$FAKE_UV_VERSION" ;;
          python)
            case "${3:-}" in
              install)
                printf 'uv %s\\n' "$*" >> "$FAKE_INSTALL_LOG"
                [[ "$FAKE_PYTHON_INSTALL_FAILS" != 'true' ]]
                ;;
              find)
                [[ -x "$FAKE_PYTHON_PATH" ]] || exit 1
                printf '%s\\n' "$FAKE_PYTHON_PATH"
                ;;
              *) exit 1 ;;
            esac
            ;;
          *) exit 1 ;;
        esac
        ;;
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
            "PATH": f"{command_dir}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "FAKE_INSTALL_LOG": str(install_log),
            "FAKE_MISE_INSTALL_FAILS": str(install_fails).lower(),
            "FAKE_PYTHON_INSTALL_FAILS": str(python_install_fails).lower(),
            "FAKE_MISE_MISSING_TOOL": missing_tool,
            "FAKE_PYTHON_PATH": str(fake_python),
            "FAKE_PYTHON_VERSION": python_version,
            "FAKE_UV_VERSION": uv_version,
            "FAKE_JAVA_VERSION": java_version,
        }
    )
    return subprocess.run(
        ["bash", str(fake_script), mode],
        cwd=fake_repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_check_accepts_uv_managed_python(tmp_path: Path) -> None:
    result = _run_script(tmp_path)

    assert result.returncode == 0
    assert "Host OS: Linux" in result.stdout
    assert "mise: mise 2026.9.12" in result.stdout
    assert "Python: 3.14.7" in result.stdout
    assert "managed by uv" in result.stdout
    assert "uv: uv 0.12.18" in result.stdout
    assert "Java: 17.0.12" in result.stdout


def test_install_uses_mise_for_uv_and_java_then_uv_for_python(tmp_path: Path) -> None:
    result = _run_script(tmp_path, mode="--install")

    assert result.returncode == 0
    assert (tmp_path / "install.log").read_text() == (
        "mise install --jobs=1 uv java\nuv uv python install 3.14.7\n"
    )


def test_mise_install_failure_is_environment_failure(tmp_path: Path) -> None:
    result = _run_script(tmp_path, mode="--install", install_fails=True)

    assert result.returncode == 70
    assert "mise wrapper failed to bootstrap mise or install" in result.stderr


def test_uv_python_install_failure_is_environment_failure(tmp_path: Path) -> None:
    result = _run_script(tmp_path, mode="--install", python_install_fails=True)

    assert result.returncode == 70
    assert "uv failed to install the pinned Python 3.14.7" in result.stderr


def test_check_rejects_missing_mise_wrapper(tmp_path: Path) -> None:
    result = _run_script(tmp_path, include_wrapper=False)

    assert result.returncode == 70
    assert "committed mise bootstrap wrapper is missing or not executable" in result.stderr


def test_check_does_not_require_global_mise(tmp_path: Path) -> None:
    result = _run_script(tmp_path)

    assert result.returncode == 0


def test_committed_wrapper_pins_mise_and_checksums() -> None:
    wrapper = MISE_WRAPPER.read_text()

    assert os.access(MISE_WRAPPER, os.X_OK)
    assert 'local mise_version="${MISE_VERSION:-2026.9.12}"' in wrapper
    assert "checksum_linux_x86_64=" in wrapper
    assert "checksum_macos_arm64=" in wrapper
    assert "https://mise.jdx.dev/v${version}/" in wrapper
    assert 'current_version="v2026.9.12"' in wrapper


def test_mise_exec_does_not_auto_install_and_uv_cannot_use_system_python() -> None:
    config = MISE_CONFIG.read_text()

    assert "exec_auto_install = false" in config
    assert 'UV_MANAGED_PYTHON = "1"' in config
    assert 'UV_PYTHON_INSTALL_DIR = "{{config_root}}/.mise/uv-python"' in config
    assert 'python = "3.14.7"' not in config


def test_check_rejects_uninstalled_mise_tool(tmp_path: Path) -> None:
    result = _run_script(tmp_path, missing_tool="java")

    assert result.returncode == 70
    assert "java is not installed for this repository" in result.stderr


def test_check_rejects_missing_uv_managed_python(tmp_path: Path) -> None:
    result = _run_script(tmp_path, include_python=False)

    assert result.returncode == 70
    assert "uv-managed Python 3.14.7 is not installed" in result.stderr


def test_check_rejects_wrong_python_version(tmp_path: Path) -> None:
    result = _run_script(tmp_path, python_version="3.14.0rc2")

    assert result.returncode == 70
    assert "expected Python 3.14.7, found 3.14.0rc2" in result.stderr


def test_check_rejects_wrong_python_pin(tmp_path: Path) -> None:
    result = _run_script(tmp_path, pinned_python_version="3.14.0rc2")

    assert result.returncode == 70
    assert "expected .python-version to pin 3.14.7" in result.stderr


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
