#!/usr/bin/env bash
# Cek sebelum commit (untuk pemelihara repo, opsional):
#   1. kata terlarang (nama alat/layanan internal, path pribadi) di file ter-track;
#   2. rahasia (token, kunci) lewat gitleaks, bila terpasang.
#
# Daftar kata TIDAK disimpan di repo (supaya daftarnya sendiri tidak bocor):
#   ${MONEV_KATA_TERLARANG:-~/.config/monev/kata-terlarang.txt}   satu kata/frasa per baris, `#` = komentar
# Pengecualian path (opsional), satu awalan path per baris:
#   ${MONEV_KATA_ABAIKAN:-~/.config/monev/kata-terlarang.abaikan}
#
# Kata dicocokkan tanpa membedakan huruf besar/kecil dan hanya sebagai kata utuh (dibatasi huruf/angka),
# jadi kata "rapat" tidak cocok dengan "rapatkan" tetapi cocok dengan "x_rapat_y".
#
# Pakai: scripts/cek-bocor.sh    · sebagai hook: ln -s ../../scripts/cek-bocor.sh .git/hooks/pre-commit
# Keluar 1 bila ada temuan.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
DAFTAR="${MONEV_KATA_TERLARANG:-$HOME/.config/monev/kata-terlarang.txt}"
ABAIKAN="${MONEV_KATA_ABAIKAN:-$HOME/.config/monev/kata-terlarang.abaikan}"
temuan=0

bersih() { sed -e 's/#.*$//' -e 's/[[:space:]]*$//' -e 's/^[[:space:]]*//' "$1" | grep -v '^$' || true; }

if [[ -f "$DAFTAR" ]]; then
  pola=""
  while IFS= read -r kata; do
    pola+="${pola:+|}\\Q${kata}\\E"
  done < <(bersih "$DAFTAR")
  if [[ -n "$pola" ]]; then
    # File ter-track + file baru yang belum di-add (kecuali yang di-ignore), supaya file baru ikut dicek.
    mapfile -d '' berkas < <(git -C "$ROOT" ls-files -z --cached --others --exclude-standard)
    if [[ -f "$ABAIKAN" ]]; then
      mapfile -t lewati < <(bersih "$ABAIKAN")
      tersaring=()
      for f in "${berkas[@]}"; do
        skip=0
        for a in "${lewati[@]}"; do [[ "$f" == "$a"* ]] && { skip=1; break; }; done
        (( skip )) || tersaring+=("$f")
      done
      berkas=("${tersaring[@]}")
    fi
    if (( ${#berkas[@]} )); then
      if hasil=$(cd "$ROOT" && grep -nIiP "(?<![[:alnum:]])(?:${pola})(?![[:alnum:]])" -- "${berkas[@]}"); then
        echo "✗ Kata terlarang ditemukan (daftar: $DAFTAR):"
        echo "$hasil"
        temuan=1
      else
        echo "✓ Kata terlarang: tidak ada di ${#berkas[@]} file repo (ter-track + baru)."
      fi
    fi
  else
    echo "– Daftar kata kosong: $DAFTAR"
  fi
else
  echo "– Daftar kata tidak ada ($DAFTAR); cek kata terlarang dilewati."
fi

if command -v gitleaks >/dev/null 2>&1; then
  if gitleaks detect --no-banner --redact --source "$ROOT"; then
    echo "✓ gitleaks: tidak ada rahasia."
  else
    echo "✗ gitleaks menemukan kemungkinan rahasia (lihat di atas)."
    temuan=1
  fi
else
  echo "– gitleaks tidak terpasang; cek rahasia dilewati (https://github.com/gitleaks/gitleaks)."
fi

exit "$temuan"
