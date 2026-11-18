"""Folder work records (lapis 2 di kontrak-sumber.md): dikenali dari isi, bukan dari nama alat pembuatnya.

Sebuah file catatan = Markdown yang punya judul `## Daily activity log` dan minimal satu baris tabel `| YYYY-MM-DD |`
(kontrak K3). Folder work records = folder yang berisi `<proyek>/<file>.md` seperti itu (K2).
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

JUDUL_AKTIVITAS = "## Daily activity log"
BARIS_TANGGAL = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|", re.M)
MAKS_UKURAN = 1_000_000            # byte; file lebih besar dilewati
# Folder yang tidak mungkin berisi catatan kerja dan mahal untuk dipindai.
LEWATI_CARI = {"node_modules", "__pycache__", "venv", ".venv", "site-packages", "dist", "build", "target",
               "snap", "go", "Library", "AppData"}


def tanggal_catatan(path: Path) -> list[str]:
    """Tanggal-tanggal di Daily activity log sebuah file; kosong bila file bukan catatan sesuai kontrak."""
    try:
        if path.stat().st_size > MAKS_UKURAN:
            return []
        teks = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    if JUDUL_AKTIVITAS not in teks:
        return []
    bagian = teks.split(JUDUL_AKTIVITAS, 1)[1]
    bagian = re.split(r"^## ", bagian, maxsplit=1, flags=re.M)[0]
    return BARIS_TANGGAL.findall(bagian)


JUDUL_PEMBELAJARAN = "## Key technical decisions and pitfalls"
BARIS_PEMBELAJARAN = re.compile(r"^-\s*(Decision|Pitfall|Observasi)\s*\((\d{4}-\d{2}-\d{2})[^)]*\)\s*:\s*(.+)$", re.M)


def _bagian(teks: str, judul: str) -> str:
    """Isi satu section `## …` (sampai section berikutnya); kosong bila tidak ada."""
    if judul not in teks:
        return ""
    return re.split(r"^## ", teks.split(judul, 1)[1], maxsplit=1, flags=re.M)[0]


def _frontmatter(teks: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", teks, re.S)
    out = {}
    for baris in (m.group(1).splitlines() if m else []):
        k, _, v = baris.partition(":")
        if k.strip() in ("title", "status") and v.strip():
            out[k.strip()] = v.split("#")[0].strip().strip('"').strip("'")
    return out


def baca(folder: Path, tanggal: str, lewati: list[str] | None = None) -> list[dict]:
    """Bahan hari `tanggal` dari folder work records, sesuai kontrak K2–K6: baris Daily activity log hari itu
    (bukan tabel lain seperti Daily time log), baris Decision/Pitfall/Observasi bertanggal itu, judul, dan status."""
    lewati = set(lewati or [])
    hasil = []
    if not folder.is_dir():
        return hasil
    for sub in sorted(folder.iterdir()):
        if not sub.is_dir() or sub.name.startswith(("_", ".")) or sub.name in lewati:
            continue
        for f in sorted(sub.glob("*.md")):
            try:
                teks = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            aktivitas = []
            for baris in _bagian(teks, JUDUL_AKTIVITAS).splitlines():
                sel = [s.strip() for s in baris.strip().strip("|").split("|")]
                if len(sel) >= 2 and sel[0] == tanggal:
                    aktivitas.append({"kegiatan": sel[1], "bukti": sel[2] if len(sel) > 2 else "",
                                      "blocker": " | ".join(sel[3:]) if len(sel) > 3 else ""})
            pembelajaran = [{"jenis": m.group(1), "teks": m.group(3).strip()}
                            for m in BARIS_PEMBELAJARAN.finditer(_bagian(teks, JUDUL_PEMBELAJARAN))
                            if m.group(2) == tanggal]
            if not aktivitas and not pembelajaran:
                continue
            fm = _frontmatter(teks)
            judul = fm.get("title") or next((b[2:].strip() for b in teks.splitlines() if b.startswith("# ")), f.stem)
            hasil.append({"file": f"{sub.name}/{f.name}", "proyek": sub.name, "judul": judul,
                          "status": fm.get("status", ""), "aktivitas": aktivitas, "pembelajaran": pembelajaran})
    return hasil


def ringkas(folder: Path, lewati: list[str] | None = None) -> dict:
    """Isi folder work records: jumlah file catatan, jumlah proyek, tanggal baris terakhir."""
    lewati = set(lewati or [])
    file, proyek, terakhir = 0, set(), ""
    if not folder.is_dir():
        return {"ada": False, "file": 0, "proyek": 0, "tanggal_terakhir": None}
    for sub in folder.iterdir():
        if not sub.is_dir() or sub.name.startswith(("_", ".")) or sub.name in lewati:
            continue
        for f in sub.glob("*.md"):
            tgl = tanggal_catatan(f)
            if tgl:
                file += 1
                proyek.add(sub.name)
                terakhir = max(terakhir, max(tgl))
    return {"ada": file > 0, "file": file, "proyek": len(proyek), "tanggal_terakhir": terakhir or None}


def cari(akar: list[Path] | None = None, kedalaman: int = 5, batas_detik: float = 20.0) -> list[dict]:
    """Cari folder work records di bawah `akar` (bawaan: home). Folder tersembunyi dan symlink tidak ditelusuri,
    jadi satu folder yang punya beberapa jalan masuk hanya muncul sekali. Urut: paling banyak file catatan."""
    akar = [Path(a).expanduser() for a in (akar or [Path.home()])]
    mulai = time.monotonic()
    temuan: dict[Path, dict] = {}
    habis_waktu = False
    for a in akar:
        a = a.resolve()
        dasar = len(a.parts)
        for dirpath, dirnames, filenames in os.walk(a, followlinks=False):
            if time.monotonic() - mulai > batas_detik:
                habis_waktu = True
                break
            d = Path(dirpath)
            tingkat = len(d.parts) - dasar
            # Folder berawalan "_" (mis. _knowledge, _plans) bukan catatan kerja (kontrak K2): tidak ditelusuri.
            dirnames[:] = [n for n in dirnames if not n.startswith((".", "_")) and n not in LEWATI_CARI
                           and tingkat < kedalaman]
            for nama in filenames:
                if not nama.endswith(".md"):
                    continue
                tgl = tanggal_catatan(d / nama)
                if not tgl:
                    continue
                root = d.parent
                t = temuan.setdefault(root, {"dir": str(root), "file": 0, "proyek": set(), "tanggal_terakhir": ""})
                t["file"] += 1
                t["proyek"].add(d.name)
                t["tanggal_terakhir"] = max(t["tanggal_terakhir"], max(tgl))
    # Catatan di sub-subfolder (<root>/<proyek>/<sub>/x.md) membuat kandidat palsu di dalam folder lain: buang.
    akar_temuan = list(temuan)
    temuan = {k: v for k, v in temuan.items() if not any(k != a and a in k.parents for a in akar_temuan)}
    hasil = [{**t, "proyek": len(t["proyek"]), "tanggal_terakhir": t["tanggal_terakhir"] or None}
             for t in temuan.values()]
    hasil.sort(key=lambda t: (-t["file"], t["dir"]))
    if habis_waktu:
        hasil.append({"dir": None, "catatan": f"pencarian dihentikan setelah {batas_detik:.0f} dtk; "
                                              "persempit dengan --akar <folder>"})
    return hasil
