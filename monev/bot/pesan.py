"""Pesan bot Telegram. Contoh tampilannya ada di docs/teknis/format-pesan-telegram.md (ubah di sana juga).

Teks kalimat diambil dari `monev/teks/bawaan.toml` (bagian `[bot.*]`, plus `[fokus]` dan `[ingat.*]` yang sama dengan
extension), bisa ditimpa `[pesan]` di config. Di sini hanya susunan pesan, tombol, dan format angka/tanggal.

Gaya: kalimat pertama (tebal) sudah menjawab "ada apa", baris berikutnya konteks singkat, lalu tombol bila perlu.
Tanpa emoji (✓ boleh, itu tanda teks). Satu Pesan punya dua bentuk: `html` untuk rich message (tabel, kutipan) dan
`teks` (parse_mode HTML biasa) sebagai cadangan bila rich message gagal.
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass, field
from datetime import date, datetime

from ..portal.rekap import BATAS
from ..teks import isi_html

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
HARI3 = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
         "November", "Desember"]
BULAN3 = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
BATAS_KIRIM = "23.59"   # batas kirim harian Monev (aturan situs)

MENTOR = {"SUBMITTED": "menunggu persetujuan mentor", "APPROVED": "sudah disetujui mentor", "REJECTED": "ditolak mentor"}
MENTOR_PENDEK = {"SUBMITTED": "menunggu mentor", "APPROVED": "disetujui mentor", "REJECTED": "ditolak mentor"}


@dataclass
class Pesan:
    teks: str                                   # parse_mode HTML (cadangan / pesan pendek)
    html: str | None = None                     # rich message; None = cukup teks biasa
    tombol: list[list[tuple[str, str]]] = field(default_factory=list)   # baris → (label, callback_data)
    judul: str = ""                             # pengingat: judul yang dicoret saat laporan sudah terkirim

    def __str__(self) -> str:
        return self.teks


class Teks:
    """Akses teks gabungan (bawaan + config): tx("bot.kartu.sapaan", nama="Rina") → HTML aman."""

    def __init__(self, data: dict):
        self.data = data

    def mentah(self, kunci: str):
        d = self.data
        for k in kunci.split("."):
            d = d[k]
        return d

    def __call__(self, kunci: str, **isi) -> str:
        return isi_html(self.mentah(kunci), **isi)


# ---------------------------------------------------------------- bantu

def e(x) -> str:
    return _html.escape(str(x), quote=False)


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


def tgl(d: date) -> str:
    """17 Nov"""
    return f"{d.day} {BULAN3[d.month - 1]}"


def tgl_hari(d: date) -> str:
    """Selasa, 17 Nov"""
    return f"{HARI[d.weekday()]}, {tgl(d)}"


def rentang(a: date, b: date) -> str:
    """17–21 Nov 2026"""
    if a.month == b.month:
        return f"{a.day}–{b.day} {BULAN3[b.month - 1]} {b.year}"
    return f"{tgl(a)} – {tgl(b)} {b.year}"


def jam_teks(jam: str) -> str:
    """'16:30' → '16.30'"""
    return jam.replace(":", ".")


def lama_teks(menit: int) -> str:
    return f"{menit // 60} jam" if menit % 60 == 0 else f"{menit} menit"


def panggilan(st: dict, dari_config: str = "") -> str:
    """Nama sapaan: `[profil] panggilan` di config, atau nama depan dari profil Monev."""
    return dari_config or ((st.get("nama") or "").split() or [""])[0]


def _susun(*bagian) -> tuple[str, str]:
    """Bagian: ("p", [baris]) | ("tabel", [[sel]], kepala|None) | ("kutip", [baris]). → (teks, html)."""
    teks, html = [], []
    for b in bagian:
        if not b:
            continue
        jenis = b[0]
        if jenis == "p":
            baris = [x for x in b[1] if x]
            teks.append("\n".join(baris))
            html.append("<p>" + "<br/>".join(baris) + "</p>")
        elif jenis == "tabel":
            rows, kepala = b[1], b[2]
            if kepala:
                teks.append("\n".join("• " + " · ".join(r) for r in rows))
                html.append("<table bordered striped compact><tr>" + "".join(f"<th>{k}</th>" for k in kepala) + "</tr>"
                            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")
            else:   # tabel kunci → nilai
                teks.append("\n".join(f"<b>{k}</b>  {v}" for k, v in rows))
                html.append("<table bordered compact>" + "".join(f"<tr><td><b>{k}</b></td><td>{v}</td></tr>" for k, v in rows)
                            + "</table>")
        elif jenis == "kutip":
            teks.append("<blockquote>" + "\n".join(b[1]) + "</blockquote>")
            html.append("<blockquote>" + "<br/>".join(b[1]) + "</blockquote>")
    return "\n\n".join(teks), "".join(html)


def _pesan(*bagian, tombol=None) -> Pesan:
    teks, html = _susun(*bagian)
    return Pesan(teks, html, tombol or [])


def nilai_hari_ini(nilai: dict | None, hari: date) -> tuple[str, str, str] | None:
    """(semboyan, nilai, penerapan) untuk hari itu dari `[profil.nilai]` di config, atau None bila kosong.

    Satu poin per hari, digilir dengan `hari.toordinal()` sehingga bot dan extension memilih poin yang sama."""
    daftar = (nilai or {}).get("poin") or []
    if not daftar:
        return None
    nama, terap = daftar[hari.toordinal() % len(daftar)]
    return (nilai or {}).get("semboyan", ""), nama, terap


def _status_laporan(tx: Teks, st: dict) -> str:
    k = st.get("kehadiran") or {}
    if st.get("sudah_isi"):
        return tx("bot.kartu.laporan_sudah", mentor=MENTOR_PENDEK.get(k.get("persetujuan"), "status mentor belum terbaca"))
    return tx("bot.kartu.laporan_belum")


def _revisi(tx: Teks, st: dict) -> str:
    rev = st.get("perlu_revisi") or []
    return ", ".join(tgl(_d(r["date"])) for r in rev) if rev else tx("bot.kartu.revisi_tidak")


# ---------------------------------------------------------------- kartu hari ini (08.00, diperbarui sepanjang hari)

def tombol_kartu(tx: Teks) -> list:
    return [[(tx.mentah("bot.tombol.status"), "b:status"), (tx.mentah("bot.tombol.rekap"), "b:minggu"),
             (tx.mentah("bot.tombol.menu"), "b:menu")]]


def kartu(tx: Teks, st: dict, nilai: dict | None = None, nama: str = "") -> Pesan:
    d = _d(st["tanggal"])
    kerja = " di ".join(e(x) for x in (st.get("posisi"), st.get("perusahaan")) if x)
    baris = [(tx("bot.kartu.label_laporan"), _status_laporan(tx, st)), (tx("bot.kartu.label_revisi"), _revisi(tx, st))]
    if not st.get("sudah_isi"):
        baris.append((tx("bot.kartu.label_batas"), f"{BATAS_KIRIM} WIB"))
    fokus = [tx.mentah("fokus.senin")] if d.weekday() == 0 else [tx.mentah("fokus.jumat")] if d.weekday() == 4 else []
    fokus = [isi_html(x) for x in fokus + list(tx.mentah("fokus.poin"))]
    n = nilai_hari_ini(nilai, d)
    if n:
        fokus.append(f"<b>{e(n[1])}.</b> {e(n[2][:1].upper() + n[2][1:])}" if n[2] else f"<b>{e(n[1])}</b>")
        if n[0]:
            fokus.append(f"<i>{e(n[0])}</i>")
    return _pesan(("p", [f"<b>{tx('bot.kartu.sapaan', nama=nama)}</b>", " · ".join(x for x in (tgl_hari(d), kerja) if x)]),
                  ("tabel", baris, None),
                  ("p", [f"<b>{tx('bot.kartu.fokus')}</b>"]),
                  ("kutip", fokus),
                  tombol=tombol_kartu(tx))


def kartu_libur(tx: Teks, st: dict, nama: str = "") -> Pesan:
    d = _d(st["tanggal"])
    return Pesan(f"<b>{tx('bot.kartu.libur_judul', nama=nama)}</b>\n{tx('bot.kartu.libur_isi', hari=tgl_hari(d))}",
                 tombol=[[(tx.mentah("bot.tombol.menu"), "b:menu")]])


# ---------------------------------------------------------------- pengingat

def ingat(tx: Teks, urutan: str, hari: date, sisa_jam: int, tunda_menit: int) -> Pesan:
    """urutan: pertama | kedua | terakhir (makin tegas). Teksnya sama dengan notifikasi extension."""
    data = {"hari": tgl_hari(hari), "batas": BATAS_KIRIM, "sisa": str(max(1, sisa_jam))}
    judul = tx(f"ingat.{urutan}.judul", **data)
    teks = f"<b>{judul}</b>\n{tx(f'ingat.{urutan}.isi', **data)}\n{tx('bot.ingat.tindakan')}"
    return Pesan(teks, judul=judul,
                 tombol=[[(tx.mentah("bot.tombol.tunda").replace("{lama}", lama_teks(tunda_menit)), f"tunda:{urutan}"),
                          (tx.mentah("bot.tombol.cek"), "cek")]])


def ingat_selesai(tx: Teks, judul: str) -> Pesan:
    """Pengingat yang laporannya sudah terkirim: judul dicoret, tombol hilang."""
    return Pesan(f"<s>{judul}</s>\n<i>{tx('bot.ingat.selesai')}</i>")


def ingat_ditunda(tx: Teks, asli: str, jam: str) -> Pesan:
    return Pesan(f"{asli}\n<i>{tx('bot.ingat.tunda', jam=jam_teks(jam))}</i>", tombol=[[(tx.mentah("bot.tombol.cek"), "cek")]])


# ---------------------------------------------------------------- perubahan dari Monev

def terkirim(tx: Teks, st: dict) -> Pesan:
    k = st.get("kehadiran") or {}
    if k.get("status") != "PRESENT":
        rincian = {"ON_LEAVE": "izin"}.get(k.get("status"), k.get("status") or "-")
    elif k.get("ada_lokasi"):
        rincian = "hadir dan lokasi ikut terkirim"
    else:
        rincian = "hadir, tapi lokasi tidak ikut terkirim, cek di Riwayat Monev"
    mentor = MENTOR.get(k.get("persetujuan"), "status mentor belum terbaca")
    return Pesan(f"<b>{tx('bot.terkirim.judul', tanggal=tgl(_d(st['tanggal'])))}</b>\n"
                 f"{tx('bot.terkirim.isi', rincian=rincian, mentor=mentor)}")


def revisi(tx: Teks, tanggal: str, catatan: str) -> Pesan:
    return Pesan(f"<b>{tx('bot.revisi.judul', tanggal=tgl(_d(tanggal)))}</b>\n"
                 f"<blockquote>{e(catatan) if catatan else tx('bot.revisi.tanpa_catatan')}</blockquote>\n"
                 f"{tx('bot.revisi.tindakan')}")


def daftar_tanggal(tanggal: list[str]) -> str:
    """["2026-11-17", "2026-11-18", "2026-11-19"] → "17, 18, dan 19 Nov"; beda bulan → "30 Nov dan 1 Des"."""
    d = [_d(t) for t in sorted(tanggal)]
    sebulan = len({(x.year, x.month) for x in d}) == 1
    teks = [str(x.day) for x in d[:-1]] if sebulan else [tgl(x) for x in d[:-1]]
    akhir = tgl(d[-1])
    if not teks:
        return akhir
    return f"{teks[0]} dan {akhir}" if len(teks) == 1 else f"{', '.join(teks)}, dan {akhir}"


def disetujui(tx: Teks, tanggal: list[str], jumlah: int, total: int) -> Pesan:
    """Satu pesan untuk semua tanggal yang baru disetujui mentor sejak pengecekan terakhir."""
    return Pesan(f"<b>{tx('bot.disetujui.judul', tanggal=daftar_tanggal(tanggal))}</b>\n"
                 f"{tx('bot.disetujui.isi', jumlah=str(jumlah), total=str(total))}")


def ditolak(tx: Teks, tanggal: str, absen_total: int) -> Pesan:
    return Pesan(f"<b>{tx('bot.ditolak.judul', tanggal=tgl(_d(tanggal)))}</b>\n"
                 f"{tx('bot.ditolak.isi', absen=str(absen_total), batas_absen=str(BATAS['peringatan_total']))}\n"
                 f"{tx('bot.ditolak.tindakan')}")


def draft(tx: Teks, jenis: str, tanggal: str, sisa: int | None = None) -> Pesan:
    """Kabar dari proses terjadwal di laptop. jenis: siap | kosong | cek | sesi | format | sesi_hampir.
    `tanggal` = tanggal laporan, atau tanggal habis sesi untuk sesi_hampir. Isi laporan tidak pernah ikut."""
    k = f"bot.draft.{jenis}"
    kapan = "" if sisa is None else "hari ini" if sisa <= 0 else f"dalam {sisa} hari"
    return Pesan(f"<b>{tx(k + '.judul', tanggal=tgl(_d(tanggal)), kapan=kapan)}</b>\n{tx(k + '.isi')}\n{tx(k + '.tindakan')}")


def web_berubah(tx: Teks) -> Pesan:
    """Situs Monev di-deploy ulang (nama file utama frontend berganti). Teks `[web]` sama dengan notifikasi extension."""
    return Pesan(f"<b>{tx('web.judul')}</b>\n{tx('web.isi')}\n{tx('web.tindakan')}")


def masa(tx: Teks, jenis: str, sisa: int, tanggal: date) -> Pesan:
    """Kabar masa magang. jenis: h30 | h7 | terakhir | selesai | dini."""
    k = f"bot.masa.{jenis}"
    return Pesan(f"<b>{tx(k + '.judul', sisa=str(sisa), tanggal=tgl(tanggal) + f' {tanggal.year}')}</b>\n{tx(k + '.isi')}")


# ---------------------------------------------------------------- sistem

def sesi(tx: Teks, sisa: int, sampai: date) -> Pesan:
    kapan = "hari ini" if sisa <= 0 else f"dalam {sisa} hari"
    return Pesan(f"<b>{tx('bot.sesi.judul', kapan=kapan, tanggal=tgl(sampai))}</b>\n{tx('bot.sesi.isi')}\n"
                 f"{tx('bot.sesi.tindakan')}")


def gangguan(tx: Teks, alasan: str, percobaan: list[str], berikut: str | None, sebab: str = "lain") -> Pesan:
    """sebab: sesi | monev | format | lain (lihat app.sebab). Tombol cara login hanya untuk sesi habis."""
    coba = " dan ".join(jam_teks(j) for j in percobaan) if len(percobaan) <= 2 \
        else ", ".join(jam_teks(j) for j in percobaan[:-1]) + f", dan {jam_teks(percobaan[-1])}"
    lanjut = tx("bot.gangguan.percobaan", jam=coba, berikut=jam_teks(berikut) if berikut else "besok")
    tombol = [(tx.mentah("bot.tombol.coba"), "coba")] + ([(tx.mentah("bot.tombol.cara"), "cara")] if sebab == "sesi" else [])
    return Pesan(f"<b>{tx('bot.gangguan.judul')}</b>\n{tx(f'bot.gangguan.sebab.{sebab}', alasan=alasan)}\n<i>{lanjut}</i>",
                 tombol=[tombol])


def gangguan_pulih(tx: Teks, jam: str) -> Pesan:
    return Pesan(f"<s>{tx('bot.gangguan.judul')}</s>\n<i>{tx('bot.gangguan.pulih', jam=jam_teks(jam))}</i>")


def ping(tx: Teks, mulai: datetime) -> Pesan:
    return Pesan(tx("bot.ping.isi", tanggal=tgl(mulai.date()), jam=f"{mulai:%H.%M}"))


# ---------------------------------------------------------------- menu (satu pesan, isinya berganti di tempat)

def _kembali(tx: Teks, *lain) -> list:
    return [[(tx.mentah("bot.tombol.kembali"), "v:menu"), *lain]]


def menu(tx: Teks, nama: str = "", menit: int = 10) -> Pesan:
    t = tx.mentah("bot.tombol")
    return _pesan(("p", [f"<b>{tx('bot.menu.judul', nama=nama)}</b>", tx("bot.menu.isi", menit=menit)]),
                  tombol=[[(t["status_hari_ini"], "v:status"), (t["rekap_minggu"], "v:minggu")],
                          [(t["rekap_bulan"], "v:bulan"), (t["jadwal"], "v:jadwal")],
                          [(t["bantuan"], "v:bantuan")]])


def memuat(tx: Teks) -> Pesan:
    """Pengganti sementara selama Chrome membaca Monev; tanpa tombol supaya tidak ditekan dua kali."""
    return _pesan(("p", [f"<i>{tx('bot.menu.memuat')}</i>"]))


def dengan_waktu(tx: Teks, p: Pesan, waktu: datetime, nama: str) -> Pesan:
    """Tambah "Data Monev pukul HH.MM." di bawah dan tombol ↻ Segarkan (`s:<nama>`, baca ulang di tempat)."""
    catatan = f"<i>{tx('bot.menu.diperbarui', jam=f'{waktu:%H.%M}')}</i>"
    tombol = [list(b) for b in p.tombol] or [[]]
    tombol[0].append((tx.mentah("bot.tombol.segarkan"), f"s:{nama}"))
    return Pesan(f"{p.teks}\n\n{catatan}", (p.html or "") + f"<p>{catatan}</p>" if p.html else None, tombol, p.judul)


def status(tx: Teks, st: dict, sesi_sampai: date | None) -> Pesan:
    d = _d(st["tanggal"])
    libur = st.get("libur_nasional") or st.get("libur_posisi")
    k = st.get("kehadiran") or {}
    belum = not libur and not st.get("sudah_isi")
    if not st.get("magang_aktif", True):
        judul = tx("bot.status.tidak_aktif")
    elif libur:
        judul = tx("bot.status.libur")
    elif st.get("sudah_isi"):
        judul = tx("bot.status.sudah", mentor=MENTOR.get(k.get("persetujuan"), "status mentor belum terbaca"))
    else:
        judul = tx("bot.status.belum")
    hari = tx("bot.status.hari_libur") if libur else tx("bot.status.hari_kerja")
    baris = [(tx("bot.status.label_tanggal"), f"{tgl_hari(d)}, {hari}"),
             (tx("bot.kartu.label_laporan"), _status_laporan(tx, st)),
             (tx("bot.kartu.label_revisi"), _revisi(tx, st))]
    if belum:
        baris.append((tx("bot.kartu.label_batas"), f"{BATAS_KIRIM} WIB"))
    baris.append((tx("bot.status.label_sesi"),
                  tx("bot.status.sesi_aktif", tanggal=tgl(sesi_sampai)) if sesi_sampai else tx("bot.status.sesi_tidak")))
    return _pesan(("p", [f"<b>{judul}</b>"]), ("tabel", baris, None),
                  ("p", [tx("bot.status.tindakan")]) if belum else None,
                  tombol=_kembali(tx))


def izin_teks(izin: int) -> str:
    """'0 dari 3 yang dibayar'; lewat jatah → '4, 1 tidak dibayar'."""
    n = BATAS["izin_dibayar"]
    return f"{izin} dari {n} yang dibayar" if izin <= n else f"{izin}, {izin - n} tidak dibayar"


def absen_teks(p: dict) -> str:
    """'0 (peringatan di 7)'. Absen periode berjalan, termasuk kehadiran yang ditolak mentor."""
    return f"{p['absen_total']} (peringatan di {BATAS['peringatan_total']})"


def kalimat_status(p: dict) -> str:
    return {"aman": "Aman, belum mendekati batas peringatan.",
            "waspada": "Hati-hati, satu absen lagi sudah kena peringatan.",
            "peringatan": "<b>Sudah masuk batas peringatan.</b>",
            "nonaktif": "<b>Sudah masuk batas nonaktif.</b>"}[p["status"]]


def rekap_minggu(tx: Teks, r: dict) -> Pesan:
    a, b = _d(r["dari"]), _d(r["sampai"])
    p = r["periode"]
    hari = [[f"{HARI3[_d(h['tanggal']).weekday()]} {_d(h['tanggal']).day}", e(h["kehadiran"]), e(h["mentor"])]
            for h in r["harian"]]
    return _pesan(("p", [f"<b>Minggu ini hadir {r['hadir']} dari {r['terhitung']} hari.</b>", rentang(a, b)]),
                  ("tabel", hari, ["Hari", "Kehadiran", "Mentor"]),
                  ("p", [f"{tx('bot.rekap.periode', ke=str(p['ke']))}: absen {absen_teks(p)}, izin {izin_teks(p['izin'])}.",
                         kalimat_status(p)]),
                  tombol=_kembali(tx, (tx.mentah("bot.tombol.rekap_bulan") + " ›", "v:bulan")))


def rekap_bulan(tx: Teks, r: dict) -> Pesan:
    """Rekap periode berjalan (satu bulan sejak tanggal mulai magang), bukan bulan kalender."""
    p, ps = r["periode"], r["persetujuan"]
    a, b = _d(p["awal"]), _d(p["akhir"])
    revisi_n = sum(1 for h in r["harian"] if h["mentor"] == "revisi")
    inti = "kehadiran penuh" if r["penuh"] else f"hadir {r['hadir']} dari {r['terhitung']} hari"
    absen = absen_teks(p) + (f", {r['ditolak']} di antaranya ditolak mentor" if r["ditolak"] else "")
    baris = [("Hadir", str(r["hadir"])),
             ("Izin", izin_teks(p["izin"])),
             ("Absen", absen),
             ("Berturut", f"absen {p['absen_berturut']} (peringatan di {BATAS['peringatan_berturut']})"),
             ("Mentor", f"{ps['disetujui']} disetujui, {ps['menunggu']} menunggu, {revisi_n} perlu revisi")]
    judul = tx("bot.rekap.periode", ke=str(p["ke"]))
    return _pesan(("p", [f"<b>{judul}, {inti}.</b>", f"{rentang(a, b)} · {r['hari_kerja']} hari kerja sampai hari ini"]),
                  ("tabel", baris, None), ("p", [kalimat_status(p)]),
                  tombol=_kembali(tx, (tx.mentah("bot.tombol.rekap_minggu") + " ›", "v:minggu")))


def jadwal(tx: Teks, kartu_jam: str, pengingat: list[str], rekap_jam: str) -> Pesan:
    baris = [(jam_teks(kartu_jam), tx("bot.jadwal.kartu"))]
    for i, j in enumerate(pengingat):
        baris.append((jam_teks(j), tx("bot.jadwal.terakhir") if i == len(pengingat) - 1 and i else tx("bot.jadwal.pengingat")))
    baris.append((f"Jum {jam_teks(rekap_jam)}", tx("bot.jadwal.rekap")))
    return _pesan(("p", [f"<b>{tx('bot.jadwal.judul')}</b>"]), ("tabel", baris, None), ("p", [tx("bot.jadwal.isi")]),
                  tombol=_kembali(tx))


def bantuan(tx: Teks, pengingat: list[str]) -> Pesan:
    jam = ", ".join(jam_teks(j) for j in pengingat[:-1]) + f", dan {jam_teks(pengingat[-1])}" if len(pengingat) > 1 \
        else jam_teks(pengingat[0]) if pengingat else "-"
    return _pesan(("p", [f"<b>{tx('bot.bantuan.judul')}</b>"]),
                  ("p", ["/menu semua pilihan", "/status status laporan hari ini", "/rekap rekap minggu ini",
                         "/rekap_bulan rekap periode berjalan", "/ping cek bot masih aktif"]),
                  ("p", [tx("bot.bantuan.isi", jam=jam), f"<i>{tx('bot.bantuan.catatan')}</i>"]),
                  tombol=_kembali(tx))
