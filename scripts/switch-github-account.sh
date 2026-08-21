#!/usr/bin/env bash
# Move this repo to a separate GitHub account.
#
# Run AFTER creating the new GitHub account and an empty repo on it.
# Usage: ./scripts/switch-github-account.sh <username> [repo-name]
set -euo pipefail

USERNAME="${1:?usage: switch-github-account.sh <username> [repo-name]}"
REPO="${2:-foulgorithm}"
EMAIL="foulgorithm@gmail.com"

echo "Setting commit identity for THIS REPO ONLY (global config untouched)..."
git config user.name "$USERNAME"
git config user.email "$EMAIL"

echo "Pointing origin at github.com/$USERNAME/$REPO ..."
git remote set-url origin "https://github.com/$USERNAME/$REPO.git"

echo
echo "Now:"
git config user.name
git config user.email
git remote get-url origin
echo
echo "Next:"
echo "  gh auth login                    # log in as $USERNAME"
echo "  gh auth switch --user $USERNAME"
echo "  git push -u origin main"
echo
echo "To return to ENVRT work later:  gh auth switch --user olwood96"
