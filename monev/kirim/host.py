"""Native Messaging: `monev-native-host` dipanggil Chrome atas nama extension, plus pemasangan & diagnosa.

Alur lengkap: `monev kirim` menulis pekerjaan ke antrian (antrian.py) → extension (tiap 30 dtk) memanggil host ini →
host menyerahkan pekerjaan → extension mengisi form di Chrome user → host menulis hasil → `monev kirim` membacanya.
"""

from __future__ import annotations

import json
import os
import struct
import sys
from pathlib import Path

from .antrian import ambil_job, tulis_hasil

HOST_NAME = "monev.maganghub.kirim"
EXTENSION_ID = "fdhbflndlipoblicgdjjkmfilocnngha"   # dari "key" di extension/manifest.json


# ---------------------------------------------------------------- native messaging

def baca_pesan(stream) -> dict | None:
    raw = stream.read(4)
    if len(raw) < 4:
        return None
    (n,) = struct.unpack("<I", raw)
    return json.loads(stream.read(n).decode("utf-8"))


def tulis_pesan(stream, obj: dict) -> None:
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    stream.write(struct.pack("<I", len(data)))
    stream.write(data)
    stream.flush()


def host_main() -> int:
    """Dipanggil Chrome (bukan user). stdout hanya untuk protokol Native Messaging."""
    inp, out = sys.stdin.buffer, sys.stdout.buffer
    try:
        msg = baca_pesan(inp) or {}
        if msg.get("type") == "ambil":
            tulis_pesan(out, {"job": ambil_job()})
        elif msg.get("type") == "nilai":   # nilai perusahaan dari config.toml untuk notifikasi fokus extension
            from ..config import load_config

            tulis_pesan(out, {"ok": True, "nilai": load_config().nilai_dict()})
        elif msg.get("type") == "pesan":   # teks notifikasi (bawaan + [pesan] di config) dan nilai perusahaan
            from ..config import load_config
            from ..teks import muat

            cfg = load_config()
            teks, asing = muat(cfg.pesan)
            tulis_pesan(out, {"ok": True, "pesan": teks, "nilai": cfg.nilai_dict(), "asing": asing})
        elif msg.get("type") == "hasil" and msg.get("id"):
            tulis_hasil(str(msg["id"]), msg.get("hasil") or {})
            tulis_pesan(out, {"ok": True})
        else:
            tulis_pesan(out, {"ok": False, "pesan": "pesan tidak dikenal"})
    except Exception as e:  # noqa: BLE001 — jawab ke extension, jangan crash diam-diam
        tulis_pesan(out, {"ok": False, "pesan": f"host error: {e}"})
    return 0


# ---------------------------------------------------------------- pemasangan

# Windows tidak memakai folder NativeMessagingHosts: Chrome membaca registry HKCU\<kunci>\<HOST_NAME>,
# yang nilai default-nya menunjuk ke file manifest (ditaruh di %LOCALAPPDATA%\monev).
KUNCI_REGISTRY_WIN = (r"Software\Google\Chrome\NativeMessagingHosts", r"Software\Chromium\NativeMessagingHosts")


def _windows() -> bool:
    return sys.platform.startswith("win")


def _localappdata() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")


def lokasi_manifest_host() -> list[Path]:
    home = Path.home()
    if sys.platform == "darwin":
        base = home / "Library/Application Support"
        return [base / "Google/Chrome/NativeMessagingHosts", base / "Chromium/NativeMessagingHosts"]
    if sys.platform.startswith("linux"):
        cfg = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        return [cfg / "google-chrome/NativeMessagingHosts", cfg / "chromium/NativeMessagingHosts"]
    if _windows():
        return [_localappdata() / "monev/NativeMessagingHosts"]
    return []


def cari_host_exe() -> str | None:
    import shutil

    found = shutil.which("monev-native-host")
    if found:
        return str(Path(found).absolute())
    for nama in ("monev-native-host", "monev-native-host.exe"):
        cand = Path(sys.executable).parent / nama
        if cand.exists():
            return str(cand)
    return None


def _registry_daftar(manifest: Path) -> None:
    import winreg  # noqa: PLC0415 — hanya ada di Windows

    for kunci in KUNCI_REGISTRY_WIN:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, rf"{kunci}\{HOST_NAME}", 0, winreg.KEY_WRITE) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, str(manifest))


def registry_terdaftar() -> bool:
    """Windows: True bila salah satu kunci registry menunjuk ke file manifest yang ada."""
    import winreg  # noqa: PLC0415

    for kunci in KUNCI_REGISTRY_WIN:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"{kunci}\{HOST_NAME}") as k:
                nilai, _ = winreg.QueryValueEx(k, "")
        except OSError:
            continue
        if nilai and Path(nilai).exists():
            return True
    return False


def manifest_host(exe: str) -> dict:
    return {
        "name": HOST_NAME,
        "description": "Jembatan CLI monev ke extension monev kirim",
        "path": exe,
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{EXTENSION_ID}/"],
    }


def pasang() -> list[Path]:
    exe = cari_host_exe()
    if not exe:
        raise RuntimeError("perintah monev-native-host tidak ditemukan; pasang ulang: "
                           "uv tool install -e <repo> --reinstall")
    tujuan = lokasi_manifest_host()
    if not tujuan:
        raise RuntimeError(f"OS ini belum didukung ({sys.platform})")
    if _windows():
        d = tujuan[0]
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{HOST_NAME}.json"
        p.write_text(json.dumps(manifest_host(exe), indent=2), encoding="utf-8")
        _registry_daftar(p)
        return [p]
    ditulis = []
    for d in tujuan:
        if d.parent.is_dir():   # hanya bila Chrome/Chromium pernah dipakai di mesin ini
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"{HOST_NAME}.json"
            p.write_text(json.dumps(manifest_host(exe), indent=2), encoding="utf-8")
            ditulis.append(p)
    if not ditulis:
        raise RuntimeError("folder profil Chrome tidak ditemukan; buka Chrome sekali dulu")
    return ditulis


def folder_profil_chrome() -> list[Path]:
    home = Path.home()
    if sys.platform == "darwin":
        bases = [home / "Library/Application Support/Google/Chrome", home / "Library/Application Support/Chromium"]
    elif sys.platform.startswith("linux"):
        cfg = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        bases = [cfg / "google-chrome", cfg / "chromium"]
    elif _windows():
        bases = [_localappdata() / "Google/Chrome/User Data", _localappdata() / "Chromium/User Data"]
    else:
        return []
    return [p for b in bases if b.is_dir() for p in b.iterdir() if (p / "Preferences").exists()]


def extension_terpasang() -> bool | None:
    """Cek `extensions.settings[ID]` di Preferences tiap profil Chrome. None = tidak bisa dicek.

    Setelah extension di-Remove, Chrome menyisakan entri kosong `"<ID>": {}` (uji #33), jadi yang dihitung
    terpasang hanya entri yang punya `path` (folder Load unpacked).
    """
    profil = folder_profil_chrome()
    if not profil:
        return None
    for p in profil:
        for f in ("Secure Preferences", "Preferences"):
            try:
                data = json.loads((p / f).read_text(encoding="utf-8", errors="ignore"))
            except (OSError, json.JSONDecodeError):
                continue
            entri = ((data.get("extensions") or {}).get("settings") or {}).get(EXTENSION_ID) or {}
            if entri.get("path"):
                return True
    return False


def chrome_berjalan() -> bool | None:
    import subprocess

    if _windows():
        try:
            r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/NH"],
                               capture_output=True, text=True)
        except (FileNotFoundError, OSError):
            return None
        return "chrome.exe" in r.stdout.lower() if r.returncode == 0 else None
    nama = "Google Chrome" if sys.platform == "darwin" else "chrome"
    try:
        return subprocess.run(["pgrep", "-x", nama], capture_output=True).returncode == 0
    except FileNotFoundError:
        return None


def diagnosa() -> list[str]:
    """Masalah yang pasti membuat extension tidak akan mengambil pekerjaan. Kosong = siap."""
    masalah = []
    host = [d / f"{HOST_NAME}.json" for d in lokasi_manifest_host()]
    if _windows():
        belum = not registry_terdaftar()
    else:
        belum = bool(host) and not any(p.exists() for p in host)
    if belum:
        masalah.append("Jembatan Native Messaging belum terdaftar → jalankan: monev extension install")
    if extension_terpasang() is False:
        masalah.append("Extension 'monev kirim' tidak ditemukan di profil Chrome mana pun → chrome://extensions → "
                       f"Developer mode → Load unpacked → {extension_dir()}")
    if chrome_berjalan() is False:
        masalah.append("Chrome tidak sedang berjalan → buka Chrome kamu (yang sudah login Monev)")
    return masalah


def extension_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "extension"
