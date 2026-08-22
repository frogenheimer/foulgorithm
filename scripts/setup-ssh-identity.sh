#!/usr/bin/env bash
# Give this repo its own SSH identity, isolated from every other repo.
#
# Why not `gh auth switch`: that changes the ACTIVE GitHub account globally, for
# every terminal and every tool on the machine. ENVRT pushes would then run as
# the wrong user. An SSH host alias is scoped to this repo's remote URL only,
# so nothing else on the machine changes behaviour.
set -euo pipefail

USERNAME="${1:?usage: setup-ssh-identity.sh <github-username> [repo-name]}"
REPO="${2:-foulgorithm}"
KEY="$HOME/.ssh/id_foulgorithm"
ALIAS="github-foulgorithm"

if [ ! -f "$KEY" ]; then
  echo "Creating a dedicated SSH key..."
  ssh-keygen -t ed25519 -C "foulgorithm@gmail.com" -f "$KEY" -N ""
else
  echo "Key already exists at $KEY, reusing it."
fi

if ! grep -q "Host $ALIAS" "$HOME/.ssh/config" 2>/dev/null; then
  echo "Adding a host alias to ~/.ssh/config..."
  mkdir -p "$HOME/.ssh"
  cat >> "$HOME/.ssh/config" <<CONF

# Foulgorithm only. Isolated from the default github.com identity so ENVRT
# work is completely unaffected.
Host $ALIAS
  HostName github.com
  User git
  IdentityFile $KEY
  IdentitiesOnly yes
CONF
else
  echo "Host alias already present in ~/.ssh/config."
fi

git remote set-url origin "git@$ALIAS:$USERNAME/$REPO.git"

echo
echo "=============================================================="
echo "ONE MANUAL STEP. Copy the key below (it is already on your"
echo "clipboard), then add it at:"
echo "  https://github.com/settings/ssh/new"
echo "while signed in as $USERNAME."
echo "=============================================================="
echo
cat "$KEY.pub"
command -v pbcopy >/dev/null && pbcopy < "$KEY.pub" && echo && echo "(copied to clipboard)"
echo
echo "Then run:  ssh -T git@$ALIAS   and   git push -u origin main"
