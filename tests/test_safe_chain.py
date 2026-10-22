import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('update_safe_chain', ROOT / 'scripts/update_safe_chain.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


def readme(version, digest):
    return f'''### Unix/Linux/macOS

```shell
curl -fsSL https://github.com/AikidoSec/safe-chain/releases/download/{version}/install-safe-chain.sh -o /tmp/install-safe-chain.sh \\
  && echo "{digest}  /tmp/install-safe-chain.sh" | sha256sum -c - \\
  && sh /tmp/install-safe-chain.sh \\
  && rm /tmp/install-safe-chain.sh
```
'''


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.destination = Path(self.tmp.name) / 'release.sh'
        self.destination.write_text('既存の設定\n')
        self.installer = b'#!/bin/sh\nexit 0\n'
        self.digest = hashlib.sha256(self.installer).hexdigest()
        self.readme = readme('1.2.3', self.digest)
        self.release = {'tag_name': '1.2.3', 'draft': False, 'prerelease': False}

    def update(self, **kwargs):
        arguments = dict(readme=self.readme, release=self.release,
                         download=lambda url: self.installer, destination=self.destination)
        arguments.update(kwargs)
        return updater.update(**arguments)

    def test_updates_only_after_verification_and_is_idempotent(self):
        urls = []

        def download(url):
            urls.append(url)
            return self.installer

        self.assertTrue(self.update(download=download))
        self.assertEqual(urls, ['https://github.com/AikidoSec/safe-chain/releases/download/1.2.3/install-safe-chain.sh'])
        self.assertIn('SAFE_CHAIN_RELEASE="1.2.3"', self.destination.read_text())
        self.assertIn(self.digest, self.destination.read_text())
        self.assertFalse(self.update())

    def test_rejects_changed_instructions_without_touching_configuration(self):
        for changed in [self.readme.replace('sha256sum -c -', 'true'),
                        self.readme.replace('&& sh /tmp/', '&& bash /tmp/'),
                        self.readme.replace('&& rm', '&& unexpected-command && rm'),
                        self.readme.replace('1.2.3', '$(command)'),
                        self.readme.replace('### Unix/Linux/macOS', '### Changed')]:
            with self.subTest(readme=changed):
                with self.assertRaises(ValueError):
                    self.update(readme=changed)
                self.assertEqual(self.destination.read_text(), '既存の設定\n')

    def test_rejects_checksum_mismatch(self):
        with self.assertRaises(ValueError):
            self.update(download=lambda url: b'tampered')
        self.assertEqual(self.destination.read_text(), '既存の設定\n')

    def test_rejects_release_mismatch_or_prerelease(self):
        for release in [{'tag_name': '1.2.4'}, {'tag_name': '1.2.3', 'draft': True},
                        {'tag_name': '1.2.3', 'prerelease': True}]:
            with self.subTest(release=release), self.assertRaises(ValueError):
                self.update(release=release)
        self.assertEqual(self.destination.read_text(), '既存の設定\n')

    def test_download_failure_preserves_configuration(self):
        def fail(url):
            raise OSError('download failed')
        with self.assertRaises(OSError):
            self.update(download=fail)
        self.assertEqual(self.destination.read_text(), '既存の設定\n')


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='safe-chain test ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.shells = self.root / 'checkout with spaces' / 'shells'
        self.shells.mkdir(parents=True)
        shutil.copy(ROOT / 'shells/safe-chain.sh', self.shells)
        shutil.copy(ROOT / 'shells/common.sh', self.shells)
        shutil.copytree(ROOT / 'scripts', self.shells.parent / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.home = self.root / 'home'
        self.home.mkdir()
        self.downloads = self.root / 'downloads'
        self.downloads.mkdir()
        for name in ['dirname', 'mktemp', 'rm', 'sh', 'mkdir', 'cat', 'chmod', 'sha256sum']:
            (self.bin / name).symlink_to(shutil.which(name))
        self.fixture = self.root / 'installer.sh'
        self.fixture.write_text('''#!/bin/sh
set -eu
[ -z "${SAFE_CHAIN_VERSION:-}" ]
printf 'mock safe-chain initialization\\n' >> "$HOME/.bashrc"
printf 'executed\\n' >> "$HOME/installer-ran"
if [ "${INSTALLER_FAIL:-0}" = 1 ]; then exit 9; fi
mkdir -p "$HOME/.safe-chain/bin"
cat > "$HOME/.safe-chain/bin/safe-chain" <<'EOF'
#!/bin/sh
printf 'Current safe-chain version: 1.2.3\\n'
EOF
chmod +x "$HOME/.safe-chain/bin/safe-chain"
''')
        curl = self.bin / 'curl'
        curl.write_text(f'#!{sys.executable}\n' + '''import os, pathlib, shutil, sys
pathlib.Path(os.environ['HOME'], 'download-url').write_text(sys.argv[2])
if os.environ.get('CURL_FAIL') == '1': sys.exit(22)
shutil.copyfile(os.environ['FIXTURE'], sys.argv[4])
''')
        curl.chmod(0o755)
        self.digest = hashlib.sha256(self.fixture.read_bytes()).hexdigest()
        self.configure(self.digest)
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin),
                        TMPDIR=str(self.downloads), FIXTURE=str(self.fixture),
                        SAFE_CHAIN_VERSION='unwanted-override')

    def configure(self, digest):
        (self.shells / 'safe-chain-release.sh').write_text(
            f'SAFE_CHAIN_RELEASE="1.2.3"\nSAFE_CHAIN_INSTALLER_SHA256="{digest}"\n')

    def run_installer(self, **env):
        command = ['bash', '-c', 'set -euo pipefail; ROOT=$1; source "$ROOT/shells/common.sh"; '
                   'APPLY=${TEST_APPLY:-1}; BACKUP_DIR="$HOME/backups"; source "$ROOT/shells/safe-chain.sh"',
                   '_', str(self.shells.parent)]
        command[0] = '/bin/bash'
        result = subprocess.run(command,
                                env=dict(self.env, **env), cwd=self.root,
                                capture_output=True, text=True)
        self.assertEqual(list(self.downloads.glob('safe-chain.*')), [], result.stderr)
        return result

    def test_verified_installer_is_idempotent_and_preserves_backup(self):
        (self.home / '.bashrc').write_text('export KEEP=yes\n')
        for _ in range(2):
            result = self.run_installer()
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home / 'installer-ran').read_text(), 'executed\n')
        self.assertEqual((self.home / 'backups/safe-chain/.bashrc').read_text(), 'export KEEP=yes\n')
        self.assertTrue((self.home / '.bashrc').read_text().startswith('export KEEP=yes\n'))
        self.assertEqual((self.home / 'download-url').read_text(),
                         'https://github.com/AikidoSec/safe-chain/releases/download/1.2.3/install-safe-chain.sh')

    def test_dry_run_has_no_download_or_home_changes(self):
        result = self.run_installer(TEST_APPLY='0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SHA-256', result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_symlink_target_is_not_modified(self):
        target = self.home / 'original'
        target.write_text('original\n')
        (self.home / '.bashrc').symlink_to(target)
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(), 'original\n')
        self.assertFalse((self.home / '.bashrc').is_symlink())
        self.assertTrue((self.home / 'backups/safe-chain/.bashrc').is_symlink())

    def test_checksum_mismatch_never_executes_installer(self):
        (self.home / '.bashrc').write_text('keep\n')
        self.configure('0' * 64)
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse((self.home / 'installer-ran').exists())

        self.assertEqual((self.home / '.bashrc').read_text(), 'keep\n')
        self.assertFalse((self.home / 'backups').exists())

    def test_download_failure_never_executes_installer(self):
        self.assertNotEqual(self.run_installer(CURL_FAIL='1').returncode, 0)
        self.assertFalse((self.home / 'installer-ran').exists())

    def test_installer_failure_is_propagated(self):
        self.assertEqual(self.run_installer(INSTALLER_FAIL='1').returncode, 9)


if __name__ == '__main__':
    unittest.main()
