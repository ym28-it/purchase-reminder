#!/usr/bin/env bash
# Run the Playwright E2E suite against a fresh DynamoDB Local table via the
# approved runner. Usage (from the repository root): bash e2e/run-e2e.sh
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}/backend"
exec ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- \
	bash -c 'cd ../e2e && bun run test "$@"' e2e "$@"
