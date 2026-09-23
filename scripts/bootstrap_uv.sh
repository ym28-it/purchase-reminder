#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_version="$(tr -d '[:space:]' < "$repo_root/.python-version")"
uv_version="$(sed -nE 's/^uv = "([^"]+)"$/\1/p' "$repo_root/mise.toml")"

if [[ -z "$python_version" || -z "$uv_version" ]]; then
  echo "Failed to read pinned Python or uv version." >&2
  exit 70
fi

bootstrap_root="${UV_BOOTSTRAP_DIR:-$repo_root/.cache/uv-bootstrap/$uv_version}"
bootstrap_python="$bootstrap_root/bin/python"
uv_bin="$bootstrap_root/bin/uv"
shim_dir="$repo_root/.cache/bin"

if [[ ! -x "$uv_bin" ]] || [[ "$("$uv_bin" --version 2>/dev/null || true)" != "uv $uv_version"* ]]; then
  system_python="$(command -v python3 || true)"
  if [[ -z "$system_python" ]]; then
    echo "ENVIRONMENT_FAILURE: python3 is required to bootstrap uv $uv_version from PyPI." >&2
    exit 70
  fi

  "$system_python" -m venv --clear "$bootstrap_root"
  "$bootstrap_python" -m pip install     --disable-pip-version-check     --no-deps     --index-url https://pypi.org/simple     "uv==$uv_version"
fi

mkdir -p "$shim_dir"
ln -sfn "$uv_bin" "$shim_dir/uv"

if ! python_path="$("$uv_bin" python find "$python_version" 2>/dev/null)"; then
  "$uv_bin" python install "$python_version"
  python_path="$("$uv_bin" python find "$python_version")"
fi

actual_python="$("$python_path" -c 'import platform; print(platform.python_version())')"
if [[ "$actual_python" != "$python_version" ]]; then
  echo "ENVIRONMENT_FAILURE: expected Python $python_version, found $actual_python." >&2
  exit 70
fi

echo "uv $uv_version: $uv_bin"
echo "Python $python_version: $python_path"
echo "Add the repository-local uv to this shell with:"
echo "  export PATH="$shim_dir:\$PATH""
