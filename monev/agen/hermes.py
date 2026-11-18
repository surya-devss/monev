"""Pasang skill `monev` ke profile Hermes (satu sumber dengan plugin Claude Code: plugin/skills/monev).

Hasil:
  <HERMES_HOME>/skills/maganghub/monev/          salinan (atau symlink) plugin/skills/monev
  <HERMES_HOME>/skill-bundles/monev.yaml          slash command /monev
Hanya path milik installer ini yang diganti/dihapus (penanda `.monev-install.json` / komentar bundle).
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

SUMBER = Path(__file__).resolve().parents[2] / "plugin" / "skills" / "monev"
PENANDA = ".monev-install.json"
TANDA_BUNDLE = "# dikelola: monev hermes install"
BUNDLE = {
    "name": "monev",
    "skills": ["monev"],
    "description": "Laporan harian Monev MagangHub: status, draft, review, kirim.",
    "instruction": ("Follow skill monev step by step. Every action goes through the monev CLI. Never send anything "
                    "before the user replies `kirim` for the draft currently shown; MCP tools are read-only."),
}


def hermes_home(profil: str | None = None, path: str | None = None) -> Path:
    if path:
        return Path(path).expanduser()
    base = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
    return base / "profiles" / profil if profil else base


def _tujuan(home: Path) -> tuple[Path, Path]:
    return home / "skills" / "maganghub" / "monev", home / "skill-bundles" / "monev.yaml"


def _milik_kita_skill(p: Path) -> bool:
    if p.is_symlink():
        return p.resolve() == SUMBER
    return (p / PENANDA).exists()


def _milik_kita_bundle(p: Path) -> bool:
    try:
        return p.read_text(encoding="utf-8").startswith(TANDA_BUNDLE)
    except OSError:
        return False


def render_bundle() -> str:
    # JSON adalah YAML yang sah; dipakai agar kutipan aman.
    baris = [TANDA_BUNDLE, f"name: {BUNDLE['name']}", "skills:"]
    baris += [f"- {s}" for s in BUNDLE["skills"]]
    baris += [f"description: {json.dumps(BUNDLE['description'], ensure_ascii=False)}",
              f"instruction: {json.dumps(BUNDLE['instruction'], ensure_ascii=False)}"]
    return "\n".join(baris) + "\n"


def pasang(home: Path, symlink: bool = False, paksa: bool = False) -> list[str]:
    if not home.is_dir():
        raise RuntimeError(f"profile Hermes tidak ada: {home}")
    skill, bundle = _tujuan(home)
    for p, milik in ((skill, _milik_kita_skill), (bundle, _milik_kita_bundle)):
        if (p.exists() or p.is_symlink()) and not milik(p) and not paksa:
            raise RuntimeError(f"{p} sudah ada dan bukan milik installer monev (pakai --force setelah dicek)")

    skill.parent.mkdir(parents=True, exist_ok=True)
    if skill.is_symlink() or skill.is_file():
        skill.unlink()
    elif skill.exists():
        shutil.rmtree(skill)
    if symlink:
        skill.symlink_to(SUMBER, target_is_directory=True)
    else:
        sementara = skill.with_name(".monev-staging")
        if sementara.exists():
            shutil.rmtree(sementara)
        shutil.copytree(SUMBER, sementara)
        (sementara / PENANDA).write_text(json.dumps({"sumber": str(SUMBER), "mode": "copy"}), encoding="utf-8")
        sementara.rename(skill)

    bundle.parent.mkdir(parents=True, exist_ok=True)
    bundle.write_text(render_bundle(), encoding="utf-8")
    return [f"skill  : {skill}" + (" → " + str(SUMBER) if symlink else " (salinan)"), f"bundle : {bundle} (/monev)"]


def lepas(home: Path) -> list[str]:
    skill, bundle = _tujuan(home)
    out = []
    if skill.is_symlink() and _milik_kita_skill(skill):
        skill.unlink()
        out.append(f"dihapus: {skill}")
    elif skill.is_dir() and _milik_kita_skill(skill):
        shutil.rmtree(skill)
        out.append(f"dihapus: {skill}")
    if bundle.exists() and _milik_kita_bundle(bundle):
        bundle.unlink()
        out.append(f"dihapus: {bundle}")
    kategori = skill.parent
    if kategori.is_dir() and not any(kategori.iterdir()):
        kategori.rmdir()
    return out or ["tidak ada yang dipasang installer monev di profile ini"]
