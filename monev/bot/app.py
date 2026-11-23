"""Proses `monev bot`: long polling Telegram + jadwal harian. Tanpa AI, hanya membaca Monev.

Hanya chat milik TELEGRAM_CHAT_ID yang dilayani; pesan dan tombol dari chat lain diabaikan.
Data Monev diambil lewat Chrome profil CLI (headless) yang dibuka per pengecekan lalu ditutup.

Pesan yang diperbarui di tempat (id-nya disimpan di state per hari):
- kartu hari ini: isinya mengikuti status terbaru di setiap pengecekan;
- pengingat: dicoret dan tombolnya hilang setelah laporan terkirim;
- gangguan: satu pesan per hari, diperbarui di setiap percobaan, dicoret setelah pulih;
- menu: tombol `v:*` mengganti isi pesan menu itu sendiri, tombol `b:*` (di kartu) membuka pesan baru,
  tombol `s:*` (↻ Segarkan) membaca ulang Monev di tempat.

Hasil baca Monev disimpan di memori (`CACHE_MENIT`): status/rekap yang ditekan lagi dalam rentang itu langsung
dijawab tanpa membuka Chrome. Pengecekan terjadwal dan tombol "Sudah kirim, cek" selalu membaca ulang.
Saat Chrome harus dibuka, pesannya diganti dulu dengan "⏳ Membaca Monev…" supaya kelihatan sedang bekerja.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta

from . import pesan as P
from .jadwal import (WIB, Konteks, baca_state, buat_jadwal, jadwal_berikutnya, jadwal_jatuh_tempo, putuskan,
                     tulis_state)
from .telegram import Telegram

CACHE_MENIT = 10
DATA = {"status": (), "minggu": ("minggu",), "bulan": ("bulan",)}   # tampilan yang butuh baca Monev → rekap


class SesiMati(RuntimeError):
    pass


class MonevTidakSiap(RuntimeError):
    pass


def sebab(ex: Exception) -> str:
    """Golongan gangguan untuk teks `[bot.gangguan.sebab]`: sesi | monev | format | lain."""
    from ..portal.api import ApiError, FormatBerubah

    if isinstance(ex, SesiMati) or (isinstance(ex, ApiError) and ex.status in (401, 403)):
        return "sesi"
    if isinstance(ex, FormatBerubah) or (isinstance(ex, ApiError) and ex.status == 404):
        return "format"
    if isinstance(ex, (MonevTidakSiap, ApiError, OSError)) or "Timeout" in type(ex).__name__:
        return "monev"
    return "lain"


def ambil(cfg, rekap: tuple[str, ...] = ()) -> dict:
    """Satu sesi Chrome headless: status + tanggal habis sesi + rekap yang diminta. Chrome selalu ditutup."""
    from ..portal.api import collect_status
    from ..portal.browser import (SESSION_LOGIN, SESSION_OK, open_browser, open_dashboard, refresh_cookie_expiry,
                                  versi_web)
    from ..portal.rekap import collect_rekap

    with open_browser(cfg, headless=True) as s:
        hasil = open_dashboard(s)
        if hasil == SESSION_LOGIN:
            raise SesiMati("sesi Monev habis, perlu login ulang")
        if hasil != SESSION_OK:
            raise MonevTidakSiap("halaman Monev tidak siap dalam 25 detik")
        out = {"status": collect_status(s), "sesi_sampai": refresh_cookie_expiry(s), "nilai": cfg.nilai_dict(),
               "versi_web": versi_web(s)}
        out["periode"] = collect_rekap(s, "periode")
        for j in rekap:
            out[j] = collect_rekap(s, j)
    return out


class Bot:
    def __init__(self, cfg, tg: Telegram, chat_id: str, log=print, ambil_data=ambil):
        from ..teks import muat

        self.cfg, self.tg, self.chat_id, self.log, self.ambil = cfg, tg, str(chat_id), log, ambil_data
        self.tx = P.Teks(muat(cfg.pesan)[0])
        self.jadwal_list = buat_jadwal(cfg)
        self.state = baca_state()
        self.mulai = datetime.now(WIB)
        self._cache: dict | None = None     # {"waktu": datetime, "isi": hasil ambil()}

    # ------------------------------------------------------------ bantu

    def konteks(self) -> Konteks:
        return Konteks(self.tx, self.cfg.nilai_dict(), self.cfg.panggilan, self.cfg.bot_tunda_menit)

    def nama(self) -> str:
        return P.panggilan({"nama": self.state.get("nama_monev", "")}, self.cfg.panggilan)

    def hari(self, sekarang: datetime) -> dict:
        """Catatan pesan hari ini (kartu, pengingat, gangguan, tunda). Hari berganti → mulai kosong."""
        h = self.state.get("hari") or {}
        if h.get("tanggal") != sekarang.date().isoformat():
            h = {"tanggal": sekarang.date().isoformat(), "ingat": []}
            self.state["hari"] = h
        return h

    def kirim(self, p) -> int | None:
        return self.tg.kirim(self.chat_id, p)

    def ubah(self, message_id: int | None, p) -> None:
        if message_id:
            try:
                self.tg.ubah(self.chat_id, message_id, p)
            except RuntimeError as ex:   # pesan terlalu lama / sudah dihapus: tidak fatal
                self.log(f"  ubah pesan {message_id} gagal: {ex}")

    def segar(self, rekap: tuple[str, ...] = ()) -> bool:
        c = self._cache
        return bool(c) and datetime.now(WIB) - c["waktu"] < timedelta(minutes=CACHE_MENIT) \
            and all(k in c["isi"] for k in rekap)

    def baca(self, rekap: tuple[str, ...] = (), segarkan: bool = False) -> dict:
        """Data Monev dari cache bila masih segar; selain itu buka Chrome (lambat) lalu simpan ke cache."""
        if not segarkan and self.segar(rekap):
            return self._cache["isi"]
        data = self.ambil(self.cfg, rekap)
        self._cache = {"waktu": datetime.now(WIB), "isi": data}
        self.state["nama_monev"] = data["status"].get("nama") or self.state.get("nama_monev", "")
        return data

    # ------------------------------------------------------------ inti: jalankan satu pengecekan

    def jalankan(self, jenis: str, sekarang: datetime) -> bool:
        """Cek Monev lalu kirim/perbarui pesan. True bila laporan hari ini sudah terkirim. Error → gangguan()."""
        rekap = ("minggu", "bulan") if jenis == "rekap" else ()
        data = self.baca(rekap, segarkan=True)
        k = putuskan(jenis, data, self.state.get("lalu", {}), sekarang, self.konteks())
        h = self.hari(sekarang)
        for tag, p in k.kirim:
            mid = self.kirim(p)
            if tag == "kartu":
                h["kartu"] = {"id": mid, "isi": p.teks}
            elif tag.startswith("ingat:"):
                h["ingat"].append({"id": mid, "judul": p.judul, "teks": p.teks, "selesai": False})
        kartu = h.get("kartu")
        if k.kartu and kartu and kartu.get("isi") != k.kartu.teks:
            self.ubah(kartu["id"], k.kartu)
            kartu["isi"] = k.kartu.teks
        if k.sudah_isi:
            for x in h["ingat"]:
                if not x["selesai"]:
                    self.ubah(x["id"], P.ingat_selesai(self.tx, x["judul"]))
                    x["selesai"] = True
            h.pop("tunda", None)
        self.state["lalu"] = k.baru
        g = h.get("gangguan")
        if g and not g.get("pulih"):
            self.ubah(g["id"], P.gangguan_pulih(self.tx, f"{sekarang:%H:%M}"))
            g["pulih"] = True
        tulis_state(self.state)
        return k.sudah_isi

    def gangguan(self, sekarang: datetime, ex: Exception) -> None:
        """Satu pesan gangguan per hari; percobaan berikutnya memperbarui pesan yang sama."""
        h = self.hari(sekarang)
        g = h.get("gangguan")
        jam = f"{sekarang:%H:%M}"
        berikut = jadwal_berikutnya(self.jadwal_list, sekarang)
        jenis, alasan = sebab(ex), str(ex)
        try:
            if g and not g.get("pulih"):
                if jam not in g["jam"]:
                    g["jam"].append(jam)
                self.ubah(g["id"], P.gangguan(self.tx, alasan, g["jam"], berikut, jenis))
            else:
                h["gangguan"] = {"id": self.kirim(P.gangguan(self.tx, alasan, [jam], berikut, jenis)), "jam": [jam]}
        except RuntimeError as ex:
            self.log(f"  gagal kirim pesan gangguan: {ex}")
        tulis_state(self.state)

    def coba_jalankan(self, jenis: str, sekarang: datetime) -> bool | None:
        try:
            return self.jalankan(jenis, sekarang)
        except Exception as ex:  # noqa: BLE001
            self.log(f"  gagal: {ex}")
            self.gangguan(sekarang, ex)
            return None

    # ------------------------------------------------------------ tampilan menu

    def tampilan(self, nama: str, segarkan: bool = False) -> P.Pesan:
        cfg = self.cfg
        if nama == "menu":
            return P.menu(self.tx, self.nama(), CACHE_MENIT)
        if nama == "jadwal":
            return P.jadwal(self.tx, cfg.bot_kartu, cfg.bot_pengingat, cfg.bot_rekap)
        if nama == "bantuan":
            return P.bantuan(self.tx, cfg.bot_pengingat)
        try:
            data = self.baca(DATA.get(nama, ()), segarkan)
        except Exception as ex:  # noqa: BLE001
            return P.Pesan(f"<b>{self.tx('bot.gangguan.judul')}</b>\n{self.tx(f'bot.gangguan.sebab.{sebab(ex)}', alasan=str(ex))}",
                           tombol=[[(self.tx.mentah("bot.tombol.kembali"), "v:menu")]])
        if nama == "minggu":
            p = P.rekap_minggu(self.tx, data["minggu"])
        elif nama == "bulan":
            p = P.rekap_bulan(self.tx, data["bulan"])
        else:
            nama = "status"
            p = P.status(self.tx, data["status"], data["sesi_sampai"])
        return P.dengan_waktu(self.tx, p, self._cache["waktu"], nama)

    def tampilkan(self, nama: str, mid: int | None = None, segarkan: bool = False) -> None:
        """Ganti pesan `mid` (atau kirim pesan baru) dengan tampilan `nama`. Bila Chrome harus dibuka,
        tampilkan "⏳ Membaca Monev…" dulu, lalu ganti dengan hasilnya."""
        if nama in DATA and (segarkan or not self.segar(DATA[nama])):
            self.tg.ketik(self.chat_id)
            muat = P.memuat(self.tx)
            if mid:
                self.ubah(mid, muat)
            else:
                mid = self.kirim(muat)
        p = self.tampilan(nama, segarkan)
        if mid:
            self.ubah(mid, p)
        else:
            self.kirim(p)

    # ------------------------------------------------------------ perintah dan tombol

    def perintah(self, teks: str) -> None:
        cmd, *arg = (teks.strip().split() or [""])
        cmd = cmd.split("@")[0].lower()
        if cmd == "/ping":
            self.kirim(P.ping(self.tx, self.mulai))
            return
        nama = {"/start": "bantuan", "/help": "bantuan", "/menu": "menu", "/status": "status",
                "/rekap": "bulan" if arg[:1] == ["bulan"] else "minggu", "/rekap_bulan": "bulan"}.get(cmd)
        if nama:
            self.tampilkan(nama)

    def tombol(self, cb: dict) -> None:
        msg = cb.get("message") or {}
        if str((msg.get("chat") or {}).get("id")) != self.chat_id:
            self.tg.jawab(cb["id"])
            return
        data, mid, sekarang = cb.get("data") or "", msg.get("message_id"), datetime.now(WIB)
        jenis, _, arg = data.partition(":")
        if jenis in ("v", "b", "s"):
            self.tg.jawab(cb["id"])     # tanda sedang bekerja ada di pesannya sendiri (⏳), bukan di toast
            self.tampilkan(arg, None if jenis == "b" else mid, segarkan=jenis == "s")
        elif jenis == "tunda":
            at = sekarang + timedelta(minutes=self.cfg.bot_tunda_menit)
            h = self.hari(sekarang)
            h["tunda"] = {"at": f"{at:%H:%M}", "urutan": arg or "pertama"}
            asal = next((x for x in h["ingat"] if x["id"] == mid), None)
            self.tg.jawab(cb["id"], self.tx.mentah("bot.ingat.tunda").replace("{jam}", f"{at:%H.%M}"))
            if asal:
                self.ubah(mid, P.ingat_ditunda(self.tx, asal["teks"], f"{at:%H:%M}"))
            tulis_state(self.state)
        elif jenis == "cek":
            self.tg.jawab(cb["id"], self.tx.mentah("bot.menu.membaca"))
            if self.coba_jalankan("pantau", sekarang) is False:
                asal = next((x for x in self.hari(sekarang)["ingat"] if x["id"] == mid), None)
                if asal:
                    self.ubah(mid, P.Pesan(f"{asal['teks']}\n<i>{self.tx('bot.ingat.cek_belum')}</i>",
                                           tombol=P.ingat(self.tx, "pertama", sekarang.date(), 1,
                                                          self.cfg.bot_tunda_menit).tombol))
        elif jenis == "coba":
            self.tg.jawab(cb["id"], self.tx.mentah("bot.menu.membaca"))
            self.coba_jalankan("pantau", sekarang)
        elif jenis == "cara":
            self.tg.jawab(cb["id"], self.tx.mentah("bot.gangguan.cara"), alert=True)
        else:
            self.tg.jawab(cb["id"])

    # ------------------------------------------------------------ jadwal dan loop

    def jadwal(self, sekarang: datetime) -> None:
        hari_ini = sekarang.date().isoformat()
        selesai = set(self.state.get("selesai", {}).get(hari_ini, []))
        for kunci, jenis in jadwal_jatuh_tempo(self.jadwal_list, sekarang, selesai):
            self.log(f"[{sekarang:%H:%M}] jadwal {kunci}")
            self.coba_jalankan(jenis, sekarang)
            selesai.add(kunci)
            self.state.setdefault("selesai", {})[hari_ini] = sorted(selesai)
            self.state["selesai"] = dict(sorted(self.state["selesai"].items())[-7:])   # 7 hari terakhir saja
            tulis_state(self.state)
        h = self.hari(sekarang)
        t = h.get("tunda")
        if t and f"{sekarang:%H:%M}" >= t["at"]:
            h.pop("tunda")
            self.log(f"[{sekarang:%H:%M}] pengingat yang ditunda")
            self.coba_jalankan("ingat:" + t["urutan"], sekarang)
            tulis_state(self.state)

    def jalan(self) -> None:
        try:
            self.tg.pasang_menu()
        except Exception as ex:  # noqa: BLE001 — menu hanya kenyamanan
            self.log(f"menu perintah gagal dipasang: {ex}")
        self.log(f"monev bot jalan · chat {self.chat_id[:3]}… · jadwal "
                 f"{', '.join(f'{j} {x}' for j, x in self.jadwal_list)} WIB")
        offset = self.state.get("offset")
        while True:
            try:
                for u in self.tg.updates(offset):
                    offset = u["update_id"] + 1
                    msg = u.get("message") or {}
                    if u.get("callback_query"):
                        self.tombol(u["callback_query"])
                    elif str((msg.get("chat") or {}).get("id")) == self.chat_id and msg.get("text"):
                        self.perintah(msg["text"])
                self.state["offset"] = offset
                tulis_state(self.state)
            except Exception as ex:  # noqa: BLE001 — jaringan putus dsb.: tunggu lalu coba lagi
                self.log(f"polling: {ex}")
                time.sleep(10)
            self.jadwal(datetime.now(WIB))
