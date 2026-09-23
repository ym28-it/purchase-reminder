#!/usr/bin/env bash
set -euo pipefail

environment_failure_exit=70
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:---check}"

usage() {
  cat <<'EOF'
Usage: bash scripts/setup_host_prerequisites.sh [--check|--install]

Checks or installs the mise-managed toolchain for the Environment Gate.
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

if ! command -v mise >/dev/null 2>&1; then
  fail "mise is required. Install mise, then rerun this command."
fi

cd "$repo_root"

if [[ "$mode" == "--install" ]]; then
  if ! mise install python uv java; then
    fail "mise failed to install the pinned Python, uv, and Java toolchain."
  fi
fi

for tool in python uv java; do
  if ! mise which "$tool" >/dev/null 2>&1; then
    fail "$tool is not installed for this repository. Run: bash scripts/setup_host_prerequisites.sh --install"
  fi
done

python_version="$(
  mise exec -- python -c 'import platform; print(platform.python_version())' 2>/dev/null || true
)"
uv_version="$(mise exec -- uv --version 2>/dev/null || true)"
java_output="$(mise exec -- java -version 2>&1 || true)"
java_version="$(
  printf '%s\n' "$java_output" | sed -nE 's/.*version "([^"]+)".*/\1/p' | head -n 1
)"

[[ "$python_version" == "3.14.7" ]] || fail "expected Python 3.14.7, found ${python_version:-unknown}."
[[ "$uv_version" == "uv 0.12.18"* ]] || fail "expected uv 0.12.18, found ${uv_version:-unknown}."

java_major="${java_version%%.*}"
if [[ "$java_major" == "1" ]]; then
  java_major="$(printf '%s' "$java_version" | cut -d. -f2)"
fi
if [[ ! "$java_major" =~ ^[0-9]+$ ]] || ((java_major < 17)); then
  fail "expected Java 17 or newer, found ${java_version:-unknown}."
fi

echo "Host OS: $host_os"
echo "mise: $(mise --version)"
echo "Python: $python_version ($(mise which python))"
echo "uv: $uv_version ($(mise which uv))"
echo "Java: $java_version ($(mise which java))"
