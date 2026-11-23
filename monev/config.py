"""Konfigurasi per user. Tidak pernah memuat password, token, atau cookie."""

from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

WEB_BASE = "https://monev.maganghub.kemnaker.go.id"
API_BASE = "https://monev-api.maganghub.kemnaker.go.id/api/v1"
LOGIN_HOST = "account.kemnaker.go.id"
API_HOST = "monev-api.maganghub.kemnaker.go.id"
TOKEN_KEY = "monev_access_token"  # nama key sessionStorage; nilainya tidak pernah dicetak


def config_dir() -> Path:
    return Path(os.environ.get("MONEV_CONFIG_DIR", "~/.config/monev")).expanduser()


def data_dir() -> Path:
    return Path(os.environ.get("MONEV_DATA_DIR", "~/.local/share/monev")).expanduser()


REPO_ROOT = Path(__file__).resolve().parent.parent


def _is_checkout() -> bool:
    """True bila monev dipasang dari clone repo (uv tool install -e / pip install -e)."""
    return (REPO_ROOT / "pyproject.toml").is_file() and (REPO_ROOT / ".claude-plugin").is_dir()


def config_path() -> Path:
    """Urutan: env MONEV_CONFIG → <repo>/config.toml (gitignored) → ~/.config/monev/config.toml."""
    if os.environ.get("MONEV_CONFIG"):
        return Path(os.environ["MONEV_CONFIG"]).expanduser()
    if _is_checkout():
        repo_cfg = REPO_ROOT / "config.toml"
        legacy = config_dir() / "config.toml"
        if not repo_cfg.exists() and legacy.exists():
            legacy.replace(repo_cfg)  # pindahkan config lama ke repo
        return repo_cfg
    return config_dir() / "config.toml"


@dataclass
class Config:
    exists: bool
    path: Path
    web_base: str = WEB_BASE
    api_base: str = API_BASE
    profile_dir: Path = field(default_factory=lambda: data_dir() / "chrome-profile")
    channel: str = "chrome"
    posisi: str = ""
    perusahaan: str = ""
    tim: str = ""
    rutinitas: list[str] = field(default_factory=list)
    jangan_disebut: list[str] = field(default_factory=list)
    lewati_proyek: list[str] = field(default_factory=list)   # [laporan]: proyek yang tidak masuk laporan
    nama_boleh: list[str] = field(default_factory=list)      # [laporan]: pengecualian saringan nama
    jam_selesai: str = "17:00"                               # [laporan]: kerja sesudah jam ini = di luar jam
    mode: str = "auto"
    workrecords_dir: Path | None = None
    lewati_folder: list[str] = field(default_factory=lambda: ["_knowledge", "_plans"])
    mcp_awalan_tool: list[str] = field(default_factory=list)
    nilai_semboyan: str = ""
    nilai_poin: list[tuple[str, str]] = field(default_factory=list)
    git_penyedia: list[str] = field(default_factory=list)
    gitlab_host: str = "gitlab.com"
    pesan: dict = field(default_factory=dict)   # [pesan]: timpa teks notifikasi bawaan (monev/teks/bawaan.toml)
    panggilan: str = ""                          # [profil] panggilan untuk sapaan; kosong = nama depan dari Monev
    bot_kartu: str = "08:00"
    bot_pengingat: list[str] = field(default_factory=lambda: ["15:00", "16:30", "20:00"])
    bot_rekap: str = "16:00"
    bot_pantau: list[str] = field(default_factory=lambda: ["12:00", "18:00", "22:00"])
    bot_tunda_menit: int = 60
    jadwal_jam: list[str] = field(default_factory=lambda: ["16:00", "17:00", "18:00", "19:00"])
    jadwal_alat_mcp: list[str] = field(default_factory=list)   # tool MCP baca untuk proses terjadwal

    @property
    def draft_dir(self) -> Path:
        return self.profile_dir.parent / "draft"

    def nilai_dict(self) -> dict | None:
        """Nilai perusahaan untuk pesan fokus (bot) dan extension; None bila `[profil.nilai] poin` kosong."""
        if not self.nilai_poin:
            return None
        return {"semboyan": self.nilai_semboyan, "poin": [list(p) for p in self.nilai_poin]}


def _poin_nilai(baris: list) -> list[tuple[str, str]]:
    """"Nama nilai: cara menerapkannya" → (nama, penerapan). Tanpa titik dua → penerapan kosong."""
    out = []
    for b in baris:
        nama, _, terap = str(b).partition(":")
        if nama.strip():
            out.append((nama.strip(), terap.strip()))
    return out


def load_config() -> Config:
    path = config_path()
    if not path.exists():
        return Config(exists=False, path=path)
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    profil = raw.get("profil", {})
    sumber = raw.get("sumber", {})
    wr = sumber.get("workrecords", {})
    browser = raw.get("browser", {})
    monev = raw.get("monev", {})
    cfg = Config(exists=True, path=path)
    cfg.web_base = monev.get("web_base", WEB_BASE).rstrip("/")
    cfg.api_base = monev.get("api_base", API_BASE).rstrip("/")
    if browser.get("profile_dir"):
        cfg.profile_dir = Path(browser["profile_dir"]).expanduser()
    cfg.channel = browser.get("channel", "chrome")
    cfg.posisi = profil.get("posisi", "")
    cfg.perusahaan = profil.get("perusahaan", "")
    cfg.tim = profil.get("tim", "")
    cfg.rutinitas = list(profil.get("rutinitas", []))
    cfg.jangan_disebut = list(profil.get("jangan_disebut", []))
    laporan = raw.get("laporan", {})
    cfg.lewati_proyek = [str(x) for x in laporan.get("lewati_proyek", [])]
    cfg.nama_boleh = [str(x) for x in laporan.get("nama_boleh", [])]
    if re.fullmatch(r"\d\d:\d\d", str(laporan.get("jam_selesai", ""))):
        cfg.jam_selesai = laporan["jam_selesai"]
    nilai = profil.get("nilai", {})
    cfg.nilai_semboyan = str(nilai.get("semboyan", ""))
    cfg.nilai_poin = _poin_nilai(nilai.get("poin", []))
    cfg.mode = sumber.get("mode", "auto")
    cfg.workrecords_dir = Path(wr["dir"]).expanduser() if wr.get("dir") else None
    cfg.lewati_folder = list(wr.get("lewati_folder", cfg.lewati_folder))
    cfg.mcp_awalan_tool = list(sumber.get("mcp", {}).get("awalan_tool", []))
    git = sumber.get("git", {})
    cfg.git_penyedia = [p for p in (str(x).lower() for x in git.get("penyedia", [])) if p in ("github", "gitlab")]
    cfg.gitlab_host = str(git.get("gitlab_host") or "gitlab.com")
    cfg.pesan = raw.get("pesan") if isinstance(raw.get("pesan"), dict) else {}
    cfg.panggilan = str(profil.get("panggilan", "")).strip()
    bot = raw.get("bot", {})
    jam = lambda x: isinstance(x, str) and re.fullmatch(r"\d\d:\d\d", x) is not None  # noqa: E731
    if jam(bot.get("kartu")):
        cfg.bot_kartu = bot["kartu"]
    if isinstance(bot.get("pengingat"), list):
        cfg.bot_pengingat = sorted(x for x in bot["pengingat"] if jam(x))
    if jam(bot.get("rekap")):
        cfg.bot_rekap = bot["rekap"]
    if isinstance(bot.get("pantau"), list):
        cfg.bot_pantau = sorted(x for x in bot["pantau"] if jam(x))
    if isinstance(bot.get("tunda_menit"), int) and 5 <= bot["tunda_menit"] <= 240:
        cfg.bot_tunda_menit = bot["tunda_menit"]
    jadwal = raw.get("jadwal", {})
    jam_draft = sorted(x for x in jadwal.get("jam", []) if jam(x))
    if jam_draft:
        cfg.jadwal_jam = jam_draft
    cfg.jadwal_alat_mcp = [str(x) for x in jadwal.get("alat_mcp", [])]
    return cfg


def detect_workrecords() -> Path | None:
    """Folder work records untuk config baru: hanya dari env MONEV_WORK_RECORDS (bila foldernya ada).
    monev tidak menebak lokasi milik alat lain; selebihnya diisi user di `[sumber.workrecords] dir`."""
    if os.environ.get("MONEV_WORK_RECORDS"):
        p = Path(os.environ["MONEV_WORK_RECORDS"]).expanduser()
        if p.is_dir():
            return p
    return None


def ensure_config() -> tuple[Config, bool]:
    """Buat config otomatis bila belum ada. Mengembalikan (config, dibuat_baru)."""
    path = config_path()
    if path.exists():
        return load_config(), False
    wr = detect_workrecords()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_config("", "", str(wr) if wr else ""), encoding="utf-8")
    return load_config(), True


def autofill_profile(cfg: Config, me: dict) -> list[str]:
    """Lengkapi [profil] dari /users/me bila masih kosong. Hanya posisi, perusahaan, dan nama mentor
    (ke jangan_disebut). Email/telepon tidak pernah disimpan. Mengembalikan daftar yang diisi."""
    if not cfg.exists:
        return []
    raw = cfg.path.read_text(encoding="utf-8")
    filled = []
    posisi = (me.get("job_role") or "").strip()
    perusahaan = (me.get("internship_company") or "").strip()
    mentor = (me.get("mentor_name") or "").strip()
    if posisi and not cfg.posisi:
        raw = raw.replace('posisi = ""', f"posisi = {_toml_str(posisi)}", 1)
        filled.append(f"posisi = {posisi}")
    if perusahaan and 'perusahaan = ""' in raw:
        raw = raw.replace('perusahaan = ""', f"perusahaan = {_toml_str(perusahaan)}", 1)
        filled.append(f"perusahaan = {perusahaan}")
    if mentor and mentor not in cfg.jangan_disebut:
        new = cfg.jangan_disebut + [mentor]
        raw = re.sub(r"^jangan_disebut = \[.*?\]", f"jangan_disebut = {_toml_list(new)}", raw, count=1, flags=re.M)
        filled.append("nama mentor → jangan_disebut")
    if filled:
        cfg.path.write_text(raw, encoding="utf-8")
    return filled


def _toml_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_list(values: list[str]) -> str:
    return "[" + ", ".join(_toml_str(v) for v in values) + "]"


def render_config(posisi: str, tim: str, workrecords_dir: str) -> str:
    return f"""# Dibuat oleh `monev init`. Tidak ada email, password, token, atau cookie di sini.

[profil]                       # posisi/perusahaan diisi otomatis dari profil Monev saat login pertama
posisi = {_toml_str(posisi)}
perusahaan = ""
tim = {_toml_str(tim)}
panggilan = ""                 # nama sapaan di bot (mis. "Rina"); kosong = nama depan dari profil Monev
rutinitas = []                 # hanya SARAN saat menyusun draft, selalu dikonfirmasi
jangan_disebut = []            # nama klien/orang/proyek yang tidak boleh muncul

[profil.nilai]                 # nilai perusahaan di pesan "fokus hari ini" (bot & extension); kosong = tidak ditampilkan
semboyan = ""                  # contoh: "Bekerja dengan integritas"
poin = []                      # contoh: ["Integritas: jujur soal progres dan hambatan", ...]; satu poin per hari

# [pesan.ingat.pertama]        # opsional: ganti teks notifikasi extension; kunci dan teks bawaan ada di
# judul = "..."                # monev/teks/bawaan.toml (yang tidak ditulis di sini tetap memakai bawaan)

[laporan]                      # saringan isi laporan; nama proyek dan klien diambil otomatis dari sumber
lewati_proyek = []             # proyek yang tidak masuk laporan, mis. proyek pribadi
nama_boleh = []                # nama yang boleh disebut walau tertangkap saringan
jam_selesai = "17:00"          # kerja sesudah jam ini dianggap di luar jam kerja

[sumber]                       # bahan draft /monev, semuanya dibaca saja (docs/teknis/kontrak-sumber.md)
mode = "auto"                  # auto | workrecords | checklist

[sumber.workrecords]           # folder catatan kerja harian (format: docs/teknis/kontrak-sumber.md)
dir = {_toml_str(workrecords_dir)}
lewati_folder = ["_knowledge", "_plans"]

[sumber.mcp]                   # MCP kantor (logtime, tiket, aktivitas git, kalender) yang terpasang di agent-mu
awalan_tool = []               # awalan nama tool (Claude Code: "mcp__<server>__") atau nama server MCP (Hermes)

[sumber.git]                   # commit, PR/MR, review milikmu lewat `gh` / `glab` yang sudah login (`monev bukti`)
penyedia = []                  # "github" dan/atau "gitlab"; kosong = tidak dipakai
gitlab_host = "gitlab.com"     # GitLab kantor/self-hosted: ganti dengan host-nya

[bot]                          # jadwal bot Telegram (WIB, hari kerja); dibaca config di server tempat bot jalan
kartu = "08:00"                # kartu hari ini: sapaan, status laporan, fokus
pengingat = ["15:00", "16:30", "20:00"]   # hanya bila laporan belum diisi; yang terakhir paling tegas
rekap = "16:00"                # Jumat: rekap minggu; hari kerja terakhir periode: rekap periode
pantau = ["12:00", "18:00", "22:00"]      # cek perubahan (terkirim, revisi, disetujui, ditolak) tanpa pengingat
tunda_menit = 60               # tombol "Ingatkan lagi" di pengingat

[jadwal]                       # draft otomatis di laptop (WIB), aktif setelah `monev jadwal pasang`
jam = ["16:00", "17:00", "18:00", "19:00"]   # jam berikutnya mencoba lagi bila bahan belum ada
alat_mcp = []                  # nama lengkap tool MCP yang hanya membaca, boleh dipakai proses terjadwal

[browser]
channel = "chrome"
"""


# ---- state (bukan rahasia): waktu login, persetujuan lokasi, hasil tes lokasi ----

def state_path() -> Path:
    return data_dir() / "state.json"


def load_state() -> dict:
    p = state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state: dict) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
