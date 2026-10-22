import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/release.yml'


def step_script(name):
    lines = WORKFLOW.read_text(encoding='utf-8').splitlines()
    start = lines.index(f'      - name: {name}')
    run = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == 'run: |')
    body = []
    for line in lines[run + 1:]:
        if line.strip() and not line.startswith(' ' * 10):
            break
        body.append(line[10:])
    return '\n'.join(body) + '\n'


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.github_env = self.dir / 'github_env'
        self.summary = self.dir / 'summary'
        self.gh_log = self.dir / 'gh.log'
        self.github_env.touch()
        self.summary.touch()

    def tearDown(self):
        self.tmp.cleanup()

    def validate(self, event, ref_name='', ref='', version=''):
        env = {
            'PATH': os.environ['PATH'],
            'EVENT_NAME': event,
            'REF_NAME': ref_name,
            'REF': ref,
            'REQUESTED_VERSION': version,
            'GITHUB_ENV': str(self.github_env),
        }
        return subprocess.run(['bash', '-c', step_script('リリースタグを検証')],
                              env=env, capture_output=True, text=True)

    def publish(self, event, existing=False):
        bin_dir = self.dir / 'bin'
        bin_dir.mkdir()
        fake_gh = bin_dir / 'gh'
        fake_gh.write_text(
            '#!/bin/bash\n'
            'echo "$*" >> "$GH_LOG"\n'
            'if [[ "$1 $2" == "release view" && "$3" == "$TAG" && $# -eq 3 ]]; then\n'
            '  [[ "$EXISTING" == 1 ]]; exit\n'
            'fi\n'
            'if [[ "$1 $2" == "release view" ]]; then echo "https://example.invalid/r/$TAG"; fi\n',
            encoding='utf-8')
        fake_gh.chmod(0o755)
        env = {
            'PATH': f'{bin_dir}:{os.environ["PATH"]}',
            'TAG': '1.2.3',
            'EVENT_NAME': event,
            'GITHUB_SHA': 'a' * 40,
            'GITHUB_STEP_SUMMARY': str(self.summary),
            'GH_LOG': str(self.gh_log),
            'EXISTING': '1' if existing else '0',
        }
        result = subprocess.run(['bash', '-c', step_script('GitHub Releaseを作成')],
                                env=env, capture_output=True, text=True)
        calls = self.gh_log.read_text(encoding='utf-8').splitlines()
        return result, calls

    def test_tag_push_accepts_semver_tag(self):
        result = self.validate('push', ref_name='1.2.3', ref='refs/tags/1.2.3')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.github_env.read_text(encoding='utf-8'), 'TAG=1.2.3\n')

    def test_rejects_tags_other_than_major_minor_patch(self):
        for tag in ['1.2', '1.2.3.4', '1.2.3-rc1', '01a.2.3', 'v1.2.3', '']:
            with self.subTest(tag=tag):
                result = self.validate('push', ref_name=tag, ref=f'refs/tags/{tag}')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('1.2.3形式', result.stdout)
        self.assertEqual(self.github_env.read_text(encoding='utf-8'), '')

    def test_manual_run_uses_input_version_only_on_master(self):
        result = self.validate('workflow_dispatch', ref_name='master',
                               ref='refs/heads/master', version='2.0.0')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.github_env.read_text(encoding='utf-8'), 'TAG=2.0.0\n')

    def test_manual_run_rejects_other_branches(self):
        result = self.validate('workflow_dispatch', ref_name='feature/x',
                               ref='refs/heads/feature/x', version='2.0.0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('masterブランチ', result.stdout)
        self.assertEqual(self.github_env.read_text(encoding='utf-8'), '')

    def test_tag_push_publishes_only_the_pushed_tag(self):
        result, calls = self.publish('push')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = [c for c in calls if c.startswith('release create')]
        self.assertEqual(len(create), 1)
        self.assertIn('--verify-tag', create[0])
        self.assertNotIn('--target', create[0])
        self.assertIn('https://example.invalid/r/1.2.3', self.summary.read_text(encoding='utf-8'))

    def test_manual_run_creates_tag_on_triggering_commit(self):
        result, calls = self.publish('workflow_dispatch')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = [c for c in calls if c.startswith('release create')]
        self.assertEqual(len(create), 1)
        self.assertIn(f'--target {"a" * 40}', create[0])
        self.assertNotIn('--verify-tag', create[0])

    def test_existing_release_is_not_overwritten(self):
        result, calls = self.publish('push', existing=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('既に存在します', result.stdout)
        self.assertFalse([c for c in calls if c.startswith('release create')])

    def test_actions_are_pinned_by_full_sha_with_version_comment(self):
        uses = re.findall(r'uses:\s*(\S+)(.*)', WORKFLOW.read_text(encoding='utf-8'))
        self.assertTrue(uses)
        for action, rest in uses:
            with self.subTest(action=action):
                self.assertRegex(action, r'@[0-9a-f]{40}$')
                self.assertRegex(rest, r'#\s*v\d')

    def test_not_triggered_by_pull_requests(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertNotIn('pull_request', text)
        self.assertIn('cancel-in-progress: false', text)


if __name__ == '__main__':
    unittest.main()
