#!/usr/bin/env bash
set -euo pipefail

environment_failure_exit=70
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mise_bin="$repo_root/bin/mise"
python_version_file="$repo_root/.python-version"
mode="${1:---check}"

usage() {
  cat <<'EOF'
Usage: bash scripts/setup_host_prerequisites.sh [--check|--install]

Bootstraps mise and checks or installs the Environment Gate toolchain.
mise manages uv and Java; uv manages the pinned Python interpreter.
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

if [[ ! -x "$mise_bin" ]]; then
  fail "the committed mise bootstrap wrapper is missing or not executable: $mise_bin"
fi

if [[ ! -f "$python_version_file" ]]; then
  fail "the pinned Python version file is missing: $python_version_file"
fi
expected_python_version="$(tr -d '[:space:]' < "$python_version_file")"
[[ "$expected_python_version" == "3.14.7" ]] || \
  fail "expected .python-version to pin 3.14.7, found ${expected_python_version:-empty}."

cd "$repo_root"

if [[ "$mode" == "--install" ]]; then
  if ! "$mise_bin" install --jobs=1 uv java; then
    fail "the mise wrapper failed to bootstrap mise or install the pinned uv and Java toolchain."
  fi
  if ! "$mise_bin" exec -- uv python install "$expected_python_version"; then
    fail "uv failed to install the pinned Python $expected_python_version interpreter."
  fi
fi

for tool in uv java; do
  if ! "$mise_bin" which "$tool" >/dev/null 2>&1; then
    fail "$tool is not installed for this repository. Run: bash scripts/setup_host_prerequisites.sh --install"
  fi
done

python_path="$(
  UV_PYTHON_DOWNLOADS=never "$mise_bin" exec -- uv python find "$expected_python_version" 2>/dev/null || true
)"
expected_python_root="$repo_root/.mise/uv-python/"
case "$python_path" in
  "$expected_python_root"*) ;;
  *) fail "uv-managed Python $expected_python_version is not installed in $expected_python_root. Run: bash scripts/setup_host_prerequisites.sh --install" ;;
esac
[[ -x "$python_path" ]] || fail "uv reported a non-executable Python interpreter: $python_path"

python_version="$("$python_path" -c 'import platform; print(platform.python_version())' 2>/dev/null || true)"
uv_version="$("$mise_bin" exec -- uv --version 2>/dev/null || true)"
java_output="$("$mise_bin" exec -- java -version 2>&1 || true)"
java_version="$(
  printf '%s\n' "$java_output" | sed -nE 's/.*version "([^"]+)".*/\1/p' | head -n 1
)"

[[ "$python_version" == "$expected_python_version" ]] || \
  fail "expected Python $expected_python_version, found ${python_version:-unknown}."
[[ "$uv_version" == "uv 0.12.18"* ]] || fail "expected uv 0.12.18, found ${uv_version:-unknown}."

java_major="${java_version%%.*}"
if [[ "$java_major" == "1" ]]; then
  java_major="$(printf '%s' "$java_version" | cut -d. -f2)"
fi
if [[ ! "$java_major" =~ ^[0-9]+$ ]] || ((java_major < 17)); then
  fail "expected Java 17 or newer, found ${java_version:-unknown}."
fi

echo "Host OS: $host_os"
echo "mise: $("$mise_bin" --version)"
echo "Python: $python_version $python_path (managed by uv)"
echo "uv: $uv_version $("$mise_bin" which uv)"
echo "Java: $java_version $("$mise_bin" which java)"
