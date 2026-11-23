"""Perintah yang memakai extension di Chrome user: kirim, extension."""

from __future__ import annotations

import sys

from ..config import load_config
from ._umum import EXIT_FAIL, EXIT_OK, _ask, _today

TAHAP_TUNGGU = 75   # detik: extension membaca antrian tiap 30 dtk


def _tunggu_extension(job: dict, timeout: int) -> dict | None:
    import time

    from ..kirim.antrian import batalkan, tunggu_hasil

    shown = {"diambil": False, "mulai": time.monotonic(), "terakhir": 0}

    def tick(diambil_path):
        if not shown["diambil"] and diambil_path.exists():
            shown["diambil"] = True
            print("  extension mengambil pekerjaan, sedang dijalankan di Chrome...", flush=True)
            return
        dtk = int(time.monotonic() - shown["mulai"])
        if not shown["diambil"] and dtk - shown["terakhir"] >= 15:
            shown["terakhir"] = dtk
            print(f"  masih menunggu extension... {dtk} dtk (maks {TAHAP_TUNGGU})", flush=True)

    print("Menunggu extension di Chrome (dicek tiap 30 dtk; lebih cepat: klik ikon monev kirim)...", flush=True)
    hasil = tunggu_hasil(job["id"], TAHAP_TUNGGU, tick)
    if hasil is None and not shown["diambil"] and batalkan(job["id"]):
        return {"ok": False, "tahap": "tidak_terhubung",
                "pesan": "Extension tidak mengambil pekerjaan. Pastikan Chrome terbuka, extension terpasang, "
                         "dan `monev extension install` sudah dijalankan. Tidak ada yang dikirim."}
    if hasil is None:
        hasil = tunggu_hasil(job["id"], timeout, tick)
    return hasil


def _laporkan_hasil(hasil: dict | None) -> int:
    if hasil is None:
        print("✗ Tidak ada hasil dari extension dalam batas waktu. Cek `monev status` sebelum mencoba lagi.")
        return EXIT_FAIL
    mark = "✓" if hasil.get("ok") else "✗"
    print(f"{mark} [{hasil.get('tahap')}] {hasil.get('pesan')}")
    st = hasil.get("status")
    if st:
        print(f"  Monev: tanggal {st.get('tanggal')}, sudah isi {st.get('sudah_isi')}, libur {st.get('libur')}")
    if hasil.get("panjang"):
        print(f"  panjang di form: {hasil['panjang']}")
    return EXIT_OK if hasil.get("ok") else EXIT_FAIL


def cmd_kirim(args) -> int:
    from pathlib import Path

    from ..config import data_dir
    from ..kirim.antrian import buat_job
    from ..kirim.host import diagnosa
    from ..laporan.draft import load
    from ..laporan.validasi import load_history, load_rules, validate
    from .laporan import cmd_status, saringan_nama

    masalah = diagnosa()
    if masalah:
        print("✗ Extension belum siap, tidak ada yang dikirim:")
        for m in masalah:
            print(f"  - {m}")
        return EXIT_FAIL

    if args.ping:
        hasil = _tunggu_extension(buat_job("ping"), 30)
        return _laporkan_hasil(hasil)

    if not args.file:
        print("✗ Sebutkan file draft: monev kirim <draft.json>  (atau --ping untuk cek koneksi)")
        return EXIT_FAIL
    path = Path(args.file)
    if not path.exists():
        print(f"✗ File tidak ditemukan: {path}")
        return EXIT_FAIL
    d = load(path)

    cfg = load_config()
    rules = load_rules()
    history = load_history(data_dir() / "arsip", rules.get("kemiripan", {}).get("riwayat", 10), exclude_date=d.date)
    res = validate(d, rules, cfg.jangan_disebut, history, today=_today(), saringan=saringan_nama(cfg, d, rules))
    if not res.ok:
        print("✗ Draft belum lolos validasi:")
        for e in res.errors:
            print(f"  ✗ {e}")
        return EXIT_FAIL

    mode = "uji" if args.uji else "kirim"
    names = rules["field"]["nama"]
    jenis = {"hadir": "laporan hadir", "izin": "izin (tidak hadir dengan keterangan)",
             "revisi": "perbaikan laporan dari mentor"}[d.jenis]
    print(f"Draft {path} · {jenis} · tanggal {d.date} · mode {mode}")
    for k, n in res.lengths.items():
        print(f"  {names.get(k, k):<28} {n:>5} karakter")
    for w in res.warnings:
        print(f"  ! {w}")

    # Persetujuan hanya di satu tempat: draft "approved": true (user membalas `kirim` di chat
    # agent) atau ketik `kirim` di terminal. Extension tidak meminta persetujuan lagi.
    if mode == "kirim" and not d.approved:
        if not sys.stdin.isatty():
            print('✗ Draft belum disetujui. Ubah "approved": true setelah user membalas `kirim`, '
                  "atau jalankan perintah ini di terminal. Tidak ada yang dikirim.")
            return EXIT_FAIL
        if _ask("Laporan TIDAK bisa diedit setelah terkirim. Ketik `kirim` untuk mengirim") != "kirim":
            print("Dibatalkan. Tidak ada yang dikirim.")
            return EXIT_FAIL

    draft = {"date": d.date, "status": d.status, "revisi": d.revisi, **d.texts()}
    job = buat_job("isi", draft, mode)
    hasil = _tunggu_extension(job, args.timeout)
    code = _laporkan_hasil(hasil)
    if mode == "kirim" and hasil and hasil.get("tahap") == "terkirim":
        _hapus_draft(path, cfg)
    if hasil and hasil.get("tahap") in ("terkirim", "tidak_pasti"):
        print("\nVerifikasi lewat Monev (sesi CLI)...")
        args.json, args.headful, args.no_login = False, False, True
        cmd_status(args)
        _sapu_draft(cfg)
    return code


def _hapus_draft(path, cfg) -> None:
    """Laporan sudah tersimpan di Monev, jadi draft lokalnya tidak diperlukan lagi."""
    from ..otomasi.rapi import hapus_draft

    try:
        if hapus_draft(path, cfg.draft_dir):
            print("  draft lokal dihapus")
    except OSError as ex:
        print(f"  ! draft lokal gagal dihapus: {ex}")


def _sapu_draft(cfg) -> None:
    """Hasil `tidak_pasti` yang ternyata masuk arsip dan draft lama ikut dibersihkan setelah verifikasi."""
    from ..config import data_dir
    from ..laporan.nilai import muat_arsip
    from ..otomasi.rapi import sapu

    try:
        for nama in sapu(cfg.draft_dir, set(muat_arsip(data_dir() / "arsip")), _today()):
            print(f"  draft lama dihapus: {nama}")
    except OSError as ex:
        print(f"  ! draft lama gagal dibersihkan: {ex}")


def cmd_extension(args) -> int:
    from ..kirim.host import EXTENSION_ID, extension_dir, pasang

    if args.aksi == "coba":
        from ..kirim.antrian import buat_job
        from ..kirim.host import diagnosa

        if diagnosa():
            print("✗ Extension belum siap: " + "; ".join(diagnosa()))
            return EXIT_FAIL
        jenis = args.jenis or "ingat"
        print(f"Minta extension menampilkan notifikasi '{jenis}' sekarang (sapaan/fokus hanya di hari kerja)...")
        return _laporkan_hasil(_tunggu_extension(buat_job("coba", {"jenis": jenis}), 75))
    if args.aksi == "install":
        try:
            files = pasang()
        except RuntimeError as e:
            print(f"✗ {e}")
            return EXIT_FAIL
        for f in files:
            print(f"✓ host Native Messaging: {f}")
    print(f"\nExtension: {extension_dir()}")
    print(f"ID       : {EXTENSION_ID}")
    print("Pasang sekali di Chrome kamu: chrome://extensions → Developer mode → Load unpacked → folder di atas.")
    print("Lalu cek: monev kirim --ping")
    return EXIT_OK
