#!/usr/bin/env bash
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/shells/common.sh"
APPLY=0
MODULE=all
while (($#)); do
  case "$1" in
    --apply) APPLY=1 ;;
    --dry-run) APPLY=0 ;;
    --only) shift; MODULE=${1:?--onlyにはモジュール名が必要です} ;;
    -h|--help) echo 'bash install.sh [--dry-run|--apply] [--only base|dotfiles|anyenv|japanese|desktop|apps|chrome-keyring|all]'; exit 0 ;;
    *) die "不明な引数: $1" ;;
  esac
  shift
done
case "$MODULE" in all|base|dotfiles|anyenv|japanese|desktop|apps|chrome-keyring) ;; *) die "不明なモジュール: $MODULE" ;; esac
source /etc/os-release
[[ "$ID" == ubuntu && ( "$VERSION_ID" == 24.04 || "$VERSION_ID" == 26.04 ) ]] || die 'Ubuntu 24.04 / 26.04 が対象です'
[[ $(dpkg --print-architecture) == amd64 ]] || die 'この構成の対応CPUはamd64です（Chrome/1Passwordを含むため）'
# sudoで全体を起動するとrootのホームに設定されるため拒否します。
[[ $EUID != 0 ]] || die 'sudoを付けず、ログインユーザーで実行してください'
source "$ROOT/config.sh"
[[ -f "$ROOT/config.local.sh" ]] && source "$ROOT/config.local.sh"
[[ "$RUBY_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die 'Rubyバージョンが不正です'
# shellcheck disable=SC2153 # config.shから読み込みます。
[[ "$NODE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die 'Nodeバージョンが不正です'
[[ "$KEYBOARD_LAYOUT" == jp || "$KEYBOARD_LAYOUT" == us ]] || die 'KEYBOARD_LAYOUTはjpまたはusです'
export ANYENV_ROOT="$HOME/.anyenv"
export ANYENV_DEFINITION_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/anyenv/anyenv-install"
export RBENV_ROOT="$ANYENV_ROOT/envs/rbenv"
export NODENV_ROOT="$ANYENV_ROOT/envs/nodenv"
export PATH="$HOME/.local/bin:$ANYENV_ROOT/bin:$PATH"
export RBENV_VERSION="$RUBY_VERSION" NODENV_VERSION="$NODE_VERSION"
CONFIG_HOME=${XDG_CONFIG_HOME:-$HOME/.config}
BACKUP_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/ubuntu-infra/backups/$(date +%Y%m%dT%H%M%S)-$$"
if [[ "$APPLY" == 1 && ( "$MODULE" == all || "$MODULE" == japanese || "$MODULE" == desktop ) ]]; then
  [[ ${XDG_CURRENT_DESKTOP:-} == *GNOME* || ${XDG_CURRENT_DESKTOP:-} == *Ubuntu* ]] || die 'GNOMEにログインした端末から実行してください'
  if [[ "$MODULE" != desktop ]] && pgrep -u "$(id -u)" -x fcitx5 >/dev/null; then
    die 'fcitx5をトレイから終了して再実行してください（設定保存の競合回避）'
  fi
  [[ -n ${DBUS_SESSION_BUS_ADDRESS:-} ]] || die 'ユーザーのD-Busセッションが必要です'
  command -v gsettings >/dev/null || die 'gsettingsがありません'
  [[ $(gsettings writable org.gnome.desktop.input-sources xkb-options) == true ]] || die 'GNOME設定が書き込み不可です'
fi
log "Ubuntu $VERSION_ID / $MODULE / apply=$APPLY"
if [[ "$APPLY" == 1 ]]; then
  mkdir -p "$BACKUP_DIR"
  log "設定のバックアップ先: $BACKUP_DIR"
fi
for step in base dotfiles anyenv japanese desktop apps chrome-keyring; do
  if [[ "$MODULE" == all || "$MODULE" == "$step" ]]; then
    log "--- $step ---"
    source "$ROOT/shells/$step.sh"
  fi
done
log '完了。適用した場合はログアウト→ログインして、日本語入力と各ツールを確認してください。'
