#!/usr/bin/env python3
"""既存設定を保持し、変更前の値をバックアップします。"""
import ast
from pathlib import Path
import shutil
import subprocess
import sys


def save(path, content, backup_dir):
    path = Path(path)
    if path.is_file() and path.read_text() == content:
        return
    if path.exists() or path.is_symlink():
        relative = path.relative_to(Path.home()) if path.is_relative_to(Path.home()) else Path(path.name)
        target = Path(backup_dir) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target, follow_symlinks=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    # シンボリックリンクの参照先を変更しません。
    if path.is_symlink():
        path.unlink()
    path.write_text(content)
    path.chmod(0o600)


def managed_block(path, name, content, backup_dir):
    path = Path(path)
    before = path.read_text() if path.exists() else ''
    start, end = f'# >>> ubuntu-infra:{name} >>>', f'# <<< ubuntu-infra:{name} <<<'
    lines = before.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip('\n') == start]
    ends = [i for i, line in enumerate(lines) if line.rstrip('\n') == end]
    replacement = f'{start}\n{content}\n{end}\n'
    if not starts and not ends:
        after = before + ('' if not before or before.endswith('\n') else '\n') + replacement
    elif len(starts) == len(ends) == 1 and starts[0] < ends[0]:
        after = ''.join(lines[:starts[0]]) + replacement + ''.join(lines[ends[0] + 1:])
    else:
        raise ValueError(f'管理ブロックが壊れています: {path}')
    save(path, after, backup_dir)


def gsettings_change(schema, key, transform, backup_dir):
    before = subprocess.check_output(['gsettings', 'get', schema, key], text=True).strip()
    after = transform(before)
    if before == after:
        return
    # resetでは他の設定も失うため、元の値を復元用ファイルに保存します。
    dest = Path(backup_dir) / 'gsettings' / f'{schema}.{key}.txt'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(before + '\n')
    subprocess.run(['gsettings', 'set', schema, key, after], check=True)


def caps_value(before):
    if before.startswith('@as '):
        before = before[4:]
    options = ast.literal_eval(before)
    # Capsに関する競合だけ除き、他のキー設定は残します。
    options = [s for s in options if not s.startswith('caps:') and s != 'ctrl:nocaps']
    return repr(options + ['ctrl:nocaps'])


def ime_value(before):
    # GVariantの値はPython辞書ではないため、GLibで解釈します。
    from gi.repository import GLib
    parsed = GLib.Variant.parse(None, before, None, None)
    values = {}
    for i in range(parsed.n_children()):
        item = parsed.get_child_value(i)
        values[item.get_child_value(0).get_string()] = item.get_child_value(1).get_variant()
    values['Gtk/IMModule'] = GLib.Variant('s', 'fcitx')
    return GLib.Variant('a{sv}', values).print_(True)


def main():
    command, *args = sys.argv[1:]
    if command == 'block':
        managed_block(*args)
    elif command == 'caps':
        gsettings_change('org.gnome.desktop.input-sources', 'xkb-options', caps_value, args[0])
    elif command == 'gnome-ime':
        gsettings_change('org.gnome.settings-daemon.plugins.xsettings', 'overrides', ime_value, args[0])
    else:
        raise ValueError(f'不明な操作: {command}')


if __name__ == '__main__':
    main()
