"""Validasi draft terhadap aturan Monev (aturan.toml) + `jangan_disebut` dari config."""

from __future__ import annotations

import difflib
import json
import re
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .draft import Draft, js_length
from .nama import Saringan

RULES_PATH = Path(__file__).with_name("aturan.toml")


def load_rules() -> dict:
    return tomllib.loads(RULES_PATH.read_text(encoding="utf-8"))


@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    lengths: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings, "lengths": self.lengths}


def _snippet(text: str, m: re.Match) -> str:
    return text[m.start():m.end()][:40]


def _pembuka(teks: str, n: int) -> str:
    return " ".join(re.findall(r"\w+", teks.lower())[:n])


def _cek_gaya(texts: dict[str, str], gaya: dict, names: dict, history: list[dict]) -> list[str]:
    """Butir yang terlalu panjang dan pembuka pembelajaran yang sama dengan laporan terakhir (`history[0]`)."""
    hasil = []
    maks = gaya.get("butir_maks", 250)
    for i, b in enumerate((x for x in texts.get("activity_log", "").splitlines() if x.strip()), 1):
        n = js_length(re.sub(r"^\s*\d+\.\s*", "", b).strip())
        if n > maks:
            hasil.append(f"{names.get('activity_log', 'activity_log')}: butir {i} {n} karakter, sebaiknya maksimal {maks}")
    teks = texts.get("lesson_learned", "")
    lama = history[0].get("lesson_learned", "") if history else ""
    pembuka = _pembuka(teks, gaya.get("pembuka_kata", 3))
    if pembuka and pembuka == _pembuka(lama, gaya.get("pembuka_kata", 3)):
        hasil.append(f"{names.get('lesson_learned', 'lesson_learned')}: pembuka sama dengan laporan terakhir → {pembuka!r}")
    return hasil


def validate(d: Draft, rules: dict | None = None, jangan_disebut: list[str] | None = None,
             history: list[dict] | None = None, today: str | None = None,
             saringan: Saringan | None = None) -> Result:
    rules = rules or load_rules()
    res = Result()
    names = rules["field"]["nama"]
    lo, hi = rules["field"]["min"], rules["field"]["max"]

    # tanggal & status
    try:
        date.fromisoformat(d.date)
    except ValueError:
        res.errors.append(f"tanggal tidak valid: {d.date!r} (format YYYY-MM-DD)")
    if d.revisi:
        if d.status != "PRESENT":
            res.errors.append("revisi hanya untuk laporan hadir (Monev tidak meminta revisi untuk izin)")
        if today and d.date > today:
            res.errors.append(f"tanggal revisi {d.date} belum terjadi")
    elif today and d.date != today:
        res.errors.append(f"tanggal draft {d.date} bukan hari ini ({today}); Monev hanya menerima laporan hari ini")
    if d.status not in rules["status"]["izinkan"]:
        res.errors.append(f"status {d.status!r} tidak diizinkan (hanya {', '.join(rules['status']['izinkan'])})")

    texts = d.texts()
    for key, text in texts.items():
        label = names.get(key, key)
        n = js_length(text.strip())
        res.lengths[key] = n
        if n < lo:
            res.errors.append(f"{label}: {n} karakter, minimal {lo}")
        elif n > hi:
            res.errors.append(f"{label}: {n} karakter, maksimal {hi}")

        for r in rules.get("terlarang", []):
            for m in re.finditer(r["regex"], text, flags=re.M):
                res.errors.append(f"{label}: {r['nama']} → {_snippet(text, m)!r}")
                break
        for term in jangan_disebut or []:
            if term and re.search(re.escape(term), text, flags=re.I):
                res.errors.append(f"{label}: menyebut {term!r} (ada di jangan_disebut)")
        if saringan:
            salah, awas = saringan.cek(text)
            res.errors += [f"{label}: {x}" for x in salah]
            res.warnings += [f"{label}: {x}" for x in awas]
        for r in rules.get("peringatan", []):
            m = re.search(r["regex"], text, flags=re.M)
            if m:
                res.warnings.append(f"{label}: {r['nama']} → {_snippet(text, m)!r}")

    res.warnings += _cek_gaya(texts, rules.get("gaya", {}), names, history or [])

    # field yang isinya sama persis satu sama lain
    vals = [v.strip() for v in texts.values() if v.strip()]
    if len(vals) != len(set(vals)):
        res.errors.append("ada field yang isinya sama persis dengan field lain")

    # kemiripan dengan laporan terdahulu
    amb = rules.get("kemiripan", {}).get("ambang", 0.85)
    for past in history or []:
        for key, text in texts.items():
            old = (past.get(key) or "").strip()
            if old and text.strip():
                ratio = difflib.SequenceMatcher(None, old, text.strip()).ratio()
                if ratio >= amb:
                    res.warnings.append(f"{names.get(key, key)}: {ratio:.0%} mirip laporan {past.get('date')}")
    return res


def load_history(archive_dir: Path, limit: int, exclude_date: str | None = None) -> list[dict]:
    if not archive_dir.is_dir():
        return []
    items = []
    for p in sorted(archive_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("date") != exclude_date:
            items.append(data)
        if len(items) >= limit:
            break
    return items
