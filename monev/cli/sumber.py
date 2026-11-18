"""Perintah sumber bahan: `monev sumber cari` (folder work records) dan `monev bukti` (aktivitas Git)."""

from __future__ import annotations

import json
from datetime import date

from ._umum import EXIT_FAIL, EXIT_OK, _config_auto, _today


def cmd_sumber(args) -> int:
    from pathlib import Path

    from ..sumber.catatan import baca, cari

    if args.aksi == "baca":
        cfg = _config_auto()
        if not (cfg.workrecords_dir and cfg.workrecords_dir.is_dir()):
            print("✗ Folder work records belum diatur: `monev sumber cari`, lalu isi [sumber.workrecords] dir.")
            return EXIT_FAIL
        d = args.tanggal or _today()
        hasil = baca(cfg.workrecords_dir, d, cfg.lewati_folder)
        if args.json:
            print(json.dumps({"tanggal": d, "folder": str(cfg.workrecords_dir), "pekerjaan": hasil},
                             indent=2, ensure_ascii=False))
            return EXIT_OK
        print(f"Work records {d} ({cfg.workrecords_dir}): {len(hasil)} pekerjaan")
        for p in hasil:
            print(f"\n• {p['judul']}  [{p['proyek']}{', ' + p['status'] if p['status'] else ''}]")
            for a in p["aktivitas"]:
                print(f"    - {a['kegiatan']}" + (f"  → {a['bukti']}" if a["bukti"] else "")
                      + (f"  ! {a['blocker']}" if a["blocker"] and a["blocker"] not in ("-", "Tidak ada") else ""))
            for b in p["pembelajaran"]:
                print(f"    {b['jenis']}: {b['teks']}")
        return EXIT_OK

    akar = [Path(a) for a in args.akar] if args.akar else None
    hasil = cari(akar, kedalaman=args.kedalaman)
    if args.json:
        print(json.dumps(hasil, indent=2, ensure_ascii=False))
        return EXIT_OK
    folder = [h for h in hasil if h.get("dir")]
    if not folder:
        print("Tidak ada folder work records (file dengan `## Daily activity log` + baris `| YYYY-MM-DD |`).")
        print("Tanpa catatan, /monev menanyakan pembelajaran & kendala. Format: docs/teknis/kontrak-sumber.md")
    for h in folder:
        print(f"• {h['dir']}\n    {h['file']} file catatan, {h['proyek']} proyek, baris terakhir {h['tanggal_terakhir']}")
    for h in hasil:
        if not h.get("dir"):
            print(f"! {h['catatan']}")
    if folder:
        print("\nPakai salah satu: isi `[sumber.workrecords] dir = \"<folder>\"` di config (monev config --edit).")
    return EXIT_OK


def cmd_bukti(args) -> int:
    from ..laporan.validasi import load_rules
    from ..sumber.git import ambil_bukti

    cfg = _config_auto()
    if not cfg.git_penyedia:
        print("✗ Jalur Git belum diatur: isi `[sumber.git] penyedia = [\"github\"]` (dan/atau \"gitlab\") di config.\n"
              "  Panduan: docs/panduan/pasang.md bagian *Sumber bahan otomatis*.")
        return EXIT_FAIL
    d = date.fromisoformat(args.tanggal or _today())
    terlarang = [r["regex"] for r in load_rules().get("terlarang", [])]
    hasil = ambil_bukti(cfg, d, terlarang)
    if args.json:
        print(json.dumps(hasil, indent=2, ensure_ascii=False))
    else:
        print(f"Aktivitas Git {d.isoformat()} (WIB, milikmu, sudah dibersihkan):")
        for p, st in hasil["penyedia"].items():
            print(f"  {'✓' if st['ok'] else '✗'} {p}: " + (f"{st['jumlah']} aktivitas" if st["ok"] else st["pesan"]))
        for a in hasil["aktivitas"]:
            extra = f" (+{a['jumlah'] - 1} commit lain)" if a.get("jumlah", 1) > 1 else ""
            print(f"  {a['waktu']}  {a['penyedia']:<6} {a['jenis']:<6} {a['aksi']:<8} {a['judul']}{extra}")
        if not hasil["aktivitas"]:
            print("  (tidak ada aktivitas)")
    return EXIT_OK if any(st["ok"] for st in hasil["penyedia"].values()) else EXIT_FAIL
