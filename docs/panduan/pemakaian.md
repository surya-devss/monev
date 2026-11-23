# Pemakaian harian

Belum memasang? Lihat [pasang.md](pasang.md) dulu.

Alurnya selalu sama: **cek status → tulis draft → validasi → baca ulang → kirim → verifikasi**. Laporan Monev
tidak bisa diedit setelah terkirim, jadi kirim hanya setelah draft dibaca ulang.

## Dengan agent (Claude Code atau Hermes)

```
/monev
```

Agent mengecek status, menyusun draft dari sumber yang ada (work records, MCP kantor, atau tanya-jawab), menjalankan
`monev validate`, lalu menampilkan draft. Balas `kirim` bila sudah benar. Agent menjalankan `monev kirim`, extension
mengisi form di Chrome-mu dan mengirim, lalu `monev status` memverifikasi.

| Perintah | Fungsi |
|---|---|
| `/monev` | laporan hari ini |
| `/monev revisi` / `/monev izin` | perbaikan yang diminta mentor / izin tidak hadir hari ini |
| `/monev latihan [YYYY-MM-DD]` | menyusun draft untuk latihan, **tidak pernah mengirim** |
| `/monev nilai` | mencari nilai perusahaan di situs resminya, lalu mengisi `[profil.nilai]` setelah kamu setujui |
| `/monev setup` | pasang dan sambungkan semuanya, dipandu agent (sesi, extension, sumber bahan, nilai) |
| `/monev status` atau `/monev:status` | cek status saja |

### Dari mana isi draft diambil

`/monev` memakai semua sumber yang tersambung ([cara menyambungkan](pasang.md#sumber-bahan-pilih-jalur)). Yang tidak
tersambung dilewati.

| Sumber | Butuh | Dipakai untuk |
|---|---|---|
| Commit, PR/MR, review | jalur Git: `gh`/`glab` login + `[sumber.git] penyedia` (`monev bukti`) | bukti hasil: "menyelesaikan…", "menggabungkan perubahan…" |
| Logtime | MCP kantor dengan tool logtime/timesheet | kerangka aktivitas hari itu, urut jam |
| Tiket | MCP kantor dengan tool tracker | nama pekerjaan yang jelas bagi mentor (nomor tiket tidak ditulis) |
| Aktivitas git | MCP kantor dengan tool commit/MR | bukti hasil: "menyelesaikan…", "merge perubahan…" |
| Kalender | MCP kantor dengan tool kalender | rutinitas yang juga ada di logtime langsung masuk draft (hapus bila tidak ikut); acara lain dan hari khusus (onboarding) ditanyakan dulu |
| Work records | folder catatan kerja harian ([format](../teknis/kontrak-sumber.md#jalur-d-folder-work-records)) | aktivitas, pembelajaran, dan kendala |
| Tanya-jawab | selalu ada | melengkapi yang kurang, terutama pembelajaran dan kendala |

Tiap kalimat di draft harus punya sumber. Nomor tiket, nama orang, link, dan IP dari sumber hanya jadi bahan dan
ditolak `monev validate` bila ikut tertulis.

### Kerja malam, akhir pekan, dan carry-over

| Kondisi | Yang terjadi di draft |
|---|---|
| Logtime hari ini berasal dari hari lain (`carry-over dari …` di work records) | tidak dihitung sebagai kerja hari ini |
| Kerja di luar jam sejak laporan terakhir yang belum tertulis di laporan mana pun | masuk laporan berikutnya: "melanjutkan … yang dikerjakan di luar jam kerja pada …", dan disebut di keraguan supaya bisa kamu hapus |
| Kerja yang sudah pernah dilaporkan | dilewati |

### Mengukur kualitas draft

Jalankan `/monev latihan <tanggal>` untuk hari yang laporannya sudah terkirim, lalu:

```bash
monev eval                         # skor semua draft latihan
monev eval --lewati 2026-11-16     # lewati hari yang sengaja berbeda dari sumber
```

Skor dihitung dari kegiatan dan pembelajaran. Kecocokan kendala ditampilkan saja karena kendala yang sama sering ditulis
dengan kata berbeda. Pakai skor untuk membandingkan hasil antar versi aturan, bukan sebagai nilai mutlak.

### Draft otomatis

Laptop bisa menyiapkan draft sendiri, jadi kamu tinggal memeriksa dan menyetujui. Pasang sekali:

```bash
monev jadwal pasang    # aktifkan jadwal
monev jadwal status    # lihat jadwal berikutnya
monev jadwal lepas     # matikan jadwal
```

Proses berjalan pukul 16.00, 17.00, 18.00, dan 19.00 WIB (`[jadwal] jam` di config). Jadwal yang terlewat saat laptop
mati atau tidur disusul setelah laptop menyala. Proses berhenti bila hari libur, laporan sudah terisi, atau draft hari
itu sudah ada. Bila bahan masih kosong, proses mencoba lagi di jam berikutnya.

| Pesan Telegram | Kapan muncul | Yang dilakukan |
|---|---|---|
| Draft laporan … sudah siap. | begitu draft tersimpan, biasanya jadwal 16.00 | jalankan `/monev`, baca draft, lalu balas `kirim` atau koreksi |
| Draft laporan … belum disusun. Bahan hari ini masih kosong… | jadwal terakhir (19.00) bila belum ada catatan kerja | lengkapi catatan kerja, lalu `/monev` |
| Draft laporan … gagal disusun otomatis. | jadwal terakhir (19.00) bila penyusunan gagal | jalankan `/monev` di laptop |
| Draft laporan … belum disusun. Sesi Monev di laptop habis… | jadwal pertama yang tidak bisa membaca Monev | jalankan `monev` di terminal untuk login |
| Draft laporan … belum disusun. Bentuk data Monev berubah… | saat itu juga | isi dari laptop dengan `/monev`, tool perlu diperbarui |
| Sesi Monev di laptop habis dalam … hari (…). | jadwal pertama tiap hari bila sisa ≤ 3 hari | `monev login` di terminal laptop |

Formatnya sama dengan pesan bot lain, contohnya ada di
[`format-pesan-telegram.md`](../teknis/format-pesan-telegram.md#22-kabar-draft-terjadwal). Pesan tidak memuat isi laporan. Proses terjadwal tidak bisa mengirim laporan, jadi laporan tetap terkirim hanya setelah
kamu membalas `kirim`. Untuk memakai MCP kantor, tulis nama lengkap tool yang hanya membaca di `[jadwal] alat_mcp`.

### Draft selalu bersih

| Kondisi | Yang terjadi pada `<draft_dir>/<tanggal>.json` |
|---|---|
| Laporan terkirim | langsung dihapus oleh `monev kirim` |
| Hasil kirim tidak pasti | disimpan sampai laporan terbukti masuk arsip |
| Tidak jadi dikirim | dihapus setelah 7 hari |
| Perbaikan dari mentor | disimpan sampai perbaikannya terkirim |

Draft `latihan-<tanggal>.json` tidak ikut dihapus karena dipakai `monev eval`. Salinan laporan yang terkirim tetap ada
di folder arsip.

## Tanpa agent (terminal saja)

```bash
monev                                    # sudah isi? hari libur?
monev draft                              # membuat template monev-<tanggal>.md, isi sendiri
monev validate monev-2026-11-17.md       # panjang 100–5000 karakter, data terlarang, kemiripan
monev kirim --uji monev-2026-11-17.md    # (pertama kali) isi form + cek lokasi, TIDAK dikirim
monev kirim monev-2026-11-17.md          # ketik `kirim` → extension mengisi dan mengirim → verifikasi
```

Izin dan perbaikan dari mentor memakai perintah yang sama, cukup isi draft-nya berbeda:

| Jenis | Isi draft JSON | Catatan |
|---|---|---|
| Hadir | `"status": "PRESENT"` + tiga kolom | lokasi asli wajib |
| Izin | `"status": "ON_LEAVE"`, `"leave_reason": "…"` (≥ 100 karakter) | hanya hari ini; tanpa lokasi |
| Perbaikan dari mentor | `"date": "<tanggal revisi>"`, `"revisi": true` + tiga kolom | hanya tanggal yang diminta revisi |

Draft teks: `# status: izin` lalu bagian `## Alasan tidak hadir`, atau `# revisi: ya` untuk perbaikan.

Persetujuan hanya di satu tempat: balasan `kirim` di chat agent (draft `"approved": true`) atau ketik `kirim` di
terminal. Extension tidak meminta persetujuan lagi.

## Popup extension

Klik ikon Monev Kirim di toolbar Chrome:

| Bagian | Isi |
|---|---|
| Atas | nama, posisi, perusahaan; tombol ↻ (muat ulang status), ? (cara pakai), ⚙ (Pengaturan) |
| Hari ini | belum diisi (batas kirim, revisi mentor, pengingat berikutnya, tombol **Buka form Monev**), sudah terkirim (kehadiran, lokasi, status mentor), atau libur |
| Revisi mentor | catatan mentor + tombol **Lihat di Riwayat**, bila ada |
| Sedang mengirim | progres saat `monev kirim` berjalan: buka form, isi, cek lokasi, kirim, pastikan masuk |
| Pengiriman terakhir | tanggal, jenis, hasil |
| Bawah | kesehatan: CLI terhubung, login Monev di Chrome ini beserta tanggal habisnya (kuning bila sisa ≤ 3 hari), jumlah jadwal pengingat |

Status tampil dari simpanan terakhir dulu, lalu diperbarui (otomatis bila lebih tua dari 5 menit). Bila CLI belum
tersambung, popup menampilkan langkah pemasangan.

## Pengingat di Chrome (tanpa bot)

Extension bisa memunculkan notifikasi desktop sendiri, tanpa server dan tanpa Telegram. Atur di popup → ⚙
**Pengaturan** (tersimpan di Chrome itu saja):

| Pengaturan | Bawaan | Keterangan |
|---|---|---|
| Aktif | ya | hanya hari kerja (libur dibaca dari Monev), hanya saat Chrome terbuka |
| Sapaan pagi | 08.00 | sapaan dengan nama + role dan tempat kerja + hari ini + batas laporan |
| Fokus hari ini | 09.00 | poin fokus kerja + satu nilai perusahaan per hari (bila `[profil.nilai]` diisi di `config.toml`) |
| Pengingat belum diisi | 15.00, 16.30, 20.00 | tidak muncul bila laporan sudah terkirim; yang terakhir tetap tampil sampai ditutup |
| Tunda pengingat | 30 menit | untuk tombol **Ingatkan lagi** |

Notifikasi pengingat punya tombol **Buka form** dan **Ingatkan … menit lagi**. Setelah `monev kirim` selesai, muncul
notifikasi hasilnya (terkirim, gagal, atau belum pasti). Jam mengikuti jam komputer. Bila Chrome baru dibuka lebih
dari 30 menit setelah suatu jadwal, jadwal itu dilewati. Bila sesi Monev di Chrome habis, muncul notifikasi untuk
login ulang, dan sapaan pagi didahului peringatan bila sesinya tinggal ≤ 3 hari. Tanggal habis dibaca dari cookie
sesi lewat izin `cookies` (hanya tanggalnya, nilainya tidak disimpan). Bila tampilan situs Monev berganti versi,
muncul notifikasi untuk mencoba `monev kirim --uji` sebelum kirim berikutnya. Tombol **Coba notifikasi** di Pengaturan, atau `monev extension coba pagi|fokus|ingat` dari terminal,
mengecek Monev sekarang dan menampilkan notifikasi itu.

**Teks notifikasi** tidak ditulis di extension. Teks bawaan ada di `monev/teks/bawaan.toml`; untuk mengganti
sebagian, tulis kunci yang sama di `config.toml` bagian `[pesan]`, lalu tekan **Muat ulang** di Pengaturan:

```toml
[pesan.ingat.pertama]
judul = "Jangan lupa laporan hari ini."

[pesan.fokus]
poin = ["Selesaikan satu task utama dulu.", "Catat hasil sambil jalan."]
```

Placeholder yang bisa dipakai: `{nama}` `{hari}` `{tanggal}` `{batas}` `{sisa}` `{alasan}`. Kunci yang salah ketik
diabaikan dan disebut di halaman Pengaturan.

Punya bot Telegram juga? Keduanya berjalan sendiri-sendiri; matikan salah satu bila terasa dobel.

## Rekap kehadiran

```bash
monev rekap            # sejak mulai magang
monev rekap --minggu   # Senin minggu ini sampai hari ini
monev rekap --bulan    # periode berjalan (bulan sejak mulai magang) sampai hari ini
```

Isinya: hari kerja, hadir, izin, absen, kehadiran ditolak mentor (dihitung absen), persetujuan mentor, sisa izin
dibayar, dan jarak ke batas peringatan. Hari libur nasional, libur daerah lokasi magang, dan `off_days` posisi
tidak dihitung.

## Daftar perintah

| Perintah | Fungsi |
|---|---|
| `monev` / `monev status [--json] [--no-login]` | status hari ini: hari kerja/libur, sudah isi, revisi mentor |
| `monev rekap [--minggu \| --bulan] [--dari --sampai] [--json]` | rekap kehadiran dan status peringatan |
| `monev draft [--hari-pertama]` | template laporan untuk ditulis sendiri |
| `monev validate FILE [--json] [--bebas-tanggal]` | cek draft sebelum dikirim |
| `monev eval [FOLDER] [--lewati D] [--json]` | skor draft latihan `<nama>-YYYY-MM-DD.json` terhadap laporan yang sudah terkirim, tanpa mengirim apa pun. Skor dihitung dari kegiatan dan pembelajaran |
| `monev kirim FILE [--uji]` | isi dan kirim lewat extension (`--uji`: isi saja, tidak dikirim) |
| `monev kirim --ping` | cek sambungan CLI ↔ extension ↔ Monev |
| `monev jadwal pasang\|status\|lepas` | atur draft otomatis di laptop |
| `monev jadwal jalan [--kering]` | jalankan proses terjadwal sekarang (`--kering`: tampilkan keputusan saja) |
| `monev extension install` | daftarkan jembatan Native Messaging (sekali) |
| `monev extension coba [pagi\|fokus\|ingat]` | tampilkan notifikasi extension sekarang |
| `monev hermes install\|uninstall [--profile …] [--symlink]` | pasang/lepas skill `/monev` di Hermes |
| `monev bot [--chat-id \| --coba kartu\|ingat\|status\|rekap\|menu\|help]` | bot Telegram ([panduan](bot-telegram.md)) |
| `monev init [--force]` | buat config sekarang (opsional, `monev` membuatnya otomatis) |
| `monev login` / `monev logout` | login ulang / hapus sesi CLI |
| `monev doctor [--tanpa-sesi] [--json]` | diagnosa config, Chrome, extension, sesi, umur refresh token, dan jalur sumber bahan A–D |
| `monev sumber cari [--akar DIR]` | temukan folder work records (dikenali dari isinya) |
| `monev sumber baca [--tanggal D] [--json]` | bahan work records satu tanggal: aktivitas, keputusan/jebakan, judul, klien, status, carry-over, dan kerja di luar jam yang belum dilaporkan |
| `monev sumber siap [--tanggal D] [--logtime N] [--json]` | kesiapan bahan: `siap`, `tipis`, atau `kosong`, plus peringatan bila repo tertinggal atau belum di-commit |
| `monev bukti [--tanggal D] [--json]` | aktivitas Git milikmu hari itu (commit, PR/MR, review), sudah dibersihkan |
| `monev config [--edit] [--json]` | lihat atau ubah config |

Kode keluar: `0` berhasil, `1` gagal, `2` perlu login. `--no-login` artinya jangan membuka jendela login (untuk
bot dan skrip).

## Aturan isi laporan

`monev validate` menolak draft yang:

- kurang dari 100 atau lebih dari 5000 karakter per kolom;
- memuat alamat IP, URL, nomor tiket/MR, hash commit, path berkas, email, token, atau nomor CVE;
- menyebut nama di `jangan_disebut` (nama mentor otomatis masuk);
- menyebut nama proyek atau klien dari sumber, karena nama itu harus ditulis umum seperti "aplikasi klien";
- memakai tag proyek yang ada di `lewati_proyek`.

Nama teknologi dan standar seperti Grafana, Wazuh, GitLab, dan ISO 27001 tetap boleh disebut.

Draft tetap bisa dikirim, tetapi mendapat peringatan bila:

- terlalu mirip dengan laporan terdahulu;
- satu butir aktivitas lebih dari 250 karakter;
- pembuka pembelajaran sama dengan laporan terakhir;
- menyebut batasan alat bantu kerja;
- tampak memuat detail temuan keamanan, seperti port yang terbuka atau jumlah dan tingkat temuan.

Aturan lengkapnya ada di [`monev/laporan/aturan.toml`](../../monev/laporan/aturan.toml). Gaya tulisan dan contoh
laporan yang lolos: [`plugin/skills/monev/references/writing-guide.md`](../../plugin/skills/monev/references/writing-guide.md).

## Config

`config.toml` di root repo (gitignored), dibuat otomatis saat pertama kali menjalankan `monev`, dengan isi yang sama
seperti [`config.example.toml`](../../config.example.toml).

| Isi | Dari mana |
|---|---|
| posisi dan perusahaan | profil Monev saat login pertama |
| `jangan_disebut` | nama mentor otomatis; tambahkan nama klien/proyek yang tidak boleh muncul |
| `rutinitas` | kosong; isi kegiatan rutin bila ingin disarankan saat menyusun draft (selalu dikonfirmasi) |
| `[laporan] lewati_proyek` | kosong; proyek yang tidak masuk laporan, misalnya proyek pribadi |
| `[laporan] nama_boleh` | kosong; nama yang boleh disebut walau tertangkap saringan nama |
| `[laporan] jam_selesai` | `17:00`; kerja sesudah jam ini dianggap di luar jam kerja |
| `[sumber.workrecords] dir` | kosong (mode tanya-jawab); diisi sendiri, atau dari env `MONEV_WORK_RECORDS` saat config dibuat |
| `[sumber.git] penyedia`, `gitlab_host` | kosong; `["github"]` dan/atau `["gitlab"]` ([cara](pasang.md#jalur-b-git)) |
| `[sumber.mcp] awalan_tool` | kosong; diisi sendiri bila memakai MCP kantor ([cara](pasang.md#sumber-bahan-pilih-jalur)) |
| `[profil.nilai]` | kosong; `semboyan` + `poin = ["Nama nilai: cara menerapkannya", …]` untuk bagian fokus di kartu hari ini (bot, 08.00) dan notifikasi fokus (extension, 09.00), satu poin per hari. Agent bisa mencarikan dari situs resmi perusahaanmu lalu mengisinya setelah kamu setujui: `/monev nilai` |

Config lama tanpa bagian `[laporan]` tetap terbaca dengan nilai bawaan. Lihat dengan `monev config`, ubah dengan
`monev config --edit`. Lokasi lain: env `MONEV_CONFIG`.
Email dan nomor telepon tidak pernah disimpan.
