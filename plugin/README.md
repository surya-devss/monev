# Plugin `monev` (Claude Code)

Skill `/monev` untuk laporan harian Monev MagangHub: cek status, susun draft dari sumber yang tersedia, validasi
dengan `monev validate`, tampilkan untuk dibaca ulang, lalu kirim **hanya setelah kamu membalas `kirim`**.

| Perintah | Fungsi |
|---|---|
| `/monev` | laporan hari ini: status → draft → validasi → review → `kirim` |
| `/monev latihan [YYYY-MM-DD]` | menyusun draft untuk tanggal itu tanpa pernah mengirim |
| `/monev nilai` | cari nilai perusahaan (situs resmi) → isi `[profil.nilai]` setelah disetujui |
| `/monev:status` | cek status saja (sudah isi, libur, revisi mentor, sesi) |

Butuh CLI `monev` dari repo yang sama. Pengiriman hanya lewat extension monev (`monev kirim`); bila extension belum siap,
skill membantu memperbaikinya atau memberi teks untuk ditempel manual. Sumber otomatis (MCP kantor, folder work records) opsional, diatur di
`config.toml` ([kontrak](../docs/teknis/kontrak-sumber.md)).

Skill yang sama dipasang ke Hermes dengan `monev hermes install`.

| Isi folder | Untuk |
|---|---|
| `.claude-plugin/plugin.json` | metadata plugin |
| `skills/monev/SKILL.md` | instruksi `/monev` |
| `skills/monev/references/sources.md` | cara mengambil bahan dari tiap sumber |
| `skills/monev/references/writing-guide.md` | gaya tulisan dan contoh laporan |
| `skills/status/SKILL.md` | instruksi `/monev:status` |

Pemasangan: [`docs/panduan/pasang.md`](../docs/panduan/pasang.md#claude-code). Cara kerja:
[`docs/teknis/arsitektur.md`](../docs/teknis/arsitektur.md).
