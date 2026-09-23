#!/usr/bin/env bash
set -euo pipefail

environment_failure_exit=70
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
shim_dir="$repo_root/.cache/bin"
mode="${1:---check}"

usage() {
  cat <<'EOF'
Usage: bash scripts/setup_host_prerequisites.sh [--check|--install]

Checks or installs the host prerequisites for the Environment Gate.
Supported hosts are Linux (including WSL2) and macOS.
EOF
}

fail() {
  echo "ENVIRONMENT_FAILURE: $*" >&2
  exit "$environment_failure_exit"
}

case "$mode" in
  --check | --install) ;;
  --help | -h)
    usage
    exit 0
    ;;
  *)
    usage >&2
    fail "unknown option: $mode"
    ;;
esac

host_os="$(uname -s 2>/dev/null || true)"
case "$host_os" in
  Linux | Darwin) ;;
  *) fail "supported hosts are Linux (including WSL2) and macOS; found ${host_os:-unknown}." ;;
esac

python_ready=false
python_version=""
if command -v python3 >/dev/null 2>&1; then
  python_version="$(
    python3 -c 'import platform; print(platform.python_version())' 2>/dev/null || true
  )"
  if [[ -n "$python_version" ]]; then
    if ! venv_probe_root="$(mktemp -d "${TMPDIR:-/tmp}/purchase-reminder-venv.XXXXXX")"; then
      fail "failed to create a temporary directory for the Python venv check."
    fi
    if python3 -m venv "$venv_probe_root/venv" >/dev/null 2>&1; then
      python_ready=true
    fi
    if ! rm -rf "$venv_probe_root"; then
      fail "failed to remove the temporary Python venv check directory."
    fi
  fi
fi

java_ready=false
java_version=""
java_major=""
if command -v java >/dev/null 2>&1; then
  java_output="$(java -version 2>&1 || true)"
  java_version="$(
    printf '%s\n' "$java_output" | sed -nE 's/.*version "([^"]+)".*/\1/p' | head -n 1
  )"
  if [[ -n "$java_version" ]]; then
    java_major="${java_version%%.*}"
    if [[ "$java_major" == "1" ]]; then
      java_major="$(printf '%s' "$java_version" | cut -d. -f2)"
    fi
    if [[ "$java_major" =~ ^[0-9]+$ ]] && ((java_major >= 17)); then
      java_ready=true
    fi
  fi
fi

if [[ "$mode" == "--check" ]]; then
  if [[ "$python_ready" != true ]]; then
    echo "ENVIRONMENT_FAILURE: python3 with the venv module is required." >&2
  fi
  if [[ "$java_ready" != true ]]; then
    echo "ENVIRONMENT_FAILURE: Java 17 or newer is required." >&2
  fi
  if [[ "$python_ready" != true || "$java_ready" != true ]]; then
    echo "Install missing prerequisites with:" >&2
    echo "  bash scripts/setup_host_prerequisites.sh --install" >&2
    exit "$environment_failure_exit"
  fi

  echo "Host OS: $host_os"
  echo "Bootstrap Python: $python_version ($(command -v python3))"
  echo "Java: $java_version ($(command -v java))"
  exit 0
fi

if [[ "$python_ready" == true && "$java_ready" == true ]]; then
  bash "$repo_root/scripts/setup_host_prerequisites.sh" --check
  exit 0
fi

run_as_root() {
  if [[ "$(id -u)" == "0" ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    fail "sudo is required to install Linux host prerequisites."
  fi
}

run_or_fail() {
  local message="$1"
  shift
  if ! "$@"; then
    fail "$message"
  fi
}

if [[ "$host_os" == "Linux" ]]; then
  if command -v apt-get >/dev/null 2>&1; then
    packages=(ca-certificates)
    if [[ "$python_ready" != true ]]; then
      packages+=(python3 python3-venv)
    fi
    if [[ "$java_ready" != true ]]; then
      packages+=(openjdk-17-jre-headless)
    fi
    run_or_fail "apt-get update failed." run_as_root apt-get update
    run_or_fail \
      "apt-get failed to install host prerequisites." \
      run_as_root apt-get install -y "${packages[@]}"
  elif command -v dnf >/dev/null 2>&1; then
    packages=(ca-certificates)
    if [[ "$python_ready" != true ]]; then
      packages+=(python3)
    fi
    if [[ "$java_ready" != true ]]; then
      packages+=(java-17-openjdk-headless)
    fi
    run_or_fail \
      "dnf failed to install host prerequisites." \
      run_as_root dnf install -y "${packages[@]}"
  else
    fail "automatic installation requires apt-get or dnf on Linux."
  fi
else
  if ! command -v brew >/dev/null 2>&1; then
    fail "Homebrew is required for automatic installation on macOS."
  fi
  if [[ "$python_ready" != true ]]; then
    run_or_fail "Homebrew failed to install Python." brew install python
    if ! python_prefix="$(brew --prefix python)"; then
      fail "Homebrew did not report the installed Python prefix."
    fi
    python_command="$python_prefix/bin/python3"
  else
    python_command="$(command -v python3)"
  fi
  if [[ "$java_ready" != true ]]; then
    run_or_fail "Homebrew failed to install Java 17." brew install openjdk@17
    if ! java_prefix="$(brew --prefix openjdk@17)"; then
      fail "Homebrew did not report the installed Java prefix."
    fi
    java_command="$java_prefix/bin/java"
  else
    java_command="$(command -v java)"
  fi

  run_or_fail "failed to create the repository-local shim directory." mkdir -p "$shim_dir"
  run_or_fail "failed to create the Python shim." ln -sfn "$python_command" "$shim_dir/python3"
  run_or_fail "failed to create the Java shim." ln -sfn "$java_command" "$shim_dir/java"
  export PATH="$shim_dir:$PATH"
fi

bash "$repo_root/scripts/setup_host_prerequisites.sh" --check
echo "Host prerequisites are ready."
