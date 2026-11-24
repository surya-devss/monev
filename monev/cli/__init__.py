"""CLI `monev`: parser dan pembagi perintah. Isi tiap perintah ada di modul per kelompok:

- `akun.py`     init, config, login, logout, doctor
- `laporan.py`  status, rekap, draft, validate, eval
- `kirim.py`    kirim, extension
- `bot.py`      bot
- `agen.py`     hermes
- `sumber.py`   sumber cari, bukti
- `jadwal.py`   jadwal pasang, status, lepas, jalan
- `_umum.py`    kode keluar, tanya-jawab terminal, config otomatis, sesi Chrome A
"""

from __future__ import annotations

import argparse
import sys

from .. import __version__
from .agen import cmd_hermes
from .akun import cmd_config, cmd_doctor, cmd_init, cmd_login, cmd_logout
from .bot import cmd_bot
from .jadwal import cmd_jadwal
from .kirim import cmd_extension, cmd_kirim
from .laporan import cmd_draft, cmd_eval, cmd_rekap, cmd_status, cmd_validate
from .sumber import cmd_bukti, cmd_sumber

PERINTAH = {"init", "login", "logout", "doctor", "status", "rekap", "kirim", "extension", "hermes", "bot",
            "config", "draft", "validate", "eval", "sumber", "bukti", "jadwal"}


def stdio_utf8() -> None:
    """Keluaran CLI selalu UTF-8.

    Di Windows, keluaran yang di-pipe atau ditangkap agent (Claude Code, Hermes) memakai encoding lokal seperti cp1252,
    yang tidak punya ✓ ✗ → sehingga print gagal dengan UnicodeEncodeError.
    """
    for s in (sys.stdout, sys.stderr):
        enc = (getattr(s, "encoding", None) or "").lower().replace("-", "").replace("_", "")
        if enc != "utf8" and hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    stdio_utf8()
    ap = argparse.ArgumentParser(prog="monev", description="Asisten laporan harian Monev MagangHub")
    ap.add_argument("--version", action="version", version=f"monev {__version__}")
    sub = ap.add_subparsers(dest="cmd", metavar="{status,rekap,kirim,jadwal,bot,extension,hermes,doctor,login,logout,config,draft,validate,eval,init,sumber,bukti}",
                            help="tanpa perintah = status")

    p = sub.add_parser("init", help="buat config otomatis (opsional; status/doctor membuatnya sendiri)")
    p.add_argument("--force", action="store_true", help="buat ulang config")
    p.add_argument("--posisi", help="timpa posisi (default: dari profil Monev)")
    p.add_argument("--tim")
    p.add_argument("--workrecords", default=None, help="timpa folder work records ('' = tidak pakai)")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("login", help="buka Chrome monev, login manual sekali")
    p.add_argument("--timeout", type=int, default=600, help="detik menunggu login (default 600)")
    p.add_argument("--uji-lokasi", action="store_true", help="(diagnosa) tes lokasi di Chrome monev")
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("logout", help="hapus sesi CLI (profil Chrome monev)")
    p.add_argument("--ya", action="store_true", help="tanpa konfirmasi")
    p.set_defaults(func=cmd_logout)

    p = sub.add_parser("doctor", help="cek config, Chrome, sesi, refresh token, jalur sumber bahan")
    p.add_argument("--headful", action="store_true", help="tampilkan jendela Chrome")
    p.add_argument("--uji-lokasi", action="store_true", help="(diagnosa) tes lokasi di Chrome monev")
    p.add_argument("--no-login", action="store_true", help="jangan buka Chrome untuk login otomatis")
    p.add_argument("--tanpa-sesi", action="store_true", help="lewati cek sesi Monev (tanpa membuka Chrome)")
    p.add_argument("--json", action="store_true", help="keluaran JSON (untuk agent / /monev setup)")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("sumber", help="work records: cari foldernya / baca bahan satu tanggal / cek kesiapan bahan")
    p.add_argument("aksi", choices=["cari", "baca", "siap"])
    p.add_argument("--tanggal", help="untuk `baca` dan `siap`: YYYY-MM-DD (default hari ini)")
    p.add_argument("--logtime", type=int, help="untuk `siap`: jumlah entri logtime tanggal itu, bila logtime dipakai")
    p.add_argument("--akar", action="append", help="folder awal pencarian (boleh berulang; bawaan: home)")
    p.add_argument("--kedalaman", type=int, default=5, help="kedalaman folder maksimal (bawaan 5)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_sumber)

    p = sub.add_parser("bukti", help="aktivitas Git milikmu (commit, PR/MR, review) lewat gh/glab, read-only")
    p.add_argument("--tanggal", help="YYYY-MM-DD (default hari ini, WIB)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_bukti)

    p = sub.add_parser("status", help="status laporan hari ini (read-only)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--headful", action="store_true")
    p.add_argument("--no-login", action="store_true", help="jangan buka Chrome untuk login otomatis (untuk cron)")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("rekap", help="rekap kehadiran: hadir/izin/absen, persetujuan mentor, peringatan (read-only)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--minggu", action="store_true", help="Senin minggu ini s.d. hari ini")
    g.add_argument("--bulan", action="store_true", help="periode berjalan (bulan sejak tanggal mulai magang) s.d. hari ini")
    p.add_argument("--dari", help="YYYY-MM-DD (timpa awal jendela)")
    p.add_argument("--sampai", help="YYYY-MM-DD (timpa akhir jendela)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--headful", action="store_true")
    p.add_argument("--no-login", action="store_true", help="jangan buka Chrome untuk login otomatis (untuk cron/bot)")
    p.set_defaults(func=cmd_rekap)

    p = sub.add_parser("kirim", help="isi & kirim laporan lewat extension monev di Chrome kamu")
    p.add_argument("file", nargs="?", help="draft .json/.md yang sudah lolos validate")
    p.add_argument("--uji", action="store_true", help="isi form + cek lokasi saja; tidak dicentang, tidak dikirim")
    p.add_argument("--ping", action="store_true", help="cek koneksi CLI ↔ extension ↔ Monev")
    p.add_argument("--timeout", type=int, default=120, help="detik menunggu extension selesai (default 120)")
    p.set_defaults(func=cmd_kirim)

    p = sub.add_parser("jadwal", help="draft otomatis di laptop: pasang, status, lepas")
    p.add_argument("aksi", choices=["pasang", "status", "lepas", "jalan"])
    p.add_argument("--kering", action="store_true", help="untuk `jalan`: tampilkan keputusan tanpa menyusun atau mengirim pesan")
    p.set_defaults(func=cmd_jadwal)

    p = sub.add_parser("extension", help="pasang jembatan CLI ↔ extension Chrome")
    p.add_argument("aksi", nargs="?", choices=["install", "info", "coba"], default="info")
    p.add_argument("jenis", nargs="?", choices=["pagi", "fokus", "ingat"],
                   help="untuk `coba`: notifikasi yang ditampilkan sekarang (bawaan: ingat)")
    p.set_defaults(func=cmd_extension)

    p = sub.add_parser("bot", help="bot Telegram pribadi: pengingat jam kerja, rekap, /status (tanpa AI)")
    p.add_argument("--chat-id", action="store_true", help="tampilkan chat id dari pesan /start ke bot")
    p.add_argument("--coba", choices=["kartu", "ingat", "status", "rekap", "menu", "help"],
                   help="kirim pesan contoh sekarang (kartu/status/rekap memakai data Monev asli)")
    p.set_defaults(func=cmd_bot)

    p = sub.add_parser("hermes", help="pasang/lepas skill /monev di profile Hermes")
    p.add_argument("aksi", choices=["install", "uninstall"])
    p.add_argument("--profile", help="named profile (~/.hermes/profiles/<nama>); default: profile utama")
    p.add_argument("--hermes-home", help="path profile Hermes langsung")
    p.add_argument("--symlink", action="store_true", help="development: skill menunjuk ke repo")
    p.add_argument("--force", action="store_true", help="timpa path yang bukan milik installer (cek dulu)")
    p.set_defaults(func=cmd_hermes)

    p = sub.add_parser("config", help="lihat config (--edit untuk mengubah)")
    p.add_argument("--edit", action="store_true", help="buka config di $EDITOR")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("draft", help="buat template laporan untuk ditulis sendiri")
    p.add_argument("-o", "--output", help="file tujuan (default monev-<tanggal>.md)")
    p.add_argument("--tanggal", help="YYYY-MM-DD (default hari ini)")
    p.add_argument("--hari-pertama", action="store_true", help="tampilkan saran kegiatan hari pertama")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_draft)

    p = sub.add_parser("validate", help="cek draft: panjang, data terlarang, kemiripan")
    p.add_argument("file", help="draft .md atau .json")
    p.add_argument("--json", action="store_true")
    p.add_argument("--bebas-tanggal", action="store_true", help="jangan wajibkan tanggal = hari ini")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("eval", help="skor draft latihan terhadap laporan yang sudah terkirim (read-only)")
    p.add_argument("folder", nargs="?", help="folder draft `<nama>-YYYY-MM-DD.json` (default folder draft monev)")
    p.add_argument("--lewati", action="append", metavar="YYYY-MM-DD", help="tanggal yang tidak dinilai (boleh berulang)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_eval)

    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in PERINTAH | {"-h", "--help", "--version"}:
        argv = ["status", *argv]          # `monev` / `monev --json` → status
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
