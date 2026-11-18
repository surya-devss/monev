"""Menjaga dokumen tetap cocok dengan kode: perintah CLI, paket, file tes, dan tautan antar dokumen."""

import contextlib
import io
import re
import unittest
from pathlib import Path

from monev.cli import PERINTAH, main

REPO = Path(__file__).resolve().parent.parent
PEMAKAIAN = (REPO / "docs/panduan/pemakaian.md").read_text(encoding="utf-8")
ARSITEKTUR = (REPO / "docs/teknis/arsitektur.md").read_text(encoding="utf-8")
TAUTAN = re.compile(r"\]\(([^)\s]+)\)")


def _dokumen() -> list[Path]:
    akar = [REPO / "README.md", REPO / "CHANGELOG.md", REPO / "CONTRIBUTING.md"]
    return akar + sorted((REPO / "docs").rglob("*.md")) + sorted((REPO / "plugin").rglob("*.md"))


def _tanpa_blok_kode(teks: str) -> str:
    return re.sub(r"```.*?```", "", teks, flags=re.DOTALL)


class TestDokumen(unittest.TestCase):
    def test_semua_perintah_cli_ada_di_pemakaian(self):
        for perintah in sorted(PERINTAH):
            with self.subTest(perintah=perintah):
                self.assertIn(f"`monev {perintah}", PEMAKAIAN)

    def test_pilihan_coba_bot_sama_dengan_cli(self):
        keluar = io.StringIO()
        with contextlib.redirect_stdout(keluar), self.assertRaises(SystemExit):
            main(["bot", "--help"])
        pilihan = re.search(r"--coba \{([^}]+)\}", keluar.getvalue()).group(1).split(",")
        baris = next(b for b in PEMAKAIAN.splitlines() if b.startswith("| `monev bot ["))
        tertulis = re.search(r"--coba ([^\]]+)\]", baris).group(1).replace("\\", "").split("|")
        self.assertEqual(sorted(tertulis), sorted(pilihan))

    def test_semua_paket_ada_di_arsitektur(self):
        for paket in sorted(p.parent.name for p in (REPO / "monev").glob("*/__init__.py")):
            with self.subTest(paket=paket):
                self.assertRegex(ARSITEKTUR, rf"[├└]── {paket}/")

    def test_semua_file_tes_ada_di_arsitektur(self):
        for tes in sorted(p.stem for p in (REPO / "tests").glob("test_*.py")):
            with self.subTest(tes=tes):
                self.assertIn(tes, ARSITEKTUR)

    def test_tautan_antar_dokumen_tidak_rusak(self):
        for dok in _dokumen():
            for tujuan in TAUTAN.findall(_tanpa_blok_kode(dok.read_text(encoding="utf-8"))):
                if re.match(r"[a-z]+:", tujuan) or tujuan.startswith("#"):
                    continue
                with self.subTest(dokumen=dok.relative_to(REPO).as_posix(), tujuan=tujuan):
                    self.assertTrue((dok.parent / tujuan.split("#")[0]).exists())


if __name__ == "__main__":
    unittest.main()
