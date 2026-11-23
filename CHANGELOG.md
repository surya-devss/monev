# Changelog

Perubahan yang terasa oleh pemakai.

## [Unreleased]

### Ditambahkan
- Saringan nama di `monev validate` dan `monev kirim`: nama proyek dan klien dikumpulkan dari sumber
  lalu ditolak bila tertulis di laporan, sedangkan nama teknologi dan standar tetap boleh disebut.
- `monev sumber siap`: cek kesiapan bahan satu tanggal tanpa menarik atau mengubah repo work records.
- `monev eval`: skor draft latihan terhadap laporan yang sudah terkirim.
- Config `[laporan] lewati_proyek`, `nama_boleh`, dan `jam_selesai`. Field opsional `client` di work records.
- `monev sumber baca` memisahkan logtime carry-over dan menampilkan kerja di luar jam yang belum dilaporkan, supaya
  bisa masuk laporan berikutnya dengan waktu yang ditulis jujur.
- `monev jadwal pasang|status|lepas|jalan`: draft disusun otomatis di laptop dan Telegram memberi kabar tanpa memuat isi
  laporan. `/monev` melanjutkan draft yang sudah tersimpan.
- Draft dihapus otomatis setelah laporan terkirim, dan draft yang tidak jadi dikirim dihapus setelah 7 hari.
- Peringatan baru di `monev validate`: butir aktivitas terlalu panjang, pembuka pembelajaran berulang, batasan alat bantu
  kerja, dan kemungkinan detail temuan keamanan. Panduan tulis diperbarui dari telaah laporan 17–18 November.
- Bot Telegram mengabari laporan yang disetujui mentor, sekali per tanggal. Beberapa tanggal digabung jadi satu pesan,
  dan persetujuan setelah 22.00 dikabari pukul 08.00 besoknya. Persetujuan lama tidak dikabari saat bot diperbarui.
- Bot mengabari masa magang (H-30, H-7, hari terakhir, dan saat Monev menandai magang tidak aktif) serta pergantian
  versi situs Monev, supaya kiriman berikutnya dicoba dulu dengan `monev kirim --uji`.
- Draft terjadwal mengabari Telegram bila sesi Monev di laptop tinggal ≤ 3 hari, dan langsung mengabari bila bentuk
  data Monev berubah.
- Extension: popup menampilkan tanggal habis sesi Monev di Chrome harian, sapaan pagi memperingatkan bila sisa ≤ 3 hari,
  dan notifikasi desktop saat situs Monev diperbarui. Butuh izin baru `cookies` (hanya tanggal habis sesi), muat
  ulang extension setelah memperbarui.

### Diubah
- Kabar draft terjadwal di Telegram memakai format pesan bot yang lain: judul tebal, tanggal `19 Nov`, tanpa emoji.
  Teksnya ada di `monev/teks/bawaan.toml` bagian `[bot.draft.*]` dan bisa ditimpa `[pesan]` di config.
- Total absen dan izin dibayar dihitung per periode (satu bulan sejak tanggal mulai magang), bukan sejak awal magang.
  Rekap bulan diganti rekap periode berjalan (`/rekap_bulan`, tombol "Rekap periode", `monev rekap --bulan`) dan
  dikirim di hari kerja terakhir periode. Absen berturut tetap dihitung lintas periode.
- Kalimat absen dan izin di rekap dibuat lebih jelas: "absen 0 (peringatan di 7), izin 0 dari 3 yang dibayar". Izin
  lewat jatah ditulis "4, 1 tidak dibayar".
- Pesan gangguan bot membedakan sesi habis, Monev tidak bisa dihubungi, dan bentuk data Monev berubah. Tombol cara
  login hanya muncul untuk sesi habis.

### Diperbaiki
- Bot dan CLI berhenti dengan pesan jelas bila field yang dipakai hilang dari respons Monev, alih-alih membacanya
  sebagai kosong (misalnya hari libur terbaca sebagai hari kerja).
- `monev status` tidak lagi membaca laporan hari lain sebagai laporan hari ini, sehingga arsip tidak menyalin laporan
  kemarin.
- Kabar "draft siap" yang gagal terkirim ke Telegram dicoba lagi di jadwal berikutnya.

## [0.2.0] - 2026-11-18

### Dokumentasi
- Panduan dan dokumen teknis disamakan dengan perilaku CLI, extension, dan bot saat ini.
- `tests/test_dokumen.py` memeriksa perintah, paket, file tes, dan tautan di dokumen.

## [0.1.0]

Rilis publik pertama: CLI `monev`, extension Chrome, skill `/monev`, dan bot Telegram.
