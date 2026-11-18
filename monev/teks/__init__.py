"""Teks notifikasi: bawaan di `bawaan.toml`, ditimpa sebagian oleh `[pesan]` di config.toml.

Extension mengambil hasil gabungannya lewat monev-native-host (`{"type": "pesan"}`), jadi tidak ada teks
notifikasi yang ditulis langsung di kode extension.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

BAWAAN = Path(__file__).with_name("bawaan.toml")
PLACEHOLDER = {"nama", "hari", "tanggal", "batas", "sisa", "alasan", "jam", "mentor", "rincian", "absen",
               "batas_absen", "kapan", "berikut", "lama", "menit"}


def bawaan() -> dict:
    return tomllib.loads(BAWAAN.read_text(encoding="utf-8"))


def _gabung(dasar: dict, timpa: dict, jalur: str, asing: list[str]) -> dict:
    out = {}
    for k, v in dasar.items():
        t = timpa.get(k)
        if isinstance(v, dict):
            out[k] = _gabung(v, t if isinstance(t, dict) else {}, f"{jalur}{k}.", asing)
        elif isinstance(v, list):
            out[k] = [str(x) for x in t] if isinstance(t, list) and t else v
        else:
            out[k] = str(t) if isinstance(t, str) and t.strip() else v
    asing += [f"{jalur}{k}" for k in timpa if k not in dasar]
    return out


def muat(timpa: dict | None = None) -> tuple[dict, list[str]]:
    """(teks gabungan, daftar kunci di config yang tidak dikenal). Kunci asing diabaikan, tipe harus sama."""
    asing: list[str] = []
    return _gabung(bawaan(), timpa or {}, "pesan.", asing), asing


def placeholder(teks: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", teks))


def semua_teks(d: dict, jalur: str = ""):
    """(kunci, teks) untuk setiap string di pohon teks; dipakai test dan `monev config`."""
    for k, v in d.items():
        if isinstance(v, dict):
            yield from semua_teks(v, f"{jalur}{k}.")
        elif isinstance(v, list):
            for i, x in enumerate(v):
                yield f"{jalur}{k}[{i}]", x
        else:
            yield f"{jalur}{k}", v


def isi_html(t: str, **data) -> str:
    """Isi placeholder untuk pesan HTML (bot): template dan nilainya di-escape, `teks` jadi <code>teks</code>,
    placeholder kosong dibuang bersama ", " di depannya (aturan yang sama dengan extension)."""
    import html

    def ganti(m):
        v = data.get(m.group(2))
        return (m.group(1) or "") + html.escape(str(v), quote=False) if v not in (None, "") else ""

    hasil = re.sub(r"(, )?\{(\w+)\}", ganti, html.escape(t, quote=False))
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", hasil)
