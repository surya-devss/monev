"""Antrian pekerjaan `monev kirim` → extension. File di <data_dir>/kirim/ (izin 700/600).

Hanya berisi draft yang sudah disetujui user; tidak ada token/password. Siklus satu pekerjaan:
`antrian-<id>.json` (dibuat CLI) → `diambil-<id>.json` (diambil extension) → `hasil-<id>.json` (dibaca CLI).
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

KEDALUWARSA_DTK = 600   # pekerjaan lebih tua dari ini tidak diambil


def antrian_dir() -> Path:
    from ..config import data_dir

    d = data_dir() / "kirim"
    d.mkdir(parents=True, exist_ok=True)
    d.chmod(0o700)
    return d


def buat_job(jenis: str, draft: dict | None = None, mode: str = "kirim") -> dict:
    job = {"id": uuid.uuid4().hex[:12], "type": jenis, "mode": mode, "dibuat": time.time()}
    if draft is not None:
        job["draft"] = draft
    path = antrian_dir() / f"antrian-{job['id']}.json"
    path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    path.chmod(0o600)
    return job


def ambil_job(sekarang: float | None = None) -> dict | None:
    """Ambil pekerjaan tertua yang belum kedaluwarsa; pindahkan ke `diambil-*` agar tidak dijalankan dua kali."""
    sekarang = sekarang or time.time()
    d = antrian_dir()
    for p in sorted(d.glob("antrian-*.json"), key=lambda x: x.stat().st_mtime):
        try:
            job = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            p.unlink(missing_ok=True)
            continue
        if sekarang - job.get("dibuat", 0) > KEDALUWARSA_DTK:
            tulis_hasil(job["id"], {"ok": False, "tahap": "kedaluwarsa",
                                    "pesan": "Extension tidak mengambil pekerjaan dalam 10 menit."})
            p.unlink(missing_ok=True)
            continue
        try:
            p.rename(d / f"diambil-{job['id']}.json")
        except FileNotFoundError:
            continue   # sudah diambil proses lain
        return job
    return None


def tulis_hasil(job_id: str, hasil: dict) -> None:
    d = antrian_dir()
    p = d / f"hasil-{job_id}.json"
    p.write_text(json.dumps(hasil, ensure_ascii=False), encoding="utf-8")
    p.chmod(0o600)
    (d / f"diambil-{job_id}.json").unlink(missing_ok=True)


def tunggu_hasil(job_id: str, timeout: float, tick=None) -> dict | None:
    d = antrian_dir()
    akhir = time.monotonic() + timeout
    while time.monotonic() < akhir:
        p = d / f"hasil-{job_id}.json"
        if p.exists():
            hasil = json.loads(p.read_text(encoding="utf-8"))
            p.unlink(missing_ok=True)
            return hasil
        if tick:
            tick(d / f"diambil-{job_id}.json")
        time.sleep(1)
    return None


def batalkan(job_id: str) -> bool:
    """Hapus pekerjaan yang belum diambil. False bila sudah diambil extension (sedang berjalan)."""
    p = antrian_dir() / f"antrian-{job_id}.json"
    if p.exists():
        p.unlink()
        return True
    return False
