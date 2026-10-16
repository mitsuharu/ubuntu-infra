#!/usr/bin/env bash
clone_once https://github.com/anyenv/anyenv.git "$ANYENV_ROOT"
clone_once https://github.com/anyenv/anyenv-install.git "$ANYENV_DEFINITION_ROOT"
clone_once https://github.com/znz/anyenv-update.git "$ANYENV_ROOT/plugins/anyenv-update"
for manager in rbenv nodenv; do
  if [[ ! -d "$ANYENV_ROOT/envs/$manager" ]]; then
    [[ ! -e "$ANYENV_ROOT/envs/$manager" ]] || die "既存ファイル: $manager"
    run "$ANYENV_ROOT/bin/anyenv" install "$manager"
  fi
done
if [[ "$APPLY" == 1 ]]; then
  [[ -x "$RBENV_ROOT/bin/rbenv" && -x "$NODENV_ROOT/bin/nodenv" ]] || die 'anyenv配下のrbenv/nodenvが不完全です'
  backup "$RBENV_ROOT/version"
  backup "$NODENV_ROOT/version"
fi
run "$RBENV_ROOT/bin/rbenv" install -s "$RUBY_VERSION"
run "$RBENV_ROOT/bin/rbenv" global "$RUBY_VERSION"
run "$RBENV_ROOT/bin/rbenv" rehash
run "$NODENV_ROOT/bin/nodenv" install -s "$NODE_VERSION"
run "$NODENV_ROOT/bin/nodenv" global "$NODE_VERSION"
run "$NODENV_ROOT/bin/nodenv" rehash
clone_once https://github.com/tpope/rbenv-aliases.git "$RBENV_ROOT/plugins/rbenv-aliases"
clone_once https://github.com/nodenv/nodenv-aliases.git "$NODENV_ROOT/plugins/nodenv-aliases"
run "$RBENV_ROOT/bin/rbenv" alias --auto
run "$NODENV_ROOT/bin/nodenv" alias --auto
run "$NODENV_ROOT/bin/nodenv" exec corepack enable
run "$NODENV_ROOT/bin/nodenv" rehash
run "$RBENV_ROOT/bin/rbenv" exec ruby --version
run "$NODENV_ROOT/bin/nodenv" exec node --version
