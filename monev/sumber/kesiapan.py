"""Cek kesiapan bahan satu tanggal sebelum draft disusun. Hanya membaca; tidak pernah menarik atau mengubah repo."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

BATAS_DETIK = 8


def nilai(aktivitas: int, logtime: int | None = None, ada_catatan: bool = True) -> str:
    """`siap`, `tipis`, atau `kosong`. `logtime=None` berarti logtime tidak dipakai atau tidak diketahui."""
    if not ada_catatan:
        return "siap" if logtime else "kosong"
    if logtime is None:
        return "siap" if aktivitas else "kosong"
    if aktivitas and logtime:
        return "siap"
    return "tipis" if aktivitas or logtime else "kosong"


def _git(folder: Path, *perintah: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_SSH_COMMAND": "ssh -oBatchMode=yes"}
    return subprocess.run(["git", "-C", str(folder), *perintah], capture_output=True, text=True,
                          timeout=BATAS_DETIK, env=env)


def kondisi_repo(folder: Path) -> dict:
    """`tertinggal`: True bila remote punya commit yang belum ada di lokal, None bila tidak bisa dipastikan."""
    hasil = {"git": False, "belum_commit": 0, "tertinggal": None}
    try:
        status = _git(folder, "status", "--porcelain")
        if status.returncode != 0:
            return hasil
        hasil.update(git=True, belum_commit=len(status.stdout.splitlines()))
        remote = _git(folder, "ls-remote", "origin", "HEAD")
        sha = remote.stdout.split()[0] if remote.returncode == 0 and remote.stdout.split() else ""
        if sha:
            hasil["tertinggal"] = _git(folder, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0
    except (OSError, subprocess.TimeoutExpired):
        pass
    return hasil


def periksa(pekerjaan: list[dict], folder: Path | None, logtime: int | None = None) -> dict:
    aktivitas = sum(len(p["aktivitas"]) for p in pekerjaan)
    ada_catatan = bool(folder and folder.is_dir())
    repo = kondisi_repo(folder) if ada_catatan else {"git": False, "belum_commit": 0, "tertinggal": None}
    peringatan = []
    if repo["tertinggal"]:
        peringatan.append("repo work records tertinggal dari remote, catatan terbaru mungkin belum terbaca")
    if repo["belum_commit"]:
        peringatan.append(f"{repo['belum_commit']} file work records belum di-commit, isinya tetap terbaca di laptop ini")
    if logtime == 0:
        peringatan.append("logtime tanggal ini masih kosong")
    return {"status": nilai(aktivitas, logtime, ada_catatan), "aktivitas": aktivitas, "logtime": logtime,
            "repo": repo, "peringatan": peringatan}
