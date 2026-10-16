import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('settings', ROOT / 'shells/settings.py')
settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)


class SettingsTests(unittest.TestCase):
    def test_block_preserves_existing_text_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '.bashrc'
            path.write_text('export EXISTING=kept\n')
            backup = Path(tmp) / 'backup'
            settings.managed_block(path, 'test', 'export NEW=yes', backup)
            first = path.read_text()
            settings.managed_block(path, 'test', 'export NEW=yes', backup)
            self.assertEqual(first, path.read_text())
            self.assertTrue(first.startswith('export EXISTING=kept\n'))
            self.assertEqual((backup / '.bashrc').read_text(), 'export EXISTING=kept\n')
            settings.managed_block(path, 'test', 'export NEW=updated', backup)
            self.assertEqual(path.read_text().count('# >>>'), 1)
            self.assertIn('export NEW=updated', path.read_text())

    def test_symlink_target_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, link = Path(tmp) / 'original', Path(tmp) / 'link'
            target.write_text('original\n')
            link.symlink_to(target)
            settings.managed_block(link, 'test', 'new', Path(tmp) / 'backup')
            self.assertEqual(target.read_text(), 'original\n')
            self.assertFalse(link.is_symlink())
            self.assertTrue((Path(tmp) / 'backup/link').is_symlink())

    def test_malformed_block_does_not_change_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'profile'
            original = '# >>> ubuntu-infra:test >>>\nkeep\n'
            path.write_text(original)
            with self.assertRaises(ValueError):
                settings.managed_block(path, 'test', 'new', Path(tmp) / 'backup')
            self.assertEqual(path.read_text(), original)

    def test_caps_preserves_unrelated_options(self):
        value = settings.caps_value("['compose:ralt', 'caps:escape', 'ctrl:nocaps']")
        self.assertEqual(value, "['compose:ralt', 'ctrl:nocaps']")
        self.assertEqual(settings.caps_value(value), value)
        self.assertEqual(settings.caps_value('@as []'), "['ctrl:nocaps']")

    def test_ime_preserves_variant_types(self):
        from gi.repository import GLib
        updated = settings.ime_value("{'OtherBool': <true>, 'OtherInt': <3>, 'Gtk/IMModule': <'ibus'>}")
        result = GLib.Variant.parse(None, updated, None, None)
        self.assertEqual(result.lookup_value('OtherBool', None).get_type_string(), 'b')
        self.assertEqual(result.lookup_value('OtherInt', None).get_type_string(), 'i')
        self.assertEqual(result.unpack()['Gtk/IMModule'], 'fcitx')


class EntrypointTests(unittest.TestCase):
    def test_dry_run_never_runs_sudo_or_creates_home_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home'
            home.mkdir()
            mock_bin = Path(tmp) / 'bin'
            mock_bin.mkdir()
            sudo = mock_bin / 'sudo'
            sudo.write_text('#!/bin/sh\necho unexpected-sudo >&2\nexit 99\n')
            sudo.chmod(0o755)
            env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'),
                       XDG_STATE_HOME=str(home / '.local/state'), PATH=f'{mock_bin}:/usr/bin:/bin')
            result = subprocess.run(['bash', str(ROOT / 'install.sh')], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('apply=0', result.stdout)
            self.assertNotIn('unexpected-sudo', result.stderr)
            self.assertEqual(list(home.iterdir()), [])

    def test_keyring_helper_keeps_existing_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home'
            keyring = home / '.local/share/keyrings/login.keyring'
            keyring.parent.mkdir(parents=True)
            keyring.write_bytes(b'existing encrypted data')
            mock_bin = Path(tmp) / 'bin'
            mock_bin.mkdir()
            for name in ('sudo', 'seahorse'):
                executable = mock_bin / name
                executable.write_text('#!/bin/sh\nexit 0\n')
                executable.chmod(0o755)
            env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'),
                       XDG_STATE_HOME=str(home / '.local/state'), PATH=f'{mock_bin}:/usr/bin:/bin')
            result = subprocess.run(['bash', str(ROOT / 'install.sh'), '--only',
                                     'chrome-keyring', '--apply'], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(keyring.read_bytes(), b'existing encrypted data')
            self.assertNotIn('existing encrypted data', result.stdout + result.stderr)
            self.assertFalse(any((home / '.local/state').rglob('*.keyring')))

    def test_clone_accepts_equivalent_github_origins_without_modification(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            for origin in ('https://github.com/anyenv/anyenv',
                           'https://github.com/anyenv/anyenv.git',
                           'git@github.com:anyenv/anyenv.git'):
                subprocess.run(['git', '-C', str(repo), 'config', 'remote.origin.url', origin], check=True)
                result = subprocess.run(['bash', '-c',
                    'source "$1"; APPLY=1; clone_once https://github.com/anyenv/anyenv.git "$2"',
                    '_', str(ROOT / 'shells/common.sh'), str(repo)], text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('既存を使用', result.stdout)
            subprocess.run(['git', '-C', str(repo), 'config', 'remote.origin.url',
                            'https://github.com/other/repository.git'], check=True)
            result = subprocess.run(['bash', '-c',
                'source "$1"; APPLY=1; clone_once https://github.com/anyenv/anyenv.git "$2"',
                '_', str(ROOT / 'shells/common.sh'), str(repo)], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('取得元が異なります', result.stderr)

    def test_unknown_module_fails_before_mutation(self):
        result = subprocess.run(['bash', str(ROOT / 'install.sh'), '--apply', '--only', 'typo'],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('不明なモジュール', result.stderr)

    def test_dotfiles_apply_is_safe_to_repeat(self):
        with tempfile.TemporaryDirectory(prefix='ubuntu infra ') as tmp:
            home = Path(tmp)
            (home / '.bashrc').write_text('export KEEP=yes\n')
            env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / 'config space'),
                       XDG_STATE_HOME=str(home / 'state'), PATH='/usr/bin:/bin')
            command = ['bash', str(ROOT / 'install.sh'), '--only', 'dotfiles', '--apply']
            for _ in range(2):
                result = subprocess.run(command, env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            text = (home / '.bashrc').read_text()
            self.assertTrue(text.startswith('export KEEP=yes\n'))
            self.assertEqual(text.count('# >>>'), 1)
            self.assertEqual(len(list((home / 'state/ubuntu-infra/backups').rglob('.bashrc'))), 1)
            subprocess.run(['bash', '-n', str(home / '.bashrc')], check=True)


if __name__ == '__main__':
    unittest.main()
