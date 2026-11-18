"""Perintah membaca Monev dan menulis draft: status, rekap, draft, validate."""

from __future__ import annotations

import json
import sys

from ..config import load_config
from ._umum import EXIT_FAIL, EXIT_NEED_LOGIN, EXIT_OK, _autofill, _config_auto, _session_or_login, _today


def _print_status(st: dict) -> None:
    print(f"Tanggal      : {st['tanggal']}" + ("  (hari pertama magang)" if st["hari_pertama"] else ""))
    print(f"Periode      : {st['periode']['mulai']} s.d. {st['periode']['selesai']}")
    if not st["magang_aktif"]:
        print("Status       : ✗ magang TIDAK aktif")
        return
    if st["libur_nasional"] or st["libur_posisi"]:
        print("Hari ini     : libur, tidak wajib isi")
    else:
        print("Hari ini     : hari kerja")
    if st["sudah_isi"]:
        k, l = st["kehadiran"] or {}, st["laporan"] or {}
        print(f"Laporan      : ✓ sudah isi — kehadiran {k.get('status')}/{k.get('persetujuan')}, "
              f"log {l.get('state')}, panjang {l.get('panjang')}")
    elif not (st["libur_nasional"] or st["libur_posisi"]):
        print("Laporan      : ✗ BELUM diisi (batas 23.59)")
    rev = st["perlu_revisi"]
    if rev is None:
        print("Revisi mentor: – tidak bisa dicek")
    elif rev:
        for r in rev:
            print(f"Revisi mentor: ! {r['date']} — {r['catatan_mentor']}")
    else:
        print("Revisi mentor: tidak ada")


def cmd_status(args) -> int:
    from ..portal.api import collect_status

    cfg = _config_auto()
    cm, s = _session_or_login(cfg, args)
    if s is None:
        print("✗ Belum login / sesi mati → jalankan: monev login", file=sys.stderr)
        return EXIT_NEED_LOGIN
    try:
        _autofill(cfg, s)
        st = collect_status(s)
    finally:
        cm.__exit__(None, None, None)
    if args.json:
        print(json.dumps(st, indent=2, ensure_ascii=False))
    else:
        _print_status(st)
        _langkah_berikutnya()
    return EXIT_OK


def _langkah_berikutnya() -> None:
    """Petunjuk singkat bila extension (satu-satunya pengirim laporan) belum siap. Tidak memengaruhi status."""
    from ..kirim.host import diagnosa

    masalah = diagnosa()
    if masalah:
        print("\nUntuk MENGIRIM laporan, extension monev belum siap:")
        for m in masalah:
            print(f"  - {m}")
        print("  Panduan: docs/panduan/pasang.md langkah 3–4.")


def cmd_rekap(args) -> int:
    from ..portal.rekap import collect_rekap, format_teks

    cfg = _config_auto()
    cm, s = _session_or_login(cfg, args)
    if s is None:
        print("✗ Belum login / sesi mati → jalankan: monev login", file=sys.stderr)
        return EXIT_NEED_LOGIN
    jenis = "minggu" if args.minggu else "bulan" if args.bulan else "periode"
    try:
        r = collect_rekap(s, jenis, args.dari, args.sampai)
    finally:
        cm.__exit__(None, None, None)
    print(json.dumps(r, indent=2, ensure_ascii=False) if args.json else format_teks(r))
    return EXIT_OK


def cmd_draft(args) -> int:
    from pathlib import Path

    from ..laporan.draft import template

    cfg = load_config()
    tanggal = args.tanggal or _today()
    out = Path(args.output or f"monev-{tanggal}.md")
    if out.exists() and not args.force:
        print(f"File sudah ada: {out} (pakai --force untuk menimpa)")
        return EXIT_FAIL
    out.write_text(template(tanggal, hari_pertama=args.hari_pertama, rutinitas=cfg.rutinitas), encoding="utf-8")
    print(f"✓ Template ditulis: {out}\nIsi, lalu: monev validate {out}")
    return EXIT_OK


def cmd_validate(args) -> int:
    from pathlib import Path

    from ..config import data_dir
    from ..laporan.draft import load
    from ..laporan.validasi import load_history, load_rules, validate

    cfg = load_config()
    path = Path(args.file)
    if not path.exists():
        print(f"✗ File tidak ditemukan: {path}")
        return EXIT_FAIL
    d = load(path)
    rules = load_rules()
    history = load_history(data_dir() / "arsip", rules.get("kemiripan", {}).get("riwayat", 10), exclude_date=d.date)
    res = validate(d, rules, cfg.jangan_disebut, history, today=None if args.bebas_tanggal else _today())
    if args.json:
        print(json.dumps(res.as_dict(), indent=2, ensure_ascii=False))
    else:
        names = rules["field"]["nama"]
        print(f"Draft {path} · tanggal {d.date} · status {d.status}")
        for k, n in res.lengths.items():
            print(f"  {names.get(k, k):<28} {n:>5} karakter")
        for e in res.errors:
            print(f"✗ {e}")
        for w in res.warnings:
            print(f"! {w}")
        print("✓ Lolos validasi." if res.ok else "✗ Belum lolos, perbaiki baris bertanda ✗.")
    return EXIT_OK if res.ok else EXIT_FAIL
