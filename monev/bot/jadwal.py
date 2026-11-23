"""Jadwal bot dan keputusan pesan apa yang dikirim. Fungsi di sini murni (tanpa jaringan) agar bisa dites.

Jadwal diambil dari `[bot]` di config (kartu, pengingat, rekap, pantau). State (`<data_dir>/bot-state.json`)
mencatat jadwal yang sudah jalan, pengamatan terakhir, dan id pesan hari ini (kartu, pengingat, gangguan) supaya
pesan itu bisa diperbarui di tempat dan tidak dobel setelah bot restart.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import pesan as P

WIB = timezone(timedelta(hours=7))   # WIB tanpa DST; tidak bergantung tzdata
JENDELA_MENIT = 30                   # jadwal yang terlewat lebih dari ini (mis. bot mati) tidak dijalankan
SESI_PERINGATAN_HARI = 3


def urutan_ingat(i: int, n: int) -> str:
    """Pengingat ke-i dari n → pertama | kedua | terakhir (sama dengan extension)."""
    if i == 0:
        return "pertama"
    return "terakhir" if i == n - 1 else "kedua"


def buat_jadwal(cfg) -> list[tuple[str, str]]:
    """[(jam WIB, jenis)] terurut. Jenis: kartu, ingat:<urutan>, rekap, pantau."""
    j = [(cfg.bot_kartu, "kartu"), (cfg.bot_rekap, "rekap")]
    j += [(x, "ingat:" + urutan_ingat(i, len(cfg.bot_pengingat))) for i, x in enumerate(cfg.bot_pengingat)]
    j += [(x, "pantau") for x in cfg.bot_pantau]
    return sorted(j)


def jadwal_jatuh_tempo(jadwal: list[tuple[str, str]], sekarang: datetime, selesai_hari_ini: set[str]) -> list[tuple[str, str]]:
    out = []
    for jam, jenis in jadwal:
        h, m = map(int, jam.split(":"))
        t = sekarang.replace(hour=h, minute=m, second=0, microsecond=0)
        kunci = f"{jam}-{jenis}"
        if t <= sekarang < t + timedelta(minutes=JENDELA_MENIT) and kunci not in selesai_hari_ini:
            out.append((kunci, jenis))
    return out


def jadwal_berikutnya(jadwal: list[tuple[str, str]], sekarang: datetime) -> str | None:
    kini = f"{sekarang:%H:%M}"
    return next((jam for jam, _ in jadwal if jam > kini), None)


@dataclass
class Konteks:
    tx: P.Teks
    nilai: dict | None = None
    panggilan: str = ""
    tunda_menit: int = 60


@dataclass
class Keputusan:
    kirim: list[tuple[str, P.Pesan]] = field(default_factory=list)   # (tag, pesan); tag: kartu | ingat:<u> | info
    kartu: P.Pesan | None = None    # isi kartu hari ini terbaru (kartu yang sudah terkirim diperbarui ke isi ini)
    sudah_isi: bool = False         # laporan hari ini sudah terkirim → pengingat hari ini diringkas
    baru: dict = field(default_factory=dict)


def putuskan(jenis: str, data: dict, lalu: dict, sekarang: datetime, k: Konteks) -> Keputusan:
    """Pesan untuk satu jadwal (atau tombol "cek") + state pengamatan baru. `lalu` = pengamatan sebelumnya."""
    st, per = data["status"], data["periode"]
    hari = P._d(st["tanggal"])
    aktif = st.get("magang_aktif")
    kerja = aktif and not (st.get("libur_nasional") or st.get("libur_posisi"))
    nama = P.panggilan(st, k.panggilan)
    out = Keputusan(sudah_isi=bool(st.get("sudah_isi")))

    # Perubahan sejak pengamatan terakhir
    if st.get("sudah_isi") and lalu.get("tanggal") == st["tanggal"] and lalu.get("sudah_isi") is False:
        out.kirim.append(("info", P.terkirim(k.tx, st)))
    lama_rev = set(lalu.get("revisi", []))
    for r in st.get("perlu_revisi") or []:
        if r["date"] not in lama_rev:
            out.kirim.append(("info", P.revisi(k.tx, r["date"], r.get("catatan_mentor", ""))))
    lama_tolak = set(lalu.get("ditolak", []))
    for t in per.get("ditolak_tanggal", []):
        if t not in lama_tolak:
            out.kirim.append(("info", P.ditolak(k.tx, t, per["periode"]["absen_total"])))
    # State lama tanpa catatan persetujuan: catat dulu tanpa mengabari, supaya persetujuan lama tidak dikirim sekaligus.
    setuju = per.get("disetujui_tanggal", [])
    if "disetujui" in lalu:
        baru_setuju = [t for t in setuju if t not in set(lalu["disetujui"])]
        if baru_setuju:
            ps = per.get("persetujuan", {})
            out.kirim.append(("info", P.disetujui(k.tx, baru_setuju, ps.get("disetujui", 0), sum(ps.values()))))

    versi = data.get("versi_web") or lalu.get("versi_web")
    if data.get("versi_web") and lalu.get("versi_web") and data["versi_web"] != lalu["versi_web"]:
        out.kirim.append(("info", P.web_berubah(k.tx)))

    masa_kirim, masa_baru = masa_magang(st, hari, lalu)
    out.kirim += [("info", P.masa(k.tx, jenis_masa, **isi)) for jenis_masa, isi in masa_kirim]

    if kerja:
        out.kartu = P.kartu(k.tx, st, k.nilai, nama)
    if jenis == "kartu":
        if kerja:
            out.kirim.insert(0, ("kartu", out.kartu))
        elif aktif:
            out.kirim.insert(0, ("info", P.kartu_libur(k.tx, st, nama)))
        if data.get("sesi_sampai"):
            sampai = data["sesi_sampai"].astimezone(WIB).date()
            sisa = (sampai - sekarang.date()).days
            if sisa <= SESI_PERINGATAN_HARI:
                out.kirim.append(("info", P.sesi(k.tx, max(sisa, 0), sampai)))
    if jenis.startswith("ingat:") and kerja and not st.get("sudah_isi"):
        out.kirim.append((jenis, P.ingat(k.tx, jenis.split(":", 1)[1], hari, 24 - sekarang.hour, k.tunda_menit)))
    if jenis == "rekap" and kerja:
        if hari.weekday() == 4 and data.get("minggu"):
            out.kirim.append(("info", P.rekap_minggu(k.tx, data["minggu"])))
        if per.get("hari_kerja_terakhir_periode") and data.get("bulan"):
            out.kirim.append(("info", P.rekap_bulan(k.tx, data["bulan"])))

    out.baru = {"tanggal": st["tanggal"], "sudah_isi": bool(st.get("sudah_isi")),
                "revisi": [r["date"] for r in st.get("perlu_revisi") or []],
                "ditolak": per.get("ditolak_tanggal", []),
                "disetujui": setuju, "versi_web": versi, **masa_baru}
    return out


MASA_HARI = (30, 7, 0)   # kabar H-30, H-7, dan hari terakhir magang


def masa_magang(st: dict, hari, lalu: dict) -> tuple[list[tuple[str, dict]], dict]:
    """Kabar masa magang ([(jenis, isi)], state baru). Satu kabar per ambang; ambang yang terlewat saat bot mati
    tidak dikirim bertumpuk, cukup yang terdekat. Magang aktif → tidak aktif dikabari sekali."""
    from datetime import date

    selesai = (st.get("periode") or {}).get("selesai")
    aktif = bool(st.get("magang_aktif"))
    sudah = set(lalu.get("masa", []))
    kirim: list[tuple[str, dict]] = []
    if selesai:
        akhir = date.fromisoformat(selesai[:10])
        sisa = (akhir - hari).days
        kena = [m for m in MASA_HARI if 0 <= sisa <= m and m not in sudah]
        if aktif and kena:
            m = min(kena)
            kirim.append(("terakhir" if m == 0 else f"h{m}", {"sisa": sisa, "tanggal": akhir}))
            sudah |= set(kena)
        if lalu.get("aktif") is True and not aktif:
            kirim.append(("selesai" if sisa <= 0 else "dini", {"sisa": sisa, "tanggal": akhir}))
    return kirim, {"masa": sorted(sudah), "aktif": aktif}


# ---------------------------------------------------------------- state

def _state_path() -> Path:
    from ..config import data_dir

    return data_dir() / "bot-state.json"


def baca_state() -> dict:
    try:
        return json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def tulis_state(s: dict) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)
