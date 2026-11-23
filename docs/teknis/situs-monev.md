# Aplikasi Monev MagangHub — fakta teknis

Web: `https://monev.maganghub.kemnaker.go.id` · API: `https://monev-api.maganghub.kemnaker.go.id/api/v1`
Sumber: `uji` = dicoba langsung · `bundle` = dibaca dari JS aplikasi · `panduan` = Panduan Peserta/Mentor v2026.10.03 (ikut di bundle).

## Aturan program

| Aturan | Sumber |
|---|---|
| Kehadiran + laporan harian dikirim bersamaan, hanya untuk **hari ini** (waktu lokasi penempatan), batas 23.59 | panduan, uji |
| Laporan **tidak bisa diedit** setelah terkirim, kecuali mentor meminta perbaikan (`NEEDS_REVISION`, tanpa batas waktu) | bundle, panduan |
| Mentor: setujui / setujui + minta perbaikan / **tolak kehadiran** (data tidak sesuai → dihitung absen). Keputusan awal maks 14 hari | panduan |
| **Periode = satu bulan sejak tanggal mulai magang**, dipakai untuk gaji dan absen. Mulai 16 Nov → periode 1 = 16 Nov–15 Des, periode 2 = 16 Des–15 Jan, dan seterusnya | pemilik (19 Nov), belum dicek ke panduan |
| Peringatan absen: 3 hari kerja berturut / 7 per periode. Nonaktif: 5 berturut / 10 per periode | panduan |
| Izin: 3 hari pertama per periode dibayar; ke-4 dst. tidak dibayar, tidak dihitung peringatan. "Tanpa Keterangan" langsung final | panduan |
| Libur: hari libur nasional + `off_days` posisi (mis. `["SATURDAY","SUNDAY"]`) tidak wajib isi | uji |
| Bulan terakhir: survei belum diisi bisa membuat laporan ditolak | panduan |
| Ada Kurikulum, Fokus Pembelajaran (mentor), evaluasi bulanan 8 aspek | panduan |
| Jaringan putus / >20 dtk: cek Riwayat sebelum mencoba lagi | panduan, bundle |

## Login & sesi

| Fakta | Sumber |
|---|---|
| SSO `account.kemnaker.go.id/auth/login` (`#username`, `#password`, csrf, tanpa captcha) | uji |
| Sesi melekat pada **profil Chrome**; profil lain = belum login | uji |
| Pengalihan ke SSO terjadi lewat JavaScript (tunggu ±3 dtk) | uji |
| Access token di `sessionStorage.monev_access_token`, JWT RS512, ttl 6 jam, klaim `fingerprint` | uji |
| Setiap request: `credentials: "include"` (cookie) + `Authorization: Bearer` + `X-Frontend-Build-ID` | bundle |
| Refresh: `POST /auth/refresh` memakai cookie `monev_refresh_token` (±30 hari) | bundle, uji |
| **Masa berlaku refresh token bergeser saat dipakai**: profil CLI login 17 Nov berlaku s.d. 17 Des, setelah dipakai harian `monev doctor` 19 Nov menunjukkan s.d. 19 Des. Sesi baru habis bila tidak dipakai ±30 hari. Batas maksimum mutlak (bila ada) belum diketahui | uji #56 |
| Tidak ada API publik/API key untuk peserta | bundle |
| Frontend Nuxt. File utama `<script type="module" src="/_nuxt/<hash>.js">` berganti setiap situs di-deploy ulang, dipakai bot dan extension sebagai penanda versi situs | uji #57 |
| Field yang dipakai bot dan CLI (`WAJIB` di `monev/portal/api.py`) ada semua di respons 19 Nov. Bila salah satu hilang, pembacaan berhenti dengan "bentuk data Monev berubah" | uji #57 |

Konsekuensi: semua akses API dijalankan **dari dalam halaman Monev di Chrome**, bukan curl/requests.

**Tiga sesi terpisah.** Masing-masing login sendiri dan habis sendiri.

| Sesi | Dipakai oleh | Tempat melihat tanggal habis | Peringatan sebelum habis |
|---|---|---|---|
| Profil Chrome CLI di laptop (`~/.local/share/monev/chrome-profile`) | `monev status`, `monev rekap`, draft terjadwal | `monev doctor` | Telegram dari draft terjadwal bila sisa ≤ 3 hari |
| Salinan profil CLI di server (volume `monev_data`) | bot Telegram | `/status` di bot (baris Sesi Monev) | kartu 08.00 bila sisa ≤ 3 hari |
| Chrome harian | extension: isi form, lokasi, pengingat desktop | popup extension, baris Login Monev | notifikasi bersama sapaan pagi bila sisa ≤ 3 hari |

## API

| Method | Path | Isi | Sumber |
|---|---|---|---|
| GET | `/users/me` | `id`, `job_role`, `internship_company`, `mentor_name` (+ kontak mentor — jangan disimpan), `off_days`, `internship_start_date/end_date`, `participant_status`, `internship_location_province_code/regency_code` | uji |
| GET | `/holidays` | seluruh daftar libur: `date`, `name`, `type` (`NATIONAL`/`REGIONAL`), `scope` (`NATIONAL`/`PROVINCE`), `province_code`, `regency_code`; filter tanggal diabaikan | uji |
| GET | `/users/me/home` | `{date, active_internship, is_holiday, is_scheduled_off_day, has_attendance}` | uji |
| GET | `/attendances?participant_id=&start_date=&end_date=` | `status`, `approval_status`, `latitude`, `longitude` | uji |
| GET | `/daily-logs?participant_id=&date=` atau `&start_date=&end_date=` | 3 field, `state`, `reviewer_notes` | uji |
| GET | `/system/time`, `/attendances/review-policy` | waktu server, kebijakan | bundle |
| POST | `/attendances/with-daily-log` | Hadir + laporan (dipicu form) | bundle, uji (lewat form) |
| POST | `/attendances` | izin / tidak hadir (`leave_reason`, `participant_id`) | bundle |
| PUT | `/daily-logs/{id}` | perbaikan, `state: REVISION_SUBMITTED` | bundle |

State: attendance `SUBMITTED / APPROVED / REJECTED`, status `PRESENT / ON_LEAVE / ABSENT / DAYOFF`.
Daily log `DRAFT / SUBMITTED / COMPLETED / NEEDS_REVISION / REVISION_SUBMITTED / APPROVED / REJECTED`.

## Form laporan (`/dashboard/riwayat?action=today`)

| Bagian | Aturan | Sumber |
|---|---|---|
| Kehadiran | Hadir / Tidak Hadir Dengan Keterangan / Tanpa Keterangan | uji |
| Uraian aktivitas · Pembelajaran yang diperoleh · Kendala yang dialami | masing-masing 100–5000 karakter (`String.length`, UTF-16) | bundle, uji |
| Alasan tidak hadir | ≥100 karakter | bundle |
| Lokasi | panduan mewajibkan izin lokasi; frontend mengirim koordinat bila ada | panduan, uji |
| Pernyataan "Saya menyatakan telah meninjau…" | wajib dicentang; tombol "Simpan dan Kirim" nonaktif sebelumnya | uji |
| Mengisi `textarea` saja tidak dikenali | perlu event `input`/`blur` | uji |
| Pop-up "Aktifkan notifikasi perangkat" | muncul di dashboard | uji |
| Daftar bernomor & baris baru | tampil rapi di detail | uji |

## Langkah mengisi form

Urutan yang dijalankan extension (`extension/isi-form.js`) untuk laporan hadir. Terbukti lewat kiriman pertama
2026-11-16 (uji #1–12); izin dan revisi memakai panel yang sama (lihat *Belum diketahui*).

1. Buka `/dashboard`, tunggu ±3 dtk. URL pindah ke `account.kemnaker.go.id/auth/login` → berhenti: user login sendiri
   di Chrome itu (sesi melekat per profil). Email/password tidak pernah diketik oleh alat.
2. Pop-up "Aktifkan notifikasi perangkat" → **Nanti saja**.
3. Cek belum isi: `GET /users/me/home` → `has_attendance: true` berarti sudah terisi, berhenti. Nilai token tidak
   pernah dikembalikan atau dicetak.
4. Buka form: `/dashboard/riwayat?action=today` (tombol **Isi Laporan Hari Ini**). Panel `Tambah laporan · <tanggal>`,
   Kehadiran = **Hadir**.
5. Isi tiga textarea (placeholder "Tulis uraian aktivitas…", "Tulis ilmu/pembelajaran…", "Tulis kendala/hambatan…").
6. Picu event `input` dan `blur` di tiap textarea; tanpa ini form masih menganggap kosong.
7. Periksa: nilai tiap textarea **sama persis** dengan draft; tidak ada pesan validasi (class `v-input--error`);
   panel lokasi "Koordinat ditemukan". Lokasi belum ada → **Tambahkan lokasi**; masih gagal → berhenti, user
   mengizinkan lokasi di Chrome (sekali per profil). Koordinat tidak pernah dibuat.
8. Centang "Saya menyatakan telah meninjau…" → **Simpan dan Kirim** aktif → klik sekali.
9. Tunggu ±5 dtk: detail "Menunggu Persetujuan". Snackbar "membutuhkan waktu lebih lama" → tunggu, jangan klik lagi.
10. Verifikasi: attendance hari itu `PRESENT`/`SUBMITTED` dengan `latitude/longitude`; daily log `SUBMITTED`; panjang
    tiga field = draft. CLI lalu menjalankan `monev status` (arsip).

Gagal setelah klik kirim → cek langkah 10 dulu; sudah masuk = selesai, belum masuk = laporkan, jangan kirim ulang
otomatis. Selektor tidak ditemukan (aplikasi berubah) → berhenti dan laporkan.

## Belum diketahui
- Batas izin. Pemilik pernah mendengar izin 5 hari dalam satu periode membuat peserta dikeluarkan, sedangkan panduan
  v2026.10.03 hanya menyebut izin ke-4 dan seterusnya tidak dibayar dan tidak dihitung peringatan (angka 5 di panduan
  untuk absen berturut). Perlu dipastikan ke mentor atau admin; bila benar, rekap perlu menghitung batas izin juga.
- Perilaku backend bila Hadir tanpa koordinat (tidak akan dipakai untuk melewati prosedur).
- Kapan state `DRAFT` muncul (frontend selalu mengirim `SUBMITTED`).
- Izin dan revisi belum pernah dikirim sungguhan. Bentuk form dari bundle (`DMLWG_CQ.js`, 17 Nov 2026):
  - satu panel untuk semua jenis: judul `Tambah laporan` / `Perbaiki laporan` (log `NEEDS_REVISION`);
  - Kehadiran = `v-select` (Hadir / Tidak Hadir Dengan Keterangan / Tidak Hadir Tanpa Keterangan), terkunci saat revisi;
  - izin: textarea placeholder `Tulis alasan tidak hadir minimal 100 karakter`; `POST /attendances` tanpa lokasi;
    hanya hari ini; sukses → snackbar `Kehadiran berhasil dikirim.`;
  - revisi: `/dashboard/riwayat?action=revision&date=<tgl>` membuka panel; `PUT /daily-logs/{id}` dengan
    `state: REVISION_SUBMITTED`, tanpa lokasi; sukses → `Perbaikan laporan harian berhasil dikirim.`;
  - panel lokasi hanya tampil untuk laporan hadir baru.
- Endpoint kurikulum / Fokus Pembelajaran.
