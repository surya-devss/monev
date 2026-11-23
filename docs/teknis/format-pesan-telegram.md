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

### 10b. Laporan disetujui mentor

Sekali per tanggal. Tanggal yang ketahuan disetujui di pengecekan yang sama digabung jadi satu pesan. Saat state bot
belum mencatat persetujuan (bot baru diperbarui), persetujuan yang ada hanya dicatat.

```html
<b>Laporan 17 dan 18 Nov disetujui mentor.</b>
Total disetujui 3 dari 4 laporan terkirim.
```

### 11. Kehadiran ditolak mentor

Sekali per tanggal.

```html
<b>Kehadiran 14 Nov ditolak mentor.</b>
Hari itu dihitung absen. Absen periode ini sekarang 1 (peringatan di 7).
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

Satu pesan per hari, diedit di setiap percobaan. Kalimat kedua mengikuti penyebabnya (`[bot.gangguan.sebab]`).

Sesi habis (dialihkan ke halaman login, atau API menjawab 401/403):

```html
<b>Bot belum bisa membaca Monev.</b>
Sesi Monev di server habis, perlu login ulang. Pengingat ditunda dulu.
<i>Dicoba 15.00 dan 16.30. Berikutnya 18.00.</i>
```

Tombol: [Coba sekarang] · [Cara memperbarui]

Monev tidak bisa dihubungi (halaman tidak siap, API 5xx, jaringan):

```html
<b>Bot belum bisa membaca Monev.</b>
Situs Monev tidak bisa dihubungi atau terlalu lambat. Biasanya pulih sendiri, pengingat ditunda dulu.
<i>Dicoba 15.00 dan 16.30. Berikutnya 18.00.</i>
```

Bentuk data berubah (field wajib hilang atau API 404):

```html
<b>Bot belum bisa membaca Monev.</b>
Bentuk data Monev berubah (/users/me/home tanpa field is_holiday). Bot berhenti dulu supaya tidak salah kabar, tool perlu diperbarui.
<i>Dicoba 15.00 dan 16.30. Berikutnya 18.00.</i>
```

Dua jenis terakhir hanya punya tombol [Coba sekarang]. Penyebab lain memakai kalimat "Penyebabnya … Pengingat ditunda dulu."

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

Tombol: [Status hari ini] · [Rekap minggu] / [Rekap periode] · [Jadwal pengingat] / [Bantuan]

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
<p>Periode 1: absen 0 (peringatan di 7), izin 1 dari 3 yang dibayar.<br/>Aman, belum mendekati batas peringatan.</p>
```

Cadangan teks biasa:

```html
<b>Minggu ini hadir 1 dari 2 hari.</b>
16–20 Nov 2026

• Sen 16 · hadir · disetujui
• Sel 17 · izin · menunggu

Periode 1: absen 0 (peringatan di 7), izin 1 dari 3 yang dibayar.
Aman, belum mendekati batas peringatan.
```

Tombol: [‹ Menu] · [Rekap periode ›]

### 18. Rekap periode

Periode = satu bulan sejak tanggal mulai magang (16 Nov–15 Des, 16 Des–15 Jan, …). Dikirim pukul 16.00 di hari kerja
terakhir periode, atau lewat /rekap_bulan dan tombol. Absen dan izin dibayar dihitung per periode, absen
berturut dihitung lintas periode.

Rich message:

```html
<p><b>Periode 1, hadir 1 dari 2 hari.</b><br/>16 Nov – 15 Des 2026 · 2 hari kerja sampai hari ini</p>
<table bordered compact><tr><td><b>Hadir</b></td><td>1</td></tr>
<tr><td><b>Izin</b></td><td>1 dari 3 yang dibayar</td></tr>
<tr><td><b>Absen</b></td><td>0 (peringatan di 7)</td></tr>
<tr><td><b>Berturut</b></td><td>absen 0 (peringatan di 3)</td></tr>
<tr><td><b>Mentor</b></td><td>1 disetujui, 1 menunggu, 0 perlu revisi</td></tr>
</table>
<p>Aman, belum mendekati batas peringatan.</p>
```

Cadangan teks biasa:

```html
<b>Periode 1, hadir 1 dari 2 hari.</b>
16 Nov – 15 Des 2026 · 2 hari kerja sampai hari ini

<b>Hadir</b>  1
<b>Izin</b>  1 dari 3 yang dibayar
<b>Absen</b>  0 (peringatan di 7)
<b>Berturut</b>  absen 0 (peringatan di 3)
<b>Mentor</b>  1 disetujui, 1 menunggu, 0 perlu revisi

Aman, belum mendekati batas peringatan.

Izin lewat jatah ditulis "4, 1 tidak dibayar". Kehadiran yang ditolak mentor ikut dihitung absen dan disebut di baris
Absen ("…, 1 di antaranya ditolak mentor").
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
<p>/menu semua pilihan<br/>/status status laporan hari ini<br/>/rekap rekap minggu ini<br/>/rekap_bulan rekap periode berjalan<br/>/ping cek bot masih aktif</p>
<p>Pengingat otomatis jam 15.00, 16.30, dan 20.00 WIB di hari kerja, hanya bila laporan belum diisi.<br/><i>Bot hanya membaca Monev. Laporan tetap ditulis dan dikirim dari laptop.</i></p>
```

Cadangan teks biasa:

```html
<b>monev bot mengingatkan dan merekap laporan Monev kamu.</b>

/menu semua pilihan
/status status laporan hari ini
/rekap rekap minggu ini
/rekap_bulan rekap periode berjalan
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

### 22. Kabar draft terjadwal

Dikirim dari laptop oleh `monev jadwal jalan`, bukan dari bot di server, dengan susunan yang sama
(`pesan.draft()`, teks `[bot.draft.*]`). Satu jenis sekali per hari, tanpa tombol, tanpa isi laporan.

Draft siap, begitu draft tersimpan:

```html
<b>Draft laporan 19 Nov sudah siap.</b>
Disusun otomatis dari catatan kerja, belum dikirim.
Periksa dan kirim dari laptop dengan <code>/monev</code>.
```

Bahan kosong, jadwal terakhir:

```html
<b>Draft laporan 19 Nov belum disusun.</b>
Bahan hari ini masih kosong sampai jadwal terakhir.
Lengkapi catatan kerja, lalu isi dari laptop dengan <code>/monev</code>.
```

Gagal disusun, jadwal terakhir:

```html
<b>Draft laporan 19 Nov gagal disusun otomatis.</b>
Prosesnya gagal atau hasilnya tidak lolos pemeriksaan.
Isi dari laptop dengan <code>/monev</code>.
```

Sesi Monev di laptop habis:

```html
<b>Draft laporan 19 Nov belum disusun.</b>
Sesi Monev di laptop habis, jadi status hari ini tidak terbaca.
Login ulang dengan menjalankan <code>monev</code> di terminal laptop.
```

Bentuk data Monev berubah, dikirim saat itu juga:

```html
<b>Draft laporan 19 Nov belum disusun.</b>
Bentuk data Monev berubah, jadi proses berhenti supaya tidak salah membaca status.
Isi dari laptop dengan <code>/monev</code> sambil menunggu tool diperbarui.
```

Sesi Monev di laptop sisa ≤ 3 hari, sekali per hari:

```html
<b>Sesi Monev di laptop habis dalam 2 hari (19 Des).</b>
Setelah itu draft otomatis dan <code>monev status</code> berhenti.
Login ulang dengan <code>monev login</code> di terminal laptop.
```

### 23. Masa magang

Dari tanggal selesai di profil Monev. Satu kabar per ambang (H-30, H-7, hari terakhir). Bila bot sempat mati
melewati beberapa ambang, cukup kabar ambang terdekat.

```html
<b>Masa magang selesai dalam 30 hari (15 Mei 2027).</b>
Di bulan terakhir, isi survei yang diminta Monev supaya laporan tidak ditolak.
```

```html
<b>Masa magang selesai dalam 7 hari (15 Mei 2027).</b>
Tetap kirim laporan setiap hari kerja sampai hari terakhir.
```

```html
<b>Hari ini hari terakhir magang (15 Mei 2027).</b>
Jangan lupa kirim laporan hari ini. Terima kasih sudah konsisten sampai akhir.
```

Saat Monev mengubah magang dari aktif ke tidak aktif, sekali:

```html
<b>Masa magang sudah selesai.</b>
Monev menandai magang tidak aktif. Pengingat dan rekap berhenti.
```

Bila itu terjadi sebelum tanggal selesai:

```html
<b>Monev menandai magang tidak aktif sebelum tanggal selesai (15 Mei 2027).</b>
Pengingat dan rekap berhenti. Tanyakan ke mentor atau admin program bila ini keliru.
```

### 24. Situs Monev diperbarui

Nama file utama frontend Monev (`/_nuxt/<hash>.js`) berganti, artinya situs di-deploy ulang. Pembacaan pertama hanya
mencatat. Teks dari `[web]`, sama dengan notifikasi desktop extension.

```html
<b>Tampilan situs Monev baru saja diperbarui.</b>
Membaca status masih jalan, tetapi form laporan bisa saja ikut berubah.
Sebelum kirim berikutnya, coba dulu dengan <code>monev kirim --uji</code>.
```
