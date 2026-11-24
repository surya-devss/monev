# Pasang

Pemasangan sekali, ±5 menit. Setelah selesai, lanjut ke [pemakaian.md](pemakaian.md).

## Kebutuhan

- **Google Chrome**, di Linux atau Windows (lihat [Dukungan](#dukungan))
- Python ≥ 3.11 dan [`uv`](https://docs.astral.sh/uv/)
- Akun Monev MagangHub (login SSO Kemnaker)

Jalankan semua perintah di **terminal biasa**, bukan lewat `!` di Claude Code, karena login membuka jendela Chrome.

## Langkah wajib

### 1. CLI

```bash
git clone https://github.com/surya-devss/monev.git
uv tool install -e ./monev      # memasang perintah monev dan monev-native-host di ~/.local/bin
monev --version
```

### 2. Login sesi CLI

```bash
monev            # jendela Chrome milik monev terbuka → login SSO Kemnaker sendiri → "✓ Login OK"
monev doctor     # semua ✓: config, Chrome, sesi, umur refresh token (±30 hari)
```

Jendela ini memakai profil Chrome terpisah dari Chrome harianmu ("Chrome A", lihat
[arsitektur](../teknis/arsitektur.md#dua-chrome-dua-sesi)). File `config.toml` di root repo terisi otomatis.

### 3. Extension di Chrome harianmu

```bash
monev extension install      # mendaftarkan jembatan Native Messaging dan menampilkan folder extension
```

Di Windows, jembatan didaftarkan di registry `HKCU\Software\Google\Chrome\NativeMessagingHosts\monev.maganghub.kirim`
(tanpa hak admin). Jalankan perintah di PowerShell atau Windows Terminal.

Lalu di Chrome biasa:

1. buka `chrome://extensions`, nyalakan **Developer mode**;
2. **Load unpacked** → pilih folder `monev/extension`;
3. pastikan ID-nya `fdhbflndlipoblicgdjjkmfilocnngha`;
4. pastikan Chrome ini sudah login Monev dan pernah mengizinkan lokasi untuk situs Monev (sekali saja).

### 4. Cek semuanya tersambung

```bash
monev kirim --ping           # ✓ [ping] Terhubung ke Monev
```

Klik ikon extension: muncul nama dan posisimu.

## Langkah opsional

### Claude Code

```bash
claude plugin marketplace add ./monev
claude plugin install monev@monev-local
```

Setelah `git pull` yang mengubah skill, jalankan `/reload-plugins` di Claude Code.

### Hermes

```bash
monev hermes install                     # profile utama (~/.hermes)
monev hermes install --profile <nama>    # named profile
monev hermes install --symlink           # untuk pengembangan: skill langsung mengikuti repo
```

Di Hermes: buka sesi baru atau `/reload-skills`, lalu `/monev`. Skill-nya sama dengan Claude Code. Untuk melepas:
`monev hermes uninstall [--profile …]`.

### Sumber bahan (pilih jalur)

Paling mudah: di Claude Code atau Hermes jalankan **`/monev setup`**. Agent mendeteksi apa yang kamu punya,
mengusulkan pengaturannya, dan menulis `config.toml` setelah kamu setujui; login dan token tetap kamu kerjakan sendiri.
Cara manualnya di bawah. Cek kapan saja dengan `monev doctor --tanpa-sesi` (bagian *Jalur sumber bahan*).

| Jalur | Untuk siapa | Menyambungkan | Cek |
|---|---|---|---|
| **A. Tanya-jawab** | semua orang | tidak perlu apa-apa | selalu ✓ |
| **B. Git** | yang commit/PR di GitHub atau GitLab (termasuk GitLab kantor) | lihat [Jalur B](#jalur-b-git) | `monev bukti` |
| **C. MCP kantor** | yang kantornya menyediakan server MCP untuk logtime, tiket, aktivitas git, atau kalender | 1. pasang server MCP itu di agent-mu mengikuti petunjuk kantormu; 2. isi `[sumber.mcp] awalan_tool` dengan awalan nama tool-nya (Claude Code, mis. `"mcp__kantor__"`) atau nama server-nya (Hermes) | `monev config` → *MCP kantor*; `/monev:status` |
| **D. Work records** | yang mencatat kerja harian dalam Markdown ([format](../teknis/kontrak-sumber.md#jalur-d-folder-work-records)) | `monev sumber cari` menemukan foldernya dari isi; isi `[sumber.workrecords] dir = "<folder>"` | `monev doctor --tanpa-sesi` → *D* |

Hanya jalur D yang mengisi **pembelajaran dan kendala** secara otomatis; jalur lain mengisi aktivitas, sisanya
ditanyakan.

#### Jalur B: Git

monev membaca commit, PR/MR, dan review **milikmu** di semua repo yang bisa diakses akunmu, lewat `gh` (GitHub) atau
`glab` (GitLab). monev tidak menyimpan token; autentikasi dipegang `gh`/`glab`.

| | GitHub | GitLab |
|---|---|---|
| Alat | [`gh`](https://cli.github.com) | [`glab`](https://gitlab.com/gitlab-org/cli) |
| Login (disarankan) | `gh auth login` → GitHub.com → HTTPS → login lewat browser | `glab auth login --hostname <host>` (host GitLab kantor, atau `gitlab.com`) |
| Atau token (PAT) | fine-grained PAT, *Repository access* sesuai kebutuhan, izin *Contents*, *Pull requests*, *Metadata* = **Read-only**; simpan di env `GH_TOKEN` | PAT scope `read_api` (+ `read_user`); env `GITLAB_TOKEN` + `GITLAB_HOST` |
| Config | `[sumber.git] penyedia = ["github"]` | `penyedia = ["gitlab"]`, `gitlab_host = "<host>"` |

PAT classic GitHub tidak disarankan: tidak ada scope read-only untuk repo private. Membaca repo kantor dengan akun
pribadi mengikuti aturan kantormu masing-masing. Uji: `monev bukti` (hari ini) atau `monev bukti --tanggal YYYY-MM-DD`.

Semua jalur hanya **membaca**. Kunci server MCP kantor disimpan di agent-mu, bukan di repo ini dan bukan di
`config.toml`. Server MCP kantor biasanya juga punya tool yang **menulis** (logtime, timer, komentar tiket);
`/monev` hanya memanggil tool baca (aturan mutlak #6 di skill), tapi agent lain di sesi yang sama tidak terikat
aturan itu. Apa yang diambil dari tiap jalur: [pemakaian.md](pemakaian.md#dari-mana-isi-draft-diambil). Kontrak
teknis: [`../teknis/kontrak-sumber.md`](../teknis/kontrak-sumber.md).

### Bot Telegram

Pengingat dan rekap ke HP: [bot-telegram.md](bot-telegram.md).

## Setelah `git pull`

| Yang berubah | Yang perlu dilakukan |
|---|---|
| kode `monev/` | tidak ada (dipasang `-e`), kecuali `pyproject.toml` berubah → `uv tool install -e . --reinstall` |
| `extension/` | klik ↻ di kartu extension pada `chrome://extensions` |
| `plugin/skills/` | `/reload-plugins` (Claude Code) atau `/reload-skills` (Hermes) |

## Login ulang dan logout

Ada **dua sesi terpisah** ([alasannya](../teknis/arsitektur.md#dua-chrome-dua-sesi)):

| Sesi | Dipakai untuk | Logout | Login lagi |
|---|---|---|---|
| Chrome A (CLI) | status, rekap, bot | `monev logout` (menghapus profil Chrome monev) | `monev login` di terminal biasa |
| Chrome B (Chrome harianmu) | mengirim laporan | logout dari menu Monev di Chrome | login di tab Monev biasa, lalu `monev kirim --ping` |

Refresh token berlaku ±30 hari; `monev doctor` menampilkan tanggal habisnya.

## Env dan kunci

**Tidak ada env yang wajib** untuk CLI, extension, dan `/monev`. Semua di bawah ini opsional. Contoh file:
[`config.example.toml`](../../config.example.toml) (pengaturan, tanpa rahasia; `monev` membuat `config.toml` dengan isi
yang sama secara otomatis) dan [`.env.example`](../../.env.example) (hanya untuk bot).

| Nama | Dipakai oleh | Untuk | Disimpan di |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | `monev bot` | bot Telegram pribadi | `<repo>/.env` (salin dari `.env.example`, gitignored, izin 600) |
| `MONEV_WORK_RECORDS` | `monev init` / config pertama | lokasi folder work records | env shell; setelah config ada, pakai `[sumber.workrecords] dir` |
| `MONEV_CONFIG`, `MONEV_CONFIG_DIR`, `MONEV_DATA_DIR` | CLI | memindahkan config / data (sesi, arsip, antrian) | env shell |
| `MONEV_CHROME_ARGS` | CLI di container | flag tambahan Chrome headless | `deploy/` / env container |

Email dan password Monev tidak pernah disimpan; login selalu diketik sendiri. Token dan cookie sesi hanya ada di
profil Chrome.
Token GitHub/GitLab dan kunci server MCP kantor dipegang `gh`/`glab`/agent-mu (lihat
[Sumber bahan](#sumber-bahan-pilih-jalur)), tidak pernah di repo ini.

## File di komputermu

| Path | Isi |
|---|---|
| `<repo>/config.toml` | pengaturan pribadi, tanpa rahasia (gitignored; contoh: `config.example.toml`) |
| `<repo>/.env` | token bot Telegram, bila memakai bot (gitignored; contoh: `.env.example`) |
| `~/.local/share/monev/chrome-profile/` | sesi CLI (izin 700, jangan dibagikan) |
| `~/.local/share/monev/kirim/` | antrian CLI ↔ extension (izin 700) |
| `~/.local/share/monev/arsip/` | teks laporan yang sudah terkirim, untuk cek kemiripan |
| `~/.local/share/monev/draft/` | draft dari skill |
| `~/.config/google-chrome/NativeMessagingHosts/monev.maganghub.kirim.json` | pendaftaran jembatan extension (Linux) |
| `%LOCALAPPDATA%\monev\NativeMessagingHosts\monev.maganghub.kirim.json` + kunci registry di atas | pendaftaran jembatan extension (Windows) |

Sesi login Monev hanya tersimpan di profil Chrome. Jangan membagikan folder profil itu.

## Dukungan

| Platform | Status |
|---|---|
| Linux | CLI, extension (termasuk kiriman laporan hadir), dan bot sudah dipakai harian |
| macOS | belum diuji (Chrome di `/Applications/Google Chrome.app`; izinkan Chrome di Location Services) |
| Windows | CLI, login, extension, dan `/monev` di Claude Code maupun Hermes sudah dipakai; `monev extension install` diuji otomatis di CI Windows |
| Claude Code | `/monev`, `/monev setup`, `/monev nilai`, `/monev latihan`, `/monev:status` |
| Hermes | `monev hermes install` lalu `/monev`, di Linux dan Windows |
| `monev jadwal` | draft otomatis terjadwal memakai systemd, jadi hanya Linux |
| GitLab (jalur B) | kode dan tes tersedia; belum diuji dengan akun nyata |
