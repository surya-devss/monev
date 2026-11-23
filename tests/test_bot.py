import os
import tempfile
import unicodedata
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

from monev.bot import jadwal, pesan
from monev.bot.telegram import MENU, Telegram, muat_env
from monev.config import Config
from monev.teks import muat

WIB = jadwal.WIB
TX = pesan.Teks(muat()[0])


def st(tanggal="2026-11-20", sudah=False, libur=False, revisi=None, lokasi=True):
    return {"tanggal": tanggal, "magang_aktif": True, "libur_nasional": libur, "libur_posisi": False,
            "sudah_isi": sudah, "perlu_revisi": revisi or [], "nama": "Rina Pratama", "posisi": "DevOps Engineer",
            "perusahaan": "PT Contoh",
            "kehadiran": {"status": "PRESENT", "persetujuan": "SUBMITTED", "ada_lokasi": lokasi} if sudah else None}


def rekap(harian=None, ditolak=None, terakhir=False):
    harian = harian or [{"tanggal": "2026-11-16", "kehadiran": "hadir", "mentor": "disetujui"},
                        {"tanggal": "2026-11-17", "kehadiran": "izin", "mentor": "menunggu"}]
    return {"dari": "2026-11-16", "sampai": "2026-11-20", "hari_kerja": len(harian), "terhitung": len(harian),
            "hadir": 1, "izin": 1, "absen": 0, "ditolak": 0, "belum": 0, "penuh": False,
            "persetujuan": {"menunggu": 1, "disetujui": 1, "ditolak": 0}, "harian": harian,
            "ditolak_tanggal": ditolak or [], "hari_kerja_terakhir_periode": terakhir,
            "periode": {"izin": 1, "izin_dibayar_sisa": 2, "absen_total": 0, "absen_berturut": 0, "status": "aman",
                        "ke": 1, "awal": "2026-11-16", "akhir": "2026-12-15"}}


NILAI = {"semboyan": "Semboyan Contoh", "poin": [["Satu", "penerapan satu."], ["Dua", "penerapan dua."],
                                                  ["Tiga", "penerapan tiga."]]}
K = jadwal.Konteks(TX)


def jam(h, m, d=20):
    return datetime(2026, 11, d, h, m, tzinfo=WIB)


def putus(jenis, status, lalu=None, waktu=None, **data):
    return jadwal.putuskan(jenis, {"status": status, "periode": data.pop("periode", rekap()), **data}, lalu or {},
                           waktu or jam(15, 0), data.pop("k", K))


class TestJadwal(unittest.TestCase):
    J = jadwal.buat_jadwal(Config(exists=True, path=Path("x")))

    def test_dari_config_terurut(self):
        self.assertEqual(self.J[:3], [("08:00", "kartu"), ("12:00", "pantau"), ("15:00", "ingat:pertama")])
        self.assertIn(("20:00", "ingat:terakhir"), self.J)
        cfg = Config(exists=True, path=Path("x"), bot_pengingat=["14:00", "19:00"], bot_kartu="07:30")
        j = jadwal.buat_jadwal(cfg)
        self.assertEqual(j[0], ("07:30", "kartu"))
        self.assertIn(("19:00", "ingat:terakhir"), j)

    def test_jatuh_tempo_sekali_dan_dalam_jendela(self):
        self.assertEqual(jadwal.jadwal_jatuh_tempo(self.J, jam(15, 10), set()), [("15:00-ingat:pertama", "ingat:pertama")])
        self.assertEqual(jadwal.jadwal_jatuh_tempo(self.J, jam(15, 40), set()), [])
        self.assertEqual(jadwal.jadwal_jatuh_tempo(self.J, jam(15, 5), {"15:00-ingat:pertama"}), [])
        self.assertEqual(jadwal.jadwal_berikutnya(self.J, jam(15, 5)), "16:00")


class TestPutuskan(unittest.TestCase):
    def test_kartu_hanya_hari_kerja_libur_satu_pesan(self):
        k = putus("kartu", st(), waktu=jam(8, 0))
        self.assertEqual([t for t, _ in k.kirim], ["kartu"])
        self.assertIn("Selamat pagi, Rina.", k.kirim[0][1].teks)
        k = putus("kartu", st(libur=True), waktu=jam(8, 0))
        self.assertEqual([t for t, _ in k.kirim], ["info"])
        self.assertIn("Hari ini libur", k.kirim[0][1].teks)
        self.assertIsNone(k.kartu)

    def test_panggilan_dari_config(self):
        k = putus("kartu", st(), waktu=jam(8, 0), k=jadwal.Konteks(TX, panggilan="Mas Rina"))
        self.assertIn("Selamat pagi, Mas Rina.", k.kirim[0][1].teks)

    def test_pengingat_hanya_bila_belum_isi(self):
        k = putus("ingat:pertama", st())
        self.assertEqual([t for t, _ in k.kirim], ["ingat:pertama"])
        self.assertIn("belum diisi", k.kirim[0][1].judul)
        self.assertEqual(putus("ingat:pertama", st(sudah=True)).kirim, [])
        self.assertEqual(putus("ingat:kedua", st(libur=True)).kirim, [])

    def test_pengingat_terakhir_menyebut_sisa_jam(self):
        k = putus("ingat:terakhir", st(), waktu=jam(20, 0))
        self.assertIn("Sisa sekitar 4 jam", k.kirim[0][1].teks)

    def test_transisi_terkirim_sekali(self):
        lalu = {"tanggal": "2026-11-20", "sudah_isi": False}
        k = putus("pantau", st(sudah=True), lalu, jam(18, 0))
        self.assertEqual(len(k.kirim), 1)
        self.assertIn("Laporan 20 Nov sudah terkirim", k.kirim[0][1].teks)
        self.assertTrue(k.sudah_isi)
        self.assertIn("✓ Terkirim, menunggu mentor", k.kartu.teks)
        self.assertEqual(putus("pantau", st(sudah=True), k.baru, jam(22, 0)).kirim, [])

    def test_revisi_dan_ditolak_baru_sekali(self):
        status = st(revisi=[{"date": "2026-11-17", "catatan_mentor": "Tambah <hasil>"}])
        k = putus("pantau", status, periode=rekap(ditolak=["2026-11-18"]))
        self.assertEqual(len(k.kirim), 2)
        self.assertIn("&lt;hasil&gt;", k.kirim[0][1].teks)   # isi dari Monev di-escape
        self.assertEqual(putus("pantau", status, k.baru, periode=rekap(ditolak=["2026-11-18"])).kirim, [])

    def test_disetujui_digabung_dan_sekali(self):
        per = {**rekap(), "disetujui_tanggal": ["2026-11-16", "2026-11-17", "2026-11-18"],
               "persetujuan": {"menunggu": 1, "disetujui": 3, "ditolak": 0}}
        k = putus("pantau", st(), {"disetujui": ["2026-11-16"]}, jam(22, 0), periode=per)
        self.assertEqual(len(k.kirim), 1)
        self.assertEqual(k.kirim[0][1].teks, "<b>Laporan 17 dan 18 Nov disetujui mentor.</b>\n"
                                             "Total disetujui 3 dari 4 laporan terkirim.")
        self.assertEqual(putus("pantau", st(), k.baru, jam(8, 0, d=21), periode=per).kirim, [])

    def test_disetujui_tidak_dikabari_saat_state_belum_mencatat(self):
        per = {**rekap(), "disetujui_tanggal": ["2026-11-16", "2026-11-17"]}
        k = putus("pantau", st(), {"tanggal": "2026-11-19", "revisi": [], "ditolak": []}, periode=per)
        self.assertEqual(k.kirim, [])
        self.assertEqual(k.baru["disetujui"], ["2026-11-16", "2026-11-17"])

    def test_disetujui_menyusul_setelah_kartu_pagi(self):
        per = {**rekap(), "disetujui_tanggal": ["2026-11-19"]}
        k = putus("kartu", st(), {"disetujui": []}, jam(8, 0), periode=per)
        self.assertEqual([t for t, _ in k.kirim], ["kartu", "info"])
        self.assertIn("Laporan 19 Nov disetujui mentor.", k.kirim[1][1].teks)

    def test_kalimat_absen_dan_izin(self):
        self.assertEqual(pesan.izin_teks(0), "0 dari 3 yang dibayar")
        self.assertEqual(pesan.izin_teks(4), "4, 1 tidak dibayar")
        m = pesan.rekap_minggu(TX, rekap()).teks
        self.assertIn("Periode 1: absen 0 (peringatan di 7), izin 1 dari 3 yang dibayar.", m)
        b = pesan.rekap_bulan(TX, rekap()).teks
        self.assertIn("<b>Izin</b>  1 dari 3 yang dibayar", b)
        self.assertIn("<b>Absen</b>  0 (peringatan di 7)", b)
        self.assertIn("<b>Berturut</b>  absen 0 (peringatan di 3)", b)

    def test_daftar_tanggal(self):
        self.assertEqual(pesan.daftar_tanggal(["2026-11-19"]), "19 Nov")
        self.assertEqual(pesan.daftar_tanggal(["2026-11-19", "2026-11-17", "2026-11-18"]), "17, 18, dan 19 Nov")
        self.assertEqual(pesan.daftar_tanggal(["2026-11-30", "2026-12-01"]), "30 Nov dan 1 Des")

    def test_rekap_jumat_dan_akhir_periode(self):
        k = putus("rekap", st(sudah=True), periode=rekap(terakhir=True), minggu=rekap(), bulan=rekap())
        self.assertEqual(len(k.kirim), 2)
        self.assertIn("Minggu ini hadir 1 dari 2 hari", k.kirim[0][1].teks)
        self.assertIn("<b>Periode 1, hadir 1 dari 2 hari.</b>\n16 Nov – 15 Des 2026", k.kirim[1][1].teks)
        k = putus("rekap", st(tanggal="2026-11-19", sudah=True), waktu=jam(16, 0, d=19), minggu=rekap(), bulan=rekap())
        self.assertEqual(k.kirim, [])

    def test_situs_diperbarui_dikabari_sekali(self):
        k = putus("pantau", st(), {}, versi_web="/_nuxt/A.js")              # pertama kali: hanya dicatat
        self.assertEqual(k.kirim, [])
        k = putus("pantau", st(), k.baru, versi_web="/_nuxt/B.js")
        self.assertEqual(len(k.kirim), 1)
        self.assertIn("Tampilan situs Monev baru saja diperbarui.", k.kirim[0][1].teks)
        self.assertIn("<code>monev kirim --uji</code>", k.kirim[0][1].teks)
        self.assertEqual(putus("pantau", st(), k.baru, versi_web="/_nuxt/B.js").kirim, [])
        self.assertEqual(putus("pantau", st(), k.baru).baru["versi_web"], "/_nuxt/B.js")   # gagal baca: tetap ingat

    def test_masa_magang_sekali_per_ambang(self):
        akhir = {"mulai": "2026-11-16", "selesai": "2026-12-20"}
        k = putus("kartu", {**st(), "periode": akhir}, {"masa": []}, jam(8, 0))   # sisa 30 hari
        self.assertIn("Masa magang selesai dalam 30 hari (20 Des 2026).", k.kirim[-1][1].teks)
        self.assertEqual(putus("pantau", {**st(), "periode": akhir}, k.baru, jam(12, 0)).kirim, [])
        # bot mati lama, ternyata sisa 5 hari: cukup kabar H-7, bukan H-30 dan H-7 sekaligus
        k = putus("kartu", {**st(tanggal="2026-12-15"), "periode": akhir}, {}, jam(8, 0, d=15))
        masa = [p.teks for t, p in k.kirim if "Masa magang" in p.teks]
        self.assertEqual(len(masa), 1)
        self.assertIn("dalam 5 hari", masa[0])

    def test_magang_tidak_aktif_dikabari_sekali(self):
        periode = {"mulai": "2026-11-16", "selesai": "2027-05-15"}
        nonaktif = {**st(), "periode": periode, "magang_aktif": False}
        k = putus("kartu", nonaktif, {"aktif": True}, jam(8, 0))
        self.assertEqual(len(k.kirim), 1)
        self.assertIn("tidak aktif sebelum tanggal selesai (15 Mei 2027)", k.kirim[0][1].teks)
        self.assertEqual(putus("kartu", nonaktif, k.baru, jam(8, 0, d=21)).kirim, [])
        selesai = {**nonaktif, "tanggal": "2027-05-16"}
        k = putus("kartu", selesai, {"aktif": True}, datetime(2027, 5, 16, 8, 0, tzinfo=WIB))
        self.assertIn("Masa magang sudah selesai.", k.kirim[0][1].teks)

    def test_sesi_hampir_habis(self):
        k = putus("kartu", st(sudah=True), waktu=jam(8, 0), sesi_sampai=datetime(2026, 11, 22, 3, 0, tzinfo=timezone.utc))
        self.assertEqual(len(k.kirim), 2)
        self.assertIn("habis dalam 2 hari (22 Nov)", k.kirim[1][1].teks)


class TestFormat(unittest.TestCase):
    def semua(self):
        out = [pesan.kartu(TX, st(), NILAI, "Rina"), pesan.kartu(TX, st(sudah=True), None, ""),
               pesan.kartu_libur(TX, st(libur=True), "Rina"), pesan.terkirim(TX, st(sudah=True)),
               pesan.revisi(TX, "2026-11-17", "a"), pesan.disetujui(TX, ["2026-11-17"], 1, 2), pesan.ditolak(TX, "2026-11-17", 1), pesan.sesi(TX, 2, date(2026, 11, 22)),
               pesan.gangguan(TX, "x", ["15:00"], "16:00"), pesan.gangguan_pulih(TX, "17:10"), pesan.ping(TX, jam(8, 0)),
               pesan.menu(TX, "Rina"), pesan.status(TX, st(), date(2026, 12, 16)), pesan.rekap_minggu(TX, rekap()),
               pesan.rekap_bulan(TX, rekap()), pesan.jadwal(TX, "08:00", ["15:00", "16:30", "20:00"], "16:00"),
               pesan.bantuan(TX, ["15:00", "16:30", "20:00"])]
        out += [pesan.draft(TX, j, "2026-11-19", 2) for j in ("siap", "kosong", "cek", "sesi", "format", "sesi_hampir")]
        out += [pesan.masa(TX, j, 7, date(2027, 5, 15)) for j in ("h30", "h7", "terakhir", "selesai", "dini")]
        out += [pesan.gangguan(TX, "x", ["15:00"], "16:00", s) for s in ("sesi", "monev", "format")]
        out += [pesan.web_berubah(TX)]
        out += [pesan.ingat(TX, u, date(2026, 11, 20), 9, 60) for u in ("pertama", "kedua", "terakhir")]
        return out

    def test_tanpa_emoji_kecuali_centang(self):
        for p in self.semua():
            for ch in p.teks + (p.html or "") + "".join(lbl for baris in p.tombol for lbl, _ in baris):
                if ch != "✓":
                    self.assertNotEqual(unicodedata.category(ch), "So", f"emoji/simbol {ch!r} di: {p.teks[:40]}")

    def test_teks_cadangan_tanpa_tag_rich(self):
        for p in self.semua():
            for tag in ("<p>", "<table", "<br/>", "<li>"):
                self.assertNotIn(tag, p.teks)

    def test_kartu_isi_dan_tombol(self):
        p = pesan.kartu(TX, st(), NILAI, "Rina")   # 20 Nov 2026 = Jumat
        self.assertIn("<table bordered compact>", p.html)
        self.assertIn("<b>Batas</b>", p.teks)
        self.assertIn("Hari kerja terakhir minggu ini", p.teks)
        self.assertIn("<i>Semboyan Contoh</i>", p.html)
        self.assertEqual([d for _, d in p.tombol[0]], ["b:status", "b:minggu", "b:menu"])
        self.assertNotIn("<b>Batas</b>", pesan.kartu(TX, st(sudah=True)).teks)

    def test_nilai_bergilir_tiap_hari(self):
        dilihat = {pesan.nilai_hari_ini(NILAI, date(2026, 11, d))[1] for d in range(16, 22)}
        self.assertEqual(len(dilihat), 3)
        self.assertIsNone(pesan.nilai_hari_ini(None, date(2026, 11, 16)))

    def test_pengingat_tombol_dan_ringkas(self):
        p = pesan.ingat(TX, "pertama", date(2026, 11, 20), 9, 60)
        self.assertEqual(p.tombol, [[("Ingatkan 1 jam lagi", "tunda:pertama"), ("Sudah kirim, cek", "cek")]])
        self.assertIn("<code>/monev</code>", p.teks)
        r = pesan.ingat_selesai(TX, p.judul)
        self.assertTrue(r.teks.startswith("<s>Laporan hari ini belum diisi.</s>"))
        self.assertEqual(r.tombol, [])

    def test_menu_berganti_di_tempat(self):
        p = pesan.menu(TX, "Rina")
        self.assertIn("Mau lihat apa, Rina?", p.teks)
        self.assertTrue(all(d.startswith("v:") for baris in p.tombol for _, d in baris))
        self.assertEqual(pesan.status(TX, st(), None).tombol, [[("‹ Menu", "v:menu")]])

    def test_status_batas_hanya_bila_belum(self):
        self.assertIn("Laporan hari ini belum diisi.", pesan.status(TX, st(), None).teks)
        self.assertNotIn("<b>Batas</b>", pesan.status(TX, st(sudah=True), None).teks)
        self.assertIn("menunggu persetujuan mentor", pesan.status(TX, st(sudah=True), None).teks)

    def test_rekap_minggu_tabel(self):
        p = pesan.rekap_minggu(TX, rekap())
        self.assertIn("<tr><td>Sel 17</td><td>izin</td><td>menunggu</td></tr>", p.html)
        self.assertIn("• Sen 16 · hadir · disetujui", p.teks)

    def test_teks_dari_config(self):
        tx = pesan.Teks(muat({"bot": {"menu": {"judul": "Halo {nama}, pilih ya."}}})[0])
        self.assertIn("Halo Rina, pilih ya.", pesan.menu(tx, "Rina").teks)

    def test_menu_perintah_tanpa_spasi(self):
        self.assertIn("menu", [c for c, _ in MENU])
        for c, _ in MENU:
            self.assertRegex(c, r"^[a-z_]+$")


def rekap_data():
    return rekap()


class TelegramPalsu:
    def __init__(self):
        self.log, self.n = [], 100

    def kirim(self, chat, p):
        self.n += 1
        self.log.append(("kirim", self.n, p))
        return self.n

    def ubah(self, chat, mid, p):
        self.log.append(("ubah", mid, p))

    def jawab(self, cb, teks=None, alert=False):
        self.log.append(("jawab", cb, teks))

    def ketik(self, chat):
        self.log.append(("ketik",))


class TestBot(unittest.TestCase):
    def setUp(self):
        from monev.bot.app import Bot

        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"MONEV_DATA_DIR": self.tmp.name})
        self.env.start()
        self.data = {"status": st(), "periode": rekap(), "sesi_sampai": None}
        self.tg = TelegramPalsu()
        self.bot = Bot(Config(exists=True, path=Path("x")), self.tg, "1", log=lambda m: None,
                       ambil_data=lambda cfg, rekap=(): {**self.ambil(), **{k: rekap_data() for k in rekap}})
        self.gagal = None
        self.dibaca = 0

    def ambil(self):
        self.dibaca += 1
        if self.gagal:
            raise RuntimeError(self.gagal)
        return dict(self.data)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_satu_hari_kartu_diperbarui_pengingat_diringkas(self):
        self.bot.jadwal(jam(8, 0))
        self.bot.jadwal(jam(15, 0))
        self.assertEqual([x[0] for x in self.tg.log], ["kirim", "kirim"])
        kartu_id, ingat_id = self.tg.log[0][1], self.tg.log[1][1]
        self.data["status"] = st(sudah=True)
        self.tg.log.clear()
        self.bot.jadwal(jam(18, 0))
        jenis = [(x[0], x[1]) for x in self.tg.log]
        self.assertIn(("ubah", kartu_id), jenis)
        self.assertIn(("ubah", ingat_id), jenis)
        self.assertEqual([x for x in jenis if x[0] == "kirim"], [("kirim", 103)])   # konfirmasi terkirim
        self.tg.log.clear()
        self.bot.jadwal(jam(20, 0))                                                    # pengingat malam tidak dikirim
        self.assertEqual([x for x in self.tg.log if x[0] == "kirim"], [])

    def test_sebab_gangguan_dan_tombol(self):
        from monev.bot.app import MonevTidakSiap, SesiMati, sebab
        from monev.portal.api import ApiError, FormatBerubah

        self.assertEqual(sebab(SesiMati("x")), "sesi")
        self.assertEqual(sebab(ApiError("/users/me", 401)), "sesi")
        self.assertEqual(sebab(FormatBerubah("/users/me/home tanpa field is_holiday")), "format")
        self.assertEqual(sebab(ApiError("/holidays", 404)), "format")
        self.assertEqual(sebab(MonevTidakSiap("x")), "monev")
        self.assertEqual(sebab(ApiError("/users/me", 502)), "monev")
        self.assertEqual(sebab(ValueError("x")), "lain")
        p = pesan.gangguan(TX, "/users/me/home tanpa field is_holiday", ["15:00"], "16:30", "format")
        self.assertIn("Bentuk data Monev berubah (/users/me/home tanpa field is_holiday).", p.teks)
        self.assertEqual([d for _, d in p.tombol[0]], ["coba"])
        self.assertEqual([d for _, d in pesan.gangguan(TX, "x", ["15:00"], None, "sesi").tombol[0]], ["coba", "cara"])

    def test_gangguan_satu_pesan_lalu_pulih(self):
        self.gagal = "sesi Monev habis, perlu login ulang"
        self.bot.jadwal(jam(15, 0))
        self.bot.jadwal(jam(16, 30))
        self.assertEqual([x[0] for x in self.tg.log], ["kirim", "ubah"])
        self.assertIn("15.00 dan 16.30", self.tg.log[1][2].teks)
        self.gagal = None
        self.bot.jadwal(jam(18, 0))
        self.assertTrue(self.tg.log[-1][2].teks.startswith("<s>Bot belum bisa membaca Monev.</s>"))

    def test_tunda_lalu_ingat_lagi(self):
        self.bot.jadwal(jam(15, 0))
        mid = self.tg.log[-1][1]
        with mock.patch("monev.bot.app.datetime") as dt:
            dt.now.return_value = jam(15, 2)
            self.bot.tombol({"id": "c1", "data": "tunda:pertama", "message": {"message_id": mid, "chat": {"id": 1}}})
        self.assertIn("Diingatkan lagi pukul 16.02", self.tg.log[-1][2].teks)
        self.tg.log.clear()
        self.bot.jadwal(jam(16, 2))                 # Jumat: rekap 16.00 ikut terkirim
        ingat = [x for x in self.tg.log if x[0] == "kirim" and "belum diisi" in x[2].teks]
        self.assertEqual(len(ingat), 1)

    def tekan(self, data, mid=7):
        self.bot.tombol({"id": "c", "data": data, "message": {"message_id": mid, "chat": {"id": 1}}})

    def test_tombol_menu_ganti_di_tempat_dan_kartu_buka_baru(self):
        self.tekan("v:status")
        self.assertEqual([x[0] for x in self.tg.log], ["jawab", "ketik", "ubah", "ubah"])   # ⏳ lalu hasil
        self.assertTrue(all(x[1] == 7 for x in self.tg.log if x[0] == "ubah"))
        self.assertIn("Membaca Monev", self.tg.log[2][2].teks)
        self.assertIn("Data Monev pukul", self.tg.log[3][2].teks)
        self.assertIn(("↻ Segarkan", "s:status"), self.tg.log[3][2].tombol[0])
        self.tg.log.clear()
        self.bot.tombol({"id": "c", "data": "b:menu", "message": {"message_id": 7, "chat": {"id": 1}}})
        self.assertEqual([x[0] for x in self.tg.log], ["jawab", "kirim"])

    def test_cache_dipakai_lalu_segarkan_baca_ulang(self):
        self.tekan("v:status")
        self.tg.log.clear()
        self.tekan("v:status")                      # masih segar: tanpa ⏳ dan tanpa Chrome
        self.assertEqual([x[0] for x in self.tg.log], ["jawab", "ubah"])
        self.assertEqual(self.dibaca, 1)
        self.tekan("v:minggu")                      # rekap minggu belum ada di cache → baca
        self.assertEqual(self.dibaca, 2)
        self.tg.log.clear()
        self.tekan("s:status")                      # ↻ Segarkan selalu baca ulang, di tempat
        self.assertEqual(self.dibaca, 3)
        self.assertEqual([x[0] for x in self.tg.log], ["jawab", "ketik", "ubah", "ubah"])
        self.bot.jadwal(jam(15, 0))                 # jadwal selalu baca ulang
        self.assertEqual(self.dibaca, 4)

    def test_perintah_kirim_tunggu_lalu_ganti(self):
        self.bot.perintah("/status")
        self.assertEqual([x[0] for x in self.tg.log], ["ketik", "kirim", "ubah"])
        self.assertEqual(self.tg.log[2][1], self.tg.log[1][1])

    def test_tombol_dari_chat_lain_diabaikan(self):
        self.bot.tombol({"id": "c", "data": "v:status", "message": {"message_id": 7, "chat": {"id": 2}}})
        self.assertEqual([x[0] for x in self.tg.log], ["jawab"])


class TestTelegram(unittest.TestCase):
    def _tg(self, gagal=()):
        tg, panggilan = Telegram("t"), []

        def call(method, params, timeout=30):
            panggilan.append((method, params))
            if any(g(method, params) for g in gagal):
                raise RuntimeError(f"Telegram {method}: HTTP 400")
            return {"message_id": 5}
        tg._call = call
        return tg, panggilan

    def test_rich_dan_tombol(self):
        tg, c = self._tg()
        self.assertEqual(tg.kirim("1", pesan.status(TX, st(), None)), 5)
        self.assertEqual(c[0][0], "sendRichMessage")
        self.assertEqual(c[0][1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"], "v:menu")

    def test_rich_gagal_jatuh_ke_teks(self):
        tg, c = self._tg([lambda m, p: m == "sendRichMessage"])
        p = pesan.status(TX, st(), None)
        tg.kirim("1", p)
        self.assertEqual([m for m, _ in c], ["sendRichMessage", "sendMessage"])
        self.assertEqual(c[1][1]["text"], p.teks)

    def test_ubah_rich_lalu_teks_dan_tidak_berubah_diabaikan(self):
        tg, c = self._tg([lambda m, p: "rich_message" in p])
        tg.ubah("1", 9, pesan.menu(TX, "S"))
        self.assertEqual([("rich_message" in p, "text" in p) for _, p in c], [(True, False), (False, True)])
        tg2, _ = self._tg()
        tg2._call = mock.Mock(side_effect=RuntimeError("Telegram editMessageText: message is not modified"))
        tg2.ubah("1", 9, pesan.ingat_selesai(TX, "x"))   # tidak melempar

    def test_teks_biasa_tanpa_tombol(self):
        tg, c = self._tg()
        tg.kirim("1", pesan.ping(TX, jam(8, 0)))
        self.assertEqual(c[0][0], "sendMessage")
        self.assertNotIn("reply_markup", c[0][1])


class TestEnv(unittest.TestCase):
    def test_env_file_dan_os_environ(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, ".env").write_text("# komentar\nTELEGRAM_BOT_TOKEN='abc'\nTELEGRAM_CHAT_ID=123\n")
            with mock.patch.dict(os.environ, {"TELEGRAM_CHAT_ID": "999"}, clear=False):
                env = muat_env(Path(d))
        self.assertEqual(env["TELEGRAM_BOT_TOKEN"], "abc")
        self.assertEqual(env["TELEGRAM_CHAT_ID"], "999")


if __name__ == "__main__":
    unittest.main()
