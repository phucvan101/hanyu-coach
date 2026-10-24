#!/usr/bin/env bash
# Xử lý clip meme nền xanh → WebM nền trong suốt cho src/assets/reactions/.
#
# Cách dùng:  bash scripts/process-reactions.sh ~/Downloads/memes
# Thư mục nguồn chia theo nhóm (tên thư mục = tên nhóm):
#   streak-5/ streak-10/ streak-15/ streak-20/ streak-30/ break/ break-30/
# Tên file tuỳ chọn thêm:
#   _2-5s    chỉ lấy từ giây 2 đến giây 5 (mặc định: 4 giây đầu)
#   _mute    bỏ âm thanh (mặc định giữ tiếng)
#   _nokey   không tách nền (mặc định tự nhận: góc clip không phải màu xanh thì giữ nguyên nền)
set -euo pipefail

SRC=${1:?Thiếu thư mục nguồn, ví dụ: bash scripts/process-reactions.sh ~/Downloads/memes}
OUT="$(cd "$(dirname "$0")/.." && pwd)/src/assets/reactions"
WIDTH=${WIDTH:-360}
SIM=${SIM:-0.15}            # còn viền xanh → tăng; mất chi tiết → giảm

# lấy màu góc trên-trái của clip làm màu nền; in ra rỗng nếu màu đó không phải xanh lá
key_color() {
  local hex r g b
  hex=$(ffmpeg -v error -ss "$2" -i "$1" -frames:v 1 -vf "crop=8:8:2:2,scale=1:1" -f rawvideo -pix_fmt rgb24 - | xxd -p)
  r=$((16#${hex:0:2})) g=$((16#${hex:2:2})) b=$((16#${hex:4:2}))
  (( g > 120 && g > r + 60 && g > b + 60 )) && echo "0x${hex:0:6}"
  return 0
}

command -v ffmpeg >/dev/null || { echo "Chưa cài ffmpeg: brew install ffmpeg"; exit 1; }

shopt -s nullglob nocaseglob
for dir in "$SRC"/*/; do
  group=$(basename "$dir")
  for f in "$dir"*.{mp4,mov,webm,gif}; do
    name=$(basename "${f%.*}")
    start=0 dur=4
    if [[ $name =~ _([0-9.]+)-([0-9.]+)s ]]; then
      start=${BASH_REMATCH[1]}
      dur=$(awk "BEGIN{print ${BASH_REMATCH[2]} - $start}")
    fi
    vf="scale=$WIDTH:-2"
    key=""
    # lấy mẫu lệch 0,5s vì nhiều clip mở đầu bằng khung đen
    [[ $name == *_nokey* ]] || key=$(key_color "$f" "$(awk "BEGIN{print $start + 0.5}")")
    [[ -n $key ]] && vf="chromakey=$key:$SIM:0.05,$vf"
    audio=(-af loudnorm=I=-16:TP=-1.5 -c:a libopus -b:a 64k)  # cân bằng độ to giữa các clip
    [[ $name == *_mute* ]] && audio=(-an)
    clean=$(echo "$name" | sed -E 's/_[0-9.]+-[0-9.]+s|_sound|_mute|_nokey//g; s/^ +| +$//g; s/ +/-/g')

    mkdir -p "$OUT/$group"
    dst="$OUT/$group/$clean.webm"
    ffmpeg -loglevel error -y -ss "$start" -t "$dur" -i "$f" -vf "$vf" \
      -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 400k -auto-alt-ref 0 "${audio[@]}" "$dst"
    echo "✓ $group/$clean.webm  $(du -h "$dst" | cut -f1)  $([[ -n $key ]] && echo "nền $key" || echo "giữ nguyên nền")"
  done
done
