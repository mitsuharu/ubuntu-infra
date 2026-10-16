#!/usr/bin/env bash
if [[ "$APPLY" == 0 ]]; then
  log 'Caps Lock→Ctrl（他のXKB設定を保持）、XDGフォルダ参照を英語化（ファイルは移動・削除しません）'
else
  /usr/bin/python3 "$ROOT/shells/settings.py" caps "$BACKUP_DIR"
  backup "$CONFIG_HOME/user-dirs.dirs"
  backup "$CONFIG_HOME/user-dirs.locale"
  command -v xdg-user-dirs-update >/dev/null || die '先に --only base --apply を実行してください'
  LANG=C xdg-user-dirs-update --force
  log '古い日本語名フォルダの内容は残しています。必要なファイルを手動で英語名側へ移してください。'
fi
