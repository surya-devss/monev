"""Panggilan API Monev dari DALAM halaman (cookie + Bearer dari sessionStorage), read-only."""

from __future__ import annotations

from datetime import date

from .browser import Session
from ..config import TOKEN_KEY

FETCH_JS = """async ({url, key}) => {
  const t = sessionStorage.getItem(key);
  const r = await fetch(url, {credentials: 'include', headers: t ? {Authorization: 'Bearer ' + t} : {}});
  let body = null;
  try { body = await r.json(); } catch (e) {}
  return {status: r.status, body};
}"""


class ApiError(RuntimeError):
    def __init__(self, path: str, status: int, message: str = ""):
        super().__init__(f"GET {path} → HTTP {status} {message}".strip())
        self.status = status


class FormatBerubah(RuntimeError):
    """Field wajib dari Monev hilang. Data tidak dipakai supaya libur atau status tidak terbaca keliru sebagai kosong."""


# Field yang dipakai keputusan bot dan CLI. Dicek ada di respons Monev asli 19 Nov 2026 (catatan uji #57).
WAJIB = {
    "/users/me": ("id", "internship_start_date", "internship_end_date", "off_days"),
    "/users/me/home": ("date", "is_holiday", "is_scheduled_off_day", "has_attendance", "active_internship"),
    "/attendances": ("date", "status", "approval_status"),
    "/daily-logs": ("date", "state"),
    "/holidays": ("date",),
}


def wajib(path: str, data):
    """Kembalikan `data` bila field wajib ada (untuk daftar: setiap baris), selain itu FormatBerubah."""
    baris = data if isinstance(data, list) else [data]
    for x in baris:
        hilang = [k for k in WAJIB[path] if not isinstance(x, dict) or k not in x]
        if hilang:
            raise FormatBerubah(f"{path} tanpa field {', '.join(hilang)}")
    return data


def get(s: Session, path: str, params: dict | None = None):
    query = ""
    if params:
        from urllib.parse import urlencode

        query = "?" + urlencode({k: v for k, v in params.items() if v not in (None, "")})
    res = s.page.evaluate(FETCH_JS, {"url": s.cfg.api_base + path + query, "key": TOKEN_KEY})
    body = res.get("body") or {}
    if res["status"] != 200:
        msg = body.get("message", "") if isinstance(body, dict) else ""
        raise ApiError(path, res["status"], msg)
    return body.get("data", body) if isinstance(body, dict) else body


def _archive(day: str, att: dict, log: dict) -> None:
    """Simpan salinan teks laporan yang SUDAH terkirim (lokal) untuk cek kemiripan. Tanpa koordinat."""
    import json

    from ..config import data_dir

    d = data_dir() / "arsip"
    d.mkdir(parents=True, exist_ok=True)
    rec = {"date": day, "status": att.get("status"), "state": log.get("state"),
           **{k: log.get(k) or "" for k in ("activity_log", "lesson_learned", "obstacles")}}
    (d / f"{day}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")


def log_tanggal(logs: list[dict], hari: str) -> dict:
    """Laporan bertanggal `hari` saja. API bisa mengembalikan laporan hari lain walau diberi parameter `date`."""
    return next((l for l in logs if (l.get("date") or "")[:10] == hari), {})


def collect_status(s: Session) -> dict:
    """Ringkasan status hari ini. Tidak memuat token, cookie, atau koordinat."""
    me = wajib("/users/me", get(s, "/users/me"))
    home = wajib("/users/me/home", get(s, "/users/me/home"))
    pid = me.get("id")
    today = home.get("date") or date.today().isoformat()
    start = (me.get("internship_start_date") or "")[:10]

    logs_today = wajib("/daily-logs", get(s, "/daily-logs", {"participant_id": pid, "date": today, "limit": 10}) or [])
    att_today = wajib("/attendances", get(s, "/attendances", {"participant_id": pid, "start_date": today, "end_date": today}) or [])

    revisions: list[dict] | None
    try:
        logs = get(s, "/daily-logs", {"participant_id": pid, "start_date": start, "end_date": today, "limit": 100}) or []
        revisions = [
            {"date": (l.get("date") or "")[:10], "catatan_mentor": l.get("reviewer_notes") or ""}
            for l in logs if l.get("state") == "NEEDS_REVISION"
        ]
    except Exception:
        revisions = None  # bentuk query rentang belum terverifikasi

    log = log_tanggal(logs_today, today)
    att = att_today[0] if att_today else {}
    if log:
        _archive(today, att, log)
    return {
        "tanggal": today,
        "nama": " ".join(w.capitalize() for w in (me.get("name") or "").split()),
        "posisi": me.get("job_role") or "",
        "perusahaan": me.get("internship_company") or "",
        "hari_pertama": bool(start) and start == today,
        "periode": {"mulai": start, "selesai": (me.get("internship_end_date") or "")[:10]},
        "magang_aktif": bool(home.get("active_internship")),
        "libur_nasional": bool(home.get("is_holiday")),
        "libur_posisi": bool(home.get("is_scheduled_off_day")),
        "off_days": me.get("off_days") or [],
        "sudah_isi": bool(home.get("has_attendance")),
        "kehadiran": {"status": att.get("status"), "persetujuan": att.get("approval_status"),
                      "ada_lokasi": att.get("latitude") is not None} if att else None,
        "laporan": {"state": log.get("state"),
                    "panjang": [len(log.get(k) or "") for k in ("activity_log", "lesson_learned", "obstacles")]}
                   if log else None,
        "perlu_revisi": revisions,
    }
