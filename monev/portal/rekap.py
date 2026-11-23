"""Rekap kehadiran dari data Monev (read-only): hari kerja, hadir, izin, absen, persetujuan mentor, peringatan.

`hitung()` murni (tanpa browser) agar bisa dites; `collect_rekap()` mengambil data lewat sesi Chrome A.
Tidak memuat koordinat, kontak, atau teks laporan.
"""

from __future__ import annotations

from datetime import date, timedelta

HARI = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

# Panduan Peserta (docs/teknis/situs-monev.md#aturan-program). Batas total absen dan izin dibayar berlaku per periode,
# yaitu satu bulan sejak tanggal mulai magang (16 Nov → 16 Nov–15 Des). Absen berturut dihitung lintas periode.
BATAS = {"peringatan_berturut": 3, "peringatan_total": 7, "nonaktif_berturut": 5, "nonaktif_total": 10,
         "izin_dibayar": 3}


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s[:10]) if s else None


def tambah_bulan(d: date, n: int) -> date:
    """Tanggal yang sama n bulan kemudian; tanggal 29–31 dipotong ke akhir bulan (31 Jan + 1 → 28/29 Feb)."""
    import calendar

    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def periode_berjalan(mulai: date, hari: date) -> tuple[int, date, date]:
    """(ke, awal, akhir) periode yang memuat `hari`. Periode ke-n = mulai + (n-1) bulan s.d. sehari sebelum periode berikutnya."""
    n = max(0, (hari.year - mulai.year) * 12 + hari.month - mulai.month)
    if n and tambah_bulan(mulai, n) > hari:
        n -= 1
    while tambah_bulan(mulai, n + 1) <= hari:
        n += 1
    return n + 1, tambah_bulan(mulai, n), tambah_bulan(mulai, n + 1) - timedelta(days=1)


def libur_berlaku(holidays: list[dict], me: dict) -> dict[date, str]:
    """Libur yang berlaku untuk lokasi magang: nasional + provinsi/kabupaten yang cocok.

    /holidays mengembalikan seluruh daftar (termasuk libur daerah lain) dan mengabaikan filter tanggal (uji #25).
    """
    prov = me.get("internship_location_province_code")
    reg = me.get("internship_location_regency_code")
    out: dict[date, str] = {}
    for h in holidays or []:
        if h.get("regency_code"):
            ok = h["regency_code"] == reg
        elif h.get("province_code"):
            ok = h["province_code"] == prov
        else:
            ok = h.get("scope") == "NATIONAL" or h.get("type") == "NATIONAL"
        d = _d(h.get("date"))
        if ok and d:
            out[d] = h.get("name") or "libur"
    return out


def hari_kerja(dari: date, sampai: date, off_days: list[str], libur: dict[date, str]) -> list[date]:
    off = {o.upper() for o in off_days or []}
    out, d = [], dari
    while d <= sampai:
        if HARI[d.weekday()] not in off and d not in libur:
            out.append(d)
        d += timedelta(days=1)
    return out


def _kelas(att: dict | None, d: date, hari_ini: date) -> str:
    """hadir · izin · absen · ditolak · belum (hari ini, belum lewat 23.59) · libur."""
    if not att:
        return "belum" if d == hari_ini else "absen"
    st, ap = att.get("status"), att.get("approval_status")
    if st == "DAYOFF":
        return "libur"
    if ap == "REJECTED":
        return "ditolak"          # panduan: kehadiran ditolak mentor dihitung absen
    return {"PRESENT": "hadir", "ON_LEAVE": "izin", "ABSENT": "absen"}.get(st, "absen")


def _streak(kelas: list[str]) -> tuple[int, int]:
    """(berturut terakhir, berturut terpanjang) untuk absen/ditolak."""
    cur = best = 0
    for k in kelas:
        if k in ("absen", "ditolak"):
            cur += 1
            best = max(best, cur)
        elif k != "belum":
            cur = 0
    return cur, best


def hitung(me: dict, attendances: list[dict], logs: list[dict], holidays: list[dict],
           dari: date, sampai: date, hari_ini: date) -> dict:
    mulai = _d(me.get("internship_start_date")) or dari
    selesai = _d(me.get("internship_end_date")) or sampai
    libur = libur_berlaku(holidays, me)
    off = me.get("off_days") or []
    att_by = {_d(a.get("date")): a for a in attendances or []}
    log_by = {_d(l.get("date")): l for l in logs or []}

    # Sejak mulai magang sampai hari ini: absen berturut tidak terputus oleh pergantian periode.
    akhir_periode = min(hari_ini, selesai)
    kerja_magang = hari_kerja(mulai, akhir_periode, off, libur)
    berturut, terpanjang = _streak([_kelas(att_by.get(d), d, hari_ini) for d in kerja_magang])
    # Periode berjalan (bulan sejak mulai magang): dasar total absen dan izin dibayar.
    ke, p_awal, p_akhir = periode_berjalan(mulai, min(hari_ini, selesai))
    p_akhir = min(p_akhir, selesai)
    kelas_p = [_kelas(att_by.get(d), d, hari_ini) for d in hari_kerja(p_awal, min(hari_ini, p_akhir), off, libur)]
    absen_total = sum(k in ("absen", "ditolak") for k in kelas_p)
    izin_total = sum(k == "izin" for k in kelas_p)

    # Jendela rekap.
    a, b = max(dari, mulai), min(sampai, akhir_periode)
    kerja = hari_kerja(a, b, off, libur) if a <= b else []
    kelas = {d: _kelas(att_by.get(d), d, hari_ini) for d in kerja}
    hitung_k = {k: sum(v == k for v in kelas.values()) for k in ("hadir", "izin", "absen", "ditolak", "belum")}
    persetujuan = {"menunggu": 0, "disetujui": 0, "ditolak": 0}
    for d in kerja:
        ap = (att_by.get(d) or {}).get("approval_status")
        key = {"SUBMITTED": "menunggu", "APPROVED": "disetujui", "REJECTED": "ditolak"}.get(ap)
        if key:
            persetujuan[key] += 1
    revisi = sorted(d.isoformat() for d, l in log_by.items()
                    if d and a <= d <= b and l.get("state") == "NEEDS_REVISION")
    terhitung = len(kerja) - hitung_k["belum"]
    mentor = {"SUBMITTED": "menunggu", "APPROVED": "disetujui", "REJECTED": "ditolak"}
    harian = [{"tanggal": d.isoformat(), "kehadiran": kelas[d],
               "mentor": "revisi" if (log_by.get(d) or {}).get("state") == "NEEDS_REVISION"
               else mentor.get((att_by.get(d) or {}).get("approval_status"), "-")} for d in kerja]
    ditolak_tanggal = sorted(d.isoformat() for d, x in att_by.items()
                             if d and x.get("approval_status") == "REJECTED")
    disetujui_tanggal = sorted(d.isoformat() for d, x in att_by.items()
                               if d and x.get("approval_status") == "APPROVED")
    terakhir_periode = (bool(hari_kerja(hari_ini, hari_ini, off, libur)) and p_awal <= hari_ini <= p_akhir
                        and not hari_kerja(hari_ini + timedelta(days=1), p_akhir, off, libur))

    if berturut >= BATAS["nonaktif_berturut"] or absen_total >= BATAS["nonaktif_total"]:
        level = "nonaktif"
    elif berturut >= BATAS["peringatan_berturut"] or absen_total >= BATAS["peringatan_total"]:
        level = "peringatan"
    elif berturut == BATAS["peringatan_berturut"] - 1 or absen_total == BATAS["peringatan_total"] - 1:
        level = "waspada"
    else:
        level = "aman"

    return {
        "dari": a.isoformat(), "sampai": b.isoformat(), "hari_ini": hari_ini.isoformat(),
        "hari_kerja": len(kerja), "terhitung": terhitung,
        **hitung_k,
        "penuh": terhitung > 0 and hitung_k["hadir"] == terhitung,
        "persetujuan": persetujuan,
        "perlu_revisi": revisi,
        "harian": harian,
        "ditolak_tanggal": ditolak_tanggal,
        "disetujui_tanggal": disetujui_tanggal,
        "hari_kerja_terakhir_periode": terakhir_periode,
        "libur_di_jendela": sorted(f"{d.isoformat()} {n}" for d, n in libur.items() if a <= d <= b),
        "periode": {
            "mulai": mulai.isoformat(), "selesai": selesai.isoformat(),
            "hari_kerja_terlewati": len(kerja_magang),
            "ke": ke, "awal": p_awal.isoformat(), "akhir": p_akhir.isoformat(),
            "izin": izin_total, "izin_dibayar_sisa": max(0, BATAS["izin_dibayar"] - izin_total),
            "absen_total": absen_total, "absen_berturut": berturut, "absen_berturut_terpanjang": terpanjang,
            "status": level,
        },
        "catatan": "total absen dan izin dibayar dihitung per periode berjalan (bulan sejak mulai magang)",
    }


def jendela(jenis: str, hari_ini: date, mulai: date) -> tuple[date, date]:
    if jenis == "minggu":
        return hari_ini - timedelta(days=hari_ini.weekday()), hari_ini
    if jenis == "bulan":   # periode berjalan, bukan bulan kalender
        return periode_berjalan(mulai, hari_ini)[1], hari_ini
    return mulai, hari_ini


def collect_rekap(s, jenis: str = "periode", dari: str | None = None, sampai: str | None = None) -> dict:
    from .api import get, wajib

    me = wajib("/users/me", get(s, "/users/me"))
    home = wajib("/users/me/home", get(s, "/users/me/home"))
    hari_ini = _d(home.get("date")) or date.today()
    mulai = _d(me.get("internship_start_date")) or hari_ini
    a, b = jendela(jenis, hari_ini, mulai)
    if dari:
        a = _d(dari)
    if sampai:
        b = _d(sampai)
    pid = me.get("id")
    rng = {"participant_id": pid, "start_date": mulai.isoformat(), "end_date": hari_ini.isoformat()}
    atts = wajib("/attendances", get(s, "/attendances", {**rng, "limit": 400}) or [])
    logs = wajib("/daily-logs", get(s, "/daily-logs", {**rng, "limit": 400}) or [])
    hol = wajib("/holidays", get(s, "/holidays") or [])
    # Hanya field yang dipakai; koordinat & teks laporan dibuang di sini.
    atts = [{k: x.get(k) for k in ("date", "status", "approval_status")} for x in atts]
    logs = [{k: x.get(k) for k in ("date", "state")} for x in logs]
    keep = ("internship_start_date", "internship_end_date", "off_days",
            "internship_location_province_code", "internship_location_regency_code")
    res = hitung({k: me.get(k) for k in keep}, atts, logs, hol, a, b, hari_ini)
    res["jenis"] = jenis
    if len(atts) >= 400 or len(logs) >= 400:
        res["catatan"] += "; data mungkin terpotong (≥400 baris)"
    return res


def format_teks(r: dict) -> str:
    p = r["periode"]
    judul = {"minggu": "Rekap minggu ini", "bulan": f"Rekap periode {p['ke']}"}.get(r.get("jenis"), "Rekap sejak mulai magang")
    status = {"aman": "✅ aman dari peringatan", "waspada": "⚠️ waspada: satu absen lagi kena peringatan",
              "peringatan": "❗ sudah masuk batas PERINGATAN", "nonaktif": "⛔ sudah masuk batas NONAKTIF"}[p["status"]]
    baris = [
        f"📋 {judul} · {r['dari']} s.d. {r['sampai']}",
        f"Hari kerja {r['hari_kerja']}" + (f" (hari ini belum isi)" if r["belum"] else ""),
        f"Hadir {r['hadir']}/{r['terhitung']} · Izin {r['izin']} · Absen {r['absen'] + r['ditolak']}"
        + (f" (termasuk {r['ditolak']} ditolak mentor)" if r["ditolak"] else ""),
        "Kehadiran penuh ✓" if r["penuh"] else "Kehadiran belum penuh",
        f"Mentor: {r['persetujuan']['disetujui']} disetujui · {r['persetujuan']['menunggu']} menunggu · "
        f"{r['persetujuan']['ditolak']} ditolak",
    ]
    if r["perlu_revisi"]:
        baris.append("Perlu revisi: " + ", ".join(r["perlu_revisi"]))
    if r["libur_di_jendela"]:
        baris.append("Libur: " + "; ".join(r["libur_di_jendela"]))
    baris += [
        "",
        f"Periode {p['ke']} ({p['awal']} s.d. {p['akhir']}): absen {p['absen_total']} (peringatan di "
        f"{BATAS['peringatan_total']}), izin " + (f"{p['izin']} dari {BATAS['izin_dibayar']} yang dibayar"
                                                  if p["izin"] <= BATAS["izin_dibayar"]
                                                  else f"{p['izin']}, {p['izin'] - BATAS['izin_dibayar']} tidak dibayar"),
        f"Sejak mulai magang ({p['mulai']}): {p['hari_kerja_terlewati']} hari kerja, absen berturut "
        f"{p['absen_berturut']} (peringatan di {BATAS['peringatan_berturut']})",
        status,
    ]
    return "\n".join(baris)
