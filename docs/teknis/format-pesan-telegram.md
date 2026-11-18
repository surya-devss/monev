# Format pesan bot Telegram

Contoh setiap pesan `monev bot`, **dibuat dari kode** ([`monev/bot/pesan.py`](../../monev/bot/pesan.py)) dengan
teks bawaan [`monev/teks/bawaan.toml`](../../monev/teks/bawaan.toml) dan data contoh. Mockup visualnya ada di kanvas
desain (baris "Bot Telegram"). Cara memakai bot: [`../panduan/bot-telegram.md`](../panduan/bot-telegram.md).

## Aturan

1. **Chat tetap pendek.** Satu kartu hari ini yang diperbarui; pengingat yang sudah tidak relevan dicoret; gangguan
   satu pesan per hari; menu berganti di tempat. Hari normal cukup tiga pesan.
2. **Kalimat pertama adalah intinya** dan dicetak tebal, cukup dibaca dari notifikasi HP.
3. **Hanya format yang ada di Telegram**: tebal, miring, coret, `kode`, kutipan, tabel (rich message), tombol.
   Telegram tidak bisa mewarnai teks. Tanpa emoji; `✓` boleh sebagai tanda teks.
4. **Pengingat selalu pesan baru** (pesan yang diedit tidak membunyikan HP). Yang lain sebisa mungkin diedit.
5. **Teks kalimat dari `bawaan.toml`**, bisa ditimpa `[pesan]` di config server. Fokus dan pengingat memakai teks
   yang sama dengan notifikasi extension. Format angka dan tanggal rekap ada di kode.
6. Tanpa titik koma, tanpa tanda pisah panjang, tanpa titik dua di tengah kalimat (dicek `tests/test_teks.py`).
   Angka selalu dengan pembandingnya ("hadir 4 dari 5 hari"). Tanggal `Jumat, 20 Nov`; jam pakai titik (`15.00`).
7. Tanpa kontak, token, atau isi laporan. Teks dari Monev (catatan mentor) di-escape.
8. Rich message (`sendRichMessage`, diedit dengan `editMessageText` + `rich_message`, Bot API 10.1+). Bila gagal,
   bot mengirim versi teks biasanya (`parse_mode=HTML`), jadi pesan tidak pernah hilang.

Tombol: `b:*` membuka pesan baru (dipakai di kartu), `v:*` mengganti isi pesan itu (menu), `tunda:<urutan>`,
`cek`, `coba`, `cara`. Setiap tombol dijawab (`answerCallbackQuery`) supaya tidak berputar.

## Contoh

### 1. Kartu hari ini (08.00, belum diisi)

Hari kerja. Dikirim sebagai rich message; isinya diperbarui di setiap pengecekan.

Rich message:

```html
<p><b>Selamat pagi, Rina.</b><br/>Selasa, 17 Nov · DevOps Engineer di PT Contoh</p>
<table bordered compact><tr><td><b>Laporan</b></td><td>Belum diisi</td></tr>
<tr><td><b>Revisi</b></td><td>Tidak ada</td></tr>
<tr><td><b>Batas</b></td><td>23.59 WIB</td></tr>
</table>
<p><b>Fokus hari ini</b></p>
<blockquote>Kerjakan task yang sudah direncanakan, satu per satu sampai selesai.<br/>Catat hasil dan kendala sambil jalan, supaya laporan tinggal disusun.<br/><b>Konsisten.</b> Maju sedikit setiap hari lebih baik daripada menunggu sempurna.<br/><i>Bekerja dengan integritas</i></blockquote>
```

Cadangan teks biasa:

```html
<b>Selamat pagi, Rina.</b>
Selasa, 17 Nov · DevOps Engineer di PT Contoh

<b>Laporan</b>  Belum diisi
<b>Revisi</b>  Tidak ada
<b>Batas</b>  23.59 WIB

<b>Fokus hari ini</b>

<blockquote>Kerjakan task yang sudah direncanakan, satu per satu sampai selesai.
Catat hasil dan kendala sambil jalan, supaya laporan tinggal disusun.
<b>Konsisten.</b> Maju sedikit setiap hari lebih baik daripada menunggu sempurna.
<i>Bekerja dengan integritas</i></blockquote>
```

Tombol: [Status] · [Rekap] · [Menu]

### 2. Kartu hari ini setelah laporan terkirim

Pesan yang sama (diedit), baris Batas hilang.

Rich message:

```html
<p><b>Selamat pagi, Rina.</b><br/>Selasa, 17 Nov · DevOps Engineer di PT Contoh</p>
<table bordered compact><tr><td><b>Laporan</b></td><td>✓ Terkirim, menunggu mentor</td></tr>
<tr><td><b>Revisi</b></td><td>Tidak ada</td></tr>
</table>
<p><b>Fokus hari ini</b></p>
<blockquote>Kerjakan task yang sudah direncanakan, satu per satu sampai selesai.<br/>Catat hasil dan kendala sambil jalan, supaya laporan tinggal disusun.<br/><b>Konsisten.</b> Maju sedikit setiap hari lebih baik daripada menunggu sempurna.<br/><i>Bekerja dengan integritas</i></blockquote>
```

Cadangan teks biasa:

```html
<b>Selamat pagi, Rina.</b>
Selasa, 17 Nov · DevOps Engineer di PT Contoh

<b>Laporan</b>  ✓ Terkirim, menunggu mentor
<b>Revisi</b>  Tidak ada

<b>Fokus hari ini</b>

<blockquote>Kerjakan task yang sudah direncanakan, satu per satu sampai selesai.
Catat hasil dan kendala sambil jalan, supaya laporan tinggal disusun.
<b>Konsisten.</b> Maju sedikit setiap hari lebih baik daripada menunggu sempurna.
<i>Bekerja dengan integritas</i></blockquote>
```

Tombol: [Status] · [Rekap] · [Menu]

### 3. Hari libur (08.00)

Satu pesan pendek, tanpa pengingat.

```html
<b>Selamat pagi, Rina. Hari ini libur.</b>
Jumat, 25 Des. Tidak wajib mengisi laporan.
```

Tombol: [Menu]

### 4. Pengingat pertama (15.00)

Hari kerja, laporan belum diisi.

```html
<b>Laporan hari ini belum diisi.</b>
Selasa, 17 Nov. Batas kirim pukul 23.59 WIB.
Isi dari laptop dengan <code>/monev</code>.
```

Tombol: [Ingatkan 1 jam lagi] · [Sudah kirim, cek]

### 5. Pengingat kedua (16.30)

```html
<b>Laporan hari ini masih belum terkirim.</b>
Jam kerja hampir selesai, sebaiknya dikirim sebelum pulang.
Isi dari laptop dengan <code>/monev</code>.
```

Tombol: [Ingatkan 1 jam lagi] · [Sudah kirim, cek]

### 6. Pengingat terakhir (20.00)

```html
<b>Laporan belum terkirim. Sisa sekitar 4 jam.</b>
Kalau sampai 23.59 belum terkirim, hari ini dihitung absen.
Isi dari laptop dengan <code>/monev</code>.
```

Tombol: [Ingatkan 1 jam lagi] · [Sudah kirim, cek]

### 7. Pengingat setelah laporan terkirim

Pengingat yang sama diedit, tombolnya hilang.

```html
<s>Laporan hari ini belum diisi.</s>
<i>Selesai, laporan sudah terkirim.</i>
```

### 8. Pengingat setelah tombol Ingatkan 1 jam lagi

```html
<b>Laporan hari ini belum diisi.</b>
Selasa, 17 Nov. Batas kirim pukul 23.59 WIB.
Isi dari laptop dengan <code>/monev</code>.
<i>Diingatkan lagi pukul 16.02.</i>
```

Tombol: [Sudah kirim, cek]

### 9. Laporan terdeteksi terkirim

```html
<b>Laporan 17 Nov sudah terkirim.</b>
Tercatat hadir dan lokasi ikut terkirim. Sekarang menunggu persetujuan mentor.
```

### 10. Mentor minta revisi

Sekali per tanggal.

```html
<b>Mentor minta revisi laporan 14 Nov.</b>
<blockquote>Tambahkan hasil konkret pada aktivitas kedua.</blockquote>
Perbaiki dari laptop dengan <code>/monev revisi</code>.
```

### 11. Kehadiran ditolak mentor

Sekali per tanggal.

```html
<b>Kehadiran 14 Nov ditolak mentor.</b>
Hari itu dihitung absen. Total absen sekarang 1 dari batas peringatan 7.
Kalau menurutmu keliru, tanyakan ke mentor.
```

### 12. Sesi Monev hampir habis

08.00, bila sisa ≤ 3 hari.

```html
<b>Sesi Monev di server habis dalam 3 hari (16 Des).</b>
Setelah itu pengingat dan rekap berhenti.
Login ulang di laptop lalu salin sesinya ke server, caranya ada di <code>docs/panduan/bot-telegram.md</code>.
```

### 13. Gangguan

Satu pesan per hari, diedit di setiap percobaan.

```html
<b>Bot belum bisa membaca Monev.</b>
Penyebabnya sesi Monev habis, perlu login ulang. Pengingat ditunda dulu.
<i>Dicoba 15.00 dan 16.30. Berikutnya 18.00.</i>
```

Tombol: [Coba sekarang] · [Cara memperbarui]

### 14. Gangguan setelah pulih

Pesan yang sama diedit.

```html
<s>Bot belum bisa membaca Monev.</s>
<i>Pulih pukul 17.10, pengingat jalan lagi.</i>
```

### 15. Menu (/menu)

Setiap tombol mengganti isi pesan ini.

Rich message:

```html
<p><b>Mau lihat apa, Rina?</b><br/>Status dan rekap dibaca dari Monev, lalu dipakai ulang selama 10 menit.</p>
```

Cadangan teks biasa:

```html
<b>Mau lihat apa, Rina?</b>
Status dan rekap dibaca dari Monev, lalu dipakai ulang selama 10 menit.
```

Tombol: [Status hari ini] · [Rekap minggu] / [Rekap bulan] · [Jadwal pengingat] / [Bantuan]

### 16. Status hari ini

/status atau tombol Status.

Rich message:

```html
<p><b>Laporan hari ini belum diisi.</b></p>
<table bordered compact><tr><td><b>Tanggal</b></td><td>Selasa, 17 Nov, hari kerja</td></tr>
<tr><td><b>Laporan</b></td><td>Belum diisi</td></tr>
<tr><td><b>Revisi</b></td><td>Tidak ada</td></tr>
<tr><td><b>Batas</b></td><td>23.59 WIB</td></tr>
<tr><td><b>Sesi Monev</b></td><td>aktif sampai 16 Des</td></tr>
</table>
<p>Isi dari laptop dengan <code>/monev</code>.</p>
```

Cadangan teks biasa:

```html
<b>Laporan hari ini belum diisi.</b>

<b>Tanggal</b>  Selasa, 17 Nov, hari kerja
<b>Laporan</b>  Belum diisi
<b>Revisi</b>  Tidak ada
<b>Batas</b>  23.59 WIB
<b>Sesi Monev</b>  aktif sampai 16 Des

Isi dari laptop dengan <code>/monev</code>.
```

Tombol: [‹ Menu]

### 17. Rekap minggu

Jumat 16.00, /rekap, atau tombol.

Rich message:

```html
<p><b>Minggu ini hadir 1 dari 2 hari.</b><br/>16–20 Nov 2026</p>
<table bordered striped compact><tr><th>Hari</th><th>Kehadiran</th><th>Mentor</th></tr>
<tr><td>Sen 16</td><td>hadir</td><td>disetujui</td></tr>
<tr><td>Sel 17</td><td>izin</td><td>menunggu</td></tr>
</table>
<p>Izin 1 (sisa izin dibayar 2), absen 0.<br/>Aman, belum mendekati batas peringatan.</p>
```

Cadangan teks biasa:

```html
<b>Minggu ini hadir 1 dari 2 hari.</b>
16–20 Nov 2026

• Sen 16 · hadir · disetujui
• Sel 17 · izin · menunggu

Izin 1 (sisa izin dibayar 2), absen 0.
Aman, belum mendekati batas peringatan.
```

Tombol: [‹ Menu] · [Rekap bulan ›]

### 18. Rekap bulan

Hari kerja terakhir bulan 16.00, /rekap_bulan, atau tombol.

Rich message:

```html
<p><b>November 2026, hadir 1 dari 2 hari.</b><br/>16–20 Nov 2026 · 2 hari kerja</p>
<table bordered compact><tr><td><b>Hadir</b></td><td>1</td></tr>
<tr><td><b>Izin</b></td><td>1 (sisa izin dibayar 2)</td></tr>
<tr><td><b>Absen</b></td><td>0, ditolak mentor 0</td></tr>
<tr><td><b>Mentor</b></td><td>1 disetujui, 1 menunggu, 0 perlu revisi</td></tr>
<tr><td><b>Berturut</b></td><td>absen 0 dari 3</td></tr>
<tr><td><b>Total</b></td><td>absen 0 dari 7</td></tr>
</table>
<p>Aman, belum mendekati batas peringatan.</p>
```

Cadangan teks biasa:

```html
<b>November 2026, hadir 1 dari 2 hari.</b>
16–20 Nov 2026 · 2 hari kerja

<b>Hadir</b>  1
<b>Izin</b>  1 (sisa izin dibayar 2)
<b>Absen</b>  0, ditolak mentor 0
<b>Mentor</b>  1 disetujui, 1 menunggu, 0 perlu revisi
<b>Berturut</b>  absen 0 dari 3
<b>Total</b>  absen 0 dari 7

Aman, belum mendekati batas peringatan.
```

Tombol: [‹ Menu] · [Rekap minggu ›]

### 19. Jadwal pengingat

Dari [bot] di config.

Rich message:

```html
<p><b>Jadwal di hari kerja</b></p>
<table bordered compact><tr><td><b>08.00</b></td><td>Kartu hari ini</td></tr>
<tr><td><b>15.00</b></td><td>Pengingat bila belum diisi</td></tr>
<tr><td><b>16.30</b></td><td>Pengingat bila belum diisi</td></tr>
<tr><td><b>20.00</b></td><td>Pengingat terakhir</td></tr>
<tr><td><b>Jum 16.00</b></td><td>Rekap minggu (Jumat)</td></tr>
</table>
<p>Ubah di <code>config.toml</code> server bagian <code>[bot]</code>, lalu restart bot.</p>
```

Cadangan teks biasa:

```html
<b>Jadwal di hari kerja</b>

<b>08.00</b>  Kartu hari ini
<b>15.00</b>  Pengingat bila belum diisi
<b>16.30</b>  Pengingat bila belum diisi
<b>20.00</b>  Pengingat terakhir
<b>Jum 16.00</b>  Rekap minggu (Jumat)

Ubah di <code>config.toml</code> server bagian <code>[bot]</code>, lalu restart bot.
```

Tombol: [‹ Menu]

### 20. Bantuan (/help, /start)

Rich message:

```html
<p><b>monev bot mengingatkan dan merekap laporan Monev kamu.</b></p>
<p>/menu semua pilihan<br/>/status status laporan hari ini<br/>/rekap rekap minggu ini<br/>/rekap_bulan rekap bulan ini<br/>/ping cek bot masih aktif</p>
<p>Pengingat otomatis jam 15.00, 16.30, dan 20.00 WIB di hari kerja, hanya bila laporan belum diisi.<br/><i>Bot hanya membaca Monev. Laporan tetap ditulis dan dikirim dari laptop.</i></p>
```

Cadangan teks biasa:

```html
<b>monev bot mengingatkan dan merekap laporan Monev kamu.</b>

/menu semua pilihan
/status status laporan hari ini
/rekap rekap minggu ini
/rekap_bulan rekap bulan ini
/ping cek bot masih aktif

Pengingat otomatis jam 15.00, 16.30, dan 20.00 WIB di hari kerja, hanya bila laporan belum diisi.
<i>Bot hanya membaca Monev. Laporan tetap ditulis dan dikirim dari laptop.</i>
```

Tombol: [‹ Menu]

### 21. /ping

```html
Bot aktif sejak 16 Nov pukul 23.52 WIB.
```

Pesan dan tombol dari chat selain milik pemilik bot diabaikan.
