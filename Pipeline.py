# -*- coding: utf-8 -*-
# @Time    : 2026/1/20 10:25
# @File    : Pipeline.py
# @Project : PaddleOCR-VL-master
# @Author  : daixun
# -*- coding: utf-8 -*-
# @Time    : 2026/1/20
# @File    : Pipeline.py
# @Project : PaddleOCR-VL-master
# @Author  : daixun

# -*- coding: utf-8 -*-
# @Time    : 2026/1/20
# @File    : Pipeline.py
# @Project : PaddleOCR-VL-master
# @Author  : daixun

import os
import json
import requests

URL = "http://192.168.0.67:8080/parse-docs"
IMAGE_DIR = r"images"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def is_image_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in IMAGE_EXTENSIONS


def rename_images_in_dir(base_dir: str):
    """
    按顺序重命名图片文件，格式：0001.xxx
    """
    index = 1

    for root, _, files in os.walk(base_dir):
        # 只处理图片，并排序，保证顺序稳定
        image_files = sorted(
            [f for f in files if is_image_file(f)]
        )

        for filename in image_files:
            ext = os.path.splitext(filename)[1].lower()
            new_name = f"{index:04d}{ext}"

            old_path = os.path.join(root, filename)
            new_path = os.path.join(root, new_name)

            # 避免重复命名覆盖
            if old_path != new_path:
                os.rename(old_path, new_path)
                print(f"Rename: {filename} -> {new_name}")

            index += 1


def process_image(image_path: str):
    print(f"Processing: {image_path}")

    with open(image_path, "rb") as f:
        files = {"files": f}
        response = requests.post(URL, files=files, timeout=60)

    response.raise_for_status()
    result = response.json()

    json_path = os.path.splitext(image_path)[0] + ".json"

    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(result.get("data"), jf, ensure_ascii=False, indent=4)

    print(f"Saved: {json_path}")


def main():
    # ① 先重命名
    rename_images_in_dir(IMAGE_DIR)

    # ② 再遍历请求接口
    for root, _, files in os.walk(IMAGE_DIR):
        for filename in files:
            if not is_image_file(filename):
                continue

            image_path = os.path.join(root, filename)

            try:
                process_image(image_path)
            except Exception as e:
                print(f"[ERROR] {image_path}: {e}")


if __name__ == "__main__":
    main()
