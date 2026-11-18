# /monev setup — pasang dan sambungkan, dipandu

Tujuan: pemakai baru (atau yang mengulang dari nol) selesai dengan CLI, sesi, extension, dan semua sumber bahan yang
ia punya tersambung, tanpa membaca dokumentasi sendiri. Agent memandu dan mengecek; **login, token, dan klik di
Chrome selalu dikerjakan user sendiri**. Agent tidak pernah meminta password/token ditempel di chat.

Setiap langkah: jalankan cek → tampilkan hasil singkat → bila perlu tindakan user, beri satu instruksi jelas → cek
lagi. Lanjut ke langkah berikutnya hanya bila lolos atau user memilih melewatinya.

## 1. CLI

`monev --version`. Gagal → user memasang (terminal biasa, bukan lewat agent):

```bash
git clone https://github.com/surya-devss/monev.git
uv tool install -e ./monev
```

## 2. Kondisi awal

```bash
monev doctor --json --tanpa-sesi
```

Ringkas `inti` (config, Chrome, extension) dan `jalur` (A–D) jadi satu tabel. Langkah 3–8 hanya untuk yang belum ✓.

## 3. Sesi Monev (CLI)

`monev status --no-login` exit `2` → minta user menjalankan `monev` di **terminal biasa** (jendela Chrome monev
terbuka, login SSO sendiri), lalu `monev doctor` → semua ✓. Posisi dan perusahaan terisi otomatis dari profil Monev.

## 4. Extension (pengirim laporan)

Doctor `extension` ✗ → ikuti pesannya, urut:
1. `monev extension install` (agent boleh menjalankan; mendaftarkan jembatan).
2. User: `chrome://extensions` → Developer mode → **Load unpacked** → folder yang dicetak perintah di atas; ID harus
   `fdhbflndlipoblicgdjjkmfilocnngha`. Chrome itu harus sudah login Monev dan mengizinkan lokasi untuk situs Monev.
3. `monev kirim --ping` → `✓ [ping] Terhubung ke Monev`.

## 5. Jalur D: folder work records

```bash
monev sumber cari --json
```

- Satu kandidat → tampilkan (folder, jumlah file, proyek, tanggal terakhir), tanya "pakai ini?".
- Beberapa → minta user memilih. Tidak ada → jelaskan singkat bahwa tanpa catatan harian, pembelajaran & kendala akan
  ditanyakan; format catatan ada di `docs/teknis/kontrak-sumber.md`. Lewati.
- Setuju → tulis `dir = "<folder>"` di bagian `[sumber.workrecords]` file config (`monev config --json` → `path`).
  Ubah baris itu saja.

## 6. Jalur C: MCP kantor

Hanya agent yang bisa melihat tool MCP di sesinya:
1. Kumpulkan tool MCP yang tersedia (Claude Code: nama `mcp__<server>__<tool>`, termasuk yang deferred; Hermes:
   server MCP yang terpasang).
2. Pilih server yang punya tool **baca** untuk salah satu fungsi: logtime/timesheet, tiket/tracker, aktivitas git,
   kalender (dari nama + deskripsi tool). Abaikan server lain (browser, dokumen, dsb.).
3. Tampilkan usulan: per server, awalan nama tool + fungsi yang ditemukan. Tidak ada → katakan "tidak ada MCP kantor
   di sesi ini" dan lewati; user yang kantornya punya MCP bisa memasangnya dulu mengikuti petunjuk kantornya.
4. Setuju → tulis `awalan_tool = ["<awalan>", …]` di `[sumber.mcp]`. Untuk dipakai juga di Hermes, tambahkan nama
   server-nya.
5. Uji satu tool baca untuk hari ini (mis. logtime) → tampilkan jumlah entri saja.

## 7. Jalur B: Git (GitHub / GitLab)

Tanyakan: "Kamu commit/PR di GitHub, GitLab, atau keduanya? (GitLab kantor: sebutkan host-nya)". Tidak memakai →
lewati.

| Penyedia | Cek | Belum siap → user menjalankan sendiri |
|---|---|---|
| GitHub | `gh auth status` | `! gh auth login` (pilih GitHub.com, HTTPS, login lewat browser). Alternatif: fine-grained PAT dengan izin *Contents*, *Pull requests*, *Metadata* = **Read-only**, disimpan sebagai env `GH_TOKEN` |
| GitLab | `glab auth status --hostname <host>` | `! glab auth login --hostname <host>`. Alternatif: PAT dengan scope `read_api` (+ `read_user`), env `GITLAB_TOKEN` + `GITLAB_HOST` |

`gh`/`glab` belum terpasang → beri tautan pemasangan (cli.github.com / gitlab.com/gitlab-org/cli), berhenti di
jalur ini sampai user bilang sudah. Setelah lolos → tulis `[sumber.git]`: `penyedia = ["github"]` / `["gitlab"]` /
keduanya, `gitlab_host = "<host>"` bila GitLab bukan gitlab.com. Uji: `monev bukti --json` → tampilkan jumlah
aktivitas hari ini per penyedia.

Ingatkan sekali: semua repo yang bisa diakses akun itu ikut terbaca (termasuk repo pribadi); saat menyusun laporan,
aktivitas yang jelas bukan pekerjaan magang ditanyakan dulu.

## 8. Nilai perusahaan (opsional)

`monev config --json` → `nilai` kosong → tawarkan `/monev nilai`.

## 9. Penutup

`monev doctor --json --tanpa-sesi` lagi → tabel akhir: inti + jalur A–D (✓ / – dilewati + alasannya). Sebutkan apa
yang masih perlu dikerjakan user, lalu: "Siap. Jalankan `/monev latihan` untuk mencoba tanpa mengirim, atau `/monev`
untuk laporan hari ini."

Bot Telegram tidak termasuk setup ini (opsional, perlu token bot): `docs/panduan/bot-telegram.md`.
