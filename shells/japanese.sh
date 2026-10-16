#!/usr/bin/env bash
run sudo apt-get update
run sudo apt-get install -y fcitx5 fcitx5-mozc fcitx5-config-qt \
  fcitx5-frontend-gtk3 fcitx5-frontend-gtk4 fcitx5-frontend-qt5 fcitx5-frontend-qt6 \
  im-config python3-gi language-pack-ja fonts-noto-cjk
if [[ "$APPLY" == 0 ]]; then
  log "fcitx5: keyboard-$KEYBOARD_LAYOUT → mozc、ユーザー設定と自動起動（バックアップ付き）"
else
  # 稼働中のfcitx5が終了時にprofileを上書きしないよう、手動終了を要求します。
  if pgrep -u "$(id -u)" -x fcitx5 >/dev/null; then
    die 'fcitx5をトレイから終了してから --only japanese --apply を再実行してください（設定保存の競合回避）'
  fi
  backup "$HOME/.xinputrc"
  im-config -n fcitx5
  write_file "$CONFIG_HOME/fcitx5/profile" <<PROFILE
[Groups/0]
Name=Default
Default Layout=$KEYBOARD_LAYOUT
DefaultIM=mozc

[Groups/0/Items/0]
Name=keyboard-$KEYBOARD_LAYOUT
Layout=

[Groups/0/Items/1]
Name=mozc
Layout=

[GroupOrder]
0=Default
PROFILE
  block "$HOME/.profile" fcitx 'export XMODIFIERS=@im=fcitx
export QT_IM_MODULE=fcitx
# GNOME上のX11/Waylandの両方でim moduleを利用します。
export GTK_IM_MODULE=fcitx'
  write_file "$CONFIG_HOME/autostart/org.fcitx.Fcitx5.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Fcitx 5
Exec=fcitx5
Terminal=false
X-GNOME-Autostart-enabled=true
DESKTOP
  /usr/bin/python3 "$ROOT/shells/settings.py" gnome-ime "$BACKUP_DIR"
fi
