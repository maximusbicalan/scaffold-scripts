#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <project-name>" >&2
  exit 1
fi

PROJECT_NAME="$1"

# Only allow a simple directory name, never a path.
if [[ -z "$PROJECT_NAME" ||
      "$PROJECT_NAME" == "." ||
      "$PROJECT_NAME" == ".." ||
      "$PROJECT_NAME" == */* ||
      "$PROJECT_NAME" == *\\* ]]; then
  echo "Error: provide a project name, not a path." >&2
  exit 1
fi

# Projects are created beside react+fastapi, under scaffold-scripts.
PROJECT_DIR="$PROJECTS_DIR/$PROJECT_NAME"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "Error: project directory does not exist: $PROJECT_DIR" >&2
  exit 1
fi

echo "WARNING: This will permanently delete:"
echo "  Project directory: $PROJECT_DIR"
echo "  Docker containers, networks, and volumes belonging to this project"
echo
printf 'Retype the project name "%s" to confirm: ' "$PROJECT_NAME"
IFS= read -r CONFIRMATION

if [[ "$CONFIRMATION" != "$PROJECT_NAME" ]]; then
  echo "Project name did not match. Deletion cancelled."
  exit 1
fi

# Remove Docker resources before deleting the Compose configuration.
if [[ -f "$PROJECT_DIR/compose.yaml" ||
      -f "$PROJECT_DIR/compose.yml" ||
      -f "$PROJECT_DIR/docker-compose.yaml" ||
      -f "$PROJECT_DIR/docker-compose.yml" ]]; then

  if ! command -v docker >/dev/null 2>&1; then
    echo "Error: Docker is required to remove the project's Docker resources." >&2
    echo "The project directory was not deleted." >&2
    exit 1
  fi

  echo "Removing Docker resources..."
  (
    cd "$PROJECT_DIR"
    docker compose down -v --remove-orphans
  )
fi

echo "Deleting project directory..."
rm -rf -- "$PROJECT_DIR"

echo "Deleted project: $PROJECT_NAME"