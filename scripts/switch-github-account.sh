#!/usr/bin/env bash
# Move this repo to a separate GitHub account.
#
# Run AFTER creating the new GitHub account and an empty public repo on it.
# Usage: ./scripts/switch-github-account.sh <new-github-username>
set -euo pipefail

USERNAME="${1:?usage: switch-github-account.sh <new-github-username>}"
EMAIL="foulgorithm@gmail.com"

echo "Setting commit identity for THIS REPO ONLY (global config untouched)..."
git config user.name "$USERNAME"
git config user.email "$EMAIL"

echo "Pointing origin at github.com/$USERNAME/foulgorithm..."
git remote set-url origin "https://github.com/$USERNAME/foulgorithm.git"

echo
echo "Done. Current settings:"
git config user.name
git config user.email
git remote -v | head -1
echo
echo "Next: authenticate as the new account, then push."
echo "  gh auth login          # choose the new account"
echo "  gh auth switch --user $USERNAME"
echo "  git push -u origin main"
