# Ikut mengembangkan

Terima kasih sudah mau mencoba dan ikut mengembangkan monev. Halaman ini menjelaskan alur kerja di repo ini.

## Alur kerja: fork lalu pull request

Perubahan masuk lewat fork, bukan push langsung:

1. **Fork** repo ini (tombol *Fork* di GitHub).
2. Clone fork-mu, lalu buat branch dari `main`:
   ```bash
   git clone https://github.com/<akunmu>/monev.git
   cd monev
   git remote add upstream https://github.com/surya-devss/monev.git
   git switch -c feat/<ringkas-perubahan>
   ```
3. Kerjakan, jalankan tes (di bawah), commit, push ke fork-mu.
4. Buka **pull request** ke `surya-devss/monev` branch `main`. Pemilik repo me-review lalu me-merge.

Sebelum mulai fitur baru, perbarui `main` dari upstream: `git fetch upstream && git rebase upstream/main`.

## Menyiapkan lingkungan

Butuh Python 3.11+ dan [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                   # .venv berisi dependency dari uv.lock
.venv/bin/python -m unittest discover -s tests
```

Untuk mencoba CLI dari kode yang sedang diubah: `uv tool install -e .`, lalu `monev --version`.
Langkah pemakaian lengkap (login, extension, bot): [docs/panduan/pasang.md](docs/panduan/pasang.md).

## Aturan perubahan

- **Satu PR satu tujuan.** Pisahkan perbaikan bug, fitur, dan perapian.
- **Tes ikut berubah** bila perilaku berubah. Semua tes harus lolos.
- **Teks bot dan notifikasi** ada di [`monev/teks/bawaan.toml`](monev/teks/bawaan.toml), bukan di kode.
- **Dokumentasi ikut diperbarui** di PR yang sama: panduan di `docs/panduan/`, cara kerja di `docs/teknis/`,
  entri di [`CHANGELOG.md`](CHANGELOG.md)
  bagian `[Unreleased]` bila terasa oleh pengguna. Fitur baru juga diperiksa di `README.md` dan langkah `/monev setup`.
  `tests/test_dokumen.py` ikut memeriksa perintah, paket, dan tautan.
- **Monev hanya dibaca.** Kode tidak boleh mengirim laporan selain lewat extension setelah pengguna menyetujui
  draft (lihat aturan di [`plugin/skills/monev/SKILL.md`](plugin/skills/monev/SKILL.md)).

## Jangan pernah di-commit

- `config.toml`, `.env`, profil Chrome, file draft, atau isi laporan siapa pun.
- Token, cookie, password, chat id, atau data pribadi (nama lengkap, kontak, lokasi).
- Nama alat atau layanan internal kantor. Repo ini umum; contoh memakai nama netral.

`scripts/cek-bocor.sh` membantu memeriksa ini sebelum commit (daftar kata disimpan di luar repo, lihat komentar di
skripnya).

## Pesan commit

Format [Conventional Commits](https://www.conventionalcommits.org/), kalimat dalam bahasa Indonesia:

```
<type>(<scope>): <ringkasan, kalimat perintah>

Alasan: <kenapa perubahan ini perlu>

Perubahan:
- <poin>

Pengujian: <tes yang benar-benar dijalankan dan hasilnya>
```

`type`: feat, fix, refactor, perf, docs, test, ci, build, chore. `scope` contohnya: bot, extension, cli, kirim,
portal, docs.

## Pertanyaan atau ide

Buka **issue** dulu untuk perubahan besar supaya arahnya disepakati sebelum dikerjakan.
