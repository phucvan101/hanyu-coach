#!/bin/bash
cd "$(dirname "$0")"
echo "Đang tắt Hanyu Coach..."
docker compose down
echo "Đã tắt. Dữ liệu học vẫn được giữ trong thư mục data."
sleep 3
