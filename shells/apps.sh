#!/usr/bin/env bash
install_deb() {
  local package=$1 url=$2 dir
  if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -qx 'install ok installed'; then
    log "導入済み: $package（更新はaptで実行）"; return
  fi
  if [[ "$APPLY" == 0 ]]; then log "公式debを取得してaptで導入: $package / $url"; return; fi
  dir=$(mktemp -d)
  curl --proto '=https' --tlsv1.2 -fL --retry 3 "$url" -o "$dir/package.deb"
  [[ $(dpkg-deb -f "$dir/package.deb" Package) == "$package" ]] || die 'debパッケージ名が想定と異なります'
  [[ $(dpkg-deb -f "$dir/package.deb" Architecture) == amd64 ]] || die 'debアーキテクチャが異なります'
  # aptの_sandboxユーザーから読み取れる一時ディレクトリにします。
  chmod 755 "$dir"
  chmod 644 "$dir/package.deb"
  if [[ "$package" == code ]]; then
    printf 'code code/add-microsoft-repo boolean true\n' | sudo debconf-set-selections
  fi
  sudo apt-get install -y "$dir/package.deb"
  rm -rf -- "$dir"
}
install_claude_desktop() {
  local keyring=/usr/share/keyrings/claude-desktop-archive-keyring.asc
  local list=/etc/apt/sources.list.d/claude-desktop.list
  local fingerprint=31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE
  local repo="deb [arch=amd64,arm64 signed-by=$keyring] https://downloads.claude.ai/claude-desktop/apt/stable stable main"
  local dir actual
  if dpkg-query -W -f='${Status}' claude-desktop 2>/dev/null | grep -qx 'install ok installed'; then
    log '導入済み: claude-desktop（更新はaptで実行）'; return
  fi
  if [[ "$APPLY" == 0 ]]; then
    log "Claude Desktop: 署名キーのフィンガープリントを照合し、aptリポジトリを登録してaptで導入 / $list"
    return
  fi
  dir=$(mktemp -d)
  curl --proto '=https' --tlsv1.2 -fL --retry 3 https://downloads.claude.ai/claude-desktop/key.asc -o "$dir/key.asc"
  # 公式手順では照合は任意ですが、apt全体が信頼するキーになるため登録前に必ず確認します。
  actual=$(gpg --show-keys --with-colons "$dir/key.asc" | awk -F: '$1 == "fpr" { print $10; exit }')
  [[ "$actual" == "$fingerprint" ]] || die "Claude Desktopの署名キーが想定と異なります: ${actual:-不明}"
  printf '%s\n' "$repo" > "$dir/claude-desktop.list"
  # umask 077のままsudo teeで書くと一般ユーザーから読めないため、モードを明示して配置します。
  sudo install -m 644 "$dir/key.asc" "$keyring"
  sudo install -m 644 "$dir/claude-desktop.list" "$list"
  rm -rf -- "$dir"
  sudo apt-get update
  sudo apt-get install -y claude-desktop
}
run sudo apt-get update
run sudo apt-get install -y curl ca-certificates gnupg
[[ "$INSTALL_CHROME" != 1 ]] || install_deb google-chrome-stable https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
[[ "$INSTALL_VSCODE" != 1 ]] || install_deb code https://update.code.visualstudio.com/latest/linux-deb-x64/stable
[[ "$INSTALL_1PASSWORD" != 1 ]] || install_deb 1password https://downloads.1password.com/linux/debian/amd64/stable/1password-latest.deb
[[ "$INSTALL_CHATGPT" != 1 ]] || install_deb chatgpt https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb
[[ "$INSTALL_CLAUDE_DESKTOP" != 1 ]] || install_claude_desktop
