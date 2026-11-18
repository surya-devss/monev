"""Perintah memasang skill /monev ke agent (`monev hermes`). Logika installer ada di `monev.agen`."""

from __future__ import annotations

from ._umum import EXIT_FAIL, EXIT_OK


def cmd_hermes(args) -> int:
    from ..agen.hermes import hermes_home, lepas, pasang

    home = hermes_home(args.profile, args.hermes_home)
    try:
        baris = lepas(home) if args.aksi == "uninstall" else pasang(home, args.symlink, args.force)
    except RuntimeError as e:
        print(f"✗ {e}")
        return EXIT_FAIL
    print(f"Profile Hermes: {home}")
    for b in baris:
        print(f"✓ {b}")
    if args.aksi == "install":
        print("Lalu di Hermes: sesi baru atau /reload-skills, kemudian /monev.")
    return EXIT_OK
