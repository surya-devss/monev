"""Sumber bahan laporan yang bisa dibaca CLI (read-only). Kontrak: docs/teknis/kontrak-sumber.md.

- `catatan.py`  folder work records: dikenali dari isinya (format kontrak), bukan dari nama alat pembuatnya
- `git.py`      aktivitas Git milik user lewat `gh` (GitHub) / `glab` (GitLab) yang sudah login
- `jalur.py`    status tiap jalur sumber untuk `monev doctor` dan `/monev setup`

MCP kantor tidak ada di sini: hanya agent yang bisa melihat dan memanggil tool MCP di sesinya.
"""
