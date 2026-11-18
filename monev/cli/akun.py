"""Perintah setup dan sesi: init, config, login, logout, doctor."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from ..config import config_path, load_config, load_state, render_config, save_state
from ._umum import (EXIT_FAIL, EXIT_NEED_LOGIN, EXIT_OK, _autofill, _config_auto, _login_flow, _session_or_login,
                    _yes)


def cmd_init(args) -> int:
    """Config otomatis: folder work records dari env MONEV_WORK_RECORDS; posisi/perusahaan diisi dari
    profil Monev saat `monev status` pertama. Tidak ada pertanyaan; argumen hanya untuk menimpa."""
    from ..config import detect_workrecords

    path = config_path()
    if path.exists() and not args.force:
        print(f"Config sudah ada: {path}\nPakai --force untuk membuat ulang.")
        return EXIT_OK
    wr = args.workrecords if args.workrecords is not None else str(detect_workrecords() or "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_config(args.posisi or "", args.tim or "", wr), encoding="utf-8")
    print(f"✓ Config ditulis: {path}")
    print(f"  work records : {wr or 'tidak ditemukan → mode checklist'}")
    print("  posisi       : diisi otomatis dari profil Monev saat `monev` pertama")
    return EXIT_OK


def cmd_config(args) -> int:
    import os
    import subprocess

    cfg = _config_auto()
    if args.edit:
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "nano"
        return subprocess.call([editor, str(cfg.path)])
    info = {
        "path": str(cfg.path),
        "posisi": cfg.posisi,
        "perusahaan": cfg.perusahaan,
        "tim": cfg.tim,
        "rutinitas": cfg.rutinitas,
        "jangan_disebut": len(cfg.jangan_disebut),   # hanya jumlah; isinya lihat file
        "mode": cfg.mode,
        "workrecords_dir": str(cfg.workrecords_dir) if cfg.workrecords_dir else None,
        "workrecords_ada": bool(cfg.workrecords_dir and cfg.workrecords_dir.is_dir()),
        "mcp_awalan_tool": cfg.mcp_awalan_tool,
        "git_penyedia": cfg.git_penyedia,
        "gitlab_host": cfg.gitlab_host,
        "nilai": cfg.nilai_dict(),
        "draft_dir": str(cfg.profile_dir.parent / "draft"),
    }
    if args.json:
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return EXIT_OK
    print(f"Config: {info['path']}  (ubah: monev config --edit)\n")
    print(f"  posisi         : {cfg.posisi or '– (otomatis dari Monev)'}")
    print(f"  perusahaan     : {cfg.perusahaan or '– (otomatis dari Monev)'}")
    print(f"  tim            : {cfg.tim or '–'}")
    print(f"  rutinitas      : {', '.join(cfg.rutinitas) or '–'}  (hanya saran, selalu dikonfirmasi)")
    print(f"  jangan_disebut : {len(cfg.jangan_disebut)} nama")
    print(f"  work records   : {info['workrecords_dir'] or '– (mode checklist)'}")
    print(f"  MCP kantor     : {', '.join(cfg.mcp_awalan_tool) or '– (tidak dipakai)'}")
    git = ", ".join(p + (f" ({cfg.gitlab_host})" if p == "gitlab" else "") for p in cfg.git_penyedia)
    print(f"  Git            : {git or '– (tidak dipakai)'}")
    if cfg.nilai_poin:
        nilai = f"{len(cfg.nilai_poin)} poin" + (f" · {cfg.nilai_semboyan}" if cfg.nilai_semboyan else "")
    else:
        nilai = "– (pesan fokus tanpa nilai; isi: /monev nilai)"
    print(f"  nilai          : {nilai}")
    return EXIT_OK


def cmd_login(args) -> int:
    ok = _login_flow(load_config(), args.timeout, ask_location=args.uji_lokasi)
    return EXIT_OK if ok else EXIT_NEED_LOGIN


def cmd_logout(args) -> int:
    """Hapus sesi CLI (profil Chrome monev). Sesi di Chrome kamu sendiri tidak tersentuh."""
    import shutil

    cfg = load_config()
    prof = cfg.profile_dir
    if not prof.exists():
        print(f"Tidak ada sesi CLI ({prof}).")
        return EXIT_OK
    print(f"Ini menghapus sesi login CLI di {prof}.")
    print("Chrome kamu sendiri (extension) tidak terpengaruh. Login lagi: jalankan `monev` di terminal biasa.")
    if not args.ya and not _yes("Lanjut hapus?"):
        print("Dibatalkan.")
        return EXIT_FAIL
    shutil.rmtree(prof)
    state = load_state()
    state.pop("login_at", None)
    save_state(state)
    print("✓ Sesi CLI dihapus.")
    return EXIT_OK


def cmd_doctor(args) -> int:
    from ..kirim.host import diagnosa
    from ..portal.browser import find_chrome
    from ..sumber.jalur import cek_jalur

    cfg = _config_auto()
    as_json = getattr(args, "json", False)
    inti: list[dict] = []
    ok_all = True

    def line(ok: bool | None, label: str, detail: str = "") -> None:
        nonlocal ok_all
        if ok is False:
            ok_all = False
        inti.append({"cek": label, "ok": ok, "detail": detail})
        if not as_json:
            print(f"{ {True: '✓', False: '✗', None: '–'}[ok]} {label}" + (f": {detail}" if detail else ""))

    def selesai(code: int) -> int:
        jalur = cek_jalur(load_config())
        if as_json:
            print(json.dumps({"ok": ok_all and code == EXIT_OK, "kode": code, "inti": inti, "jalur": jalur},
                             indent=2, ensure_ascii=False))
            return code
        print("\nJalur sumber bahan /monev:")
        for kode, j in jalur.items():
            tanda = {True: "✓", False: "✗", None: "–"}[j["ok"]] if j["aktif"] else "·"
            print(f"  {tanda} {kode}. {j['nama']}: {j['detail']}" + (f"\n      → {j['langkah']}" if j["langkah"] else ""))
        if code == EXIT_OK:
            print("\nSemua OK." if ok_all else "\nAda yang perlu diperbaiki (lihat ✗).")
        return code

    line(cfg.exists, "config", str(cfg.path) if cfg.exists else "belum ada → monev init")
    chrome = find_chrome()
    line(bool(chrome), "Chrome asli", chrome or "Google Chrome tidak ditemukan → pasang dari google.com/chrome")
    masalah_ext = diagnosa()
    line(not masalah_ext, "extension", "; ".join(masalah_ext) if masalah_ext else
         "jembatan terdaftar, extension terpasang, Chrome berjalan (uji: monev kirim --ping)")
    line(None, "profil Chrome monev", str(cfg.profile_dir))
    if not chrome:
        return selesai(EXIT_FAIL)
    if getattr(args, "tanpa_sesi", False):
        line(None, "sesi Monev", "dilewati (--tanpa-sesi)")
        return selesai(EXIT_OK if ok_all else EXIT_FAIL)
    return selesai(_doctor_sesi(cfg, args, line, as_json))


def _doctor_sesi(cfg, args, line, as_json: bool) -> int:
    from ..portal.api import get
    from ..portal.browser import refresh_cookie_expiry, test_location

    if as_json:
        args.no_login = True   # jangan mencampur keluaran login dengan JSON
    cm, s = _session_or_login(cfg, args)
    if s is None:
        line(False, "sesi Monev", "belum login / sesi mati → monev login")
        return EXIT_NEED_LOGIN
    ok = True
    _autofill(cfg, s)
    cfg = load_config()
    line(bool(cfg.posisi), "profil", f"{cfg.posisi or '?'} · {cfg.perusahaan or '?'}")
    ok &= bool(cfg.posisi)
    try:
        try:
            me = get(s, "/users/me")
            line(True, "sesi Monev", "GET /users/me 200" + (f", periode mulai {me.get('internship_start_date', '')[:10]}" if me else ""))
        except Exception as e:  # noqa: BLE001
            line(False, "sesi Monev", str(e))
            ok = False
        exp = refresh_cookie_expiry(s)
        if exp:
            days = (exp - datetime.now(timezone.utc)).days
            line(days > 3, "refresh token", f"berlaku s.d. {exp.astimezone().date()} (±{days} hari)")
            ok &= days > 3
        else:
            line(None, "refresh token", "tanggal kedaluwarsa tidak terbaca")
        if args.uji_lokasi:
            geo = test_location(s)
            line(None, "lokasi (uji)", f"akurasi ±{geo.get('accuracy_m')} m" if geo.get("ok") else str(geo.get("error")))
        else:
            line(None, "lokasi", "dikirim dari Chrome kamu saat submit (Chrome monev tidak dapat lokasi)")
    finally:
        cm.__exit__(None, None, None)
    return EXIT_OK if ok else EXIT_FAIL
