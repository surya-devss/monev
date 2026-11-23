"""Format file draft laporan.

Dua bentuk yang setara:
- JSON (dibuat skill/Claude): {"date", "status", "activity_log", "lesson_learned", "obstacles", ...}
- Teks (ditulis manusia): bagian bertajuk `## Uraian aktivitas` dst., lihat `template()`.

Tiga jenis: hadir (status PRESENT), izin (status ON_LEAVE + leave_reason, hanya hari ini), dan perbaikan laporan
yang diminta mentor (`"revisi": true` / `# revisi: ya`, tanggal = tanggal yang diminta revisi, kehadiran tidak berubah).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

FIELDS = ("activity_log", "lesson_learned", "obstacles")
HEADINGS = {
    "uraian aktivitas": "activity_log",
    "pembelajaran yang diperoleh": "lesson_learned",
    "kendala yang dialami": "obstacles",
    "alasan tidak hadir": "leave_reason",
}
STATUS_ALIASES = {"hadir": "PRESENT", "present": "PRESENT", "izin": "ON_LEAVE",
                  "tidak hadir dengan keterangan": "ON_LEAVE", "on_leave": "ON_LEAVE"}


@dataclass
class Draft:
    date: str
    status: str = "PRESENT"
    activity_log: str = ""
    lesson_learned: str = ""
    obstacles: str = ""
    leave_reason: str = ""
    sources: list[str] = field(default_factory=list)
    nama_sumber: list[str] = field(default_factory=list)   # nama proyek/klien dari sumber, untuk saringan nama
    keraguan: list[str] = field(default_factory=list)      # catatan draft otomatis untuk dibaca saat review
    approved: bool = False
    revisi: bool = False

    @property
    def jenis(self) -> str:
        return "revisi" if self.revisi else ("izin" if self.status == "ON_LEAVE" else "hadir")

    def texts(self) -> dict[str, str]:
        if self.status == "ON_LEAVE":
            return {"leave_reason": self.leave_reason}
        return {k: getattr(self, k) for k in FIELDS}

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)


def js_length(text: str) -> int:
    """Panjang seperti String.length JavaScript (unit UTF-16), sama dengan yang dihitung form Monev."""
    return len(text.encode("utf-16-le")) // 2


def _parse_text(raw: str) -> Draft:
    meta: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in raw.splitlines():
        m = re.match(r"^\s*#\s*(tanggal|status|revisi)\s*:\s*(.+?)\s*$", line, re.I)
        if m and current is None:
            meta[m.group(1).lower()] = m.group(2)
            continue
        h = re.match(r"^\s*##\s+(.+?)\s*$", line)
        if h:
            current = HEADINGS.get(h.group(1).strip().lower())
            if current:
                sections[current] = []
            continue
        if line.lstrip().startswith("<!--") or line.lstrip().startswith(">"):
            continue  # komentar / petunjuk template
        if current:
            sections[current].append(line)
    status = STATUS_ALIASES.get(meta.get("status", "hadir").strip().lower(), meta.get("status", "PRESENT").upper())
    d = Draft(date=meta.get("tanggal", date.today().isoformat()), status=status,
              revisi=meta.get("revisi", "").strip().lower() in ("ya", "true", "1"))
    for key, lines in sections.items():
        setattr(d, key, "\n".join(lines).strip())
    return d


def load(path: Path) -> Draft:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
        known = {k: data[k] for k in Draft.__dataclass_fields__ if k in data}
        return Draft(**known)
    return _parse_text(raw)


def template(tanggal: str, hari_pertama: bool = False, rutinitas: list[str] | None = None) -> str:
    """Template teks untuk ditulis sendiri (tanpa Claude)."""
    saran = ["onboarding / pengenalan perusahaan", "pengenalan tim", "sesi mentoring", "setup akun & akses"] \
        if hari_pertama else (rutinitas or [])
    saran_txt = "\n".join(f"> - {s}" for s in saran) or "> - (tidak ada saran)"
    return f"""# tanggal: {tanggal}
# status: Hadir

> Petunjuk (baris diawali ">" diabaikan):
> - Tiap bagian minimal 100 karakter. Tulis yang benar-benar terjadi hari ini.
> - Sebut proyek/sistem dan hasilnya. Jangan tulis IP, link, nomor tiket, nama orang, atau detail celah keamanan.
> - Kandidat kegiatan (pakai hanya yang benar terjadi):
{saran_txt}

## Uraian aktivitas
1.

## Pembelajaran yang diperoleh


## Kendala yang dialami

"""
