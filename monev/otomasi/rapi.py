"""Menjaga folder draft tetap bersih. Hanya menyentuh `<draft_dir>/<YYYY-MM-DD>.json`; draft latihan tidak dihapus."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

POLA = re.compile(r"\d{4}-\d{2}-\d{2}\.json")
SIMPAN_HARI = 7   # draft hadir yang tidak jadi dikirim tidak bisa dipakai lagi setelah harinya lewat


def hapus_draft(path: Path, folder: Path) -> bool:
    """Hapus draft yang sudah terkirim. File di luar folder draft milik pemakai, jadi dibiarkan."""
    if path.resolve().parent != folder.resolve() or not POLA.fullmatch(path.name):
        return False
    path.unlink(missing_ok=True)
    return True


def sapu(folder: Path, terkirim: set[str], hari_ini: str) -> list[str]:
    """Hapus draft yang laporannya sudah ada di arsip atau sudah lewat `SIMPAN_HARI`.
    Draft perbaikan dari mentor dibiarkan: arsip tanggalnya berisi laporan lama, bukan perbaikannya."""
    batas = (date.fromisoformat(hari_ini) - timedelta(days=SIMPAN_HARI)).isoformat()
    dihapus = []
    for p in sorted(folder.glob("????-??-??.json")) if folder.is_dir() else []:
        if not POLA.fullmatch(p.name):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("revisi"):
            continue
        if p.stem in terkirim or p.stem < batas:
            p.unlink(missing_ok=True)
            dihapus.append(p.name)
    return dihapus
