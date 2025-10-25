#!/usr/bin/env bash
set -euo pipefail

echo "Installing recommended CJK fonts..."

if [[ "$OSTYPE" == "darwin"* ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Install Homebrew first or install fonts manually."
    exit 1
  fi
  brew tap homebrew/cask-fonts
  echo "Installing Noto Sans CJK..."
  brew install --cask font-noto-sans-cjk
  echo "Done. Restart your app."
elif [[ -f /etc/debian_version ]]; then
  echo "Detected Debian/Ubuntu"
  sudo apt update
  sudo apt install -y fonts-noto-cjk fonts-noto-cjk-extra
  echo "Done. Restart your app."
elif [[ -f /etc/redhat-release ]]; then
  echo "Detected RHEL/CentOS. Please install Noto CJK manually or copy .ttf into the project's ./fonts/ folder."
  exit 1
else
  echo "Unknown OS. Please install a CJK font such as Noto Sans CJK or Source Han Sans, or copy the .ttf into ./fonts/."
  exit 1
fi
