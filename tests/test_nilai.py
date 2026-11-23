import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from monev.laporan.draft import Draft
from monev.laporan.nama import Saringan, buat_saringan, ditemukan
from monev.laporan.nilai import arsip_sah, muat_arsip, nilai_draft, sudah_dilaporkan
from monev.laporan.validasi import load_rules, validate
from monev.portal.api import log_tanggal
from monev.sumber import catatan, kesiapan

ISI = "Kalimat pengisi agar panjang field melewati batas minimal seratus karakter yang diwajibkan oleh aplikasi Monev."
RULES = load_rules()


def draft(aktivitas: str) -> Draft:
    return Draft(date="2026-11-17", activity_log=f"{aktivitas} {ISI}", lesson_learned=f"Belajar. {ISI}",
                 obstacles=f"Kendala. {ISI} Tambahan.")


class TestStatusHariIni(unittest.TestCase):
    def test_laporan_hari_lain_tidak_terbaca_sebagai_hari_ini(self):
        kemarin = {"date": "2026-11-17T00:00:00Z", "state": "APPROVED"}
        self.assertEqual(log_tanggal([kemarin], "2026-11-18"), {})

    def test_laporan_hari_ini_dipilih_walau_bukan_baris_pertama(self):
        kemarin, hari_ini = {"date": "2026-11-17"}, {"date": "2026-11-18", "state": "SUBMITTED"}
        self.assertEqual(log_tanggal([kemarin, hari_ini], "2026-11-18"), hari_ini)


class TestKesiapan(unittest.TestCase):
    def test_empat_kondisi_bahan(self):
        self.assertEqual(kesiapan.nilai(3, 2), "siap")
        self.assertEqual(kesiapan.nilai(3, 0), "tipis")
        self.assertEqual(kesiapan.nilai(0, 2), "tipis")
        self.assertEqual(kesiapan.nilai(0, 0), "kosong")

    def test_tanpa_logtime_dinilai_dari_work_records(self):
        self.assertEqual(kesiapan.nilai(1), "siap")
        self.assertEqual(kesiapan.nilai(0), "kosong")

    def test_tanpa_work_records_dinilai_dari_logtime(self):
        self.assertEqual(kesiapan.nilai(0, 2, ada_catatan=False), "siap")
        self.assertEqual(kesiapan.nilai(0, 0, ada_catatan=False), "kosong")

    def _git(self, folder: Path, *perintah: str) -> None:
        subprocess.run(["git", "-C", str(folder), "-c", "user.name=t", "-c", "user.email=t@example.com", *perintah],
                       check=True, capture_output=True)

    def test_repo_tertinggal_terdeteksi_tanpa_mengubah_lokal(self):
        with tempfile.TemporaryDirectory() as t:
            asal, lokal = Path(t, "asal"), Path(t, "lokal")
            asal.mkdir()
            self._git(asal, "init", "-q", "-b", "main")
            self._git(asal, "commit", "-q", "--allow-empty", "-m", "satu")
            subprocess.run(["git", "clone", "-q", str(asal), str(lokal)], check=True, capture_output=True)
            self.assertIs(kesiapan.kondisi_repo(lokal)["tertinggal"], False)
            self._git(asal, "commit", "-q", "--allow-empty", "-m", "dua")
            sebelum = subprocess.run(["git", "-C", str(lokal), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
            self.assertIs(kesiapan.kondisi_repo(lokal)["tertinggal"], True)
            sesudah = subprocess.run(["git", "-C", str(lokal), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
            self.assertEqual(sebelum, sesudah)

    def test_folder_bukan_repo(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(kesiapan.kondisi_repo(Path(t))["git"], False)


class TestSaringanNama(unittest.TestCase):
    def setUp(self):
        semua = [{"proyek": "aplikasi-contoh", "client": "Klien Sejahtera"}, {"proyek": "monitoring", "client": "internal"}]
        hari_ini = [{"proyek": "monitoring", "judul": "[Grafana] Perjelas alert ACME Tools dan modul ZORO"}]
        self.s = buat_saringan(semua, hari_ini, ["Proyek Rahasia"], RULES, "ACME Indonesia", lewati=["maganghub"])

    def test_nama_klien_dari_sumber_memblokir(self):
        for teks in ("Mengerjakan Aplikasi Contoh hari ini.", "Mendukung klien sejahtera.", "Membantu proyek rahasia."):
            with self.subTest(teks=teks):
                self.assertFalse(validate(draft(teks), saringan=self.s).ok)

    def test_nama_di_dalam_satu_kata_tertangkap(self):
        self.assertTrue(ditemukan("Pertamina", "Modul MyPertamina diperbarui"))

    def test_teknologi_perusahaan_dan_program_boleh(self):
        teks = "[Grafana] Memperbaiki alert Wazuh di GitLab untuk ISO 27001 di ACME Indonesia, program MagangHub."
        self.assertEqual(validate(draft(teks), saringan=self.s).errors, [])

    def test_alat_internal_perusahaan_memblokir(self):
        self.assertFalse(validate(draft("Memperjelas alert ACME Tools."), saringan=self.s).ok)

    def test_akronim_judul_hanya_peringatan(self):
        res = validate(draft("Memperbaiki modul ZORO."), saringan=self.s)
        self.assertTrue(res.ok, res.errors)
        self.assertTrue(any("ZORO" in w for w in res.warnings))

    def test_nama_boleh_mengecualikan(self):
        s = buat_saringan([{"proyek": "aplikasi-contoh"}], [], [], RULES, boleh=["Aplikasi Contoh"])
        self.assertEqual(s.dilarang, [])

    def test_proyek_dilewati_ditolak_sebagai_tag(self):
        self.assertFalse(validate(draft("1. [Maganghub] Merapikan bot."), saringan=self.s).ok)

    def test_nama_program_di_kalimat_biasa_tetap_lolos(self):
        res = validate(draft("Mengikuti onboarding peserta MagangHub."), saringan=self.s)
        self.assertTrue(res.ok, res.errors)

    def test_tanpa_saringan_perilaku_lama_tetap(self):
        self.assertTrue(validate(draft("Mengerjakan Aplikasi Contoh."), saringan=Saringan()).ok)


class TestPeringatanAlatAi(unittest.TestCase):
    def test_agent_diberi_peringatan(self):
        res = validate(draft("Pengujian tidak bisa dijalankan oleh agent."))
        self.assertTrue(any("alat AI" in w for w in res.warnings))

    def test_agent_wazuh_tidak_ditandai(self):
        for teks in ("Memperbaiki agent Wazuh yang macet.", "Memasang Wazuh agent di server."):
            with self.subTest(teks=teks):
                self.assertFalse(any("alat AI" in w for w in validate(draft(teks)).warnings))


class TestCatatanProyek(unittest.TestCase):
    def test_client_dan_daftar_proyek_dibaca(self):
        isi = ('---\ntitle: "Tugas"\nclient: "Klien Sejahtera"\n---\n\n## Daily activity log\n\n'
               "| 2026-11-17 | kerja | hasil | - |\n")
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "proyek-a").mkdir()
            (Path(t) / "proyek-a" / "tugas.md").write_text(isi, encoding="utf-8")
            (Path(t) / "pribadi").mkdir()
            (Path(t) / "pribadi" / "tugas.md").write_text(isi, encoding="utf-8")
            self.assertEqual(catatan.baca(Path(t), "2026-11-17", ["PRIBADI"])[0]["client"], "Klien Sejahtera")
            self.assertEqual(len(catatan.baca(Path(t), "2026-11-17", ["PRIBADI"])), 1)
            self.assertEqual(catatan.daftar_proyek(Path(t), ["pribadi"]),
                             [{"proyek": "proyek-a", "client": "Klien Sejahtera"}])


class TestCarryOver(unittest.TestCase):
    ISI = """# Tugas

## Daily activity log

| 2026-11-17 | kerja siang | hasil | - |

## Daily time log

| Date | Start | End | Duration | Activity | Time basis |
|---|---|---|---|---|---|
| 2026-11-16 | 10:00 | 12:00 | 02:00:00 | kerja jam kantor | observed |
| 2026-11-16 | 21:00 | 23:00 | 02:00:00 | migrasi dashboard pemantauan malam | observed |
| 2026-11-14 | 09:00 | 11:00 | 02:00:00 | perbaikan agent akhir pekan | observed |
| 2026-11-17 | 14:00 | 17:00 | 03:00:00 | logtime kerja lama | carry-over dari 2026-11-14 09:00-11:00 |
"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "proyek").mkdir()
        (self.dir / "proyek" / "tugas.md").write_text(self.ISI, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_carry_over_dipisahkan_dari_aktivitas_hari_itu(self):
        hasil = catatan.baca(self.dir, "2026-11-17")[0]
        self.assertEqual(hasil["carry_over"][0]["asal"], [{"tanggal": "2026-11-14", "mulai": "09:00", "selesai": "11:00"}])
        self.assertEqual(len(hasil["aktivitas"]), 1)

    def test_kerja_malam_terdeteksi_kerja_kantor_tidak(self):
        hasil = catatan.kerja_luar_jam(self.dir, "2026-11-17", {"2026-11-16"})
        self.assertEqual([h["kegiatan"] for h in hasil], ["migrasi dashboard pemantauan malam"])

    def test_hari_tanpa_laporan_dihitung_luar_jam(self):
        hasil = catatan.kerja_luar_jam(self.dir, "2026-11-16", {"2026-11-13"})
        self.assertEqual([h["kegiatan"] for h in hasil], ["perbaikan agent akhir pekan"])

    def test_kerja_sebelum_laporan_terakhir_tidak_ditawarkan_lagi(self):
        hasil = catatan.kerja_luar_jam(self.dir, "2026-11-17", {"2026-11-13", "2026-11-16"})
        self.assertNotIn("perbaikan agent akhir pekan", [h["kegiatan"] for h in hasil])

    def test_sebelum_laporan_pertama_tidak_dihitung(self):
        hasil = catatan.kerja_luar_jam(self.dir, "2026-11-17", {"2026-11-16"})
        self.assertNotIn("perbaikan agent akhir pekan", [h["kegiatan"] for h in hasil])

    def test_tanpa_arsip_tidak_ada_kandidat(self):
        self.assertEqual(catatan.kerja_luar_jam(self.dir, "2026-11-17", set()), [])

    def test_kerja_yang_sudah_dilaporkan_dikenali(self):
        laporan = [{"activity_log": "1. Melakukan migrasi dashboard pemantauan pada malam hari.",
                    "lesson_learned": "Saya memahami pentingnya pengujian sebelum perubahan diterapkan ke produksi."}]
        self.assertTrue(sudah_dilaporkan("migrasi dashboard pemantauan malam", laporan))
        self.assertFalse(sudah_dilaporkan("rotasi sertifikat server surel", laporan))


class TestNilai(unittest.TestCase):
    ASLI = {"date": "2026-11-17", "status": "PRESENT",
            "activity_log": "1. Memperbaiki alert penyimpanan server Grafana.\n2. Menyusun dokumen standar keamanan ISO.",
            "lesson_learned": "Saya memahami pentingnya memeriksa titik mount sebelum membuat alert penyimpanan.",
            "obstacles": "Akses produksi menunggu persetujuan penanggung jawab infrastruktur sebelum perubahan diterapkan."}

    def test_draft_sama_mendapat_skor_penuh(self):
        hasil = nilai_draft(self.ASLI, self.ASLI)
        self.assertEqual(hasil["skor"], 100)
        self.assertEqual(hasil["butir_tambahan"], 0)

    def test_draft_berbeda_mendapat_skor_rendah(self):
        lain = {"activity_log": "1. Mengikuti onboarding bersama peserta program.\n2. Mengenal lingkungan kantor baru.",
                "lesson_learned": "Saya mengenal budaya perusahaan dari sesi perkenalan bersama seluruh peserta baru.",
                "obstacles": "Belum ada hambatan berarti karena seluruh kegiatan pengenalan berjalan sesuai jadwal."}
        hasil = nilai_draft(lain, self.ASLI)
        self.assertEqual(hasil["kegiatan"]["cocok"], 0)
        self.assertEqual(hasil["butir_tambahan"], 2)
        self.assertEqual(hasil["skor"], 0)

    def test_butir_tambahan_terhitung(self):
        tambah = replace_log(self.ASLI, "\n3. Mengikuti pelatihan komunikasi bersama tim pemasaran perusahaan.")
        self.assertEqual(nilai_draft(tambah, self.ASLI)["butir_tambahan"], 1)

    def test_arsip_tanpa_kehadiran_tidak_sah(self):
        self.assertTrue(arsip_sah(self.ASLI, "2026-11-17"))
        self.assertFalse(arsip_sah({**self.ASLI, "status": None}, "2026-11-17"))
        self.assertFalse(arsip_sah(self.ASLI, "2026-11-18"))

    def test_kendala_tidak_masuk_skor(self):
        lain = {**self.ASLI, "obstacles": "Belum ada hambatan berarti karena seluruh kegiatan berjalan sesuai jadwal."}
        hasil = nilai_draft(lain, self.ASLI)
        self.assertEqual(hasil["kendala"]["cocok"], 0)
        self.assertEqual(hasil["skor"], 100)

    def test_muat_arsip_hanya_yang_sah(self):
        with tempfile.TemporaryDirectory() as t:
            Path(t, "2026-11-17.json").write_text(json.dumps(self.ASLI), encoding="utf-8")
            Path(t, "2026-11-18.json").write_text(json.dumps({**self.ASLI, "date": "2026-11-18", "status": None}), encoding="utf-8")
            self.assertEqual(list(muat_arsip(Path(t))), ["2026-11-17"])


def replace_log(asli: dict, tambahan: str) -> dict:
    return {**asli, "activity_log": asli["activity_log"] + tambahan}


if __name__ == "__main__":
    unittest.main()
