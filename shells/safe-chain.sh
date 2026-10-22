#!/usr/bin/env bash
# source先で終了処理や環境変数を共有すると、後続モジュールへ影響するためサブシェルに閉じる。
(
  set -euo pipefail
  source "$ROOT/shells/safe-chain-release.sh"
  if [[ "$APPLY" == 0 ]]; then
    log "Safe Chain $SAFE_CHAIN_RELEASE: 公式インストーラーを取得し、SHA-256照合後にshで実行"
    log '配置先: ~/.safe-chain / シェル設定は変更前にバックアップ（リンク先は変更しません）'
    exit 0
  fi

  if [[ -x "$HOME/.safe-chain/bin/safe-chain" ]] &&
    [[ "$("$HOME/.safe-chain/bin/safe-chain" --version)" == "Current safe-chain version: $SAFE_CHAIN_RELEASE" ]]; then
    log "Safe Chain $SAFE_CHAIN_RELEASE は導入済みです。npm safe-chain-verify で有効化を確認してください。"
    exit 0
  fi

  tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/safe-chain.XXXXXX")
  trap 'rm -rf -- "$tmp_dir"' EXIT
  installer="$tmp_dir/install-safe-chain.sh"
  curl -fsSL "https://github.com/AikidoSec/safe-chain/releases/download/${SAFE_CHAIN_RELEASE}/install-safe-chain.sh" -o "$installer"
  printf '%s  %s\n' "$SAFE_CHAIN_INSTALLER_SHA256" "$installer" | sha256sum -c -

  # 上流setupが使うパスを各シェルに問い合わせ、変更対象を先に保護する。
  profiles=("$HOME/.bashrc")
  if command -v zsh >/dev/null; then profiles+=("$(zsh -c 'echo ${ZDOTDIR:-$HOME}/.zshrc')"); fi
  if command -v fish >/dev/null; then profiles+=("$(fish -c 'echo ~/.config/fish/config.fish')"); fi
  if command -v pwsh >/dev/null; then profiles+=("$(pwsh -NoProfile -Command 'echo $PROFILE')"); fi
  /usr/bin/python3 "$ROOT/scripts/safe_chain_profiles.py" "$BACKUP_DIR/safe-chain" "${profiles[@]}"

  # 環境変数による旧方式のバージョン上書きは、固定URLとハッシュの対応を崩すため使わない。
  unset SAFE_CHAIN_VERSION
  sh "$installer"
  "$HOME/.safe-chain/bin/safe-chain" --version
  log 'Safe Chain: ターミナルを再起動し、npm safe-chain-verify を実行してください。'
)
