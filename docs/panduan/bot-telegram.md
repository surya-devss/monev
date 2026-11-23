# Bot Telegram `monev bot`

Bot pribadi yang mengingatkan kalau laporan Monev hari ini belum diisi, memberi tahu kalau mentor minta revisi,
menyetujui laporan, atau menolak kehadiran, dan mengirim rekap kehadiran. Bot ini **tidak memakai AI** dan **hanya membaca** Monev.
Menulis dan mengirim laporan tetap dilakukan dari laptop.

Satu bot untuk satu orang. Bot hanya menjawab chat milik pemiliknya (`TELEGRAM_CHAT_ID`); pesan dari orang lain
diabaikan tanpa balasan.

## Isi halaman

1. [Yang dikirim bot](#yang-dikirim-bot)
2. [Persiapan: buat bot dan ambil chat id](#persiapan-buat-bot-dan-ambil-chat-id)
3. [Menjalankan bot](#menjalankan-bot) (laptop atau server sendiri)
4. [Sesi Monev di server habis](#sesi-monev-di-server-habis)
5. [Kalau ada masalah](#kalau-ada-masalah)
6. [Mengubah pesan atau jadwal](#mengubah-pesan-atau-jadwal)

## Yang dikirim bot

Rancangannya: chat tetap pendek. Hari kerja yang normal cukup tiga pesan (kartu hari ini, satu pengingat bila
perlu, konfirmasi terkirim). Pesan yang sudah tidak relevan diperbarui di tempat, bukan ditumpuk.

### Otomatis (WIB, jam dari `[bot]` di config)

| Jam bawaan | Pesan | Kapan dikirim |
|---|---|---|
| 08.00 | **Kartu hari ini**: sapaan, status laporan, revisi, batas kirim, fokus hari ini dan satu nilai perusahaan; tombol Status, Rekap, Menu. Isinya **diperbarui** di setiap pengecekan (mis. jadi "✓ Terkirim, menunggu mentor") | hari kerja |
| 08.00 | "Selamat pagi, … Hari ini libur." (satu pesan, tanpa pengingat) | hari libur |
| 08.00 | Sesi Monev di server hampir habis | sisa ≤ 3 hari |
| 15.00, 16.30, 20.00 | Pengingat, makin tegas; tombol **Ingatkan 1 jam lagi** dan **Sudah kirim, cek**. Setelah laporan terkirim, pengingat dicoret dan tombolnya hilang | hari kerja, laporan belum diisi |
| 16.00 | Rekap minggu (Jumat) dan rekap periode (hari kerja terakhir periode) | hari kerja |

**Periode** = satu bulan sejak tanggal mulai magang, sama dengan hitungan gaji dan absen MagangHub. Mulai 16 Nov →
periode 1 = 16 Nov–15 Des, periode 2 = 16 Des–15 Jan. Total absen dan sisa izin dibayar di rekap dihitung per periode,
absen berturut dihitung lintas periode. `/rekap_bulan` dan tombol "Rekap periode" menampilkan periode berjalan.

Setiap jadwal, ditambah pengecekan pada 12.00, 18.00, dan 22.00, juga mendeteksi perubahan:

- laporan baru saja terkirim (beserta status lokasi dan persetujuan mentor),
- mentor minta revisi (beserta catatannya),
- laporan disetujui mentor (beberapa tanggal digabung jadi satu pesan),
- kehadiran ditolak mentor (dihitung absen),
- masa magang tinggal 30 hari, 7 hari, hari terakhir, dan saat Monev menandai magang tidak aktif,
- tampilan situs Monev diperbarui (nama file utama frontend berganti). Artinya form bisa ikut berubah, jadi kiriman
  berikutnya dicoba dulu dengan `monev kirim --uji`.

Persetujuan yang terjadi setelah pengecekan 22.00 dikabari pukul 08.00 besoknya, tepat setelah kartu hari ini.
Saat bot baru diperbarui, persetujuan dan versi situs yang sudah ada hanya dicatat dan tidak dikabari.

Bila Monev tidak bisa dibaca, bot mengirim **satu** pesan gangguan per hari; percobaan berikutnya memperbarui pesan
itu, dan setelah pulih pesannya dicoret. Penyebabnya dibedakan:

| Penyebab | Artinya | Tombol |
|---|---|---|
| Sesi habis | dialihkan ke halaman login, atau API menjawab 401/403 | **Coba sekarang**, **Cara memperbarui** |
| Monev tidak bisa dihubungi | halaman tidak siap dalam 25 detik, API 5xx, atau jaringan | **Coba sekarang** |
| Bentuk data berubah | field yang dipakai bot hilang dari respons Monev, atau API 404. Bot berhenti supaya libur atau status tidak terbaca keliru | **Coba sekarang** |

Hari libur nasional, libur daerah lokasi magang, dan hari libur posisi (`off_days`, biasanya Sabtu–Minggu) dibaca
dari Monev. Kalau bot mati lebih dari 30 menit melewati suatu jadwal, jadwal itu dilewati (tidak dikirim terlambat).
Jadwal yang sudah jalan dan id pesan hari itu dicatat, jadi bot yang restart tidak mengirim dobel.

### Menu dan perintah

Tombol **Menu** Telegram (atau ketik `/`) berisi `/menu`, `/status`, `/rekap`, `/help`. `/rekap_bulan` dan `/ping`
tetap bisa diketik.

`/menu` mengirim satu pesan bertombol: Status hari ini, Rekap minggu, Rekap periode, Jadwal pengingat, Bantuan.
Setiap tombol **mengganti isi pesan menu itu** (ada tombol "‹ Menu" untuk kembali), jadi chat tidak bertambah.
Tombol di kartu hari ini membuka pesan baru supaya kartunya tetap utuh.

Status dan rekap butuh membuka Chrome untuk membaca Monev (5–15 detik di server). Selama itu pesannya berganti jadi
"⏳ Membaca Monev…" dan muncul "mengetik…" di atas chat. Hasil baca disimpan 10 menit: menekan lagi dalam rentang itu
langsung dijawab. Di bawah hasil ada "Data Monev pukul HH.MM" dan tombol **↻ Segarkan** untuk membaca ulang
(misalnya tepat setelah mengirim laporan). Pengecekan terjadwal dan tombol "Sudah kirim, cek" selalu membaca ulang.

Contoh tampilan semua pesan: [`../teknis/format-pesan-telegram.md`](../teknis/format-pesan-telegram.md).

### Config di server

Nama, posisi, dan perusahaan dibaca dari profil Monev, tidak perlu ditulis. Yang diatur di `config.toml` server
(di Docker: `/data/config.toml` di volume `monev_data`) hanya:

```toml
[profil]
panggilan = "Rina"            # nama sapaan; kosong = nama depan dari Monev

[profil.nilai]                 # nilai perusahaan di kartu hari ini (sama dengan extension)
semboyan = "..."
poin = ["Nilai: cara menerapkannya", ...]

[bot]                          # jadwal (WIB, hari kerja)
kartu = "08:00"
pengingat = ["15:00", "16:30", "20:00"]
rekap = "16:00"
pantau = ["12:00", "18:00", "22:00"]
tunda_menit = 60

[pesan.bot.menu]               # opsional: ganti teks; kunci dan teks bawaan di monev/teks/bawaan.toml
judul = "Mau lihat apa, {nama}?"
```

Bot membaca config sekali saat start. Setelah mengubah `/data/config.toml` di volume `monev_data`, jalankan
`docker restart monev-bot`.

## Persiapan: buat bot dan ambil chat id

Butuh CLI `monev` yang sudah terpasang dan sudah login ([pasang.md](pasang.md)).

1. Di Telegram, chat **@BotFather** → `/newbot` → beri nama dan username (harus diakhiri `bot`).
   BotFather memberi **token**. Token ini rahasia: jangan ditempel di chat atau di-commit.
2. Buat file `.env` di root repo (sudah di-`.gitignore`), isi:
   ```
   TELEGRAM_BOT_TOKEN=<token dari BotFather>
   ```
3. Buka bot barumu di Telegram, kirim `/start`.
4. Ambil chat id:
   ```bash
   monev bot --chat-id
   ```
   Salin angka yang muncul ke `.env`:
   ```
   TELEGRAM_CHAT_ID=<angka tadi>
   ```
5. Coba kirim pesan contoh:
   ```bash
   monev bot --coba menu      # pesan menu bertombol
   monev bot --coba kartu     # kartu hari ini, data Monev asli
   monev bot --coba ingat     # tiga pengingat
   monev bot --coba status    # status hari ini, data Monev asli
   monev bot --coba rekap     # rekap minggu dan bulan, data Monev asli
   ```

Token dan chat id juga bisa diberikan lewat environment variable dengan nama yang sama; nilai env menang atas `.env`.

## Menjalankan bot

Pilih satu. Jangan jalankan dua bot dengan token yang sama sekaligus: Telegram hanya memberi pesan masuk ke salah
satunya.

### A. Di laptop

```bash
monev bot
```

Bot jalan selama terminal terbuka dan laptop menyala. Cocok untuk mencoba. Pengingat tidak sampai kalau laptop
tidur.

### B. Di server sendiri dengan Docker

Server butuh Docker dan RAM kosong ±600 MB (Chrome dibuka hanya saat mengecek, lalu ditutup; puncak terukur
±300 MB).

Sesi Monev tidak bisa dibuat langsung di server karena login butuh layar. Caranya: login di laptop, lalu salin
profil sesinya ke server.

**1. Di laptop: bungkus profil sesi** (tanpa cache, hanya bisa dibaca kamu)
```bash
umask 077
tar -czf monev-profile.tgz -C ~/.local/share/monev \
  --exclude='chrome-profile/Singleton*' --exclude='*/Cache' --exclude='*/Code Cache' \
  --exclude='*/GPUCache' --exclude='*/Service Worker/CacheStorage' chrome-profile
scp monev-profile.tgz <server>:/root/
rm monev-profile.tgz
```

**2. Di server: masukkan ke volume Docker**
```bash
docker volume create monev_data
docker run --rm -v monev_data:/data -v /root/monev-profile.tgz:/p.tgz:ro alpine \
  sh -c 'tar -xzf /p.tgz -C /data && chown -R 1000:1000 /data'
rm /root/monev-profile.tgz
```

**3. Bangun image dan cek sesi terbaca dari server**
```bash
docker build -t monev-bot:local -f deploy/Dockerfile .
docker run --rm --shm-size=256m -v monev_data:/data monev-bot:local monev status --no-login
```
Harus menampilkan status hari ini. Kalau keluar "Belum login", ulangi langkah 1–2.

**4. Jalankan**

Buat `deploy/.env` (isi token dan chat id seperti di atas), lalu:
```bash
docker compose -f deploy/docker-compose.yml up -d --build
docker logs -f monev-bot     # "monev bot jalan · chat 848… · jadwal 08:00, 12:00, …"
```

## Sesi Monev di server habis

Sesi berlaku ±30 hari dan masa berlakunya bergeser setiap kali dipakai, jadi bot yang membaca Monev setiap hari
biasanya tidak kehabisan sesi ([situs-monev](../teknis/situs-monev.md#login--sesi)). Tanggal habisnya ada di `/status`,
dan bot mengingatkan mulai 3 hari sebelum habis. Untuk memperpanjang:

1. Di laptop: `monev login` (jendela Chrome terbuka, login sendiri). Pastikan muncul "berlaku s.d. …".
2. Ulangi [langkah B.1–B.2](#b-di-server-sendiri-dengan-docker) untuk menyalin profil baru ke server.
3. `docker restart monev-bot`, lalu kirim `/status` ke bot.

## Kalau ada masalah

| Gejala | Penyebab yang paling mungkin | Yang dilakukan |
|---|---|---|
| Bot tidak menjawab sama sekali | container mati, atau ada bot lain memakai token yang sama | `docker ps`, `docker logs --tail 50 monev-bot`; matikan `monev bot` di laptop |
| "Bot belum bisa membaca Monev. Sesi Monev di server habis…" | sesi di server kedaluwarsa | [Sesi Monev di server habis](#sesi-monev-di-server-habis) |
| "… Situs Monev tidak bisa dihubungi atau terlalu lambat…" | Monev sedang lambat atau down | tekan **Coba sekarang** nanti, atau tunggu jadwal berikutnya |
| "… Bentuk data Monev berubah (…)…" | Monev mengganti API, kode `monev` perlu diperbarui | isi laporan dari laptop seperti biasa, lalu perbaiki `WAJIB` di `monev/portal/api.py` dan pembacanya |
| "Tampilan situs Monev baru saja diperbarui." | Monev di-deploy ulang | sebelum kirim berikutnya: `monev kirim --uji` |
| Tombol tidak bereaksi, tidak ada ⏳ | bot mati atau polling terputus | `docker logs --tail 20 monev-bot`; `/ping` |
| `/status` lama sekali | Chrome di server kekurangan memori | `docker stats monev-bot`; pastikan `shm_size` 256m dan limit 600M tetap ada |
| Menu perintah tidak muncul | `setMyCommands` gagal saat start | restart bot, atau `monev bot --coba menu` sekali |
| `monev bot --chat-id` bilang "Belum ada pesan masuk" | belum mengirim `/start` ke bot, atau bot lain sedang jalan | kirim `/start`, hentikan bot lain, ulangi |

## Mengubah pesan atau jadwal

| Mau mengubah | File |
|---|---|
| Teks pesan (untuk dirimu) | `[pesan.bot.*]` di config server, kunci sama dengan [`monev/teks/bawaan.toml`](../../monev/teks/bawaan.toml) |
| Teks pesan bawaan (untuk semua) | [`monev/teks/bawaan.toml`](../../monev/teks/bawaan.toml), lalu contoh di [`format-pesan-telegram.md`](../teknis/format-pesan-telegram.md) |
| Susunan pesan dan tombol | [`monev/bot/pesan.py`](../../monev/bot/pesan.py) |
| Jam jadwal | `[bot]` di config server (tanpa ubah kode) |
| Daftar perintah di Menu | `MENU` di [`monev/bot/telegram.py`](../../monev/bot/telegram.py) |
| Cara bot menjawab perintah | [`monev/bot/app.py`](../../monev/bot/app.py) |
| Batas peringatan dan izin | `BATAS` di [`monev/portal/rekap.py`](../../monev/portal/rekap.py) |

Setelah mengubah, jalankan tes (`.venv/bin/python -m unittest discover -s tests`) dan `monev bot --coba …` untuk
melihat hasilnya di Telegram.
