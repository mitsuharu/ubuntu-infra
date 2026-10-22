#!/usr/bin/env python3
"""公式インストーラーが変更するシェル設定を事前に保護する。"""
from pathlib import Path
import shutil
import sys


def prepare_profiles(paths, backup_dir):
    home = Path.home()
    profiles = list(dict.fromkeys(Path(path) for path in paths))
    # 一つでも保護できないパスがあれば、他のファイルを変更する前に停止する。
    for path in profiles:
        if path == home or not path.is_absolute() or not path.is_relative_to(home) or '..' in path.parts:
            raise ValueError(f'ホーム外のシェル設定は自動変更しません: {path}')
        destination = Path(backup_dir) / path.relative_to(home)
        if destination.exists() or destination.is_symlink():
            raise ValueError(f'バックアップが既に存在します: {destination}')
        parent = path.parent
        while parent != home:
            if parent.is_symlink():
                raise ValueError(f'設定の親ディレクトリがシンボリックリンクです: {parent}')
            parent = parent.parent
        if (path.exists() or path.is_symlink()) and not path.is_file():
            raise ValueError(f'通常ファイルとして読めないシェル設定です: {path}')

    for path in profiles:
        if not path.exists():
            continue
        destination = Path(backup_dir) / path.relative_to(home)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # 同じ適用で先に保存されたバックアップを上書きしない。
        shutil.copy2(path, destination, follow_symlinks=False)
        if path.is_symlink():
            content = path.read_bytes()
            path.unlink()
            path.write_bytes(content)
            path.chmod(0o600)


if __name__ == '__main__':
    prepare_profiles(sys.argv[2:], sys.argv[1])
