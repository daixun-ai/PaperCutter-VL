#!/usr/bin/env bash

set -e  # 任意一条失败直接退出（防止悄悄出错）

INPUTS=(
'/home/gjh/datasets/中考真题/广东省/语文/七年级/统编版/上册/第一单元/3 雨的四季-刘湛秋'

)

for input_path in "${INPUTS[@]}"; do
    echo "========================================"
    echo "Processing: $input_path"
    echo "----------------------------------------"

    python main.py -i "$input_path"

    echo "Done: $input_path"
done

echo "✅ All tasks finished."
