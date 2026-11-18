"""Jalur Git (read-only): commit, PR/MR, dan review milik user pada tanggal D, lewat `gh` / `glab` yang sudah login.

monev tidak menyimpan atau membaca token: autentikasi dipegang `gh`/`glab` (login mereka sendiri, atau env yang
mereka baca: `GH_TOKEN`, `GITLAB_TOKEN`). Keluaran sudah dibersihkan: tanpa nama repo, hash, URL, nomor PR/MR,
email, dan kata di `jangan_disebut` (pola sama dengan `monev validate`).

GitHub (diverifikasi 17 Nov 2026): events API `PushEvent` hanya memuat `before`/`head` dan `PullRequestEvent`
hanya nomor PR, jadi commit diambil per push dengan `repos/{repo}/commits?sha=&author=&since=&until=` (semua branch)
dan judul PR/issue diambil per nomor. Events API hanya mencakup ±90 hari / 300 event terakhir.
GitLab: `GET /events` milik user (push_data hanya judul commit terakhir per push). Belum diuji dengan akun nyata.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import date, datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7))


class GagalPerintah(RuntimeError):
    pass


def _jalankan(args: list[str], timeout: int = 30) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise GagalPerintah(f"{args[0]}: {e}") from e
    if r.returncode != 0:
        pesan = (r.stderr or r.stdout).strip().splitlines()
        raise GagalPerintah(pesan[0] if pesan else f"{args[0]} keluar {r.returncode}")
    return r.stdout


def _json(args: list[str]):
    return json.loads(_jalankan(args) or "null")


def tgl_wib(iso: str) -> date:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(WIB).date()


def jam_wib(iso: str) -> str:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(WIB).strftime("%H:%M")


def bersihkan(teks: str, terlarang: list[str], jangan_disebut: list[str]) -> str:
    """Baris pertama saja, tanpa pola terlarang (aturan.toml) dan kata `jangan_disebut`."""
    baris = (teks or "").strip().splitlines()
    t = baris[0] if baris else ""
    # Nomor PR/MR/issue berapa pun digitnya (aturan.toml baru menolak #NN ke atas), lalu pola terlarang lain.
    for pola in [r"(?<![\w&])#\d+\b", r"(?<![\w!])!\d+\b", *terlarang]:
        t = re.sub(pola, "", t, flags=re.M)
    for kata in jangan_disebut:
        if kata:
            t = re.sub(re.escape(kata), "", t, flags=re.I)
    t = re.sub(r"\(\s*\)|\[\s*\]", "", t)
    return re.sub(r"\s{2,}", " ", t).strip(" -:·")


# ---------------------------------------------------------------- status

def status_github() -> dict:
    if not shutil.which("gh"):
        return {"ok": False, "pesan": "gh tidak terpasang → pasang dari https://cli.github.com lalu `gh auth login`"}
    try:
        login = _jalankan(["gh", "api", "user", "--jq", ".login"]).strip()
    except GagalPerintah as e:
        return {"ok": False, "pesan": f"gh belum login ({e}) → `gh auth login`, atau isi GH_TOKEN"}
    return {"ok": True, "akun": login}


def status_gitlab(host: str) -> dict:
    if not shutil.which("glab"):
        return {"ok": False, "pesan": "glab tidak terpasang → pasang dari https://gitlab.com/gitlab-org/cli lalu "
                                      f"`glab auth login --hostname {host}`"}
    try:
        akun = _json(["glab", "api", "--hostname", host, "user"]) or {}
    except (GagalPerintah, json.JSONDecodeError) as e:
        return {"ok": False, "pesan": f"glab belum login ke {host} ({e}) → `glab auth login --hostname {host}`, "
                                      "atau isi GITLAB_TOKEN + GITLAB_HOST"}
    return {"ok": True, "akun": akun.get("username", "")}


# ---------------------------------------------------------------- GitHub

def _jendela_utc(d: date) -> tuple[str, str]:
    awal = datetime(d.year, d.month, d.day, tzinfo=WIB)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (awal.astimezone(timezone.utc).strftime(fmt),
            (awal + timedelta(days=1)).astimezone(timezone.utc).strftime(fmt))


def github(d: date, login: str) -> list[dict]:
    events = []
    for halaman in (1, 2, 3):
        isi = _json(["gh", "api", f"users/{login}/events?per_page=100&page={halaman}"]) or []
        events += isi
        if not isi or min(tgl_wib(e["created_at"]) for e in isi) < d:
            break
    sejak, sampai = _jendela_utc(d)
    aktivitas, sha_dilihat, judul_cache = [], set(), {}

    def judul(repo: str, jenis: str, nomor) -> str:
        kunci = (repo, jenis, nomor)
        if kunci not in judul_cache:
            try:
                judul_cache[kunci] = (_json(["gh", "api", f"repos/{repo}/{jenis}/{nomor}"]) or {}).get("title", "")
            except (GagalPerintah, json.JSONDecodeError):
                judul_cache[kunci] = ""
        return judul_cache[kunci]

    for ev in events:
        if tgl_wib(ev["created_at"]) != d:
            continue
        repo, p, jenis_ev = ev.get("repo", {}).get("name", ""), ev.get("payload") or {}, ev.get("type")
        if jenis_ev == "PushEvent":
            cabang = (p.get("ref") or "").removeprefix("refs/heads/")
            for sha in (p.get("head"), cabang):
                if not sha:
                    continue
                try:
                    commits = _json(["gh", "api", f"repos/{repo}/commits?sha={sha}&author={login}"
                                                   f"&since={sejak}&until={sampai}&per_page=100"]) or []
                    break
                except (GagalPerintah, json.JSONDecodeError):
                    commits = []
            for c in commits:
                if c["sha"] in sha_dilihat or len(c.get("parents", [])) > 1:
                    continue
                sha_dilihat.add(c["sha"])
                aktivitas.append({"penyedia": "github", "jenis": "commit", "aksi": "commit",
                                  "waktu_iso": c["commit"]["author"]["date"], "judul": c["commit"]["message"]})
        elif jenis_ev in ("PullRequestEvent", "PullRequestReviewEvent"):
            nomor = (p.get("pull_request") or {}).get("number") or p.get("number")
            aksi = p.get("action", "")
            if jenis_ev == "PullRequestEvent" and aksi not in ("opened", "closed", "merged", "reopened"):
                continue
            aktivitas.append({"penyedia": "github", "jenis": "review" if jenis_ev.endswith("ReviewEvent") else "pr",
                              "aksi": aksi, "waktu_iso": ev["created_at"], "judul": judul(repo, "pulls", nomor)})
        elif jenis_ev == "IssuesEvent" and p.get("action") in ("opened", "closed"):
            nomor = (p.get("issue") or {}).get("number")
            aktivitas.append({"penyedia": "github", "jenis": "issue", "aksi": p["action"],
                              "waktu_iso": ev["created_at"], "judul": judul(repo, "issues", nomor)})
    return aktivitas


# ---------------------------------------------------------------- GitLab

def gitlab(d: date, host: str) -> list[dict]:
    kemarin, besok = (d - timedelta(days=1)).isoformat(), (d + timedelta(days=1)).isoformat()
    events = _json(["glab", "api", "--hostname", host, f"events?after={kemarin}&before={besok}&per_page=100"]) or []
    aktivitas = []
    for ev in events:
        if tgl_wib(ev["created_at"]) != d:
            continue
        aksi, target = ev.get("action_name", ""), ev.get("target_type") or ""
        if aksi.startswith("pushed"):
            push = ev.get("push_data") or {}
            n = push.get("commit_count") or 0
            if not n or not push.get("commit_title"):
                continue
            aktivitas.append({"penyedia": "gitlab", "jenis": "commit", "aksi": "push", "jumlah": n,
                              "waktu_iso": ev["created_at"], "judul": push["commit_title"]})
        elif target == "MergeRequest":
            aktivitas.append({"penyedia": "gitlab", "jenis": "mr", "aksi": aksi,
                              "waktu_iso": ev["created_at"], "judul": ev.get("target_title", "")})
        elif target in ("Note", "DiffNote", "DiscussionNote") and (ev.get("note") or {}).get("noteable_type") == "MergeRequest":
            aktivitas.append({"penyedia": "gitlab", "jenis": "review", "aksi": "komentar",
                              "waktu_iso": ev["created_at"], "judul": ev.get("target_title", "")})
        elif target == "Issue" and aksi in ("opened", "closed"):
            aktivitas.append({"penyedia": "gitlab", "jenis": "issue", "aksi": aksi,
                              "waktu_iso": ev["created_at"], "judul": ev.get("target_title", "")})
    return aktivitas


# ---------------------------------------------------------------- gabungan

def ambil_bukti(cfg, d: date, terlarang: list[str]) -> dict:
    hasil = {"tanggal": d.isoformat(), "penyedia": {}, "aktivitas": []}
    mentah = []
    for penyedia in cfg.git_penyedia:
        st = status_github() if penyedia == "github" else status_gitlab(cfg.gitlab_host)
        if not st["ok"]:
            hasil["penyedia"][penyedia] = {"ok": False, "pesan": st["pesan"]}
            continue
        try:
            baru = github(d, st["akun"]) if penyedia == "github" else gitlab(d, cfg.gitlab_host)
        except (GagalPerintah, json.JSONDecodeError, KeyError) as e:
            hasil["penyedia"][penyedia] = {"ok": False, "pesan": f"gagal membaca aktivitas: {e}"}
            continue
        hasil["penyedia"][penyedia] = {"ok": True, "jumlah": len(baru)}
        mentah += baru
    for a in sorted(mentah, key=lambda a: a["waktu_iso"]):
        j = bersihkan(a["judul"], terlarang, cfg.jangan_disebut)
        if not j:
            continue
        item = {"waktu": jam_wib(a.pop("waktu_iso")), **{k: v for k, v in a.items() if k != "judul"}, "judul": j}
        hasil["aktivitas"].append(item)
    return hasil
