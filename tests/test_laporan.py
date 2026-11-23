import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from monev.laporan.draft import Draft, js_length, load, template
from monev.laporan.validasi import validate

FIX = Path(__file__).parent / "fixtures" / "draft-2026-11-16.json"
FILLER = " Kalimat pengisi agar panjang field melewati batas minimal seratus karakter yang diwajibkan Monev."


def base() -> Draft:
    return load(FIX)


def with_activity(text: str) -> Draft:
    return replace(base(), activity_log=text + FILLER)


class TestLolos(unittest.TestCase):
    def test_laporan_terkirim_2026_11_16_lolos(self):
        res = validate(base(), today="2026-11-16")
        self.assertEqual(res.errors, [])
        self.assertEqual(res.lengths, {"activity_log": 550, "lesson_learned": 433, "obstacles": 301})

    def test_kalimat_wajar_tidak_salah_tangkap(self):
        for teks in ["Mengisi laporan sebelum pukul 23.59 WIB.", "Memakai Grafana versi 12.0 dan Docker.",
                     "1. Rapat tim pada Senin, 16 November 2026.", "Membaca dokumen standar/pedoman tim.",
                     "Menyelesaikan 3 dari 5 tugas (60%)."]:
            with self.subTest(teks=teks):
                self.assertEqual(validate(with_activity(teks)).errors, [])


class TestGagal(unittest.TestCase):
    def test_terlalu_pendek(self):
        res = validate(replace(base(), obstacles="Tidak ada kendala."))
        self.assertTrue(any("minimal 100" in e for e in res.errors))

    def test_data_terlarang(self):
        kasus = {
            "alamat IP": "Cek server 10.20.30.40 hari ini.",
            "URL": "Membuka https://monitoring.example.com/d/abc untuk cek.",
            "nomor tiket": "Mengerjakan tiket #3257 tentang alert.",
            "nomor MR/PR": "Merge request !12 sudah di-merge.",
            "hash commit": "Commit b6af252 sudah di-push.",
            "path berkas": "Mengubah /home/user/devops/config.yml.",
            "email": "Mengirim ke budi@example.com.",
            "token/secret": "Token xoxb-1234-abcd-efgh dipasang.",
            "nomor CVE": "Menemukan CVE-2024-21626 di server.",
        }
        for nama, teks in kasus.items():
            with self.subTest(nama=nama):
                res = validate(with_activity(teks))
                self.assertTrue(any(nama in e for e in res.errors), res.errors)

    def test_jangan_disebut(self):
        res = validate(with_activity("Membantu proyek Qamara."), jangan_disebut=["qamara"])
        self.assertTrue(any("jangan_disebut" in e for e in res.errors))

    def test_tanggal_bukan_hari_ini(self):
        res = validate(base(), today="2026-11-17")
        self.assertTrue(any("bukan hari ini" in e for e in res.errors))

    def test_status_absent_ditolak(self):
        res = validate(replace(base(), status="ABSENT"))
        self.assertTrue(any("tidak diizinkan" in e for e in res.errors))

    def test_izin_butuh_alasan(self):
        res = validate(Draft(date="2026-11-16", status="ON_LEAVE", leave_reason="Sakit."))
        self.assertTrue(any("Alasan tidak hadir" in e for e in res.errors))

    def test_izin_hanya_hari_ini(self):
        d = Draft(date="2026-11-16", status="ON_LEAVE", leave_reason="Sakit demam sejak pagi." + FILLER)
        self.assertTrue(validate(d, today="2026-11-16").ok)
        self.assertTrue(any("bukan hari ini" in e for e in validate(d, today="2026-11-17").errors))

    def test_revisi_boleh_tanggal_lampau(self):
        d = replace(base(), revisi=True)
        self.assertEqual(d.jenis, "revisi")
        self.assertTrue(validate(d, today="2026-11-20").ok, validate(d, today="2026-11-20").errors)
        self.assertTrue(any("belum terjadi" in e for e in validate(d, today="2026-11-10").errors))

    def test_revisi_bukan_untuk_izin(self):
        d = Draft(date="2026-11-16", status="ON_LEAVE", leave_reason="Sakit." + FILLER, revisi=True)
        self.assertTrue(any("revisi hanya untuk laporan hadir" in e for e in validate(d).errors))

    def test_revisi_dari_json_dan_teks(self):
        with tempfile.TemporaryDirectory() as t:
            j = Path(t, "r.json")
            j.write_text(json.dumps({"date": "2026-11-14", "revisi": True, "activity_log": "a"}))
            self.assertTrue(load(j).revisi)
            m = Path(t, "r.md")
            m.write_text("# tanggal: 2026-11-14\n# revisi: ya\n\n## Uraian aktivitas\nisi\n")
            self.assertEqual(load(m).jenis, "revisi")
            m.write_text("# tanggal: 2026-11-14\n# status: izin\n\n## Alasan tidak hadir\nsakit\n")
            self.assertEqual(load(m).jenis, "izin")


class TestPeringatan(unittest.TestCase):
    def test_tanda_baca_khas_ai(self):
        for teks in ["Perlu izin dulu; saya mengajukan izin.", "Merevisi draf — memisahkan bab fakta.",
                     "Merevisi draf laporan: memisahkan bab fakta."]:
            with self.subTest(teks=teks):
                self.assertTrue(any("tanda baca" in w or "titik dua" in w for w in validate(with_activity(teks)).warnings))
        for teks in ["1. [ISO 27001] Merevisi draf laporan dengan memisahkan bab fakta.", "Rapat pukul 09.15 WIB."]:
            with self.subTest(teks=teks):
                self.assertFalse(any("tanda baca" in w or "titik dua" in w for w in validate(with_activity(teks)).warnings))

    def test_markdown(self):
        res = validate(with_activity("Menyelesaikan **deploy** aplikasi."))
        self.assertTrue(any("markdown" in w for w in res.warnings))

    def test_mirip_laporan_lama(self):
        lama = json.loads(FIX.read_text())
        lama["date"] = "2026-11-15"
        res = validate(base(), history=[lama])
        self.assertTrue(any("mirip laporan 2026-11-15" in w for w in res.warnings))

    def test_detail_temuan_keamanan(self):
        for teks in ["Port yang tampak tersaring ternyata masih dapat dijangkau lewat proxy.",
                     "Menemukan 3 temuan pada layanan.", "Mencatat temuan kritis pada server."]:
            with self.subTest(teks=teks):
                self.assertTrue(any("detail temuan" in w for w in validate(with_activity(teks)).warnings))
        for teks in ["Menyusun laporan penilaian kerentanan.", "Mencocokkan hasil pindai dengan konfigurasi layanan.",
                     "Menyampaikan temuan kepada penanggung jawab layanan."]:
            with self.subTest(teks=teks):
                self.assertFalse(any("detail temuan" in w for w in validate(with_activity(teks)).warnings))

    def test_batasan_alat_bantu(self):
        res = validate(with_activity("Pengujian tidak dapat dijalankan melalui alat bantu otomatis."))
        self.assertTrue(any("alat bantu" in w for w in res.warnings))

    def test_butir_terlalu_panjang(self):
        pas = replace(base(), activity_log="1. " + "a" * 250 + "\n2. Membaca dokumen.")
        self.assertFalse(any("butir" in w for w in validate(pas).warnings))
        panjang = replace(base(), activity_log="1. Membaca dokumen.\n2. " + "a" * 251)
        self.assertTrue(any("butir 2 251 karakter" in w for w in validate(panjang).warnings))

    def test_pembuka_pembelajaran_berulang(self):
        d = replace(base(), lesson_learned="Saya belajar bahwa setiap klaim perlu bukti." + FILLER)
        sama = [{"date": "2026-11-15", "lesson_learned": "saya belajar bahwa jadwal perlu dicatat."}]
        beda = [{"date": "2026-11-15", "lesson_learned": "Dari perbaikan alert, saya memahami dampaknya."}]
        self.assertTrue(any("pembuka sama" in w for w in validate(d, history=sama).warnings))
        self.assertFalse(any("pembuka sama" in w for w in validate(d, history=beda).warnings))


class TestFormat(unittest.TestCase):
    def test_js_length_utf16(self):
        self.assertEqual(js_length("abc"), 3)
        self.assertEqual(js_length("😀"), 2)  # emoji = 2 unit UTF-16, sama seperti di browser

    def test_template_bisa_dibaca_balik(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "d.md"
            teks = template("2026-11-17", hari_pertama=True).replace(
                "## Uraian aktivitas\n1.", "## Uraian aktivitas\n1. Menyusun dokumen.", 1)
            p.write_text(teks, encoding="utf-8")
            d = load(p)
        self.assertEqual(d.date, "2026-11-17")
        self.assertEqual(d.status, "PRESENT")
        self.assertEqual(d.activity_log, "1. Menyusun dokumen.")
        self.assertNotIn("Petunjuk", d.lesson_learned)


class TestChrome(unittest.TestCase):
    def test_find_chrome_macos_windows(self):
        import os
        import sys
        from unittest import mock

        from monev.portal.browser import find_chrome

        with tempfile.TemporaryDirectory() as tmp, mock.patch("shutil.which", return_value=None):
            exe = Path(tmp, "Google", "Chrome", "Application", "chrome.exe")
            exe.parent.mkdir(parents=True)
            exe.touch()
            with mock.patch.object(sys, "platform", "win32"), mock.patch.dict(os.environ, {"LOCALAPPDATA": tmp}):
                self.assertEqual(find_chrome(), str(exe))
            with mock.patch.object(sys, "platform", "darwin"), mock.patch("os.path.isfile", return_value=True):
                self.assertTrue(find_chrome().endswith("Google Chrome"))


if __name__ == "__main__":
    unittest.main()
