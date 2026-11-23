"""Timer systemd milik user untuk `monev jadwal jalan`. `Persistent=true` menyusul jadwal saat laptop mati atau tidur."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

NAMA = "monev-draft"
BATAS_DETIK = 1200


def folder_unit() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "systemd" / "user"


def _kutip(teks: str) -> str:
    return '"' + teks.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def isi_service(monev: str, folder_path: list[str]) -> str:
    urut = list(dict.fromkeys([*folder_path, "/usr/local/bin", "/usr/bin", "/bin"]))
    return f"""[Unit]
Description=Monev: susun draft laporan harian

[Service]
Type=oneshot
Environment={_kutip("PATH=" + ":".join(urut))}
ExecStart={_kutip(monev)} jadwal jalan
TimeoutStartSec={BATAS_DETIK}
"""


def isi_timer(jam: list[str]) -> str:
    kalender = "\n".join(f"OnCalendar=*-*-* {j}:00 Asia/Jakarta" for j in jam)
    return f"""[Unit]
Description=Monev: jadwal draft laporan harian

[Timer]
{kalender}
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
"""


def _systemctl(*perintah: str, run=subprocess.run) -> subprocess.CompletedProcess:
    return run(["systemctl", "--user", *perintah], capture_output=True, text=True)


def pasang(monev: str, folder_path: list[str], jam: list[str], run=subprocess.run) -> None:
    folder = folder_unit()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{NAMA}.service").write_text(isi_service(monev, folder_path), encoding="utf-8")
    (folder / f"{NAMA}.timer").write_text(isi_timer(jam), encoding="utf-8")
    for perintah in (("daemon-reload",), ("enable", "--now", f"{NAMA}.timer")):
        hasil = _systemctl(*perintah, run=run)
        if hasil.returncode != 0:
            raise RuntimeError(hasil.stderr.strip() or f"systemctl {perintah[0]} gagal")


def lepas(run=subprocess.run) -> None:
    _systemctl("disable", "--now", f"{NAMA}.timer", run=run)
    for akhiran in ("service", "timer"):
        (folder_unit() / f"{NAMA}.{akhiran}").unlink(missing_ok=True)
    _systemctl("daemon-reload", run=run)


def keadaan(run=subprocess.run) -> dict:
    timer = f"{NAMA}.timer"
    berikut = _systemctl("show", timer, "--property=NextElapseUSecRealtime", "--value", run=run).stdout.strip()
    return {"terpasang": (folder_unit() / timer).exists(),
            "aktif": _systemctl("is-active", timer, run=run).stdout.strip() == "active",
            "berikutnya": berikut}
