# Bash / Zsh 共通。システムPATHは保持します。
export PATH="$HOME/.local/bin:$PATH"
export ANYENV_ROOT="$HOME/.anyenv"
if [ -x "$ANYENV_ROOT/bin/anyenv" ]; then
  export PATH="$ANYENV_ROOT/bin:$PATH"
  if [ -n "${ZSH_VERSION:-}" ]; then
    eval "$(anyenv init - zsh)"
  elif [ -n "${BASH_VERSION:-}" ]; then
    eval "$(anyenv init - bash)"
  fi
fi
# 公式インストーラーが追記する読み込み行だけに頼らない。追記位置によってはnodenv配下に残るcorepack由来のyarnが優先されるため、anyenvの後で先頭に追加する。
if [ -d "$HOME/.yarn/switch/bin" ]; then
  export PATH="$HOME/.yarn/switch/bin:$PATH"
fi
if [ -t 0 ]; then export GPG_TTY="$(tty)"; fi
if [ -d "$HOME/Android/Sdk" ]; then
  export ANDROID_HOME="$HOME/Android/Sdk"
  export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
fi
if [ -d "$HOME/development/flutter/bin" ]; then
  export PATH="$HOME/development/flutter/bin:$PATH"
fi
alias relogin='exec "$SHELL" -l'
alias ls='ls --color=auto -F'
alias la='ls --color=auto -FA'
alias ll='ls --color=auto -l'
alias ys='yarn start'
alias ya='yarn android'
