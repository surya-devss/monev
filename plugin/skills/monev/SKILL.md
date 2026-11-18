---
name: monev
description: "Laporan harian Monev MagangHub: cek status, susun draft dari sumber yang tersedia, validasi, minta review, lalu kirim lewat extension monev (monev kirim) setelah user membalas `kirim`. Use when the user mentions: monev, maganghub, laporan harian magang, isi laporan hari ini, presensi magang, revisi mentor monev, izin monev."
version: 0.2.0
author: monev contributors
license: MIT
argument-hint: "[setup | status | latihan [YYYY-MM-DD] | revisi | izin | nilai]"
---

Skill ini dipakai Claude Code (plugin `monev`) dan Hermes (bundle `/monev`); semua aksi lewat CLI `monev`, jadi langkahnya sama di keduanya. Bagian bertanda *(Claude Code)* dilewati di agent lain.

Argumen `status` → jalankan `monev status --no-login` (read-only), tampilkan ringkasannya, lalu berhenti. *(Claude Code: boleh memakai skill `monev:status`.)*

Argumen `setup` → pasang dan sambungkan semuanya, dipandu: ikuti `references/setup.md` langkah demi langkah, lalu berhenti (tidak menyusun laporan).

Argumen `nilai` → isi nilai perusahaan untuk pesan "fokus hari ini" (bot & extension):
1. `monev config --json` → `perusahaan` (diisi otomatis dari profil Monev; kosong → minta user menjalankan `monev status` dulu, berhenti) dan `nilai` (sudah terisi → tampilkan, tanya mau diganti atau tidak).
2. Cari nilai inti/budaya perusahaan itu di **situs resmi perusahaan** (halaman tentang kami / core value / budaya); sumber lain hanya bila situs resmi tidak memuatnya, dan sebutkan itu. Nama nilai sering berupa **gambar** (teks halaman hanya memuat judul/semboyan; uji 17 Nov): ambil URL gambar di bagian itu dari HTML, unduh ke folder sementara, lalu baca gambarnya. Tidak ketemu → katakan apa adanya, tawarkan user menulis sendiri; **jangan mengarang nilai**.
3. Tampilkan usulan: `semboyan` (bila ada), daftar nilai persis seperti di sumber, dan satu kalimat penerapan per nilai (tulisan agent, ditandai "tulisan sendiri, bukan kutipan resmi"), plus URL sumber.
4. Hanya setelah user setuju: tulis ke `config.toml` (path dari `monev config --json`), bagian `[profil.nilai]`: `semboyan = "…"`, `poin = ["Nilai: penerapan", …]`. Ubah bagian itu saja.
5. `monev config` → baris *nilai* terisi. Ingatkan: bot di server membaca config di servernya sendiri (lihat `docs/panduan/bot-telegram.md`); extension mengambil nilai lewat `monev-native-host` saat notifikasi fokus berikutnya.

Argumen `latihan [tanggal]` → **mode latihan**: jalankan langkah 1–4 untuk tanggal itu (default hari ini) walaupun laporan sudah terisi atau hari libur, tulis draft ke `<draft_dir>/latihan-<D>.json`, validasi dengan `monev validate --bebas-tanggal`, tampilkan draft + sumber + keraguan. **Langkah 5 (kirim) tidak pernah dijalankan** di mode ini, walaupun user membalas `kirim`; sarankan `/monev` biasa di hari kerja berikutnya. Di akhir, tampilkan juga sumber mana yang terdeteksi/terpakai dan apa yang kurang — untuk menilai kualitas skill.

# /monev — laporan harian Monev MagangHub

Tujuan: laporan hari ini terkirim tepat waktu, **jujur**, jelas bagi mentor, dan **selalu di-review user sebelum dikirim**. Laporan Monev tidak bisa diedit setelah terkirim, dan mentor bisa menolak kehadiran bila isinya tidak sesuai kenyataan (dihitung absen).

Rujukan (baca saat langkahnya tiba):
- `references/sources.md` — cara mengambil bahan per sumber (MCP kantor, Git, work records, checklist)
- `references/setup.md` — `/monev setup`: deteksi dan sambungkan jalur sumber, extension, nilai perusahaan
- `references/writing-guide.md` — gaya tulisan, batas data, contoh laporan yang lolos

## Aturan mutlak

1. **Tidak mengirim apa pun** sebelum user membalas `kirim` untuk draft yang **sedang ditampilkan**. Draft berubah → minta `kirim` lagi.
2. **Tidak mengarang.** Setiap kalimat punya sumber (entri logtime, tiket, commit, kalender, baris work record, atau jawaban user). Rutinitas yang tercatat di logtime **dan** kalender pada hari D langsung masuk draft sebagai satu butir, lalu disebut di keraguan ("hapus bila tidak ikut"). Kandidat lain (rutinitas yang hanya ada di satu sumber, acara kalender non-rutin, kegiatan hari pertama, atau rutinitas di hari yang punya acara khusus seharian seperti onboarding/pelatihan) hanya masuk setelah dikonfirmasi user.
3. **Tidak menyentuh kredensial.** Tidak mengetik password, tidak menampilkan token/cookie, tidak menampilkan kontak orang lain.
4. **Lokasi selalu asli** dari Chrome user. Tidak membuat koordinat.
5. **Tidak pernah memilih "Tidak Hadir Tanpa Keterangan"** dan tidak pernah retry kirim secara buta.
6. MCP (server mana pun) hanya dipakai **read-only**. Tools yang menulis (`create_*`, `update_*`, `delete_*`, `comment_*`, `start_timer`, `stop_timer`, `record_event`, `set_*`, `assign_*`) dilarang.

## Langkah

### 0. Prasyarat
Jalankan `monev --version`. Tidak ada → hentikan, beri tahu user cara pasang (`uv tool install -e <repo monev>`, lihat README repo).

### 1. Status
```bash
monev status --json --no-login
```
- Exit `2` → sesi belum ada/mati. Minta user menjalankan `monev` di **terminal biasa** (jendela login terbuka sendiri), lalu ulangi. Berhenti.
- `magang_aktif: false` → laporkan, berhenti.
- `libur_nasional` / `libur_posisi` → "hari ini libur, tidak wajib isi", berhenti (kecuali user minta lain).
- `sudah_isi: true` → tampilkan ringkasan (status kehadiran, state log), berhenti.
- `perlu_revisi` tidak kosong → tawarkan alur revisi (bagian Revisi) sebelum laporan hari ini.
- Catat `tanggal` (= D) dan `hari_pertama`.

Lalu `monev config --json` → `posisi`, `perusahaan`, `rutinitas`, `workrecords_dir`, `workrecords_ada`, `mcp_awalan_tool`, `git_penyedia`, `draft_dir`.

### 2. Kumpulkan bahan
Deteksi sumber yang tersedia dan pakai **semuanya**, read-only (detail: `references/sources.md`):

| Sumber | Tersedia bila |
|---|---|
| MCP kantor (logtime, kalender, aktivitas git, tiket) | `mcp_awalan_tool` tidak kosong **dan** tool yang cocok ada di sesi |
| Git (GitHub/GitLab) | `git_penyedia` tidak kosong → `monev bukti --tanggal D --json` |
| Work records | `workrecords_ada: true` |
| Checklist / cerita | selalu (wajib bila sumber di atas tidak ada atau bahan tidak cukup) |

Tidak ada satu pun sumber otomatis → setelah laporan selesai, sarankan sekali `/monev setup` untuk menyambungkan sumber.

Jenis hari menentukan pertanyaan: `hari_pertama` → kandidat onboarding / pengenalan tim / mentoring / setup akun; hari setelah libur → "melanjutkan apa?"; hari biasa → rutinitas dari config + kalender.

Bila bahan sudah cukup dari sumber otomatis, **jangan wawancara**; tanyakan paling banyak 1–2 hal yang benar-benar kurang (mis. aktivitas tanpa hasil). Bila tidak ada sumber otomatis: tampilkan checklist kandidat + satu pertanyaan wajib "Pekerjaan utama hari ini apa, dan hasilnya apa?".

### 3. Susun & validasi
Ikuti `references/writing-guide.md`. Tulis draft JSON ke `<draft_dir>/<D>.json`:

```json
{"date": "D", "status": "PRESENT", "activity_log": "…", "lesson_learned": "…", "obstacles": "…",
 "sources": ["logtime:…", "tiket:…", "git:…", "kalender:…", "record:…", "jawaban:…"], "approved": false}
```

Lalu `monev validate <file>`. Ada ✗ → perbaiki teks, ulangi sampai lolos. Peringatan (!) → perbaiki bila masuk akal, sisanya sebutkan ke user.

### 4. Review
Tampilkan ke user:
- tiga field apa adanya (persis yang akan dikirim) + jumlah karakter,
- daftar sumber singkat,
- keraguan material (maks 3), mis. "rutinitas X belum dikonfirmasi",
- penutup: "Balas `kirim` untuk mengirim, atau koreksi."

Koreksi → ubah file, `monev validate` lagi, tampilkan ulang.

### 5. Kirim (hanya setelah `kirim`)
Ubah `"approved": true` di file draft. Pengirim **hanya extension monev**; agent tidak pernah mengisi form Monev sendiri lewat alat browser apa pun.

1. `monev kirim --ping` lolos → `monev kirim <file>`. Extension mengisi form di Chrome user, mengecek lokasi asli, lalu mengirim; CLI memverifikasi lewat `monev status`. Pada kiriman pertama, jalankan `monev kirim --uji <file>` dulu (isi + lokasi, tanpa centang/kirim), minta user melihat form, baru `monev kirim <file>`. Hasil `tidak_pasti` → **jangan kirim ulang**, lanjut verifikasi.
2. `--ping` gagal → tampilkan pesan perbaikannya (extension belum terpasang, Chrome belum dibuka, belum login Monev) dan bantu user memperbaikinya (`docs/panduan/pasang.md` langkah 3–4), lalu ulangi langkah 1. Bila tidak bisa diperbaiki hari itu → berikan teks tiga field untuk ditempel user sendiri di form Monev, lalu lanjut ke verifikasi setelah user bilang sudah.

Extension menangani ketiga jenis draft: hadir, izin (`"status": "ON_LEAVE"`), dan perbaikan dari mentor (`"revisi": true`).

### 6. Verifikasi
`monev status --no-login` → harus `sudah isi`, kehadiran `PRESENT/SUBMITTED`, log `SUBMITTED`, panjang sama dengan draft (arsip tersimpan otomatis). Laporkan hasil ke user. Gagal/tidak yakin → cek Riwayat; **jangan kirim ulang** tanpa bukti belum masuk.

## Revisi dari mentor
`perlu_revisi` berisi tanggal + catatan mentor. Tampilkan catatan mentor dan isi lama (lihat di Riwayat). Susun perbaikan dari sumber tanggal itu, tulis draft dengan `"date": "<tanggal revisi>", "revisi": true` + tiga field → `monev validate` (tanggal lampau diterima untuk revisi) → review → `kirim` → `monev kirim <file>` (extension membuka panel "Perbaiki laporan" tanggal itu, mengisi, mengirim; status jadi `REVISION_SUBMITTED`). Kehadiran tidak berubah dan lokasi tidak dikirim. Pada revisi pertama lewat extension, jalankan `monev kirim --uji <file>` dulu.

## Izin
Hanya bila user sendiri bilang izin/tidak hadir, dan hanya untuk **hari ini** (Monev tidak menerima izin tanggal lain). Draft `{"date": "<hari ini>", "status": "ON_LEAVE", "leave_reason": "…≥100 karakter…"}` → validate → review → `kirim` → `monev kirim <file>` (extension memilih "Tidak Hadir Dengan Keterangan", mengisi alasan, mengirim; lokasi tidak dikirim). Tidak pernah "Tanpa Keterangan". Ingatkan: izin ke-4 dst. per periode tidak dibayar. Pada izin pertama lewat extension, jalankan `monev kirim --uji <file>` dulu.
