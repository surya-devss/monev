import unittest
from datetime import date

from monev.portal.rekap import hitung, jendela, libur_berlaku, periode_berjalan

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
        self.assertEqual(r["disetujui_tanggal"], ["2026-11-16"])

    def test_hari_kerja_terakhir_periode(self):
        # Periode 1 = 16 Nov–15 Des 2026. 15 Des = Selasa (hari kerja terakhir); 30 Nov dan 14 Des bukan
        terakhir = lambda d: hitung(ME, [], [], [], d, d, d)["hari_kerja_terakhir_periode"]  # noqa: E731
        self.assertTrue(terakhir(date(2026, 12, 15)))
        self.assertFalse(terakhir(date(2026, 12, 14)))
        self.assertFalse(terakhir(date(2026, 11, 30)))


class TestPeriode(unittest.TestCase):
    def test_periode_bulan_sejak_mulai(self):
        mulai = date(2026, 11, 16)
        self.assertEqual(periode_berjalan(mulai, date(2026, 11, 19)), (1, date(2026, 11, 16), date(2026, 12, 15)))
        self.assertEqual(periode_berjalan(mulai, date(2026, 12, 15)), (1, date(2026, 11, 16), date(2026, 12, 15)))
        self.assertEqual(periode_berjalan(mulai, date(2026, 12, 16)), (2, date(2026, 12, 16), date(2027, 1, 15)))
        self.assertEqual(periode_berjalan(mulai, date(2027, 5, 15)), (6, date(2027, 4, 16), date(2027, 5, 15)))

    def test_mulai_akhir_bulan_dipotong(self):
        self.assertEqual(periode_berjalan(date(2027, 1, 31), date(2027, 3, 1)), (2, date(2027, 2, 28), date(2027, 3, 30)))

    def test_absen_dan_izin_per_periode_berturut_lintas_periode(self):
        # Periode 1: izin 4 Des dan absen 14–15 Des (2 hari). Periode 2 mulai 16 Des: absen 16 Des.
        hadir = [att(d.isoformat()) for d in (date(2026, 11, 16) + __import__("datetime").timedelta(days=i)
                                               for i in range(28)) if d.weekday() < 5 and d.day != 4]
        atts = hadir + [att("2026-12-04", status="ON_LEAVE")]
        atts = [a for a in atts if a["date"] not in ("2026-12-14", "2026-12-15")]
        r = hitung(ME, atts, [], [], date(2026, 12, 16), date(2026, 12, 17), date(2026, 12, 17))
        p = r["periode"]
        self.assertEqual((p["ke"], p["awal"], p["akhir"]), (2, "2026-12-16", "2027-01-15"))
        self.assertEqual(p["izin"], 0)                     # izin periode 1 tidak terbawa
        self.assertEqual(p["absen_total"], 1)              # hanya 16 Des
        self.assertEqual(p["absen_berturut"], 3)           # 14, 15, 16 Des tetap berturut


class TestBentukData(unittest.TestCase):
    def test_field_wajib_hilang_ditolak(self):
        from monev.portal.api import FormatBerubah, wajib

        home = {"date": "2026-11-19", "is_holiday": False, "is_scheduled_off_day": False, "has_attendance": True,
                "active_internship": True}
        self.assertIs(wajib("/users/me/home", home), home)
        self.assertEqual(wajib("/attendances", []), [])
        with self.assertRaisesRegex(FormatBerubah, "is_holiday"):
            wajib("/users/me/home", {k: v for k, v in home.items() if k != "is_holiday"})
        with self.assertRaisesRegex(FormatBerubah, "approval_status"):
            wajib("/attendances", [att("2026-11-19"), {"date": "2026-11-18", "status": "PRESENT"}])


class TestJendela(unittest.TestCase):
    def test_minggu_dan_bulan(self):
        today = date(2026, 11, 19)  # Kamis
        self.assertEqual(jendela("minggu", today, date(2026, 11, 16))[0], date(2026, 11, 16))
        self.assertEqual(jendela("bulan", today, date(2026, 11, 16))[0], date(2026, 11, 16))   # periode berjalan
        self.assertEqual(jendela("bulan", date(2026, 12, 20), date(2026, 11, 16))[0], date(2026, 12, 16))


if __name__ == "__main__":
    unittest.main()
