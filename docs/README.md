# Dokumentasi

Dokumen dibagi tiga menurut pembacanya. Setiap fakta ditulis di satu tempat saja; dokumen lain cukup merujuk.

## Pertanyaan umum → file

Untuk manusia maupun agent AI yang membaca repo ini: mulai dari baris yang cocok.

| Pertanyaan | Baca |
|---|---|
| Bagaimana memasang dari nol? Env/kunci apa yang perlu? | [`panduan/pasang.md`](panduan/pasang.md) (bagian *Env dan kunci*) |
| Setup dari nol dengan bantuan agent? | `/monev setup` ([langkahnya](../plugin/skills/monev/references/setup.md)) |
| Bagaimana menyambungkan GitHub/GitLab, MCP kantor, atau work records? Scope token? | [`panduan/pasang.md`](panduan/pasang.md#sumber-bahan-pilih-jalur) |
| Format work records apa yang dibaca? Apa yang boleh dipanggil dari MCP? | [`teknis/kontrak-sumber.md`](teknis/kontrak-sumber.md) |
| Alur harian: draft → validasi → kirim? Izin dan revisi? | [`panduan/pemakaian.md`](panduan/pemakaian.md) |
| Dari mana isi draft diambil? | [`panduan/pemakaian.md`](panduan/pemakaian.md#dari-mana-isi-draft-diambil) |
| Pengingat dan sapaan pagi (extension atau Telegram)? | [`panduan/pemakaian.md`](panduan/pemakaian.md#pengingat-di-chrome-tanpa-bot), [`panduan/bot-telegram.md`](panduan/bot-telegram.md) |
| Bagaimana extension dan CLI bekerja? | [`teknis/arsitektur.md`](teknis/arsitektur.md) |
| Fakta aplikasi Monev (API, form, aturan program)? | [`teknis/situs-monev.md`](teknis/situs-monev.md) |
| Instruksi untuk agent yang menyusun laporan | [`../plugin/skills/monev/SKILL.md`](../plugin/skills/monev/SKILL.md) |

## `panduan/`: untuk pemakai

Cara melakukan sesuatu, langkah demi langkah.

| File | Isi |
|---|---|
| [`pasang.md`](panduan/pasang.md) | kebutuhan, pemasangan CLI + login + extension, opsional Claude Code/Hermes, login ulang, file lokal, dukungan OS |
| [`pemakaian.md`](panduan/pemakaian.md) | alur harian dengan/tanpa agent, rekap, daftar perintah, aturan isi laporan, config |
| [`bot-telegram.md`](panduan/bot-telegram.md) | bot Telegram: yang dikirim, persiapan, menjalankan di laptop/server, sesi habis, masalah umum |

## `teknis/`: cara kerja

Untuk yang ingin mengubah kode atau memahami alasan di balik rancangan.

| File | Isi | Diperbarui bila… |
|---|---|---|
| [`arsitektur.md`](teknis/arsitektur.md) | komponen, alur data, dua Chrome dua sesi, bot, struktur kode | perilaku tool atau struktur kode berubah |
| [`situs-monev.md`](teknis/situs-monev.md) | fakta aplikasi Monev: aturan program, login/sesi, API, form (dengan sumber tiap fakta) | ada fakta Monev baru yang terverifikasi |
| [`format-pesan-telegram.md`](teknis/format-pesan-telegram.md) | aturan penulisan dan contoh setiap pesan bot | teks pesan di `monev/bot/pesan.py` berubah |
| [`kontrak-sumber.md`](teknis/kontrak-sumber.md) | kontrak sumber bahan: MCP kantor, format folder work records, aturan read-only | format work records yang dibaca atau cara memilih tool MCP berubah |

## Di luar `docs/`

| File | Isi |
|---|---|
| [`../README.md`](../README.md) | gambaran singkat dan mulai cepat |
| [`../config.example.toml`](../config.example.toml), [`../.env.example`](../.env.example) | contoh config (tanpa rahasia) dan kunci bot |
| [`../scripts/cek-bocor.sh`](../scripts/cek-bocor.sh) | cek kata terlarang dan rahasia sebelum commit (pemelihara, opsional) |
| [`../CHANGELOG.md`](../CHANGELOG.md) | perubahan yang terasa oleh pemakai |
| [`../plugin/skills/monev/`](../plugin/skills/monev/) | instruksi untuk agent (`SKILL.md`, cara mengambil sumber, gaya tulisan, prosedur kirim) |
| [`../monev/laporan/aturan.toml`](../monev/laporan/aturan.toml) | aturan isi laporan yang dipakai `monev validate` |

## Aturan pemeliharaan

- Perubahan perilaku skill → ubah `plugin/skills/monev/` **dan** `teknis/arsitektur.md` di commit yang sama.
- Perubahan yang terasa oleh pemakai → tambah baris di `CHANGELOG.md` bagian `[Unreleased]` di commit yang sama.
- Di `situs-monev.md`, setiap fakta diberi sumber: `uji`, `bundle`, `panduan`, atau `belum diketahui`.
- Teks pesan bot diubah di kode dulu, lalu contoh di `format-pesan-telegram.md` diperbarui.
- Default config di `monev/config.py` (`render_config`) berubah → buat ulang `config.example.toml` (tes
  `test_config` gagal bila keduanya berbeda).
- Repo tidak menyebut alat/layanan internal kantor mana pun, path pribadi, atau rahasia; yang spesifik orang/kantor
  hanya di `config.toml` lokal.
- Pemelihara bisa memasang pengecek sebelum commit (opsional):

  ```bash
  mkdir -p ~/.config/monev
  printf '%s\n' 'nama-internal-1' 'nama-internal-2' > ~/.config/monev/kata-terlarang.txt   # satu kata per baris
  scripts/cek-bocor.sh                                   # cek sekali
  ln -s ../../scripts/cek-bocor.sh .git/hooks/pre-commit # atau: cek otomatis setiap commit
  ```
