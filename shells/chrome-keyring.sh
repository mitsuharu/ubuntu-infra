#!/usr/bin/env bash
run sudo apt-get update
run sudo apt-get install -y seahorse gnome-keyring libpam-gnome-keyring
log '自動ログイン用: 「パスワードと鍵」で「ログイン」を右クリック → パスワードの変更'
log '現在のパスワードを入力 → 新しいパスワードと確認欄を空のまま続行 → 警告を確認'
log '空パスワードにすると、このキーリング内の秘密情報はパスワードで暗号化されません。'
log 'login.keyringの削除、Chromeの--password-store=basic設定は行いません。'
if [[ "$APPLY" == 1 ]]; then
  # 変更はSecret Serviceの画面で行い、スクリプトにはパスワードを渡しません。
  # 暗号化キーを含む可能性があるため、通常の設定バックアップにも秘密情報をコピーしません。
  if [[ -n ${DISPLAY:-}${WAYLAND_DISPLAY:-} ]]; then
    seahorse >/dev/null 2>&1 &
  else
    log 'GUIセッションで seahorse を実行し、docs/chrome-keyring.mdの手順に従ってください。'
  fi
fi
