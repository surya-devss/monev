"""Status tiap jalur sumber bahan (A–D) untuk `monev doctor` dan `/monev setup`. Tidak membuka Chrome/Monev."""

from __future__ import annotations

from .catatan import ringkas
from .git import status_github, status_gitlab


def cek_jalur(cfg) -> dict:
    """{kode: {"nama", "aktif", "ok", "detail", "langkah"}}. `ok` None = tidak bisa dicek CLI."""
    jalur = {"A": {"nama": "checklist / tanya-jawab", "aktif": True, "ok": True,
                   "detail": "selalu tersedia", "langkah": ""}}

    if cfg.git_penyedia:
        status = {p: (status_github() if p == "github" else status_gitlab(cfg.gitlab_host)) for p in cfg.git_penyedia}
        rusak = [f"{p}: {s['pesan']}" for p, s in status.items() if not s["ok"]]
        jalur["B"] = {"nama": "Git (GitHub/GitLab)", "aktif": True, "ok": not rusak,
                      "detail": ", ".join(f"{p} @{s['akun']}" for p, s in status.items() if s["ok"]) or "-",
                      "langkah": "; ".join(rusak)}
    else:
        jalur["B"] = {"nama": "Git (GitHub/GitLab)", "aktif": False, "ok": None, "detail": "tidak dipakai",
                      "langkah": "isi [sumber.git] penyedia = [\"github\"] / [\"gitlab\"] (atau /monev setup)"}

    if cfg.mcp_awalan_tool:
        jalur["C"] = {"nama": "MCP kantor", "aktif": True, "ok": None,
                      "detail": ", ".join(cfg.mcp_awalan_tool), "langkah": "dicek agent: tool berawalan itu ada di sesi?"}
    else:
        jalur["C"] = {"nama": "MCP kantor", "aktif": False, "ok": None, "detail": "tidak dipakai",
                      "langkah": "pasang MCP kantor di agent, lalu isi [sumber.mcp] awalan_tool (atau /monev setup)"}

    if cfg.workrecords_dir:
        r = ringkas(cfg.workrecords_dir, cfg.lewati_folder)
        jalur["D"] = {"nama": "work records", "aktif": True, "ok": r["ada"],
                      "detail": (f"{cfg.workrecords_dir} · {r['file']} file, {r['proyek']} proyek, "
                                 f"terakhir {r['tanggal_terakhir']}") if r["ada"] else str(cfg.workrecords_dir),
                      "langkah": "" if r["ada"] else "folder tidak ada / tidak berisi catatan sesuai kontrak → monev sumber cari"}
    else:
        jalur["D"] = {"nama": "work records", "aktif": False, "ok": None, "detail": "tidak dipakai",
                      "langkah": "monev sumber cari → isi [sumber.workrecords] dir (atau /monev setup)"}
    return jalur
