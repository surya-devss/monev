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


def saringan_nama(cfg, d, rules: dict):
    """Saringan nama untuk draft `d`: proyek dan klien dibaca dari work records saat ini, ditambah `nama_sumber` draft."""
    from ..laporan.nama import buat_saringan
    from ..sumber.catatan import baca, daftar_proyek

    folder = cfg.workrecords_dir
    ada = bool(folder and folder.is_dir())
    semua = daftar_proyek(folder, cfg.lewati_folder) if ada else []
    hari_ini = baca(folder, d.date, cfg.lewati_folder) if ada else []
    return buat_saringan(semua, hari_ini, d.nama_sumber, rules, cfg.perusahaan, cfg.nama_boleh, cfg.lewati_proyek)


def cmd_eval(args) -> int:
    """Skor draft latihan terhadap laporan yang benar-benar terkirim. Hanya membaca."""
    import re
    from pathlib import Path

    from ..config import data_dir
    from ..laporan.draft import load
    from ..laporan.nilai import arsip_sah, nilai_draft
    from ..laporan.validasi import load_rules, validate

    cfg = load_config()
    folder = Path(args.folder) if args.folder else cfg.draft_dir
    rules = load_rules()
    hasil, dilewati = [], []
    # `<tanggal>.json` adalah draft yang dipakai mengirim, jadi tidak dinilai: isinya sama dengan kunci jawaban.
    for p in sorted(folder.glob("*-????-??-??.json")):
        tanggal = re.search(r"\d{4}-\d{2}-\d{2}", p.name).group()
        if tanggal in (args.lewati or []):
            continue
        f_arsip = data_dir() / "arsip" / f"{tanggal}.json"
        arsip = json.loads(f_arsip.read_text(encoding="utf-8")) if f_arsip.exists() else {}
        if not arsip_sah(arsip, tanggal):
            dilewati.append(tanggal)
            continue
        d = load(p)
        res = validate(d, rules, cfg.jangan_disebut, saringan=saringan_nama(cfg, d, rules))
        hasil.append({"tanggal": tanggal, "file": p.name, **nilai_draft(json.loads(p.read_text(encoding="utf-8")), arsip),
                      "lolos_validasi": res.ok, "pelanggaran": res.errors})
    rata = round(sum(h["skor"] for h in hasil) / len(hasil)) if hasil else None
    if args.json:
        print(json.dumps({"folder": str(folder), "rata_rata": rata, "hasil": hasil, "dilewati": dilewati},
                         indent=2, ensure_ascii=False))
    else:
        for h in hasil:
            print(f"{h['tanggal']}  skor {h['skor']:>3}  kegiatan {h['kegiatan']['cocok']}/{h['kegiatan']['total']}"
                  f" (+{h['butir_tambahan']} tambahan)  pembelajaran {h['pembelajaran']['cocok']}/{h['pembelajaran']['total']}"
                  f"  kendala {h['kendala']['cocok']}/{h['kendala']['total']} (tidak masuk skor)"
                  f"  {'lolos' if h['lolos_validasi'] else 'GAGAL validasi'}")
            for e in h["pelanggaran"]:
                print(f"    ✗ {e}")
        if dilewati:
            print(f"Dilewati, arsip tidak sah atau belum ada: {', '.join(dilewati)}")
        print(f"Rata-rata skor: {rata}" if hasil else f"✗ Tidak ada draft yang bisa dinilai di {folder}")
    return EXIT_OK if hasil else EXIT_FAIL


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
    res = validate(d, rules, cfg.jangan_disebut, history, today=None if args.bebas_tanggal else _today(),
                   saringan=saringan_nama(cfg, d, rules))
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
