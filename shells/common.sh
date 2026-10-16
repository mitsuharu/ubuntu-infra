#!/usr/bin/env bash
log() { printf '%s\n' "$*"; }
die() { printf 'エラー: %s\n' "$*" >&2; exit 1; }
run() {
  printf '+'; printf ' %q' "$@"; printf '\n'
  if [[ "$APPLY" == 1 ]]; then "$@"; fi
}
github_url() {
  local url=${1%/}
  url=${url%.git}
  url=${url/#git@github.com:/https://github.com/}
  printf '%s' "$url"
}
clone_once() {
  local url=$1 dest=$2
  if [[ -d "$dest/.git" ]]; then
    [[ "$(github_url "$(git -C "$dest" remote get-url origin)")" == "$(github_url "$url")" ]] || die "取得元が異なります: $dest"
    log "既存を使用: $dest（自動pullしません）"
  elif [[ -e "$dest" || -L "$dest" ]]; then
    die "既存パスを保護します: $dest"
  else
    run mkdir -p "$(dirname "$dest")"
    run git clone "$url" "$dest"
  fi
}
backup() {
  local file=$1 target
  if [[ -e "$file" || -L "$file" ]]; then
    target="$BACKUP_DIR/${file#"$HOME"/}"
    mkdir -p "$(dirname "$target")"
    cp -a -- "$file" "$target"
  fi
}
write_file() {
  local dest=$1 tmp
  tmp=$(mktemp)
  cat > "$tmp"
  if [[ -f "$dest" ]] && cmp -s "$tmp" "$dest"; then rm -f "$tmp"; return; fi
  backup "$dest"
  mkdir -p "$(dirname "$dest")"
  # リンク先を上書きせず、このパスだけを管理します。
  rm -f -- "$dest"
  install -m 600 "$tmp" "$dest"
  rm -f "$tmp"
}
block() { /usr/bin/python3 "$ROOT/shells/settings.py" block "$1" "$2" "$3" "$BACKUP_DIR"; }
