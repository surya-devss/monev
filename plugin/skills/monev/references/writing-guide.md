# Panduan menulis laporan Monev

Pembaca: **mentor dari kantor** (tahu proyeknya) + disimpan di sistem pemerintah.

## Bentuk tiap field (masing-masing 100–5000 karakter)

| Field | Isi | Bentuk |
|---|---|---|
| Uraian aktivitas | apa yang dikerjakan hari ini + hasilnya | daftar bernomor `1.` `2.` (tampil rapi di Monev); satu butir per pekerjaan: `[Proyek/Sistem] apa yang dikerjakan → hasil/cara memastikannya` |
| Pembelajaran yang diperoleh | hal yang dipahami dan **kenapa penting** | 1 paragraf; dari keputusan teknis/akar masalah/arahan mentor; bukan mengulang aktivitas; tulis pelajaran umumnya tanpa menceritakan temuan keamanan; pembuka **berbeda dari laporan terakhir**, jangan selalu "Saya belajar bahwa…" |
| Kendala yang dialami | hambatan nyata + **cara menangani atau langkah berikutnya** | 1 paragraf; utamakan kolom blocker, status `blocked`, pekerjaan yang benar-benar tertahan karena menunggu izin atau pihak lain, lalu masalah teknis yang menghambat pekerjaan; prosedur biasa (meminta izin, jadwal di luar jam sibuk, review) bukan kendala bila pekerjaan tetap berjalan; bukti lemah → sebut di keraguan; tidak ada kendala → kalimat jujur, **berbeda dari hari sebelumnya** |

## Gaya
- Bahasa Indonesia resmi, kalimat aktif, orang pertama secukupnya ("saya" boleh di Pembelajaran).
- Tanpa markdown, emoji, jargon internal (`T3`, `L5`, `fase B`, `canary`) → ganti kata biasa.
- **Tanda baca seperti laporan kerja biasa, bukan teks buatan AI**: tanpa titik koma (`;`), tanpa tanda pisah panjang
  (`—`), dan tanpa titik dua di tengah kalimat ("…laporan: memisahkan…", "…kegiatan rutin: sesi…"). Pecah jadi dua
  kalimat, atau sambung dengan kata hubung (dengan, sehingga, lalu, berupa, karena). `monev validate` memberi
  peringatan bila tanda ini muncul.
- Sebut proyek/sistem dan hasil; hindari kalimat umum ("mengerjakan tugas", "melanjutkan pekerjaan").
- Satu butir aktivitas paling panjang sekitar 250 karakter. Pekerjaan yang lebih panjang dipecah atau dipadatkan ke hasil utamanya.
- Kata kerja langsung: "Menilai kerentanan", bukan "Melakukan penilaian kerentanan". Hindari frasa kaku: "dibatalkan", bukan "ditutup sebagai dibatalkan", dan "membuat versi HTML", bukan "merender versi HTML".
- Sebutan tetap sama dari hari ke hari: sesi harian peserta magang, doa pagi bersama, dan rapat harian tim DevOps. Label butir memakai bidang kerja, misalnya `[Monitoring]` untuk alert dan dasbor, bukan nama alatnya.
- Waktu apa adanya: kerja di luar jam dari hari sebelumnya ditulis "melanjutkan … yang dikerjakan di luar jam kerja pada …", tidak ditulis seolah dikerjakan pada jam kerja hari ini.
- Peran apa adanya: tulis yang benar-benar saya analisis, putuskan, terapkan, atau verifikasi; jangan dilebihkan. Batasan alat bantu kerja bukan kendala laporan, jadi tidak perlu diceritakan.

## Batas data (dicek `monev validate`, juga dijaga saat menulis)
Boleh: nama teknologi dan standar (Grafana, Wazuh, VPN, GitLab, ISO 27001), teknik kerja, nama dokumen, hasil, keputusan teknis.
Ditulis umum: nama klien dan aplikasi klien ("aplikasi klien"), nama server atau alat buatan internal ("server alat internal tim").
Tidak boleh: IP, hostname/URL internal, nomor tiket/MR, hash commit, path, token, email, **nama orang** (termasuk mentor — tulis "mentor"), detail kerentanan (jumlah/tingkat temuan, versi rentan, CVE, port atau jalur akses yang terbuka, konfigurasi yang bisa disalahgunakan), isi `jangan_disebut`, pekerjaan di `lewati_proyek`.

## Contoh yang lolos (terkirim 2026-11-16, hari pertama)

Uraian aktivitas
```
1. Mengikuti onboarding bersama peserta MagangHub di PT Contoh Digital, berupa pengenalan perusahaan, lingkungan kantor, dan aturan kerja selama program magang.
2. Mengikuti pengenalan dari tim DevOps mengenai peran tim, lingkup pekerjaan, serta alur kerja yang akan dijalani selama magang.
3. Mengikuti sesi mentoring awal bersama mentor untuk membahas arahan, target, dan cara pelaporan selama program.
4. Mempelajari aplikasi Monev, meliputi alur pengisian kehadiran dan laporan harian, ketentuan izin, serta proses peninjauan laporan oleh mentor.
```

## Contoh hari kerja (bentuk, bukan isi nyata)
```
1. [Monitoring] Merancang pemeriksaan ketersediaan server pemantauan dari server terpisah agar tim tetap mendapat notifikasi saat server utama berhenti, lalu menguji format pesan DOWN/UP.
2. [ISO 27001] Menyusun draf laporan penilaian kerentanan sesuai format dokumen standar perusahaan dan merevisinya berdasarkan masukan.
```

## Kesalahan yang pernah terjadi (jangan diulang)
- Memasukkan rutinitas (sesi magang rutin, daily meeting tim) padahal hari itu onboarding → rutinitas hanya bila terbukti/dikonfirmasi.
- Melewatkan onboarding/pengenalan tim/mentoring di hari pertama → cek `hari_pertama`.
- Terlalu generik sampai mentor tidak tahu apa yang dikerjakan → sebut proyek + hasil.
- Menceritakan kondisi layanan yang ditemukan saat pengujian → tulis pelajarannya, misalnya "hasil pindai perlu dicocokkan dengan konfigurasi layanan".
- Menulis bahwa alat bantu otomatis tidak bisa menjalankan sesuatu → tulis pekerjaan yang dilakukan saja.
- Menulis kendala tanpa kelanjutan → tambahkan cara menangani atau langkah berikutnya.
