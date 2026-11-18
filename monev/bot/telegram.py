"""Klien Telegram Bot API (urllib, tanpa library tambahan) dan pembaca token dari env / <repo>/.env.

Token tidak pernah dicetak: pesan error yang memuat URL disensor jadi `***`.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

# Daftar perintah di tombol Menu Telegram (setMyCommands). Nama: huruf kecil + garis bawah.
# /rekap_bulan dan /ping tetap bisa diketik walau tidak ada di daftar.
MENU = [
    ("menu", "Semua pilihan"),
    ("status", "Status laporan hari ini"),
    ("rekap", "Rekap minggu ini"),
    ("help", "Bantuan"),
]


def muat_env(repo_root: Path | None = None) -> dict[str, str]:
    """TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID. os.environ menang; <repo>/.env (KEY=VALUE) sebagai cadangan."""
    from ..config import REPO_ROOT

    env: dict[str, str] = {}
    f = (repo_root or REPO_ROOT) / ".env"
    if f.is_file():
        for ln in f.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


class Telegram:
    def __init__(self, token: str):
        self._token = token

    def _call(self, method: str, params: dict, timeout: float = 30):
        url = f"https://api.telegram.org/bot{self._token}/{method}"
        data = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                desc = json.loads(e.read().decode("utf-8")).get("description", "")
            except Exception:  # noqa: BLE001
                desc = ""
            raise RuntimeError(f"Telegram {method}: HTTP {e.code} {desc}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise RuntimeError(f"Telegram {method}: {str(e).replace(self._token, '***')}") from None
        if not body.get("ok"):
            raise RuntimeError(f"Telegram {method}: {body.get('description', 'gagal')}")
        return body["result"]

    @staticmethod
    def _papan(p) -> dict:
        tombol = getattr(p, "tombol", None) or []
        return {"inline_keyboard": [[{"text": label, "callback_data": data} for label, data in baris] for baris in tombol]}

    def kirim(self, chat_id: str, p) -> int | None:
        """Kirim pesan.Pesan (atau str). Ada `html` → rich message; gagal → teks biasa. Mengembalikan message_id."""
        html = getattr(p, "html", None)
        markup = {"reply_markup": self._papan(p)} if getattr(p, "tombol", None) else {}
        if html:
            try:
                m = self._call("sendRichMessage", {"chat_id": chat_id, "rich_message": {"html": html}, **markup})
                return (m or {}).get("message_id")
            except RuntimeError:
                pass
        m = self._call("sendMessage", {"chat_id": chat_id, "text": str(getattr(p, "teks", p)), "parse_mode": "HTML",
                                       "disable_web_page_preview": True, **markup})
        return (m or {}).get("message_id")

    def ubah(self, chat_id: str, message_id: int, p) -> None:
        """Ganti isi pesan yang sudah terkirim (tombol ikut diganti; tanpa tombol = tombol dihapus).
        Ada `html` → rich (editMessageText + rich_message, Bot API 10.1+); gagal → teks biasa.
        Isi yang sama persis diabaikan (Telegram menolaknya dengan "message is not modified")."""
        dasar = {"chat_id": chat_id, "message_id": message_id, "reply_markup": self._papan(p)}
        coba = []
        if getattr(p, "html", None):
            coba.append({**dasar, "rich_message": {"html": p.html}})
        coba.append({**dasar, "text": str(getattr(p, "teks", p)), "parse_mode": "HTML", "disable_web_page_preview": True})
        for i, params in enumerate(coba):
            try:
                self._call("editMessageText", params)
                return
            except RuntimeError as e:
                if "not modified" in str(e):
                    return
                if i == len(coba) - 1:
                    raise

    def ketik(self, chat_id: str) -> None:
        """Tampilkan "mengetik…" di atas chat (hilang sendiri setelah ±5 detik atau saat pesan berikutnya masuk)."""
        try:
            self._call("sendChatAction", {"chat_id": chat_id, "action": "typing"}, timeout=10)
        except RuntimeError:
            pass

    def jawab(self, callback_id: str, teks: str | None = None, alert: bool = False) -> None:
        """Wajib untuk setiap tombol yang ditekan; tanpa ini Telegram menampilkan loading di tombol."""
        params = {"callback_query_id": callback_id, "show_alert": alert}
        if teks:
            params["text"] = teks[:200]
        self._call("answerCallbackQuery", params)

    def updates(self, offset: int | None, timeout: int = 50) -> list[dict]:
        params = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            params["offset"] = offset
        return self._call("getUpdates", params, timeout=timeout + 15)

    def saya(self) -> dict:
        return self._call("getMe", {})

    def pasang_menu(self) -> None:
        """Daftar perintah yang muncul saat user mengetik / atau menekan tombol Menu."""
        self._call("setMyCommands", {"commands": [{"command": c, "description": d} for c, d in MENU]})
