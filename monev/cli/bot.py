"""Perintah bot Telegram pribadi (`monev bot`). Logika bot ada di paket `monev.bot`."""

from __future__ import annotations

from ._umum import EXIT_FAIL, EXIT_OK, _config_auto


def cmd_bot(args) -> int:
    from ..bot import pesan
    from ..bot.app import Bot, ambil
    from ..bot.jadwal import WIB
    from ..bot.telegram import Telegram, muat_env

    env = muat_env()
    token = env.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("✗ TELEGRAM_BOT_TOKEN belum ada. Isi di <repo>/.env (gitignored):\n"
              "    TELEGRAM_BOT_TOKEN=<token dari @BotFather>\n    TELEGRAM_CHAT_ID=<lihat: monev bot --chat-id>")
        return EXIT_FAIL
    tg = Telegram(token)
    try:
        me = tg.saya()
    except RuntimeError as ex:
        print(f"✗ Token ditolak Telegram: {ex}")
        return EXIT_FAIL

    if args.chat_id:
        print(f"Bot: @{me.get('username')}. Kirim /start ke bot itu dari akun Telegram kamu, lalu jalankan ini lagi.")
        ids = {}
        for u in tg.updates(None, timeout=0):
            c = (u.get("message") or {}).get("chat") or {}
            if c.get("id"):
                ids[c["id"]] = c.get("type")
        if not ids:
            print("Belum ada pesan masuk.")
            return EXIT_FAIL
        for i, t in ids.items():
            print(f"  chat id: {i}  ({t})")
        print("Isi ke .env: TELEGRAM_CHAT_ID=<chat id di atas>")
        return EXIT_OK

    chat = env.get("TELEGRAM_CHAT_ID")
    if not chat:
        print("✗ TELEGRAM_CHAT_ID belum ada di .env → jalankan: monev bot --chat-id")
        return EXIT_FAIL

    cfg = _config_auto()
    bot = Bot(cfg, tg, chat, log=lambda m: print(m, flush=True))
    if args.coba:
        from datetime import datetime

        tg.pasang_menu()
        sekarang = datetime.now(WIB)
        if args.coba in ("help", "menu"):
            bot.kirim(bot.tampilan("bantuan" if args.coba == "help" else "menu"))
        elif args.coba == "ingat":
            for i, u in enumerate(("pertama", "kedua", "terakhir")):
                bot.kirim(pesan.ingat(bot.tx, u, sekarang.date(), 24 - (15, 16, 20)[i], cfg.bot_tunda_menit))
        elif args.coba in ("status", "rekap"):
            bot.kirim(bot.tampilan("status" if args.coba == "status" else "minggu"))
            if args.coba == "rekap":
                bot.kirim(bot.tampilan("bulan"))
        else:   # kartu: kartu hari ini dari data Monev asli (tidak memengaruhi jadwal)
            try:
                data = ambil(cfg)
            except Exception as ex:  # noqa: BLE001
                print(f"✗ {ex}")
                return EXIT_FAIL
            st = data["status"]
            nama = pesan.panggilan(st, cfg.panggilan)
            libur = st.get("libur_nasional") or st.get("libur_posisi")
            bot.kirim(pesan.kartu_libur(bot.tx, st, nama) if libur else pesan.kartu(bot.tx, st, data.get("nilai"), nama))
        print(f"✓ Pesan contoh '{args.coba}' dikirim ke @{me.get('username')}.")
        return EXIT_OK

    bot.jalan()
    return EXIT_OK
