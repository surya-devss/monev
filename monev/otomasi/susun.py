"""Keputusan dan batas izin proses draft terjadwal. Proses ini hanya menyiapkan draft dan tidak bisa mengirim laporan."""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from pathlib import Path

BATAS_DETIK = 900
MODEL = "sonnet"
AWALAN_TULIS = ("create_", "update_", "delete_", "comment_", "start_", "stop_", "record_", "set_", "assign_")

# Jenis kabar Telegram. Teksnya di `monev/teks/bawaan.toml` bagian `[bot.draft.*]`, tanpa isi laporan.
KABAR = ("siap", "kosong", "cek", "sesi", "format", "sesi_hampir")


def putuskan(status: dict, ada_draft: bool, bahan: str) -> str:
    if not status.get("magang_aktif"):
        return "nonaktif"
    if status.get("libur_nasional") or status.get("libur_posisi"):
        return "libur"
    if status.get("sudah_isi"):
        return "sudah_isi"
    if ada_draft:
        return "ada_draft"
    return "tunggu_bahan" if bahan == "kosong" else "susun"


def alat_baca(nama: list[str]) -> list[str]:
    """Tool MCP yang boleh dipakai: harus ditulis lengkap di config dan bukan tool penulis."""
    return [n for n in nama if n.startswith("mcp__") and not n.rsplit("__", 1)[-1].startswith(AWALAN_TULIS)]


def perintah_claude(repo: Path, config: Path, kerja: Path, alat_mcp: list[str]) -> list[str]:
    """`dontAsk` menolak semua yang tidak tertulis di sini, termasuk `monev kirim` dan tool MCP penulis."""
    # Aturan izin Claude Code memakai garis miring maju, juga di Windows.
    repo, config, kerja = repo.as_posix(), config.as_posix(), kerja.as_posix()
    izin = ["Skill", "ToolSearch",
            f"Read(/{repo}/plugin/**)", f"Read(/{repo}/docs/teknis/kontrak-sumber.md)", f"Read(/{config})",
            "Read(~/.claude/plugins/**)", f"Read(/{kerja}/**)", f"Edit(/{kerja}/**)",
            "Bash(monev --version)", "Bash(monev config --json)", "Bash(monev sumber baca:*)",
            "Bash(monev sumber siap:*)", "Bash(monev bukti:*)", "Bash(monev validate:*)", *alat_baca(alat_mcp)]
    return ["claude", "-p", "--model", MODEL, "--no-session-persistence", "--permission-mode", "dontAsk",
            "--tools", "Read,Write,Edit,Bash,Skill,ToolSearch", "--allowedTools", *izin,
            "--disallowedTools", "Bash(monev kirim:*)"]


def prompt(tanggal: str, file: Path) -> str:
    return (f"Gunakan skill monev:monev dengan argumen: otomatis {tanggal} {file}\n\n"
            "Ini proses terjadwal. Tidak ada orang yang bisa menjawab, jadi jangan bertanya dan jangan mengirim apa pun.")


@contextmanager
def kunci(path: Path):
    """Menghasilkan True bila tidak ada proses lain yang sedang berjalan."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        try:
            if sys.platform.startswith("win"):
                import msvcrt  # noqa: PLC0415

                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl  # noqa: PLC0415

                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:   # BlockingIOError (Linux/macOS) atau PermissionError (Windows): proses lain memegang kunci
            yield False
            return
        yield True


def sudah_dikabari(path: Path, tanggal: str, jenis: str) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("tanggal") == tanggal and jenis in data.get("kabar", [])


def catat_kabar(path: Path, tanggal: str, jenis: str) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    kabar = data.get("kabar", []) if data.get("tanggal") == tanggal else []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tanggal": tanggal, "kabar": [*kabar, jenis]}, ensure_ascii=False), encoding="utf-8")
