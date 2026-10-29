#!/usr/bin/env bash
# source先で終了処理や環境変数を共有すると、後続モジュールへ影響するためサブシェルに閉じる。
(
  set -euo pipefail
  if [[ "$APPLY" == 0 ]]; then
    log 'Yarn Switch: 公式インストーラー（https://repo.yarnpkg.com/install）を取得し、bashで実行して最新の安定版を導入'
    log '配置先: ~/.yarn/switch / シェル設定は変更前にバックアップ（リンク先は変更しません）'
    exit 0
  fi

  # corepack enable は使わない。Node.js 25以降はcorepackが梱包されず、Yarn公式もYarn Switchを推奨するため。
  # curl | bash にしない。ダウンロード失敗時に set -e で確実に停止させるため。
  # バージョンとハッシュを固定しない。公式インストーラーは常に最新の安定版を取得し、固定できる配布物がないため。
  tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/yarn-switch.XXXXXX")
  trap 'rm -rf -- "$tmp_dir"' EXIT
  installer="$tmp_dir/install-yarn-switch.sh"
  curl -fsSL https://repo.yarnpkg.com/install -o "$installer"

  # 公式インストーラー（yarn switch postinstall）は ZDOTDIR を見ず、ホーム直下の設定に追記する。
  profiles=("$HOME/.bashrc" "$HOME/.zshrc")
  fish_config="$HOME/.config/fish/config.fish"
  if command -v fish >/dev/null || [[ -e "$fish_config" || -L "$fish_config" ]]; then profiles+=("$fish_config"); fi
  /usr/bin/python3 "$ROOT/scripts/safe_chain_profiles.py" "$BACKUP_DIR/yarn-switch" "${profiles[@]}"

  bash "$installer"
  "$HOME/.yarn/switch/bin/yarn" switch --version
  log 'Yarn Switch: ターミナルを再起動し、yarn switch --version を実行してください。'
)
