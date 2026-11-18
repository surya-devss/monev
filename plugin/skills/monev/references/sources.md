# Sumber bahan laporan

Semua sumber **read-only**. Ambil untuk tanggal D (dari `monev status --json`), zona Asia/Jakarta.
Nomor tiket/MR, hash, IP, URL, nama orang dari sumber dipakai sebagai bahan saja; tidak pernah masuk teks laporan.

## 1. MCP kantor (bila `mcp_awalan_tool` di `monev config --json` tidak kosong)

Tool yang dipakai: tool MCP di sesi yang namanya diawali salah satu entri `mcp_awalan_tool` (Claude Code, mis.
`mcp__<server>__`; muat schema dulu lewat ToolSearch, `select:` beberapa tool sekaligus) atau tool dari server MCP yang
namanya tercantum di sana (Hermes). Daftar kosong, atau tidak ada tool yang cocok di sesi → lewati sumber ini.

Server MCP kantor biasanya juga punya tool **tulis** (logtime, timer, komentar tiket). Hanya tool baca yang boleh
dipanggil (aturan mutlak #6), walaupun tidak ada hook yang memblokir.

Pilih tool menurut **fungsi**, dari nama dan deskripsinya:

| Fungsi | Argumen | Ambil |
|---|---|---|
| Logtime / timesheet | tanggal D | entri waktu: jam, proyek, deskripsi → kerangka aktivitas (urut jam) |
| Kalender | tanggal D | acara hari itu → **kandidat** kegiatan; acara khusus (onboarding, mentoring, rapat non-rutin) jadi pertanyaan singkat "ikut acara X?", acara berulang tidak otomatis masuk |
| Aktivitas git (commit, MR/PR) | tanggal D | bukti hasil ("menyelesaikan …", "merge perubahan …") |
| Tiket / tracker | tiket yang muncul di entri logtime | judul & status tiket → nama pekerjaan yang jelas bagi mentor |

Tool sebuah fungsi menjawab "belum terhubung" atau kosong → lewati fungsi itu saja.
Belum ada entri logtime untuk D → pakai kalender + aktivitas git + work records; sebutkan di keraguan "logtime hari ini belum ada".

**Rutinitas**: blok rutin harian (doa pagi, daily meeting, sesi magang rutin, rapat
mingguan) yang tercatat di logtime **dan** kalender pada D → masuk draft sebagai satu butir "Mengikuti kegiatan rutin: …"
dan disebut di keraguan ("hapus bila tidak ikut"). Tetap **ditanyakan dulu** (checklist) bila: hanya ada di salah satu
sumber, `hari_pertama`, atau hari itu ada acara khusus seharian (onboarding, pelatihan, kunjungan): uji 2026-11-16
mencatat "sesi magang rutin" di kalender & logtime padahal hari itu onboarding.

**Proyek yang tidak dilaporkan**: aktivitas yang label/proyek/judulnya memuat kata di `jangan_disebut` (baca dari file config, path dari
`monev config --json`; `--json` hanya memberi jumlahnya) → lewati sejak mengumpulkan bahan, bukan menunggu ditolak `monev validate`. Sebutkan singkat di sumber
("N aktivitas dilewati: jangan_disebut"). Pengecualian sekali saja cukup lewat koreksi saat review.

**Logtime carry-over**: entri logtime hari D yang di work record ditandai *carry-over* dari tanggal lain (kerja hari
lain yang baru dicatat hari ini) **bukan** aktivitas D → jangan masukkan; sebutkan di keraguan. Yang dianggap bukti:
entri logtime berlabel proyek (bukan carry-over), commit/MR, baris work record, atau konfirmasi user.

## 2. Git (bila `git_penyedia` tidak kosong)

```bash
monev bukti --tanggal D --json
```

Commit, PR/MR, dan review **milik user** di semua repo GitHub/GitLab yang bisa diakses akun `gh`/`glab`-nya, jam WIB,
sudah dibersihkan (tanpa nama repo, hash, URL, nomor PR/MR, nama di `jangan_disebut`). Pakai sebagai **bukti hasil**
("menyelesaikan …", "menggabungkan perubahan …"), bukan kerangka utama: satu PR bisa berisi banyak commit kecil.
Commit di repo pribadi/side project ikut terambil → bila jelas bukan pekerjaan magang, tanyakan dulu sebelum dipakai.
`penyedia.<x>.ok: false` → lewati penyedia itu dan sebutkan pesannya di keraguan. Judul PR/commit ditulis ulang dengan
bahasa laporan, tidak disalin mentah.

## 3. Work records (bila `workrecords_ada: true`)

Folder `workrecords_dir`; lewati folder di `lewati_folder` dan semua folder berawalan `_`. Format yang dibaca:
`docs/teknis/kontrak-sumber.md` di repo monev.

```bash
monev sumber baca --tanggal D --json
```

Per pekerjaan: `judul`, `proyek`, `status`, `aktivitas` (baris *Daily activity log* hari D saja, bukan tabel lain seperti
*Daily time log*: kegiatan · bukti · blocker) dan `pembelajaran` (baris `Decision`/`Pitfall`/`Observasi` bertanggal D).
Jangan grep file sendiri: baris tanggal juga muncul di tabel lain.

- Aktivitas: `aktivitas[].kegiatan` + `bukti` → butir uraian (tanpa nomor tiket/commit/path).
- Pembelajaran: `pembelajaran[]` (keputusan dan alasannya, jebakan yang ditemui).
- Kendala: `aktivitas[].blocker`, `status: blocked`, kata "menunggu", "gagal", "belum"; tanda *carry-over* di kolom
  mana pun = kerja tanggal lain (lihat aturan logtime carry-over di atas).
- Judul pekerjaan: `judul` (buang nomor tiket).
- Kerja di luar jam: baris D jam 00.00–04.59 ikut D. Bila D hari kerja setelah libur, baris tanggal libur sebelumnya (yang belum pernah dilaporkan, cek arsip `~/.local/share/monev/arsip/`) boleh masuk sebagai "melanjutkan …".

## 4. Checklist / cerita (selalu tersedia)

Pakai bila sumber 1–3 tidak ada, atau untuk mengisi kekurangan. Tampilkan kandidat sebagai checklist; hanya yang **dicentang** user yang dipakai.

| Jenis hari | Kandidat |
|---|---|
| `hari_pertama` | onboarding bersama peserta · pengenalan tim (posisi dari config) · sesi mentoring awal · setup akun & akses kerja · mempelajari aplikasi Monev |
| hari biasa | `rutinitas` dari config · acara kalender (bila ada) |
| setelah libur/izin | "melanjutkan pekerjaan apa?" |

Selalu satu pertanyaan wajib bila tidak ada sumber otomatis: **"Pekerjaan utama hari ini apa, untuk proyek/sistem apa, dan hasilnya apa?"** (boleh cerita bebas).
Pembelajaran/kendala ditanyakan hanya bila jawaban belum memuatnya.
