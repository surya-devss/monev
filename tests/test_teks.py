import re
import unittest

from monev import teks
from monev.laporan.validasi import load_rules


class TestTeksBawaan(unittest.TestCase):
    def test_placeholder_dikenal(self):
        for kunci, t in teks.semua_teks(teks.bawaan()):
            with self.subTest(kunci=kunci):
                self.assertLessEqual(teks.placeholder(t), teks.PLACEHOLDER)

    def test_lolos_aturan_tanda_baca_laporan(self):
        pola = [re.compile(r["regex"]) for r in load_rules()["peringatan"]
                if "tanda baca" in r["nama"] or "titik dua" in r["nama"]]
        self.assertEqual(len(pola), 2)
        for kunci, t in teks.semua_teks(teks.bawaan()):
            with self.subTest(kunci=kunci):
                self.assertFalse(any(p.search(t) for p in pola), t)

    def test_timpa_sebagian_dan_tipe_salah_diabaikan(self):
        hasil, asing = teks.muat({"fokus": {"poin": ["Satu."], "judul": 5}, "baru": {"x": "y"}})
        self.assertEqual(hasil["fokus"]["poin"], ["Satu."])
        self.assertEqual(hasil["fokus"]["judul"], teks.bawaan()["fokus"]["judul"])
        self.assertEqual(hasil["pagi"], teks.bawaan()["pagi"])
        self.assertEqual(asing, ["pesan.baru"])


if __name__ == "__main__":
    unittest.main()
