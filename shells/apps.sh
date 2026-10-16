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
run sudo apt-get update
run sudo apt-get install -y curl ca-certificates
[[ "$INSTALL_CHROME" != 1 ]] || install_deb google-chrome-stable https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
[[ "$INSTALL_VSCODE" != 1 ]] || install_deb code https://update.code.visualstudio.com/latest/linux-deb-x64/stable
[[ "$INSTALL_1PASSWORD" != 1 ]] || install_deb 1password https://downloads.1password.com/linux/debian/amd64/stable/1password-latest.deb
[[ "$INSTALL_CHATGPT" != 1 ]] || install_deb chatgpt https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb
if [[ "$INSTALL_CLAUDE" == 1 ]]; then
  if command -v claude >/dev/null; then
    log 'Claude Code導入済み（更新はclaude update）'
  elif [[ "$APPLY" == 0 ]]; then
    log 'Claude Code: https://claude.ai/install.sh を取得後、ユーザー権限でbash実行'
  else
    claude_installer=$(mktemp)
    curl --proto '=https' --tlsv1.2 -fL --retry 3 https://claude.ai/install.sh -o "$claude_installer"
    bash "$claude_installer" stable
    rm -f "$claude_installer"
  fi
fi
