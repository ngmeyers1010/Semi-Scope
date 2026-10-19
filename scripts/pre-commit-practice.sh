#!/bin/sh
# Opt-in git hook: refresh docs/practice.html whenever you commit, so the progress page on your
# dashboard matches the exercises you've passed. Install once from the repo root:
#     ln -s ../../scripts/pre-commit-practice.sh .git/hooks/pre-commit
# Remove with: rm .git/hooks/pre-commit
# It never blocks a commit: if the check fails for any reason, you just get a warning.
cd "$(git rev-parse --show-toplevel)" || exit 0
PY=$(command -v python3 || command -v python) || { echo "pre-commit: python not found, practice page not updated"; exit 0; }
if "$PY" practice/check.py --html >/dev/null 2>&1; then
  git add docs/practice.html
else
  echo "pre-commit: couldn't update docs/practice.html (commit continues)"
fi
exit 0
