import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='yarn-switch test ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.shells = self.root / 'checkout with spaces' / 'shells'
        self.shells.mkdir(parents=True)
        shutil.copy(ROOT / 'shells/yarn-switch.sh', self.shells)
        shutil.copy(ROOT / 'shells/common.sh', self.shells)
        shutil.copytree(ROOT / 'scripts', self.shells.parent / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.home = self.root / 'home'
        self.home.mkdir()
        self.downloads = self.root / 'downloads'
        self.downloads.mkdir()
        for name in ['bash', 'dirname', 'mktemp', 'rm', 'mkdir', 'cat', 'chmod', 'grep']:
            (self.bin / name).symlink_to(shutil.which(name))
        # 公式インストーラーと同じく、未追記の場合だけ各シェル設定へ読み込み行を足す。
        self.fixture = self.root / 'installer.sh'
        self.fixture.write_text('''#!/usr/bin/env bash
set -euo pipefail
printf 'executed\\n' >> "$HOME/installer-ran"
if [ "${INSTALLER_FAIL:-0}" = 1 ]; then exit 9; fi
mkdir -p "$HOME/.yarn/switch/bin"
printf 'export PATH="$HOME/.yarn/switch/bin:$PATH"\\n' > "$HOME/.yarn/switch/env"
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
  grep -qs 'yarn/switch/env' "$rc" || printf '# Added by Yarn Switch\\nsource "%s"\\n' "$HOME/.yarn/switch/env" >> "$rc"
done
cat > "$HOME/.yarn/switch/bin/yarn" <<'MOCK'
#!/usr/bin/env bash
printf '6.0.0\\n'
MOCK
chmod +x "$HOME/.yarn/switch/bin/yarn"
''')
        curl = self.bin / 'curl'
        curl.write_text(f'#!{sys.executable}\n' + '''import os, pathlib, shutil, sys
pathlib.Path(os.environ['HOME'], 'download-url').write_text(sys.argv[2])
if os.environ.get('CURL_FAIL') == '1': sys.exit(22)
shutil.copyfile(os.environ['FIXTURE'], sys.argv[4])
''')
        curl.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin),
                        TMPDIR=str(self.downloads), FIXTURE=str(self.fixture))
        self.env.pop('GITHUB_PATH', None)

    def run_installer(self, backup='backups', **env):
        command = ['/bin/bash', '-c', 'set -euo pipefail; ROOT=$1; source "$ROOT/shells/common.sh"; '
                   'APPLY=${TEST_APPLY:-1}; BACKUP_DIR="$HOME/$2"; source "$ROOT/shells/yarn-switch.sh"',
                   '_', str(self.shells.parent), backup]
        result = subprocess.run(command, env=dict(self.env, **env), cwd=self.root,
                                capture_output=True, text=True)
        self.assertEqual(list(self.downloads.glob('yarn-switch.*')), [], result.stderr)
        return result

    def test_official_installer_is_downloaded_and_executed_with_backup(self):
        (self.home / '.bashrc').write_text('export KEEP=yes\n')
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('6.0.0', result.stdout)
        self.assertEqual((self.home / 'download-url').read_text(), 'https://repo.yarnpkg.com/install')
        self.assertEqual((self.home / 'backups/yarn-switch/.bashrc').read_text(), 'export KEEP=yes\n')
        self.assertTrue((self.home / '.bashrc').read_text().startswith('export KEEP=yes\n'))
        # 実行前に存在しなかった設定はバックアップしない。
        self.assertFalse((self.home / 'backups/yarn-switch/.zshrc').exists())

    def test_rerun_updates_without_duplicating_shell_settings(self):
        for backup in ['backups/first', 'backups/second']:
            result = self.run_installer(backup=backup)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home / 'installer-ran').read_text(), 'executed\nexecuted\n')
        self.assertEqual((self.home / '.bashrc').read_text().count('yarn/switch/env'), 1)
        self.assertEqual((self.home / 'backups/second/yarn-switch/.zshrc').read_text(),
                         (self.home / '.zshrc').read_text())

    def test_dry_run_has_no_download_or_home_changes(self):
        result = self.run_installer(TEST_APPLY='0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Yarn Switch', result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_symlink_target_is_not_modified(self):
        target = self.home / 'original'
        target.write_text('original\n')
        (self.home / '.bashrc').symlink_to(target)
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(), 'original\n')
        self.assertFalse((self.home / '.bashrc').is_symlink())
        self.assertTrue((self.home / 'backups/yarn-switch/.bashrc').is_symlink())

    def test_profile_outside_home_stops_before_installer(self):
        outside = self.root / 'outside'
        (outside / 'fish').mkdir(parents=True)
        (outside / 'fish/config.fish').write_text('keep\n')
        (self.home / '.config').symlink_to(outside)
        (self.home / '.bashrc').write_text('keep\n')
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse((self.home / 'installer-ran').exists())
        self.assertEqual((self.home / '.bashrc').read_text(), 'keep\n')
        self.assertEqual((outside / 'fish/config.fish').read_text(), 'keep\n')

    def test_download_failure_never_executes_installer(self):
        self.assertNotEqual(self.run_installer(CURL_FAIL='1').returncode, 0)
        self.assertFalse((self.home / 'installer-ran').exists())

    def test_installer_failure_is_propagated(self):
        self.assertEqual(self.run_installer(INSTALLER_FAIL='1').returncode, 9)


class ShellSettingsTests(unittest.TestCase):
    def test_yarn_switch_precedes_nodenv_yarn(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / '.yarn/switch/bin').mkdir(parents=True)
            # anyenvの初期化を模擬し、nodenv配下のyarnが先にPATHへ入る状況を作る。
            anyenv = home / '.anyenv/bin/anyenv'
            anyenv.parent.mkdir(parents=True)
            anyenv.write_text('#!/bin/sh\necho \'export PATH="$HOME/.anyenv/envs/nodenv/shims:$PATH"\'\n')
            anyenv.chmod(0o755)
            for shell in ['bash', 'zsh']:
                if shutil.which(shell) is None:
                    continue
                with self.subTest(shell=shell):
                    result = subprocess.run([shell, '-c', '. "$1"; printf %s "$PATH"', '_',
                                             str(ROOT / 'dotfiles/shell.sh')],
                                            env=dict(os.environ, HOME=str(home), PATH='/usr/bin:/bin'),
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    entries = result.stdout.split(':')
                    self.assertEqual(entries[0], f'{home}/.yarn/switch/bin')
                    self.assertIn(f'{home}/.anyenv/envs/nodenv/shims', entries)

    def test_path_is_unchanged_without_yarn_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(['bash', '-c', '. "$1"; printf %s "$PATH"', '_',
                                     str(ROOT / 'dotfiles/shell.sh')],
                                    env=dict(os.environ, HOME=tmp, PATH='/usr/bin:/bin'),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('.yarn/switch', result.stdout)


class AnyenvTests(unittest.TestCase):
    def test_anyenv_no_longer_enables_corepack(self):
        result = subprocess.run(['bash', str(ROOT / 'install.sh'), '--only', 'anyenv'],
                                env=dict(os.environ, PATH='/usr/bin:/bin'), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('corepack', result.stdout)


if __name__ == '__main__':
    unittest.main()
