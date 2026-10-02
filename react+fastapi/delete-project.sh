#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <project-name>" >&2
  exit 1
fi

PROJECT_NAME="$1"

# Only allow a simple directory name—never a path.
if [[ -z "$PROJECT_NAME" || "$PROJECT_NAME" == "." || "$PROJECT_NAME" == ".." ||
      "$PROJECT_NAME" == */* || "$PROJECT_NAME" == *\\* ]]; then
  echo "Error: provide a project name, not a path." >&2
  exit 1
fi

PROJECT_DIR="$SCRIPT_DIR/$PROJECT_NAME"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "Error: project directory does not exist: $PROJECT_DIR" >&2
  exit 1
fi

echo "WARNING: This will permanently delete:"
echo "  $PROJECT_DIR"
printf 'Retype the project name "%s" to confirm: ' "$PROJECT_NAME"
IFS= read -r CONFIRMATION

if [[ "$CONFIRMATION" != "$PROJECT_NAME" ]]; then
  echo "Project name did not match. Deletion cancelled."
  exit 1
fi

rm -rf -- "$PROJECT_DIR"
echo "Deleted project: $PROJECT_NAME"