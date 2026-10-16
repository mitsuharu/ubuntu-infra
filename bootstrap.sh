#!/usr/bin/env bash
set -euo pipefail
# 公開先が確定してから、そのリポジトリURLを指定してください。
[[ $# -ge 1 ]] || { echo '使い方: bash bootstrap.sh https://github.com/OWNER/ubuntu-infra.git [--apply]' >&2; exit 1; }
repo_url=$1
shift
[[ "$repo_url" == https://github.com/*/ubuntu-infra.git ]] || { echo 'ubuntu-infraのHTTPS URLを指定してください' >&2; exit 1; }
[[ $EUID != 0 ]] || { echo 'sudoを付けずに実行してください' >&2; exit 1; }
if ! command -v git >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y git ca-certificates
fi
repo_dir="$HOME/ubuntu-infra"
if [[ -d "$repo_dir/.git" ]]; then
  [[ $(git -C "$repo_dir" remote get-url origin) == "$repo_url" ]] || { echo '既存の取得元が異なります' >&2; exit 1; }
elif [[ -e "$repo_dir" || -L "$repo_dir" ]]; then
  echo '既存の~/ubuntu-infraを保護するため停止します' >&2; exit 1
else
  git clone "$repo_url" "$repo_dir"
fi
exec bash "$repo_dir/install.sh" "$@"
