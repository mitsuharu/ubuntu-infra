import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_FINGERPRINT = '31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE'

# apps.shのClaude Desktop部分だけを動かすため、ほかのアプリは無効にして読み込みます。
APPS_SNIPPET = '''
set -euo pipefail
umask 077
ROOT=$1
APPLY=$2
source "$ROOT/shells/common.sh"
INSTALL_CHROME=0 INSTALL_VSCODE=0 INSTALL_1PASSWORD=0 INSTALL_CHATGPT=0 INSTALL_CLAUDE=0
INSTALL_CLAUDE_DESKTOP=1
source "$ROOT/shells/apps.sh"
'''


class ClaudeDesktopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self.sudo_log = tmp / 'sudo.log'
        self.placed = tmp / 'placed'
        self.placed.mkdir()
        self.mock_bin = tmp / 'bin'
        self.mock_bin.mkdir()
        # sudoは実行せず記録だけし、installの配置内容とモードは検証用ディレクトリへ写します。
        self.write_exec('sudo', f'''#!/bin/sh
printf '%s\\n' "$*" >> {shlex.quote(str(self.sudo_log))}
if [ "$1" = install ]; then
  eval "last=\\${{$#}}"
  cp "$4" {shlex.quote(str(self.placed))}/"$(basename "$last")"
  printf '%s %s\\n' "$3" "$(basename "$last")" >> {shlex.quote(str(self.placed))}/modes
fi
''')
        self.write_exec('curl', '''#!/bin/sh
while [ $# -gt 0 ]; do
  if [ "$1" = -o ]; then echo 'dummy key' > "$2"; fi
  shift
done
''')
        self.set_fingerprint(OFFICIAL_FINGERPRINT)
        self.set_installed(False)
        self.env = dict(os.environ, HOME=str(tmp / 'home'), PATH=f'{self.mock_bin}:/usr/bin:/bin')

    def tearDown(self):
        self.tmp.cleanup()

    def write_exec(self, name, text):
        path = self.mock_bin / name
        path.write_text(text)
        path.chmod(0o755)

    def set_fingerprint(self, fingerprint):
        # 主キーのfprの後にサブキーのfprが続く、gpg --with-colonsの出力を模します。
        self.write_exec('gpg', f'''#!/bin/sh
echo 'pub:-:4096:1:BAA929FF1A7ECACE:1700000000:::-:::scSC::::::23::0:'
echo 'fpr:::::::::{fingerprint}:'
echo 'fpr:::::::::0000000000000000000000000000000000000000:'
''')

    def set_installed(self, installed):
        status = 'install ok installed' if installed else 'unknown ok not-installed'
        self.write_exec('dpkg-query', f"#!/bin/sh\nprintf '%s' '{status}'\n")

    def run_apps(self, apply):
        return subprocess.run(['bash', '-c', APPS_SNIPPET, '_', str(ROOT), '1' if apply else '0'],
                              env=self.env, text=True, capture_output=True)

    def sudo_commands(self):
        return self.sudo_log.read_text().splitlines() if self.sudo_log.exists() else []

    def test_dry_run_only_reports_plan(self):
        result = self.run_apps(apply=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Claude Desktop:', result.stdout)
        self.assertEqual(self.sudo_commands(), [])

    def test_apply_registers_official_repository_and_installs_package(self):
        result = self.run_apps(apply=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.placed / 'claude-desktop.list').read_text(),
                         'deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/claude-desktop-archive-keyring.asc] '
                         'https://downloads.claude.ai/claude-desktop/apt/stable stable main\n')
        self.assertEqual((self.placed / 'modes').read_text().splitlines(),
                         ['644 claude-desktop-archive-keyring.asc', '644 claude-desktop.list'])
        commands = self.sudo_commands()
        self.assertIn('apt-get install -y claude-desktop', commands)
        # リポジトリ登録後のapt-get updateを経てから導入します。
        self.assertLess(max(i for i, c in enumerate(commands) if c.startswith('install ')),
                        len(commands) - 1 - commands[::-1].index('apt-get update'))

    def test_wrong_fingerprint_stops_before_trusting_key(self):
        self.set_fingerprint('0123456789ABCDEF0123456789ABCDEF01234567')
        result = self.run_apps(apply=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('署名キーが想定と異なります', result.stderr)
        self.assertFalse(any(c.startswith('install ') or 'claude-desktop' in c for c in self.sudo_commands()))

    def test_subkey_fingerprint_is_not_accepted_as_primary(self):
        self.write_exec('gpg', f'''#!/bin/sh
echo 'fpr:::::::::0123456789ABCDEF0123456789ABCDEF01234567:'
echo 'fpr:::::::::{OFFICIAL_FINGERPRINT}:'
''')
        result = self.run_apps(apply=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('apt-get install -y claude-desktop', self.sudo_commands())

    def test_installed_package_is_left_to_apt_updates(self):
        self.set_installed(True)
        result = self.run_apps(apply=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('導入済み: claude-desktop', result.stdout)
        self.assertFalse(any(c.startswith('install ') or 'claude-desktop' in c for c in self.sudo_commands()))


if __name__ == '__main__':
    unittest.main()
