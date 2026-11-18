import unittest
from datetime import date

from monev.portal.rekap import hitung, jendela, libur_berlaku

ME = {"internship_start_date": "2026-11-16T00:00:00+07:00", "internship_end_date": "2027-05-15T23:59:59+07:00",
      "off_days": ["SATURDAY", "SUNDAY"], "internship_location_province_code": "32",
      "internship_location_regency_code": "3273"}
HOL = [
    {"date": "2026-11-18", "name": "Libur Nasional Uji", "scope": "NATIONAL", "type": "NATIONAL"},
    {"date": "2026-11-19", "name": "Libur Provinsi Lain", "scope": "PROVINCE", "type": "REGIONAL", "province_code": "96"},
    {"date": "2026-11-20", "name": "Libur Provinsi Sendiri", "scope": "PROVINCE", "type": "REGIONAL", "province_code": "32"},
]


def att(d, status="PRESENT", ap="SUBMITTED"):
    return {"date": d, "status": status, "approval_status": ap}


class TestLibur(unittest.TestCase):
    def test_hanya_nasional_dan_provinsi_sendiri(self):
        lib = libur_berlaku(HOL, ME)
        self.assertIn(date(2026, 11, 18), lib)
        self.assertNotIn(date(2026, 11, 19), lib)
        self.assertIn(date(2026, 11, 20), lib)


class TestHitung(unittest.TestCase):
    def test_minggu_penuh(self):
        # 16–20 Nov: 18 & 20 libur → hari kerja 16, 17, 19
        atts = [att("2026-11-16", ap="APPROVED"), att("2026-11-17"), att("2026-11-19")]
        r = hitung(ME, atts, [], HOL, date(2026, 11, 16), date(2026, 11, 20), date(2026, 11, 20))
        self.assertEqual(r["hari_kerja"], 3)
        self.assertEqual(r["hadir"], 3)
        self.assertTrue(r["penuh"])
        self.assertEqual(r["persetujuan"], {"menunggu": 2, "disetujui": 1, "ditolak": 0})
        self.assertEqual(r["periode"]["status"], "aman")

    def test_hari_ini_belum_isi_bukan_absen(self):
        r = hitung(ME, [att("2026-11-16")], [], [], date(2026, 11, 16), date(2026, 11, 17), date(2026, 11, 17))
        self.assertEqual(r["belum"], 1)
        self.assertEqual(r["absen"], 0)
        self.assertTrue(r["penuh"])

    def test_absen_berturut_dan_ditolak(self):
        # 16 hadir ditolak mentor, 17 & 18 kosong (lewat) → 3 berturut → peringatan
        atts = [att("2026-11-16", ap="REJECTED")]
        r = hitung(ME, atts, [], [], date(2026, 11, 16), date(2026, 11, 19), date(2026, 11, 19))
        self.assertEqual(r["ditolak"], 1)
        self.assertEqual(r["absen"], 2)
        self.assertEqual(r["periode"]["absen_berturut"], 3)
        self.assertEqual(r["periode"]["status"], "peringatan")
        self.assertFalse(r["penuh"])

    def test_izin_dan_revisi(self):
        atts = [att("2026-11-16"), att("2026-11-17", status="ON_LEAVE")]
        logs = [{"date": "2026-11-16", "state": "NEEDS_REVISION"}]
        r = hitung(ME, atts, logs, [], date(2026, 11, 16), date(2026, 11, 17), date(2026, 11, 17))
        self.assertEqual(r["izin"], 1)
        self.assertEqual(r["periode"]["izin_dibayar_sisa"], 2)
        self.assertEqual(r["perlu_revisi"], ["2026-11-16"])
        self.assertFalse(r["penuh"])

    def test_sebelum_mulai_magang_tidak_dihitung(self):
        r = hitung(ME, [att("2026-11-16")], [], [], date(2026, 11, 9), date(2026, 11, 16), date(2026, 11, 16))
        self.assertEqual(r["dari"], "2026-11-16")
        self.assertEqual(r["hari_kerja"], 1)


class TestUntukBot(unittest.TestCase):
    def test_harian_dan_ditolak(self):
        atts = [att("2026-11-16", ap="APPROVED"), att("2026-11-17", ap="REJECTED")]
        logs = [{"date": "2026-11-16", "state": "NEEDS_REVISION"}]
        r = hitung(ME, atts, logs, [], date(2026, 11, 16), date(2026, 11, 18), date(2026, 11, 18))
        self.assertEqual([h["kehadiran"] for h in r["harian"]], ["hadir", "ditolak", "belum"])
        self.assertEqual([h["mentor"] for h in r["harian"]], ["revisi", "ditolak", "-"])
        self.assertEqual(r["ditolak_tanggal"], ["2026-11-17"])

    def test_hari_kerja_terakhir_bulan(self):
        # 30 Nov 2026 = Senin (hari kerja terakhir); 27 Nov (Jumat) bukan
        self.assertTrue(hitung(ME, [], [], [], date(2026, 11, 30), date(2026, 11, 30),
                               date(2026, 11, 30))["hari_kerja_terakhir_bulan"])
        self.assertFalse(hitung(ME, [], [], [], date(2026, 11, 27), date(2026, 11, 27),
                                date(2026, 11, 27))["hari_kerja_terakhir_bulan"])


class TestJendela(unittest.TestCase):
    def test_minggu_dan_bulan(self):
        today = date(2026, 11, 19)  # Kamis
        self.assertEqual(jendela("minggu", today, date(2026, 11, 16))[0], date(2026, 11, 16))
        self.assertEqual(jendela("bulan", today, date(2026, 11, 16))[0], date(2026, 11, 1))


if __name__ == "__main__":
    unittest.main()
