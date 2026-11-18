import tempfile
import unittest
from pathlib import Path

from monev.agen import hermes


class TestHermes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_pasang_salinan_dan_lepas(self):
        hermes.pasang(self.home)
        skill = self.home / "skills/maganghub/monev"
        self.assertTrue((skill / "SKILL.md").exists())
        self.assertTrue((skill / "references/sources.md").exists())
        bundle = (self.home / "skill-bundles/monev.yaml").read_text()
        self.assertIn("name: monev", bundle)
        self.assertIn("- monev", bundle)
        hermes.pasang(self.home)  # upgrade: menimpa milik sendiri
        hermes.lepas(self.home)
        self.assertFalse(skill.exists())
        self.assertFalse((self.home / "skill-bundles/monev.yaml").exists())
        self.assertFalse((self.home / "skills/maganghub").exists())

    def test_symlink(self):
        hermes.pasang(self.home, symlink=True)
        skill = self.home / "skills/maganghub/monev"
        self.assertTrue(skill.is_symlink())
        self.assertEqual(skill.resolve(), hermes.SUMBER)
        hermes.lepas(self.home)
        self.assertFalse(skill.is_symlink())

    def test_tolak_timpa_milik_orang(self):
        asing = self.home / "skills/maganghub/monev"
        asing.mkdir(parents=True)
        (asing / "SKILL.md").write_text("punya orang lain")
        with self.assertRaises(RuntimeError):
            hermes.pasang(self.home)
        hermes.lepas(self.home)  # tidak menghapus milik orang lain
        self.assertTrue((asing / "SKILL.md").exists())

    def test_profile_tidak_ada(self):
        with self.assertRaises(RuntimeError):
            hermes.pasang(self.home / "tidak-ada")

    def test_skill_netral_agent(self):
        teks = (hermes.SUMBER / "SKILL.md").read_text()
        self.assertTrue(teks.startswith("---\nname: monev\n"))
        self.assertIn("version:", teks.split("---")[1])
        self.assertIn("Hermes", teks)


if __name__ == "__main__":
    unittest.main()
