import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from monev.cli import jadwal as cli_jadwal
from monev.cli import kirim as cli_kirim
from monev.otomasi import jadwal, rapi, susun

HARI_KERJA = {"magang_aktif": True, "libur_nasional": False, "libur_posisi": False, "sudah_isi": False}


class TestRapi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "draft"
        self.dir.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _tulis(self, nama: str, **isi) -> Path:
        p = self.dir / nama
        p.write_text(json.dumps(isi), encoding="utf-8")
        return p

    def test_hapus_draft_di_folder_draft(self):
        p = self._tulis("2026-11-18.json")
        self.assertTrue(rapi.hapus_draft(p, self.dir))
        self.assertFalse(p.exists())

    def test_file_di_luar_folder_draft_tidak_dihapus(self):
        p = Path(self.tmp.name) / "2026-11-18.json"
        p.write_text("{}", encoding="utf-8")
        self.assertFalse(rapi.hapus_draft(p, self.dir))
        self.assertTrue(p.exists())

    def test_draft_latihan_tidak_dihapus(self):
        p = self._tulis("latihan-2026-11-18.json")
        self.assertFalse(rapi.hapus_draft(p, self.dir))
        self.assertEqual(rapi.sapu(self.dir, {"2026-11-18"}, "2026-12-30"), [])
        self.assertTrue(p.exists())

    def test_sapu_draft_yang_sudah_ada_di_arsip(self):
        self._tulis("2026-11-17.json")
        self.assertEqual(rapi.sapu(self.dir, {"2026-11-17"}, "2026-11-18"), ["2026-11-17.json"])

    def test_sapu_menyimpan_draft_belum_terkirim_yang_masih_baru(self):
        self._tulis("2026-11-18.json")
        self.assertEqual(rapi.sapu(self.dir, set(), "2026-11-18"), [])

    def test_sapu_draft_kedaluwarsa(self):
        self._tulis("2026-11-01.json")
        self.assertEqual(rapi.sapu(self.dir, set(), "2026-11-18"), ["2026-11-01.json"])

    def test_draft_revisi_tidak_disapu(self):
        p = self._tulis("2026-11-01.json", revisi=True)
        self.assertEqual(rapi.sapu(self.dir, {"2026-11-01"}, "2026-11-18"), [])
        self.assertTrue(p.exists())


class TestKirimMenghapusDraft(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        data = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"MONEV_DATA_DIR": self.tmp.name})
        self.env.start()
        self.cfg = SimpleNamespace(draft_dir=data / "draft", jangan_disebut=[])
        self.cfg.draft_dir.mkdir()
        self.file = self.cfg.draft_dir / "2026-11-18.json"
        self.file.write_text(json.dumps({"date": "2026-11-18", "approved": True}), encoding="utf-8")

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_tidak_pasti_yang_masuk_arsip_ikut_dibersihkan(self):
        arsip = Path(self.tmp.name) / "arsip"
        arsip.mkdir()
        isi = {"date": "2026-11-18", "status": "PRESENT", "activity_log": "a", "lesson_learned": "b", "obstacles": "c"}
        (arsip / "2026-11-18.json").write_text(json.dumps(isi), encoding="utf-8")
        with mock.patch("monev.cli.kirim._today", return_value="2026-11-18"):
            self._kirim("tidak_pasti")
        self.assertFalse(self.file.exists())

    def _kirim(self, tahap: str, uji: bool = False) -> None:
        lolos = SimpleNamespace(ok=True, errors=[], warnings=[], lengths={})
        args = SimpleNamespace(ping=False, file=str(self.file), uji=uji, timeout=1)
        with mock.patch("monev.kirim.host.diagnosa", return_value=[]), \
                mock.patch("monev.kirim.antrian.buat_job", return_value={"id": "x"}), \
                mock.patch("monev.cli.kirim.load_config", return_value=self.cfg), \
                mock.patch("monev.laporan.validasi.load_rules", return_value={"field": {"nama": {}}}), \
                mock.patch("monev.laporan.validasi.load_history", return_value=[]), \
                mock.patch("monev.laporan.validasi.validate", return_value=lolos), \
                mock.patch("monev.cli.laporan.saringan_nama", return_value=None), \
                mock.patch("monev.cli.laporan.cmd_status", return_value=0), \
                mock.patch("monev.cli.kirim._tunggu_extension", return_value={"ok": tahap == "terkirim", "tahap": tahap}), \
                mock.patch("builtins.print"):
            cli_kirim.cmd_kirim(args)

    def test_terkirim_menghapus_draft(self):
        self._kirim("terkirim")
        self.assertFalse(self.file.exists())

    def test_tidak_pasti_menyimpan_draft(self):
        self._kirim("tidak_pasti")
        self.assertTrue(self.file.exists())

    def test_gagal_menyimpan_draft(self):
        self._kirim("extension")
        self.assertTrue(self.file.exists())

    def test_mode_uji_menyimpan_draft(self):
        self._kirim("siap_centang", uji=True)
        self.assertTrue(self.file.exists())


class TestTerimaDraft(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.hasil = self.dir / "hasil.json"
        self.tujuan = self.dir / "draft" / "2026-11-18.json"
        self.cfg = SimpleNamespace(jangan_disebut=[])

    def tearDown(self):
        self.tmp.cleanup()

    def _terima(self, res, **isi) -> bool:
        self.hasil.write_text(json.dumps({"date": "2026-11-18", "status": "PRESENT", **isi}), encoding="utf-8")
        with mock.patch("monev.laporan.validasi.load_rules", return_value={}), \
                mock.patch("monev.laporan.validasi.load_history", return_value=[]), \
                mock.patch("monev.laporan.validasi.validate", return_value=res), \
                mock.patch("monev.cli.laporan.saringan_nama", return_value=None), \
                mock.patch.dict(os.environ, {"MONEV_DATA_DIR": self.tmp.name}):
            return cli_jadwal._terima(self.cfg, self.hasil, self.tujuan, "2026-11-18")

    def test_peringatan_masuk_keraguan_dan_draft_belum_disetujui(self):
        res = SimpleNamespace(ok=True, warnings=["butir 1 terlalu panjang"])
        self.assertTrue(self._terima(res, approved=True, keraguan=["cek rutinitas"]))
        data = json.loads(self.tujuan.read_text(encoding="utf-8"))
        self.assertFalse(data["approved"])
        self.assertEqual(data["keraguan"], ["cek rutinitas", "Peringatan validasi: butir 1 terlalu panjang"])

    def test_draft_gagal_validasi_tidak_disimpan(self):
        self.assertFalse(self._terima(SimpleNamespace(ok=False, warnings=[])))
        self.assertFalse(self.tujuan.exists())


class TestKabarDraftSiap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"MONEV_DATA_DIR": self.tmp.name})
        self.env.start()
        self.cfg = SimpleNamespace(draft_dir=Path(self.tmp.name) / "draft")
        self.cfg.draft_dir.mkdir()
        self.draft = self.cfg.draft_dir / "2026-11-19.json"
        self.tg = mock.Mock()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def _susun(self, *_) -> bool:
        self.draft.write_text("{}", encoding="utf-8")
        return True

    def _proses(self, sesi_sampai=None, status_error=None) -> None:
        status = {**HARI_KERJA, "tanggal": "2026-11-19"}
        env = {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}
        sampai = sesi_sampai or datetime(2026, 12, 19, tzinfo=timezone.utc)
        with mock.patch("monev.cli.jadwal._session_or_login", return_value=(mock.MagicMock(), object())), \
                mock.patch("monev.portal.api.collect_status", return_value=status, side_effect=status_error), \
                mock.patch("monev.portal.browser.refresh_cookie_expiry", return_value=sampai), \
                mock.patch("monev.cli.jadwal._bahan", return_value="siap"), \
                mock.patch("monev.cli.jadwal._susun", side_effect=self._susun), \
                mock.patch("monev.bot.telegram.muat_env", return_value=env), \
                mock.patch("monev.bot.telegram.Telegram", return_value=self.tg), \
                mock.patch("builtins.print"):
            cli_jadwal._proses(self.cfg, False, False)

    def test_kabar_gagal_dicoba_lagi_di_jadwal_berikutnya(self):
        self.tg.kirim.side_effect = [RuntimeError("timeout"), 1]
        self._proses()
        self._proses()
        self.assertEqual(self.tg.kirim.call_count, 2)

    def test_kabar_berhasil_tidak_dikirim_ulang(self):
        self._proses()
        self._proses()
        self.assertEqual(self.tg.kirim.call_count, 1)

    def test_draft_buatan_pemilik_tidak_dikabari(self):
        self.draft.write_text("{}", encoding="utf-8")
        self._proses()
        self.tg.kirim.assert_not_called()

    def test_sesi_laptop_hampir_habis_dikabari_sekali(self):
        self.draft.write_text("{}", encoding="utf-8")
        sampai = datetime(2026, 11, 21, 5, tzinfo=timezone.utc)
        self._proses(sampai)
        self._proses(sampai)
        self.assertEqual(self.tg.kirim.call_count, 1)
        self.assertIn("Sesi Monev di laptop habis dalam 2 hari (21 Nov).", self.tg.kirim.call_args[0][1].teks)

    def test_format_monev_berubah_langsung_dikabari(self):
        from monev.portal.api import FormatBerubah

        self._proses(status_error=FormatBerubah("/users/me/home tanpa field is_holiday"))
        self.assertIn("Bentuk data Monev berubah", self.tg.kirim.call_args[0][1].teks)


class TestPutuskan(unittest.TestCase):
    def test_hari_kerja_dengan_bahan_disusun(self):
        self.assertEqual(susun.putuskan(HARI_KERJA, False, "siap"), "susun")
        self.assertEqual(susun.putuskan(HARI_KERJA, False, "tipis"), "susun")

    def test_bahan_kosong_menunggu(self):
        self.assertEqual(susun.putuskan(HARI_KERJA, False, "kosong"), "tunggu_bahan")

    def test_draft_tidak_disusun_dua_kali(self):
        self.assertEqual(susun.putuskan(HARI_KERJA, True, "siap"), "ada_draft")

    def test_libur_sudah_isi_dan_nonaktif_berhenti(self):
        self.assertEqual(susun.putuskan({**HARI_KERJA, "libur_posisi": True}, False, "siap"), "libur")
        self.assertEqual(susun.putuskan({**HARI_KERJA, "sudah_isi": True}, False, "siap"), "sudah_isi")
        self.assertEqual(susun.putuskan({**HARI_KERJA, "magang_aktif": False}, False, "siap"), "nonaktif")


class TestBatasIzin(unittest.TestCase):
    def test_tool_mcp_penulis_dibuang(self):
        alat = ["mcp__kantor__list_entries", "mcp__kantor__create_entry", "mcp__kantor__update_status", "Bash"]
        self.assertEqual(susun.alat_baca(alat), ["mcp__kantor__list_entries"])

    def test_perintah_tidak_mengizinkan_kirim(self):
        cmd = susun.perintah_claude(Path("/repo"), Path("/repo/config.toml"), Path("/data/otomatis"), [])
        izin = cmd[cmd.index("--allowedTools") + 1:cmd.index("--disallowedTools")]
        self.assertFalse([i for i in izin if "kirim" in i])
        self.assertEqual(cmd[cmd.index("--permission-mode") + 1], "dontAsk")
        self.assertEqual(cmd[cmd.index("--disallowedTools") + 1], "Bash(monev kirim:*)")

    def test_hanya_folder_kerja_yang_bisa_ditulis(self):
        cmd = susun.perintah_claude(Path("/repo"), Path("/repo/config.toml"), Path("/data/otomatis"), [])
        self.assertEqual([i for i in cmd if i.startswith("Edit(")], ["Edit(//data/otomatis/**)"])


class TestKabarDanKunci(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_kabar_sekali_per_hari(self):
        f = self.dir / "kabar.json"
        self.assertFalse(susun.sudah_dikabari(f, "2026-11-18", "siap"))
        susun.catat_kabar(f, "2026-11-18", "siap")
        self.assertTrue(susun.sudah_dikabari(f, "2026-11-18", "siap"))
        self.assertFalse(susun.sudah_dikabari(f, "2026-11-19", "siap"))

    def test_proses_kedua_tidak_mendapat_kunci(self):
        f = self.dir / "jadwal.lock"
        with susun.kunci(f) as pertama:
            self.assertTrue(pertama)
            with susun.kunci(f) as kedua:
                self.assertFalse(kedua)

    def test_kabar_tidak_memuat_isi_laporan(self):
        from monev import teks

        for jenis in susun.KABAR:
            bagian = teks.bawaan()["bot"]["draft"][jenis]
            self.assertEqual(set(bagian), {"judul", "isi", "tindakan"})
            self.assertLessEqual(set().union(*(teks.placeholder(t) for t in bagian.values())), {"tanggal", "kapan"})

    def test_kabar_mengikuti_format_pesan_bot(self):
        from monev.bot import pesan as P
        from monev.teks import muat

        p = P.draft(P.Teks(muat()[0]), "siap", "2026-11-19")
        self.assertEqual(p.teks.splitlines()[0], "<b>Draft laporan 19 Nov sudah siap.</b>")
        self.assertIn("<code>/monev</code>", p.teks)


class TestUnitSystemd(unittest.TestCase):
    def test_timer_menyusul_jadwal_terlewat(self):
        isi = jadwal.isi_timer(["16:00", "17:00"])
        self.assertIn("Persistent=true", isi)
        self.assertIn("OnCalendar=*-*-* 16:00:00 Asia/Jakarta", isi)
        self.assertIn("OnCalendar=*-*-* 17:00:00 Asia/Jakarta", isi)

    def test_service_menjalankan_proses_terjadwal(self):
        isi = jadwal.isi_service("/opt/monev", ["/opt", "/opt"])
        self.assertIn('ExecStart="/opt/monev" jadwal jalan', isi)
        self.assertIn('Environment="PATH=/opt:/usr/local/bin:/usr/bin:/bin"', isi)

    def test_pasang_dan_lepas(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}):
            run = mock.Mock(return_value=SimpleNamespace(returncode=0, stdout="", stderr=""))
            jadwal.pasang("/opt/monev", [], ["16:00"], run=run)
            self.assertTrue((jadwal.folder_unit() / "monev-draft.timer").exists())
            jadwal.lepas(run=run)
            self.assertFalse((jadwal.folder_unit() / "monev-draft.timer").exists())


if __name__ == "__main__":
    unittest.main()
