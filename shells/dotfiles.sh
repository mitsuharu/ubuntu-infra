#!/usr/bin/env bash
if [[ "$APPLY" == 0 ]]; then
  log '共通シェル設定を ~/.bashrc / ~/.zshrc から読み込み（既存設定を保持）'
else
  write_file "$CONFIG_HOME/ubuntu-infra/shell.sh" < "$ROOT/dotfiles/shell.sh"
  # printf %qで空白を含むXDG_CONFIG_HOMEにも対応します。
  printf -v shell_load '[ -r %q ] && . %q' "$CONFIG_HOME/ubuntu-infra/shell.sh" "$CONFIG_HOME/ubuntu-infra/shell.sh"
  block "$HOME/.bashrc" shell "$shell_load"
  block "$HOME/.zshrc" shell "$shell_load"
fi
