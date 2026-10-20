#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo " ==== HANYU COACH – Luyện tiếng Trung ===="
echo ""
if ! docker info >/dev/null 2>&1; then
  echo " Docker Desktop chưa chạy. Đang mở Docker Desktop..."
  open -a Docker
  for i in $(seq 1 60); do
    sleep 3
    docker info >/dev/null 2>&1 && break
  done
fi
if ! docker info >/dev/null 2>&1; then
  echo " [LỖI] Không khởi động được Docker Desktop. Hãy mở Docker Desktop bằng tay rồi chạy lại file này."
  read -n 1 -s -r -p " Nhấn phím bất kỳ để đóng..."
  exit 1
fi
echo " Đang khởi động ứng dụng (lần đầu mất 2–5 phút để tải và cài đặt)..."
if ! docker compose up -d --build; then
  echo " [LỖI] Không khởi động được. Kiểm tra kết nối mạng rồi chạy lại."
  read -n 1 -s -r -p " Nhấn phím bất kỳ để đóng..."
  exit 1
fi
for i in $(seq 1 60); do
  curl -s http://localhost:8765/api/health >/dev/null 2>&1 && break
  sleep 2
done
open http://localhost:8765
echo ""
echo " Đã mở trình duyệt: http://localhost:8765"
echo " Ứng dụng tiếp tục chạy nền. Muốn tắt hẳn: chạy Stop-Mac.command"
sleep 5
