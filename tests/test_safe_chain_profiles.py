import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('safe_chain_profiles', ROOT / 'scripts/safe_chain_profiles.py')
profiles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profiles)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / 'home'
        self.home.mkdir()
        self.backup = self.home / 'backups/safe-chain'
        self.env = mock.patch.dict(os.environ, HOME=str(self.home))
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_regular_profiles_are_backed_up_without_changes(self):
        bash = self.home / '.bashrc'
        bash.write_text('keep\n')
        profiles.prepare_profiles([bash, self.home / '.zshrc'], self.backup)
        self.assertEqual(bash.read_text(), 'keep\n')
        self.assertEqual((self.backup / '.bashrc').read_text(), 'keep\n')
        self.assertFalse((self.home / '.zshrc').exists())

    def test_symlink_is_backed_up_and_replaced_by_independent_copy(self):
        original = self.home / 'original'
        original.write_text('keep\n')
        rc = self.home / '.bashrc'
        rc.symlink_to(original)
        profiles.prepare_profiles([rc, rc], self.backup)
        self.assertTrue((self.backup / '.bashrc').is_symlink())
        self.assertFalse(rc.is_symlink())
        rc.write_text('updated\n')
        self.assertEqual(original.read_text(), 'keep\n')

    def test_invalid_paths_stop_before_any_profile_changes(self):
        original = self.home / 'original'
        original.write_text('keep\n')
        rc = self.home / '.bashrc'
        rc.symlink_to(original)
        broken = self.home / '.zshrc'
        broken.symlink_to(self.home / 'missing')
        for invalid in [self.home, self.home.parent / '.zshrc', self.home / '../outside', broken]:
            with self.subTest(path=invalid), self.assertRaises(ValueError):
                profiles.prepare_profiles([rc, invalid], self.backup)
            self.assertTrue(rc.is_symlink())
            self.assertFalse(self.backup.exists())

    def test_symlink_parent_is_not_modified(self):
        original = self.home / 'original'
        original.mkdir()
        (original / 'config.fish').write_text('keep\n')
        link = self.home / 'fish'
        link.symlink_to(original, target_is_directory=True)
        with self.assertRaises(ValueError):
            profiles.prepare_profiles([link / 'config.fish'], self.backup)
        self.assertEqual((original / 'config.fish').read_text(), 'keep\n')
        self.assertFalse(self.backup.exists())

    def test_existing_backup_is_never_overwritten(self):
        bash = self.home / '.bashrc'
        bash.write_text('new\n')
        self.backup.mkdir(parents=True)
        (self.backup / '.bashrc').write_text('original\n')
        with self.assertRaises(ValueError):
            profiles.prepare_profiles([bash], self.backup)
        self.assertEqual((self.backup / '.bashrc').read_text(), 'original\n')


if __name__ == '__main__':
    unittest.main()
