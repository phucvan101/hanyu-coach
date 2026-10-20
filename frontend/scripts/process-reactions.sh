#!/usr/bin/env bash
# Xử lý clip meme nền xanh → WebM nền trong suốt cho src/assets/reactions/.
#
# Cách dùng:  bash scripts/process-reactions.sh ~/Downloads/memes
# Thư mục nguồn chia theo nhóm (tên thư mục = tên nhóm):
#   streak-5/ streak-10/ streak-15/ streak-20/ streak-30/ break/ break-30/
# Tên file tuỳ chọn thêm:
#   _2-5s    chỉ lấy từ giây 2 đến giây 5 (mặc định: 4 giây đầu)
#   _sound   giữ âm thanh
#   _nokey   clip không có nền xanh, bỏ bước tách nền
set -euo pipefail

SRC=${1:?Thiếu thư mục nguồn, ví dụ: bash scripts/process-reactions.sh ~/Downloads/memes}
OUT="$(cd "$(dirname "$0")/.." && pwd)/src/assets/reactions"
WIDTH=${WIDTH:-360}
KEY=${KEY:-0x00FF00}        # màu nền cần xoá
SIM=${SIM:-0.15}            # còn viền xanh → tăng; mất chi tiết → giảm

command -v ffmpeg >/dev/null || { echo "Chưa cài ffmpeg: brew install ffmpeg"; exit 1; }

shopt -s nullglob nocaseglob
for dir in "$SRC"/*/; do
  group=$(basename "$dir")
  for f in "$dir"*.{mp4,mov,webm,gif}; do
    name=$(basename "${f%.*}")
    start=0 dur=4
    if [[ $name =~ _([0-9.]+)-([0-9.]+)s ]]; then
      start=${BASH_REMATCH[1]}
      dur=$(echo "${BASH_REMATCH[2]} - $start" | bc)
    fi
    vf="scale=$WIDTH:-2"
    [[ $name == *_nokey* ]] || vf="chromakey=$KEY:$SIM:0.05,$vf"
    audio=(-an)
    [[ $name == *_sound* ]] && audio=(-c:a libopus -b:a 64k)
    clean=$(echo "$name" | sed -E 's/_[0-9.]+-[0-9.]+s|_sound|_nokey//g')

    mkdir -p "$OUT/$group"
    dst="$OUT/$group/$clean.webm"
    ffmpeg -loglevel error -y -ss "$start" -t "$dur" -i "$f" -vf "$vf" \
      -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 400k -auto-alt-ref 0 "${audio[@]}" "$dst"
    echo "✓ $group/$clean.webm  $(du -h "$dst" | cut -f1)"
  done
done
