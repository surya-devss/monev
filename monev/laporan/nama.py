"""Saringan nama: nama klien dan proyek diambil dari sumber saat validasi, jadi tidak ada daftar yang harus dirawat.

Nama teknologi, standar, perusahaan sendiri, dan program magang boleh disebut (`[nama]` di aturan.toml).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

AKRONIM = re.compile(r"\b(?:[A-Z]{3,}|[A-Z][a-z]+[A-Z][A-Za-z]+)\b")
FRASA = re.compile(r"\b([A-Z][A-Za-z]{2,})\s+([A-Z][a-z]{2,})\b")
TAG = re.compile(r"\[([^\]]+)\]")
NON_KLIEN = {"", "internal", "none", "-"}


def normal(teks: str) -> str:
    return re.sub(r"[^a-z0-9]", "", teks.lower())


def _token(teks: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", teks.lower())


def ditemukan(nama: str, teks: str) -> bool:
    """Cocok walau beda huruf besar dan pemisah; nama panjang juga cocok di dalam satu kata (Pertamina di MyPertamina)."""
    n, kata = normal(nama), _token(teks)
    for i in range(len(kata)):
        gabungan = ""
        for k in kata[i:i + 4]:
            gabungan += k
            if gabungan == n:
                return True
    return len(n) >= 6 and any(n in k for k in kata)


@dataclass
class Saringan:
    dilarang: list[str] = field(default_factory=list)    # proyek/klien dari sumber: memblokir draft
    diwaspadai: list[str] = field(default_factory=list)  # akronim dari judul pekerjaan: peringatan
    lewati: list[str] = field(default_factory=list)      # proyek yang tidak masuk laporan

    def cek(self, teks: str) -> tuple[list[str], list[str]]:
        """Kembalikan (kesalahan, peringatan) untuk satu field."""
        salah = [f"menyebut {n!r} dari sumber, tulis secara umum (mis. \"aplikasi klien\")"
                 for n in self.dilarang if ditemukan(n, teks)]
        awas = [f"{n!r} mungkin nama internal, tulis secara umum bila bukan teknologi umum"
                for n in self.diwaspadai if ditemukan(n, teks)]
        tag = {normal(t) for t in TAG.findall(teks)}
        for n in self.lewati:
            if normal(n) in tag:
                salah.append(f"proyek {n!r} tidak masuk laporan (lewati_proyek)")
            elif ditemukan(n, teks):
                awas.append(f"menyebut {n!r}, pastikan bukan pekerjaan yang dilewati (lewati_proyek)")
        return salah, awas


def buat_saringan(semua: list[dict], hari_ini: list[dict], tambahan: list[str], rules: dict, perusahaan: str = "",
                  boleh: list[str] | None = None, lewati: list[str] | None = None) -> Saringan:
    """`semua`: proyek/klien seluruh catatan. `hari_ini`: pekerjaan tanggal draft. `tambahan`: nama dari sumber lain."""
    aturan = rules.get("nama", {})
    kata_perusahaan = set(_token(perusahaan))
    aman = {normal(x) for x in [*aturan.get("umum", []), *aturan.get("program", []), *(boleh or [])]}
    aman |= kata_perusahaan | {normal(perusahaan)}
    lewati_norm = {normal(x) for x in lewati or []}

    def layak(nama: str) -> bool:
        n, kata = normal(nama), _token(nama)
        return len(n) >= 3 and n not in aman and n not in lewati_norm and not all(k in aman or k.isdigit() for k in kata)

    def unik(nama: list[str]) -> list[str]:
        return list({normal(n): n for n in nama if layak(n)}.values())

    dilarang = [p.get("proyek", "") for p in semua + hari_ini] + list(tambahan)
    dilarang += [p.get("client", "") for p in semua + hari_ini if p.get("client", "").lower() not in NON_KLIEN]
    diwaspadai = []
    for p in hari_ini:
        judul = p.get("judul", "")
        diwaspadai += AKRONIM.findall(judul)
        # "<Perusahaan> Tools" adalah nama alat internal, walau nama perusahaannya sendiri boleh disebut.
        dilarang += [f"{a} {b}" for a, b in FRASA.findall(judul) if a.lower() in kata_perusahaan]
    keras = unik(dilarang)
    sudah = {normal(n) for n in keras}
    return Saringan(keras, [n for n in unik(diwaspadai) if normal(n) not in sudah], list(lewati or []))
