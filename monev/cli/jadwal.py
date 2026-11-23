"""Perintah `monev jadwal`: pasang, status, lepas, dan proses draft terjadwal."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from ..bot.jadwal import SESI_PERINGATAN_HARI, WIB
from ..config import REPO_ROOT, data_dir
from ._umum import EXIT_FAIL, EXIT_NEED_LOGIN, EXIT_OK, _config_auto, _session_or_login, _today


def _f_kabar() -> Path:
    return data_dir() / "jadwal-kabar.json"


def sisa_sesi(sampai, tanggal: str) -> int | None:
    """Hari tersisa sampai sesi Monev laptop habis, dihitung dari tanggal Monev hari ini."""
    if not sampai:
        return None
    return (sampai.astimezone(WIB).date() - datetime.fromisoformat(tanggal[:10]).date()).days


def _kabari(cfg, tanggal: str, jenis: str, sampai: str | None = None, sisa: int | None = None) -> None:
    """Satu jenis pesan hanya dikirim sekali per hari. Gagal mengirim tidak menggagalkan proses."""
    from ..bot import pesan as P
    from ..bot.telegram import Telegram, muat_env
    from ..otomasi.susun import catat_kabar, sudah_dikabari
    from ..teks import muat

    if sudah_dikabari(_f_kabar(), tanggal, jenis):
        return
    env = muat_env()
    if not (env.get("TELEGRAM_BOT_TOKEN") and env.get("TELEGRAM_CHAT_ID")):
        print("! Telegram belum diatur, pesan dilewati.")
        return
    try:
        tx = P.Teks(muat(getattr(cfg, "pesan", None))[0])
        Telegram(env["TELEGRAM_BOT_TOKEN"]).kirim(env["TELEGRAM_CHAT_ID"], P.draft(tx, jenis, sampai or tanggal, sisa))
    except RuntimeError as ex:
        print(f"! Pesan Telegram gagal: {ex}")
        return
    catat_kabar(_f_kabar(), tanggal, jenis)


def _bahan(cfg, tanggal: str) -> str:
    from ..sumber.catatan import baca
    from ..sumber.kesiapan import periksa

    folder = cfg.workrecords_dir
    if not (folder and folder.is_dir()):
        return "siap" if cfg.mcp_awalan_tool or cfg.git_penyedia else "kosong"
    return periksa(baca(folder, tanggal, cfg.lewati_folder + cfg.lewati_proyek), folder)["status"]


def _terima(cfg, hasil: Path, tujuan: Path, tanggal: str) -> bool:
    """Periksa ulang hasil agent di Python. Draft selalu disimpan belum disetujui."""
    from ..laporan.draft import load
    from ..laporan.validasi import load_history, load_rules, validate
    from .laporan import saringan_nama

    try:
        d = load(hasil)
    except (OSError, ValueError, TypeError):
        return False
    if d.date != tanggal or d.status != "PRESENT" or d.revisi:
        return False
    d.approved = False
    rules = load_rules()
    riwayat = load_history(data_dir() / "arsip", rules.get("kemiripan", {}).get("riwayat", 10), exclude_date=d.date)
    res = validate(d, rules, cfg.jangan_disebut, riwayat, today=tanggal, saringan=saringan_nama(cfg, d, rules))
    if not res.ok:
        return False
    d.keraguan += [f"Peringatan validasi: {w}" for w in res.warnings]
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    sementara = tujuan.with_suffix(".tmp")
    sementara.write_text(d.to_json(), encoding="utf-8")
    os.replace(sementara, tujuan)
    return True


def _susun(cfg, tanggal: str, tujuan: Path) -> bool:
    from ..otomasi.susun import BATAS_DETIK, perintah_claude, prompt

    kerja = data_dir() / "otomatis"
    shutil.rmtree(kerja, ignore_errors=True)
    kerja.mkdir(parents=True, mode=0o700)
    hasil = kerja / f"{tanggal}.json"
    try:
        # Keluaran agent bisa memuat isi laporan, jadi tidak diteruskan ke log.
        p = subprocess.run(perintah_claude(REPO_ROOT, cfg.path, kerja, cfg.jadwal_alat_mcp), cwd=kerja,
                           input=prompt(tanggal, hasil), capture_output=True, text=True, timeout=BATAS_DETIK)
        return p.returncode == 0 and hasil.exists() and _terima(cfg, hasil, tujuan, tanggal)
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        shutil.rmtree(kerja, ignore_errors=True)


def _proses(cfg, terakhir: bool, kering: bool) -> int:
    from ..laporan.nilai import muat_arsip
    from ..otomasi.rapi import sapu
    from ..otomasi.susun import catat_kabar, putuskan, sudah_dikabari
    from ..portal.api import FormatBerubah, collect_status
    from ..portal.browser import refresh_cookie_expiry

    kabari = (lambda *_, **__: None) if kering else (lambda t, j, **isi: _kabari(cfg, t, j, **isi))
    try:
        cm, s = _session_or_login(cfg, SimpleNamespace(headful=False, no_login=True))
        if s is None:
            print("Sesi Monev tidak aktif.")
            kabari(_today(), "sesi")
            return EXIT_NEED_LOGIN
        try:
            st = collect_status(s)
            sesi_sampai = refresh_cookie_expiry(s)
        finally:
            cm.__exit__(None, None, None)
    except FormatBerubah as ex:
        print(f"Bentuk data Monev berubah: {ex}")
        kabari(_today(), "format")
        return EXIT_FAIL
    except Exception as ex:  # noqa: BLE001 — proses terjadwal harus berhenti rapi dan mencoba lagi di jam berikutnya
        print(f"Monev tidak terbaca: {type(ex).__name__}")
        if terakhir:
            kabari(_today(), "cek")
        return EXIT_FAIL

    tanggal = st["tanggal"]
    sisa = sisa_sesi(sesi_sampai, tanggal)
    if sisa is not None and sisa <= SESI_PERINGATAN_HARI:
        print(f"Sesi Monev di laptop habis dalam {sisa} hari.")
        kabari(tanggal, "sesi_hampir", sampai=sesi_sampai.astimezone(WIB).date().isoformat(), sisa=sisa)
    if not kering:
        for nama in sapu(cfg.draft_dir, set(muat_arsip(data_dir() / "arsip")), tanggal):
            print(f"Draft lama dihapus: {nama}")
    tujuan = cfg.draft_dir / f"{tanggal}.json"
    aksi = putuskan(st, tujuan.exists(), _bahan(cfg, tanggal))
    print(f"{tanggal}: {aksi}" + (" (uji kering, tidak menyusun)" if kering and aksi == "susun" else ""))
    if aksi == "tunggu_bahan" and terakhir:
        kabari(tanggal, "kosong")
    # Pesan yang gagal terkirim dicoba lagi, tetapi draft yang ditulis sendiri oleh pemilik tidak perlu dikabari.
    if aksi == "ada_draft" and sudah_dikabari(_f_kabar(), tanggal, "tersusun"):
        kabari(tanggal, "siap")
    if aksi != "susun" or kering:
        return EXIT_OK
    if _susun(cfg, tanggal, tujuan):
        print("Draft tersimpan.")
        catat_kabar(_f_kabar(), tanggal, "tersusun")
        _kabari(cfg, tanggal, "siap")
        return EXIT_OK
    print("Draft gagal disusun.")
    if terakhir:
        _kabari(cfg, tanggal, "cek")
    return EXIT_FAIL


def _jalan(args) -> int:
    from ..bot.jadwal import WIB
    from ..otomasi.susun import kunci

    cfg = _config_auto()
    sekarang = datetime.now(WIB).strftime("%H:%M")
    # Timer menyusul jadwal kemarin saat laptop baru menyala, padahal bahan hari ini belum ada.
    if sekarang < cfg.jadwal_jam[0] and not args.kering:
        print(f"Belum waktunya, jadwal pertama pukul {cfg.jadwal_jam[0]}.")
        return EXIT_OK
    with kunci(data_dir() / "jadwal.lock") as dapat:
        if not dapat:
            print("Proses lain masih berjalan.")
            return EXIT_OK
        return _proses(cfg, sekarang >= cfg.jadwal_jam[-1], args.kering)


def _pasang() -> int:
    from ..bot.telegram import muat_env
    from ..otomasi.jadwal import pasang

    cfg = _config_auto()
    monev, claude = shutil.which("monev"), shutil.which("claude")
    if not (monev and claude):
        print("✗ Perintah `monev` dan `claude` harus tersedia di PATH.")
        return EXIT_FAIL
    node = shutil.which("node")
    folder = [str(Path(p).parent) for p in (monev, claude, node) if p]
    try:
        pasang(monev, folder, cfg.jadwal_jam)
    except (OSError, RuntimeError) as ex:
        print(f"✗ Jadwal gagal dipasang: {ex}")
        return EXIT_FAIL
    print(f"✓ Draft otomatis aktif pukul {', '.join(cfg.jadwal_jam)} WIB.")
    env = muat_env()
    if not (env.get("TELEGRAM_BOT_TOKEN") and env.get("TELEGRAM_CHAT_ID")):
        print("! Telegram belum diatur di .env, draft tetap disusun tanpa pesan.")
    if cfg.mcp_awalan_tool and not cfg.jadwal_alat_mcp:
        print("! `[jadwal] alat_mcp` masih kosong, jadi proses terjadwal tidak membaca MCP kantor.")
    return EXIT_OK


def cmd_jadwal(args) -> int:
    from ..otomasi.jadwal import keadaan, lepas

    if args.aksi == "jalan":
        return _jalan(args)
    if args.aksi == "pasang":
        return _pasang()
    if args.aksi == "lepas":
        lepas()
        print("✓ Draft otomatis dilepas.")
        return EXIT_OK
    k = keadaan()
    if not k["terpasang"]:
        print("Draft otomatis belum dipasang: monev jadwal pasang")
        return EXIT_OK
    print(f"Draft otomatis: {'aktif' if k['aktif'] else 'tidak aktif'}")
    print(f"Berikutnya    : {k['berikutnya'] or '-'}")
    print("Log           : journalctl --user -u monev-draft.service")
    return EXIT_OK
