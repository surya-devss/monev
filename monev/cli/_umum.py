"""Bagian bersama perintah CLI: kode keluar, tanya-jawab terminal, config otomatis, dan sesi Chrome A."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from ..config import load_state, save_state

EXIT_OK, EXIT_FAIL, EXIT_NEED_LOGIN = 0, 1, 2


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        ans = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        ans = ""
    return ans or default


def _yes(prompt: str) -> bool:
    return _ask(prompt + " (y/N)").lower() in {"y", "ya", "yes"}


def _today() -> str:
    from datetime import date

    return date.today().isoformat()  # zona waktu sistem (WIB di mesin user)


def _config_auto():
    from ..config import ensure_config

    cfg, created = ensure_config()
    if created:
        wr = cfg.workrecords_dir or "tidak ditemukan → mode checklist"
        print(f"ⓘ Config dibuat otomatis: {cfg.path} (work records: {wr})", file=sys.stderr)
    return cfg


def _autofill(cfg, s) -> None:
    from ..config import autofill_profile
    from ..portal.api import get

    try:
        filled = autofill_profile(cfg, get(s, "/users/me"))
    except Exception:  # noqa: BLE001 — pelengkap, tidak boleh menggagalkan perintah
        return
    if filled:
        print("ⓘ Config dilengkapi otomatis dari profil Monev: " + ", ".join(filled), file=sys.stderr)


def _login_flow(cfg, timeout: int, ask_location: bool = False) -> bool:
    """Buka Chrome monev (berjendela), tunggu user login, simpan sesi. True bila berhasil.

    Lokasi TIDAK diurus di sini (keputusan opsi A, 2026-11-16): Chrome yang dijalankan tool tidak
    mendapat lokasi, jadi langkah kirim dilakukan di Chrome user. `ask_location` hanya untuk uji.
    """
    from ..portal.browser import SESSION_OK, open_browser, open_dashboard, test_location, wait_session

    state = load_state()
    print("Membuka Chrome milik monev (profil terpisah dari Chrome kamu)...")
    with open_browser(cfg, headless=False) as s:
        if open_dashboard(s) != SESSION_OK:
            print("\n→ Login di JENDELA CHROME YANG BARU TERBUKA (bukan Chrome kamu yang biasa).")
            print(f"  Menunggu sampai dashboard Monev terbuka (maks {timeout // 60} menit)...")
            if wait_session(s.page, timeout, stop_on_login=False) != SESSION_OK:
                print("✗ Login tidak selesai (batas waktu habis atau jendela ditutup).")
                return False
        # Token di tab saja belum cukup: tanpa cookie refresh token, sesi hilang saat Chrome ditutup (uji #31).
        from ..portal.browser import refresh_cookie_expiry

        exp = None
        for _ in range(20):
            exp = refresh_cookie_expiry(s)
            if exp:
                break
            s.page.wait_for_timeout(500)
        if not exp:
            nama = sorted({c["name"] for c in s.ctx.cookies() if "kemnaker" in c.get("domain", "")})
            print("✗ Dashboard terbuka, tapi sesi jangka panjang (cookie monev_refresh_token) TIDAK tersimpan,")
            print("  jadi sesi akan hilang begitu jendela ditutup. Cookie yang ada: " + ", ".join(nama))
            print("  Coba login lagi; bila ada pilihan 'Ingat saya' di halaman login, centang.")
            return False
        # Chrome menulis cookie ke disk berkala (±30 dtk). Menutup lebih cepat = refresh token hilang dari profil
        # walau sudah terbaca di memori (uji #31, #45). Tunggu, lalu buktikan dengan membuka profil lagi.
        print("  Login diterima. Menyimpan sesi ke profil (±35 dtk, jangan tutup jendela)...", flush=True)
        s.page.wait_for_timeout(35_000)
        state["login_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        if ask_location:
            print("\n[uji] Tes lokasi di Chrome monev.")
            state["lokasi_diizinkan"] = _yes("Izinkan tes lokasi ASLI perangkat ini untuk situs Monev?")
        if ask_location and state.get("lokasi_diizinkan"):
            print("Tes lokasi (koordinat tidak ditampilkan)...")
            geo = test_location(s)
            state["lokasi_tes"] = {**geo, "at": state["login_at"]}
            print("  ✓ lokasi OK, akurasi ±%s m" % geo.get("accuracy_m") if geo.get("ok")
                  else f"  ✗ lokasi gagal: {geo.get('error')}")
    tersimpan = _sesi_tersimpan(cfg)
    if not tersimpan:
        print("✗ Login berhasil, tapi sesi TIDAK tersimpan di profil monev (cookie monev_refresh_token tidak ada")
        print("  setelah Chrome ditutup). Jalankan `monev login` lagi; bila berulang, buka issue di repo.")
        return False
    print(f"✓ Login OK, sesi tersimpan di profil monev (berlaku s.d. {tersimpan.astimezone().date()}).")
    save_state(state)
    return True


def _sesi_tersimpan(cfg):
    """Tanggal habis refresh token yang benar-benar ada di profil (dibuka ulang tanpa layar), atau None."""
    from ..portal.browser import open_browser, refresh_cookie_expiry

    with open_browser(cfg, headless=True) as s:
        return refresh_cookie_expiry(s)


def _session_or_login(cfg, args):
    """Buka sesi tanpa layar; bila belum login dan dijalankan interaktif, buka Chrome untuk login dulu.

    Mengembalikan context manager Session yang siap dipakai, atau None (perlu login).
    """
    from ..portal.browser import SESSION_OK, open_browser, open_dashboard

    for attempt in (1, 2):
        cm = open_browser(cfg, headless=not args.headful)
        s = cm.__enter__()
        if open_dashboard(s) == SESSION_OK:
            return cm, s
        cm.__exit__(None, None, None)
        interactive = sys.stdin.isatty() and not getattr(args, "no_login", False)
        if attempt == 2 or not interactive:
            return None, None
        print("Sesi Monev belum ada / sudah mati.")
        if not _login_flow(cfg, timeout=600, ask_location=False):
            return None, None
    return None, None
