import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from monev.config import Config
from monev.laporan.validasi import load_rules
from monev.sumber import catatan, git, jalur

CATATAN = """---
title: "Contoh pekerjaan"
status: "in_progress"
---

# Contoh pekerjaan

## Key technical decisions and pitfalls

- Decision (2026-11-16): sesuatu.

## Daily activity log

| Date | Observed progress/activity | Evidence/result | Blocker/decision |
|---|---|---|---|
| 2026-11-16 | kerja satu | hasil | - |
| 2026-11-17 | kerja dua | hasil | menunggu akses |

## Daily time log

| 2026-12-31 | 09:00 | 10:00 | bukan aktivitas |
"""
TERLARANG = [r["regex"] for r in load_rules()["terlarang"]]


class TestCatatan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.wr = self.home / "kerja" / "catatan"
        for proyek, n in (("alpha", 2), ("beta", 1)):
            (self.wr / proyek).mkdir(parents=True)
            for i in range(n):
                (self.wr / proyek / f"tugas-{i}.md").write_text(CATATAN, encoding="utf-8")
        (self.wr / "_knowledge" / "x").mkdir(parents=True)
        (self.wr / "_knowledge" / "x" / "catatan.md").write_text(CATATAN, encoding="utf-8")
        (self.home / "proyek" / "repo" / "docs").mkdir(parents=True)
        (self.home / "proyek" / "repo" / "docs" / "kontrak.md").write_text(
            "## Daily activity log\n| YYYY-MM-DD | contoh format |\n", encoding="utf-8")
        (self.home / ".tersembunyi").symlink_to(self.wr)   # jalan masuk kedua ke folder yang sama
        (self.wr / "alpha" / "sub" / "dalam").mkdir(parents=True)   # catatan bertingkat → bukan folder baru
        (self.wr / "alpha" / "sub" / "dalam" / "x.md").write_text(CATATAN, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_tanggal_hanya_dari_daily_activity_log(self):
        self.assertEqual(catatan.tanggal_catatan(self.wr / "alpha" / "tugas-0.md"), ["2026-11-16", "2026-11-17"])
        self.assertEqual(catatan.tanggal_catatan(self.home / "proyek" / "repo" / "docs" / "kontrak.md"), [])

    def test_cari_mengenali_isi_bukan_nama(self):
        hasil = catatan.cari([self.home])
        self.assertEqual(len(hasil), 1, hasil)           # symlink & folder tersembunyi tidak menggandakan
        self.assertEqual(hasil[0]["dir"], str(self.wr.resolve()))
        self.assertEqual(hasil[0]["file"], 3)            # _knowledge dilewati
        self.assertEqual(hasil[0]["proyek"], 2)
        self.assertEqual(hasil[0]["tanggal_terakhir"], "2026-11-17")

    def test_baca_hanya_bagian_kontrak(self):
        h = catatan.baca(self.wr, "2026-11-17", ["_knowledge"])
        self.assertEqual(len(h), 3)                      # 3 file di alpha/beta; _knowledge & sub-subfolder tidak
        p = h[0]
        self.assertEqual((p["judul"], p["status"], p["proyek"]), ("Contoh pekerjaan", "in_progress", "alpha"))
        self.assertEqual(p["aktivitas"], [{"kegiatan": "kerja dua", "bukti": "hasil", "blocker": "menunggu akses"}])
        self.assertEqual(p["pembelajaran"], [])
        h16 = catatan.baca(self.wr, "2026-11-16")
        self.assertEqual(h16[0]["pembelajaran"], [{"jenis": "Decision", "teks": "sesuatu."}])
        self.assertEqual(catatan.baca(self.wr, "2026-12-31"), [])   # baris Daily time log tidak terbaca

    def test_ringkas(self):
        r = catatan.ringkas(self.wr, ["_knowledge"])
        self.assertEqual((r["ada"], r["file"], r["proyek"], r["tanggal_terakhir"]), (True, 3, 2, "2026-11-17"))
        self.assertFalse(catatan.ringkas(self.home / "tidak-ada")["ada"])


class TestBersihkan(unittest.TestCase):
    def test_buang_data_terlarang_dan_nama(self):
        t = git.bersihkan("fix: perbaiki login (#123) lihat https://x.y/z oleh Budi\nbaris kedua", TERLARANG, ["Budi"])
        self.assertEqual(t, "fix: perbaiki login lihat oleh")
        self.assertEqual(git.bersihkan("Revert a1b2c3d4e5", TERLARANG, []), "Revert")


def palsu(respons: dict):
    """_jalankan palsu: cocokkan potongan argumen terakhir dengan kunci di `respons`."""
    def jalankan(args, timeout=30):
        kunci = args[-1] if not args[-1].startswith("--") else args[-3]
        for pola, isi in respons.items():
            if pola in kunci:
                if isinstance(isi, Exception):
                    raise isi
                return isi if isinstance(isi, str) else json.dumps(isi)
        return "[]"
    return jalankan


class TestGithub(unittest.TestCase):
    EVENTS = [
        {"type": "PushEvent", "created_at": "2026-11-17T02:00:00Z", "repo": {"name": "org/app"},
         "payload": {"ref": "refs/heads/fitur", "head": "aaa", "before": "bbb"}},
        {"type": "PullRequestEvent", "created_at": "2026-11-17T05:00:00Z", "repo": {"name": "org/app"},
         "payload": {"action": "merged", "number": 7, "pull_request": {"number": 7}}},
        {"type": "PullRequestEvent", "created_at": "2026-11-17T05:01:00Z", "repo": {"name": "org/app"},
         "payload": {"action": "labeled", "number": 7}},
        {"type": "PushEvent", "created_at": "2026-11-15T02:00:00Z", "repo": {"name": "org/app"},
         "payload": {"ref": "refs/heads/main", "head": "ccc"}},
    ]
    COMMITS = [
        {"sha": "c1", "parents": [{}], "commit": {"author": {"date": "2026-11-17T01:30:00Z"},
                                                  "message": "feat: tambah halaman rekap\n\nisi"}},
        {"sha": "c2", "parents": [{}, {}], "commit": {"author": {"date": "2026-11-17T01:40:00Z"},
                                                      "message": "Merge branch x"}},
    ]

    def test_commit_semua_branch_pr_dan_waktu_wib(self):
        respons = {"/events?": self.EVENTS, "commits?sha=aaa": self.COMMITS,
                   "pulls/7": {"title": "Rekap mingguan (#7)"}}
        with mock.patch.object(git, "_jalankan", side_effect=palsu(respons)):
            a = git.github(date(2026, 11, 17), "saya")
        self.assertEqual([(x["jenis"], x["aksi"]) for x in a], [("commit", "commit"), ("pr", "merged")])
        cfg = Config(exists=True, path=Path("x"), git_penyedia=["github"])
        with mock.patch.object(git, "_jalankan", side_effect=palsu(respons)), \
                mock.patch.object(git, "status_github", return_value={"ok": True, "akun": "saya"}):
            h = git.ambil_bukti(cfg, date(2026, 11, 17), TERLARANG)
        self.assertEqual(h["penyedia"]["github"], {"ok": True, "jumlah": 2})
        self.assertEqual([(x["waktu"], x["judul"]) for x in h["aktivitas"]],
                         [("08:30", "feat: tambah halaman rekap"), ("12:00", "Rekap mingguan")])
        self.assertNotIn("org/app", json.dumps(h))

    def test_head_hilang_pakai_nama_branch(self):
        respons = {"/events?": self.EVENTS[:1], "commits?sha=aaa": git.GagalPerintah("404"),
                   "commits?sha=fitur": self.COMMITS[:1]}
        with mock.patch.object(git, "_jalankan", side_effect=palsu(respons)):
            a = git.github(date(2026, 11, 17), "saya")
        self.assertEqual(len(a), 1)

    def test_belum_login(self):
        cfg = Config(exists=True, path=Path("x"), git_penyedia=["github"])
        with mock.patch.object(git, "status_github", return_value={"ok": False, "pesan": "gh belum login"}):
            h = git.ambil_bukti(cfg, date(2026, 11, 17), TERLARANG)
        self.assertEqual(h["penyedia"]["github"], {"ok": False, "pesan": "gh belum login"})
        self.assertEqual(h["aktivitas"], [])


class TestGitlab(unittest.TestCase):
    def test_push_mr_komentar(self):
        events = [
            {"action_name": "pushed to", "created_at": "2026-11-17T03:00:00Z", "target_type": None,
             "push_data": {"commit_count": 3, "commit_title": "perbaiki alert disk"}},
            {"action_name": "accepted", "created_at": "2026-11-17T04:00:00Z", "target_type": "MergeRequest",
             "target_title": "Alert disk !12"},
            {"action_name": "commented on", "created_at": "2026-11-17T04:30:00Z", "target_type": "DiffNote",
             "target_title": "Alert disk", "note": {"noteable_type": "MergeRequest"}},
            {"action_name": "pushed new", "created_at": "2026-11-17T05:00:00Z", "push_data": {"commit_count": 0}},
            {"action_name": "opened", "created_at": "2026-11-16T03:00:00Z", "target_type": "Issue", "target_title": "x"},
        ]
        with mock.patch.object(git, "_jalankan", side_effect=palsu({"events?": events})):
            a = git.gitlab(date(2026, 11, 17), "gitlab.contoh.id")
        self.assertEqual([(x["jenis"], x["aksi"]) for x in a], [("commit", "push"), ("mr", "accepted"), ("review", "komentar")])
        self.assertEqual(a[0]["jumlah"], 3)


class TestJalur(unittest.TestCase):
    def test_semua_kosong_memberi_langkah(self):
        j = jalur.cek_jalur(Config(exists=True, path=Path("x")))
        self.assertTrue(j["A"]["ok"])
        for k in "BCD":
            self.assertFalse(j[k]["aktif"])
            self.assertTrue(j[k]["langkah"])

    def test_git_dan_catatan_aktif(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "p").mkdir()
            (Path(t) / "p" / "a.md").write_text(CATATAN, encoding="utf-8")
            cfg = Config(exists=True, path=Path("x"), workrecords_dir=Path(t), git_penyedia=["github"],
                         mcp_awalan_tool=["mcp__kantor__"])
            with mock.patch.object(jalur, "status_github", return_value={"ok": True, "akun": "saya"}):
                j = jalur.cek_jalur(cfg)
        self.assertEqual((j["B"]["ok"], j["C"]["ok"], j["D"]["ok"]), (True, None, True))
        self.assertIn("@saya", j["B"]["detail"])


if __name__ == "__main__":
    unittest.main()
