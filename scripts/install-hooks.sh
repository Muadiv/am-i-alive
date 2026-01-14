#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="${ROOT_DIR}/.git/hooks"

if [[ ! -d "${HOOKS_DIR}" ]]; then
  echo "Git hooks directory not found: ${HOOKS_DIR}" >&2
  exit 1
fi

cat > "${HOOKS_DIR}/pre-commit" <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../scripts" && pwd)"

"${SCRIPT_DIR}/check.sh"
HOOK

chmod +x "${HOOKS_DIR}/pre-commit"
chmod +x "${ROOT_DIR}/scripts/check.sh"

echo "Pre-commit hook installed."
