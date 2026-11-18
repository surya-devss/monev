---
name: status
description: "Cek status Monev MagangHub tanpa menyusun laporan: sudah isi atau belum, hari kerja/libur, revisi mentor, kesehatan sesi & plugin. Use when the user asks: status monev, sudah isi laporan belum, cek monev, monev nyambung belum."
---

# /monev:status — cek status (read-only)

Tidak menyusun draft, tidak membuka form, tidak mengirim apa pun.

1. `monev --version`. Gagal → CLI belum terpasang: beri tahu `uv tool install -e <repo monev>` (lihat README repo). Berhenti.
2. `monev status --no-login`
   - exit `2` → sesi belum ada/mati: minta user menjalankan `monev` di **terminal biasa** (jendela login terbuka sendiri). Berhenti.
   - sukses → tampilkan apa adanya.
3. `monev doctor --json --no-login` → ringkas jadi tabel: `inti` (config, Chrome, extension, profil, sesi, umur refresh token) dan `jalur` A–D (sumber bahan). Jalur yang belum tersambung → sarankan `/monev setup`.
4. Cek sumber skill `/monev` (tanpa memanggil apa pun yang menulis):
   - MCP kantor: `monev config --json` → `mcp_awalan_tool`; kosong → "tidak dipakai", terisi → ada tool berawalan itu di sesi? (ya/tidak)
   - Extension monev: `monev kirim --ping` (✓ Terhubung / pesan perbaikan apa adanya)
5. Penutup satu baris:
   - belum isi & hari kerja → "Jalankan `/monev` untuk menyusun laporan (batas 23.59)."
   - ada revisi mentor → "Jalankan `/monev revisi`."
   - sudah isi / libur → "Tidak ada yang perlu dilakukan."
