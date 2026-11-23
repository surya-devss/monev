# Kontrak sumber bahan

monev **hanya membaca** bahan laporan; ia tidak membuat catatan kerja dan tidak menulis ke alat lain. Alat apa pun
yang menghasilkan bahan (agent pencatat kerja, MCP kantor, GitHub/GitLab, catatan buatan sendiri) cukup memenuhi
kontrak di halaman ini. Tidak ada kode yang saling mengimpor dan monev tidak menyimpan nama atau lokasi alat
tertentu: semua yang spesifik orang/kantor ada di `config.toml` lokal (gitignored). Sumber dikenali dari **isi dan
fungsinya**, bukan dari nama alat pembuatnya.

```
PENGHASIL bahan                      KONTRAK (halaman ini)                PEMAKAI
alat milik user (apa pun)   ───►     format + cara akses per jalur  ───►  /monev (Claude Code / Hermes) + CLI
                                     + pilihan di config.toml              read-only
```

## Jalur

Huruf jalur sama dengan keluaran `monev doctor` dan `/monev setup`.

| Jalur | Sumber | Aktif bila (`monev config --json`) | Dibaca oleh | Mengisi kolom |
|---|---|---|---|---|
| A | Checklist / tanya-jawab | selalu | skill; tanpa agent: `monev draft` | semua, dari jawaban user |
| B | Git: commit, PR/MR, review milik user | `git_penyedia` tidak kosong | CLI `monev bukti` (lewat `gh` / `glab`) | aktivitas (bukti hasil) |
| C | MCP kantor: logtime, tiket, aktivitas git, kalender | `mcp_awalan_tool` tidak kosong dan tool-nya ada di sesi agent | skill, lewat MCP client agent | aktivitas, jam, judul pekerjaan, kandidat acara |
| D | Folder work records | `workrecords_ada: true` | CLI `monev sumber baca` (bahan satu tanggal) dan `monev sumber cari` (menemukan folder) | aktivitas, **pembelajaran, kendala** |

Cara skill mengambil tiap jalur: [`plugin/skills/monev/references/sources.md`](../../plugin/skills/monev/references/sources.md).
Cara menyambungkan: [`../panduan/pasang.md`](../panduan/pasang.md#sumber-bahan-pilih-jalur), atau `/monev setup`.

## Jalur B: Git

| Butir | Kontrak |
|---|---|
| Pengenal | `[sumber.git] penyedia = ["github", "gitlab"]`, `gitlab_host` (bawaan `gitlab.com`) |
| Akses | `gh` / `glab` yang sudah login, atau env yang mereka baca (`GH_TOKEN`; `GITLAB_TOKEN` + `GITLAB_HOST`). monev tidak membaca atau menyimpan nilai token |
| Izin minimal | GitHub fine-grained PAT: *Contents*, *Pull requests*, *Metadata* = Read-only (PAT classic tidak punya scope read-only untuk repo private, jadi tidak disarankan). GitLab PAT: `read_api` (+ `read_user`) |
| Cakupan | aktivitas **milik user** di semua repo yang bisa diakses akunnya, tanggal D (WIB) |
| GitHub | events API (±90 hari / 300 event terakhir); commit per push lewat `repos/{repo}/commits?sha=&author=&since=&until=` (semua branch, merge commit dilewati); judul PR/issue per nomor. Terverifikasi 17 Nov 2026 |
| GitLab | `GET /events` milik user; per push hanya judul commit terakhir + jumlah commit. **Belum diuji dengan akun nyata** |
| Keluaran | `{waktu, penyedia, jenis: commit/pr/mr/review/issue, aksi, judul}`; judul sudah dibersihkan dari nama repo, hash, URL, nomor PR/MR/issue, email, dan `jangan_disebut` |
| Gagal | penyedia yang tidak siap dilaporkan (`ok: false` + langkah perbaikan); penyedia lain tetap dipakai |

## Jalur C: MCP kantor

| Butir | Kontrak |
|---|---|
| Pengenal | `[sumber.mcp] awalan_tool`: awalan nama tool (Claude Code, mis. `mcp__<server>__`) atau nama server MCP (Hermes) |
| Fungsi yang dicari | logtime/timesheet, kalender, aktivitas git (commit, MR/PR), tiket/tracker; dipilih dari nama dan deskripsi tool, bukan nama tetap |
| Akses | hanya tool **baca**. Tool dengan pola nama `create_*`, `update_*`, `delete_*`, `comment_*`, `start_timer`, `stop_timer`, `record_event`, `set_*`, `assign_*` dilarang (aturan mutlak #6 di `SKILL.md`), walaupun server tidak memblokirnya |
| Kunci | dipegang MCP client agent (config agent / env milik agent). monev tidak pernah meminta, menyimpan, atau membaca token MCP |
| Deteksi | `/monev setup`: agent memeriksa tool MCP di sesinya, mengusulkan awalan, user menyetujui |
| Sumber kosong / belum terhubung | fungsi itu dilewati; draft dilengkapi dari jalur lain |

## Jalur D: folder work records

| # | Butir | Bentuk yang diharapkan |
|---|---|---|
| K1 | Lokasi | `[sumber.workrecords] dir` di `config.toml` (atau env `MONEV_WORK_RECORDS` saat config dibuat). Ditemukan dengan `monev sumber cari`, yang mengenali folder dari isinya (K2–K3) |
| K2 | Struktur | `<folder>/<proyek>/<file>.md`; folder di `lewati_folder` dan semua folder berawalan `_` dilewati |
| K3 | Aktivitas | tabel di bawah judul `## Daily activity log`, baris diawali `\| YYYY-MM-DD \|`, kolom: kegiatan · bukti/hasil · blocker/keputusan |
| K4 | Pembelajaran | baris `Decision (YYYY-MM-DD…)`, `Pitfall (…)`, `Observasi (…)` di bawah `## Key technical decisions and pitfalls` |
| K5 | Judul | frontmatter `title` atau judul `# …` (nomor tiket dibuang saat menulis laporan) |
| K6 | Status | frontmatter `status`; `blocked` dibaca sebagai kendala |
| K7 | Klien (opsional) | frontmatter `client`: nama klien atau `internal`; nama klien dan nama folder proyek masuk saringan nama `monev validate` |
| K8 | Waktu kerja (opsional) | tabel di bawah `## Daily time log`, kolom: tanggal · mulai · selesai · durasi · kegiatan · dasar waktu. Teks `carry-over dari YYYY-MM-DD HH:MM-HH:MM` menandai jam yang berasal dari tanggal lain |

Section lain di file diabaikan, jadi format yang lebih lengkap tetap terbaca. Mengubah salah satu baris K1–K8
berarti mengubah halaman ini, `sources.md`, dan `monev/sumber/catatan.py` (`cari`, `baca`) beserta tesnya di commit
yang sama. Hanya tabel di bawah `## Daily activity log` yang dibaca untuk aktivitas; baris bertanggal di tabel lain
(*Daily time log* hanya dipakai untuk mengenali carry-over dan kerja di luar jam, K8).

## Aturan arah data

- **Satu arah, read-only.** monev tidak menulis ke work records, MCP, Git host, atau alat lain.
- Nomor tiket, MR, hash, IP, URL, dan nama orang dari sumber hanya jadi bahan; tidak masuk teks laporan
  (dicek `monev validate`).
- Nama proyek dan klien dari sumber ditulis umum. Nama dikumpulkan saat validasi, jadi tidak ada daftar yang dirawat.
  Teknologi, standar, nama perusahaan sendiri, dan nama program ada di `[nama]` pada `monev/laporan/aturan.toml`.
- `monev sumber siap` hanya membaca: repo work records tidak pernah ditarik atau diubah.
- Rutinitas yang tercatat di logtime **dan** kalender masuk draft dan disebut di keraguan; yang hanya di satu sumber,
  hari pertama, atau hari dengan acara khusus ditanyakan dulu.
  Logtime yang ditandai *carry-over* dari tanggal lain bukan aktivitas hari itu. Kerja di luar jam yang belum
  dilaporkan boleh masuk laporan hari kerja berikutnya dengan waktu yang ditulis jujur. Aktivitas Git di repo yang jelas bukan pekerjaan magang juga ditanyakan dulu.

## Siapa punya apa

| Punya | Jalur aktif | Hasil `/monev` |
|---|---|---|
| MCP kantor + work records | A + C + D (+ B) | draft hampir lengkap; tanya 0–2 hal |
| Git + work records | A + B + D | aktivitas dari catatan + bukti dari commit/PR; tanya sedikit |
| Git saja | A + B | aktivitas dari commit/PR; pembelajaran & kendala **ditanyakan** |
| work records saja | A + D | draft lengkap dari catatan; tanpa jam/tiket |
| tidak ada | A | Claude bertanya; CLI `monev draft` + `validate` tetap jalan |

Pembelajaran dan kendala (dua dari tiga kolom wajib, masing-masing ≥ 100 karakter) hanya punya sumber otomatis di
jalur D. Tanpa catatan harian, dua kolom itu ditanyakan.
