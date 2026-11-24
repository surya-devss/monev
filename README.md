# monev: asisten laporan harian Monev MagangHub

![monev: popup extension dan pesan bot Telegram](docs/img/hero.png)

Membantu mengecek, menulis, dan mengirim laporan harian di
[Monev MagangHub](https://monev.maganghub.kemnaker.go.id) dengan **review sebelum kirim** dan **lokasi asli**,
plus pengingat dan rekap kehadiran lewat Telegram.

Jalan di **Linux** dan **Windows**. Tersedia sebagai skill `/monev` di **Claude Code** dan **Hermes Agent**.

<p>
  <img src="docs/img/platform/claude-code.svg" alt="" height="20" align="absmiddle"> <b>Claude Code</b> &nbsp;
  <img src="docs/img/platform/hermes-agent.png" alt="" height="20" align="absmiddle"> <b>Hermes Agent</b> &nbsp;
  <picture><source media="(prefers-color-scheme: dark)" srcset="docs/img/platform/linux-putih.svg"><img src="docs/img/platform/linux.svg" alt="" height="18" align="absmiddle"></picture> <b>Linux</b> &nbsp;
  <img src="docs/img/platform/windows.svg" alt="" height="16" align="absmiddle"> <b>Windows</b>
</p>

Email dan password Monev tidak disimpan, login selalu kamu ketik sendiri. Sesi login hanya ada di profil Chrome.

## Alurnya

```mermaid
flowchart TB
  subgraph SUMBER["Sumber · dibaca saja"]
    direction TB
    GIT["🔀 <b>Git</b><br/><small>commit, PR/MR, review</small>"]
    MCP["🔌 <b>MCP kantor</b><br/><small>logtime, tiket, kalender</small>"]
    WR["📝 <b>Catatan</b><br/><small>folder work records</small>"]
  end

  subgraph LAPTOP["Laptop"]
    direction TB
    AGENT["✨ <b>Agent /monev</b><br/><small>Claude Code atau Hermes</small>"]
    CLI["⌨️ <b>CLI monev</b><br/><small>status, validasi, kirim</small>"]
    EXT["🧩 <b>Extension</b><br/><small>di Chrome harianmu</small>"]
  end

  subgraph LUAR["Monev & HP"]
    direction TB
    MONEV["🌐 <b>Monev</b><br/><small>situs laporan harian</small>"]
    BOT["🤖 <b>Bot</b><br/><small>server atau laptop, opsional</small>"]
    HP["📱 <b>Telegram</b><br/><small>pengingat dan rekap</small>"]
  end

  CLI -. "① cek status" .-> MONEV
  WR -- "②" --> AGENT
  MCP -- "②" --> AGENT
  GIT -- "② bahan" --> CLI
  AGENT == "③ kamu balas kirim" ==> CLI
  CLI == "④" ==> EXT
  EXT == "④ isi form" ==> MONEV
  BOT -. "⑤ baca" .-> MONEV
  BOT -- "⑤ kabari" --> HP

  classDef sumber fill:#1e293b,stroke:#64748b,color:#f1f5f9
  classDef laptop fill:#0f3d36,stroke:#86ead4,stroke-width:2px,color:#ecfdf9
  classDef luar fill:#1f2a44,stroke:#8ea2ff,color:#eef2ff
  class GIT,MCP,WR sumber
  class AGENT,CLI,EXT laptop
  class MONEV,BOT,HP luar
  style SUMBER fill:transparent,stroke:#64748b,stroke-dasharray:5 4
  style LAPTOP fill:transparent,stroke:#86ead4,stroke-dasharray:5 4
  style LUAR fill:transparent,stroke:#8ea2ff,stroke-dasharray:5 4
```

1. **Cek status**: CLI membaca status hari ini dari Monev.
2. **Kumpulkan bahan**: agent membaca catatan dan MCP kantor, CLI membaca aktivitas Git.
3. **Kamu memutuskan**: draft dicek aturan Monev lewat CLI. Tanpa balasan `kirim`, berhenti di sini.
4. **Extension mengirim**: CLI menitipkan draft ke extension, yang mengisi form di Chrome-mu dengan lokasi asli.
5. **Bot mengabari**: bot opsional membaca Monev, lalu mengirim pengingat, kabar revisi mentor, dan rekap ke Telegram.

Garis putus-putus berarti hanya membaca. Laporan tidak pernah terkirim tanpa balasan `kirim` darimu.

## Bagian-bagiannya

| Bagian | Fungsi | Wajib? |
|---|---|---|
| CLI `monev` | status, rekap, tulis dan validasi draft, cek kesiapan bahan, skor kualitas draft, kirim | ya |
| Extension Chrome | mengisi form Monev di Chrome-mu atas perintah CLI, supaya lokasi yang terkirim asli | ya, untuk kirim |
| Skill `/monev` (Claude Code atau Hermes) | menyusun draft dari tanya-jawab, commit/PR GitHub-GitLab, MCP kantor (logtime, tiket, kalender), atau folder work records ([pilih jalur](docs/panduan/pasang.md#sumber-bahan-pilih-jalur)) | tidak |
| Bot Telegram `monev bot` | pengingat jam kerja, notifikasi revisi/ditolak, rekap mingguan dan bulanan | tidak |

### CLI dan Claude Code

Draft disusun dari sumber kerjamu, divalidasi terhadap aturan Monev, lalu ditampilkan utuh untuk direview.
Tidak ada yang terkirim sebelum kamu membalas `kirim`. Panduan: [docs/panduan/pemakaian.md](docs/panduan/pemakaian.md).

Draft yang menyebut nama klien atau proyek pribadi ditolak, sedangkan nama teknologi seperti Grafana dan GitLab tetap
boleh. Logtime carry-over tidak dihitung sebagai kerja hari itu. Kerja di luar jam yang belum dilaporkan masuk ke
laporan berikutnya dengan keterangan waktu yang jujur.

| Review draft di Claude Code | Perintah CLI |
|---|---|
| ![Claude Code menampilkan draft untuk direview](docs/img/terminal-review.jpg) | ![monev status, validate, dan kirim --ping](docs/img/terminal-cli.jpg) |

### Extension Chrome

Popup menampilkan status hari ini, progres saat CLI meminta kirim, dan kesehatan sambungan. Jadwal notifikasi
diatur di halaman Pengaturan. Panduan: [docs/panduan/pemakaian.md](docs/panduan/pemakaian.md).

| Belum diisi | Sedang mengirim |
|---|---|
| ![Popup: laporan belum diisi](docs/img/extension-popup-belum.jpg) | ![Popup: progres pengiriman](docs/img/extension-popup-mengirim.jpg) |
| **Terkirim** | **Pengaturan** |
| ![Popup: laporan terkirim](docs/img/extension-popup-terkirim.jpg) | ![Halaman Pengaturan](docs/img/extension-pengaturan.jpg) |

### Bot Telegram

Satu kartu pagi yang diperbarui sepanjang hari, pengingat bertombol, dan `/menu` yang isinya berganti di tempat.
Saat membaca Monev, pesannya menampilkan ⏳ dulu. Panduan: [docs/panduan/bot-telegram.md](docs/panduan/bot-telegram.md).

Semua nama dan data di gambar adalah contoh.

## Mulai cepat

Mau menyimpan salinan sendiri? Klik **Use this template** di GitHub, lalu clone repo milikmu.

```bash
git clone https://github.com/surya-devss/monev.git
uv tool install -e ./monev
monev                        # login sekali di jendela Chrome yang terbuka
monev extension install      # lalu Load unpacked folder extension/ di chrome://extensions
monev kirim --ping           # cek semuanya tersambung
```

Pakai Claude Code atau Hermes? Setelah CLI terpasang, `/monev setup` memandu sisanya: login, extension, dan
menyambungkan sumber bahan (GitHub/GitLab, MCP kantor, work records).

Langkah lengkap ada di [docs/panduan/pasang.md](docs/panduan/pasang.md).

## Dokumentasi

| Mau… | Baca |
|---|---|
| memasang | [docs/panduan/pasang.md](docs/panduan/pasang.md) |
| mengisi laporan setiap hari | [docs/panduan/pemakaian.md](docs/panduan/pemakaian.md) |
| memasang bot Telegram | [docs/panduan/bot-telegram.md](docs/panduan/bot-telegram.md) |
| memahami cara kerjanya | [docs/teknis/arsitektur.md](docs/teknis/arsitektur.md) |
| melihat semua dokumen | [docs/README.md](docs/README.md) |
| ikut mengembangkan | [CONTRIBUTING.md](CONTRIBUTING.md) |

Riwayat perubahan: [CHANGELOG.md](CHANGELOG.md).

## Struktur repo

```
monev/
├── monev/               kode Python: cli/ (perintah), portal/, laporan/, kirim/, bot/, agen/, sumber/, teks/
│                        (lihat docs/teknis/arsitektur.md#struktur-kode)
├── extension/           extension Chrome
├── plugin/              skill /monev untuk Claude Code (juga dipasang ke Hermes)
├── deploy/              Dockerfile dan docker-compose untuk bot
├── scripts/             alat pemelihara repo (cek-bocor.sh)
├── tests/               unit test
├── docs/                panduan/ (pemakai), teknis/ (cara kerja)
├── config.example.toml  contoh config (dibuat otomatis oleh `monev`, tanpa rahasia)
└── .env.example         contoh kunci bot Telegram
```

Satu CLI, tiga cara pakai: terminal (`monev …`), Claude Code (plugin `/monev`), dan Hermes (`monev hermes install`).
Ketiganya menjalankan perintah CLI yang sama.

## Tes

```bash
.venv/bin/python -m unittest discover -s tests
```

## Tanggung jawab

monev adalah proyek independen dan tidak berafiliasi dengan Kemnaker atau MagangHub.
Tool ini membantu mengecek dan mengisi laporan di akun pribadi masing-masing. Isi laporan tetap tanggung jawab
peserta dan harus sesuai pekerjaan nyata.

## Lisensi

[MIT](LICENSE)
