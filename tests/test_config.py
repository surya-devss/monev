import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from monev import config

REPO = Path(__file__).resolve().parent.parent


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _muat(self, isi: str) -> config.Config:
        f = self.dir / "config.toml"
        f.write_text(isi, encoding="utf-8")
        with mock.patch.dict(os.environ, {"MONEV_CONFIG": str(f)}):
            return config.load_config()

    def test_contoh_sama_dengan_config_bawaan(self):
        contoh = (REPO / "config.example.toml").read_text(encoding="utf-8")
        self.assertEqual(contoh, config.render_config("", "", ""))

    def test_config_bawaan_kosong_dan_tanpa_path(self):
        cfg = self._muat(config.render_config("", "", ""))
        self.assertIsNone(cfg.workrecords_dir)
        self.assertEqual(cfg.mcp_awalan_tool, [])
        self.assertNotIn("/home/", config.render_config("", "", ""))

    def test_config_lama_tanpa_bagian_mcp_tetap_terbaca(self):
        cfg = self._muat('[profil]\nposisi = "X"\n\n[sumber]\nmode = "auto"\n\n'
                         '[sumber.workrecords]\ndir = "/tmp/wr"\nlewati_folder = ["_a"]\n')
        self.assertEqual(cfg.posisi, "X")
        self.assertEqual(cfg.workrecords_dir, Path("/tmp/wr"))
        self.assertEqual(cfg.lewati_folder, ["_a"])
        self.assertEqual(cfg.mcp_awalan_tool, [])

    def test_awalan_tool_mcp_dibaca(self):
        cfg = self._muat('[sumber.mcp]\nawalan_tool = ["mcp__kantor__", "kantor"]\n')
        self.assertEqual(cfg.mcp_awalan_tool, ["mcp__kantor__", "kantor"])

    def test_deteksi_work_records_hanya_dari_env_monev(self):
        lain = {"WORK_RECORDS_DIR": str(self.dir), "HERMES_WORK_RECORDS": str(self.dir), "HOME": str(self.dir)}
        with mock.patch.dict(os.environ, lain, clear=True):
            self.assertIsNone(config.detect_workrecords())
        with mock.patch.dict(os.environ, {"MONEV_WORK_RECORDS": str(self.dir)}, clear=True):
            self.assertEqual(config.detect_workrecords(), self.dir)
        with mock.patch.dict(os.environ, {"MONEV_WORK_RECORDS": str(self.dir / "tidak-ada")}, clear=True):
            self.assertIsNone(config.detect_workrecords())


if __name__ == "__main__":
    unittest.main()
