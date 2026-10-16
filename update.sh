#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ $# == 0 || ( $# == 1 && $1 == --apply ) ]] || { echo '使い方: bash update.sh [--apply]' >&2; exit 1; }
[[ -d "$ROOT/.git" ]] || { echo 'Gitでcloneした構成から実行してください' >&2; exit 1; }
[[ -z $(git -C "$ROOT" status --porcelain) ]] || { echo '未コミットの変更があります' >&2; exit 1; }
branch=$(git -C "$ROOT" symbolic-ref --quiet --short HEAD)
[[ "$branch" == main || "$branch" == master ]] || { echo 'main / masterから実行してください' >&2; exit 1; }
git -C "$ROOT" pull --ff-only
if [[ ${1:-} == --apply ]]; then bash "$ROOT/install.sh" --apply; fi
