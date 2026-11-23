"""Skor kualitas draft terhadap laporan yang benar-benar terkirim (`monev eval`). Tanpa AI dan tanpa pustaka tambahan.

Kemiripan = TF-IDF kata (70%) + TF-IDF trigram huruf (30%). Ambang dikalibrasi dari uji mundur November 2026,
sampelnya masih sedikit, jadi skor dipakai untuk membandingkan versi aturan, bukan sebagai nilai mutlak.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

AMBANG = 0.28
STOP = set("""dan di ke dari yang untuk pada dengan agar serta atau lalu saya juga dalam oleh sebagai itu ini tersebut
karena sehingga bahwa sudah telah akan bisa dapat harus perlu tidak belum masih ada para secara hari sebuah setiap
kami kita mereka nya adalah yaitu berupa melalui hingga sampai saat bila jika""".split())
AWALAN = ("meng", "meny", "mem", "men", "me", "peng", "pem", "pen", "ber", "ter", "per", "di")
AKHIRAN = ("kannya", "annya", "kan", "an", "nya", "i")


def _dasar(kata: str) -> str:
    for a in AWALAN:
        if kata.startswith(a) and len(kata) - len(a) >= 4:
            kata = kata[len(a):]
            break
    for z in AKHIRAN:
        if kata.endswith(z) and len(kata) - len(z) >= 4:
            return kata[:-len(z)]
    return kata


def _kata(teks: str) -> list[str]:
    return [_dasar(k) for k in re.findall(r"[a-z0-9]+", teks.lower()) if k not in STOP and len(k) > 1]


def _trigram(teks: str) -> list[str]:
    s = " ".join(_kata(teks))
    return [s[i:i + 3] for i in range(max(len(s) - 2, 0))]


def _cosinus(a: dict, b: dict) -> float:
    atas = sum(v * b.get(k, 0) for k, v in a.items())
    bawah = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return atas / bawah if bawah else 0.0


class Pembanding:
    def __init__(self, dokumen: list[str]):
        self.n = len(dokumen) or 1
        self.df_kata, self.df_tri = Counter(), Counter()
        for d in dokumen:
            self.df_kata.update(set(_kata(d)))
            self.df_tri.update(set(_trigram(d)))

    def _vektor(self, token: list[str], df: Counter) -> dict:
        return {k: (1 + math.log(v)) * (math.log((1 + self.n) / (1 + df[k])) + 1) for k, v in Counter(token).items()}

    def skor(self, a: str, b: str) -> float:
        kata = _cosinus(self._vektor(_kata(a), self.df_kata), self._vektor(_kata(b), self.df_kata))
        tri = _cosinus(self._vektor(_trigram(a), self.df_tri), self._vektor(_trigram(b), self.df_tri))
        return 0.7 * kata + 0.3 * tri


def butir(teks: str) -> list[str]:
    return [re.sub(r"^\d+\.\s*", "", b).strip() for b in teks.splitlines() if b.strip()]


def kalimat(teks: str) -> list[str]:
    return [k.strip() for k in re.split(r"(?<=[.!?])\s+", teks) if len(k.strip()) > 20]


def arsip_sah(arsip: dict, tanggal: str) -> bool:
    """Arsip bisa dipakai sebagai kunci jawaban bila tanggalnya cocok dan kehadirannya tercatat."""
    return arsip.get("date") == tanggal and bool(arsip.get("status")) \
        and all(arsip.get(k) for k in ("activity_log", "lesson_learned", "obstacles"))


def muat_arsip(folder: Path) -> dict[str, dict]:
    """Laporan terkirim yang sah, per tanggal."""
    hasil = {}
    for f in sorted(folder.glob("????-??-??.json")) if folder.is_dir() else []:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if arsip_sah(data, f.stem):
            hasil[f.stem] = data
    return hasil


def sudah_dilaporkan(kegiatan: str, laporan: list[dict]) -> bool:
    """True bila `kegiatan` sudah tertulis di salah satu laporan."""
    teks = [t for l in laporan for t in butir(l["activity_log"]) + kalimat(l["lesson_learned"])]
    p = Pembanding(teks + [kegiatan])
    return any(p.skor(kegiatan, t) >= AMBANG for t in teks)


def _tercakup(asli: list[str], draft: list[str], p: Pembanding) -> int:
    return sum(1 for a in asli if draft and max(p.skor(a, d) for d in draft) >= AMBANG)


def nilai_draft(draft: dict, asli: dict) -> dict:
    """Bandingkan satu draft dengan laporan asli pada tanggal yang sama. Kendala ditampilkan tetapi tidak masuk skor:
    kendala yang sama sering ditulis dengan kata berbeda, jadi pencocokan kata belum bisa menilainya dengan adil."""
    keg_a, keg_d = butir(asli["activity_log"]), butir(draft.get("activity_log", ""))
    bel_a, bel_d = kalimat(asli["lesson_learned"]), kalimat(draft.get("lesson_learned", ""))
    ken_a, ken_d = kalimat(asli["obstacles"]), kalimat(draft.get("obstacles", ""))
    p = Pembanding(keg_a + keg_d + bel_a + bel_d + ken_a + ken_d)
    tambahan = sum(1 for d in keg_d if not keg_a or max(p.skor(d, a) for a in keg_a) < AMBANG)
    bagian = {"kegiatan": (_tercakup(keg_a, keg_d, p), len(keg_a)),
              "pembelajaran": (_tercakup(bel_a, bel_d, p), len(bel_a)),
              "kendala": (_tercakup(ken_a, ken_d, p), len(ken_a))}
    rasio = {k: (c / t if t else 0.0) for k, (c, t) in bagian.items()}
    skor = 0.7 * rasio["kegiatan"] + 0.3 * rasio["pembelajaran"]
    return {**{k: {"cocok": c, "total": t} for k, (c, t) in bagian.items()},
            "butir_tambahan": tambahan, "skor": round(skor * 100)}
