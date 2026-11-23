"""Chrome asli dengan profil khusus milik tool. Sesi login hidup di profil ini.

Token dan cookie tidak pernah dicetak, disimpan di luar profil, atau dikirim ke luar browser.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

from playwright.sync_api import BrowserContext, Page, sync_playwright

from ..config import API_HOST, LOGIN_HOST, TOKEN_KEY, Config

SESSION_OK = "ok"
SESSION_LOGIN = "login"        # dialihkan ke SSO: belum login / sesi mati
SESSION_TIMEOUT = "timeout"    # halaman tidak siap dalam batas waktu


def find_chrome() -> str | None:
    """Lokasi Google Chrome di Linux, macOS, atau Windows (yang dipakai Playwright channel="chrome")."""
    import os
    import shutil
    import sys

    for name in ("google-chrome", "google-chrome-stable", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    candidates: list[str] = []
    if sys.platform == "darwin":
        candidates = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                      os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    elif sys.platform.startswith("win"):
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base:
                candidates.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
    else:
        candidates = ["/opt/google/chrome/chrome", "/usr/bin/google-chrome"]
    return next((c for c in candidates if os.path.isfile(c)), None)


@dataclass
class Session:
    ctx: BrowserContext
    page: Page
    cfg: Config


@contextmanager
def open_browser(cfg: Config, headless: bool) -> Iterator[Session]:
    cfg.profile_dir.mkdir(parents=True, exist_ok=True)
    cfg.profile_dir.chmod(0o700)
    import os

    # Di container Chrome biasanya butuh "--no-sandbox --disable-dev-shm-usage" (diatur di Dockerfile, bukan default).
    extra = os.environ.get("MONEV_CHROME_ARGS", "").split()
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(cfg.profile_dir),
            channel=cfg.channel,
            headless=headless,
            no_viewport=not headless,
            args=extra,
        )
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            yield Session(ctx=ctx, page=page, cfg=cfg)
        finally:
            ctx.close()


def _has_token(page: Page) -> bool:
    try:
        return bool(page.evaluate("k => !!sessionStorage.getItem(k)", TOKEN_KEY))
    except Exception:  # halaman sedang berpindah
        return False


def wait_session(page: Page, timeout_s: float, stop_on_login: bool = True) -> str:
    """Tunggu sampai halaman Monev punya token, atau (bila stop_on_login) dialihkan ke SSO.

    Pengalihan ke halaman login terjadi lewat JavaScript, jadi URL awal belum bisa dipercaya.
    Saat menunggu user login, stop_on_login=False: halaman SSO memang diharapkan muncul.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if page.is_closed():
                return SESSION_TIMEOUT
            url = page.url
            if stop_on_login and LOGIN_HOST in url:
                return SESSION_LOGIN
            if "monev.maganghub" in url and _has_token(page):
                return SESSION_OK
            page.wait_for_timeout(500)
        except Exception:  # jendela/browser ditutup user
            return SESSION_TIMEOUT
    return SESSION_TIMEOUT


def open_dashboard(s: Session, timeout_s: float = 25) -> str:
    s.page.goto(s.cfg.web_base + "/dashboard", wait_until="domcontentloaded")
    return wait_session(s.page, timeout_s)


VERSI_JS = """() => { const s = document.querySelector('script[type=module][src*="/_nuxt/"]');
  return s ? s.getAttribute('src') : null; }"""


def versi_web(s: Session) -> str | None:
    """Nama file utama frontend Monev (mis. `/_nuxt/BOw8CLsC.js`). Berganti setiap situs di-deploy ulang (uji #57)."""
    try:
        return s.page.evaluate(VERSI_JS)
    except Exception:  # noqa: BLE001 — hanya penanda, tidak boleh menggagalkan pembacaan status
        return None


def refresh_cookie_expiry(s: Session) -> datetime | None:
    """Tanggal kedaluwarsa refresh token (hanya tanggalnya, nilai cookie tidak dibaca)."""
    for c in s.ctx.cookies(f"https://{API_HOST}"):
        if c.get("name") == "monev_refresh_token" and c.get("expires", -1) > 0:
            return datetime.fromtimestamp(c["expires"], tz=timezone.utc)
    return None


GEO_JS = """() => new Promise(resolve => {
  if (!('geolocation' in navigator)) return resolve({ok: false, error: 'tidak didukung'});
  navigator.geolocation.getCurrentPosition(
    p => resolve({ok: true, accuracy_m: Math.round(p.coords.accuracy)}),
    e => resolve({ok: false, code: e.code, error: e.message}),
    {enableHighAccuracy: true, timeout: 15000, maximumAge: 60000});
})"""


def test_location(s: Session) -> dict:
    """Minta lokasi asli dari Chrome. Koordinat tidak dikembalikan, hanya berhasil/gagal + akurasi."""
    s.ctx.grant_permissions(["geolocation"], origin=s.cfg.web_base)
    return s.page.evaluate(GEO_JS)
