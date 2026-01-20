# -*- coding: utf-8 -*-
# @Time    : 2026/1/6 16:07
# @File    : rename_image.py
# @Project : PaddleOCR-VL-master
# @Author  : daixun
import os


def rename_images(
        folder_path,
        prefix="img",
        start_index=1,
        digits=4,
        extensions=(".jpg", ".jpeg", ".png", ".bmp", ".webp")
):
    files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(extensions)
    ]

    files.sort()  # 保证顺序稳定

    for i, filename in enumerate(files, start=start_index):
        ext = os.path.splitext(filename)[1]
        new_name = f"{prefix}_{str(i).zfill(digits)}{ext}"

        old_path = os.path.join(folder_path, filename)
        new_path = os.path.join(folder_path, new_name)

        if old_path != new_path:
            os.rename(old_path, new_path)

    print(f"完成：共重命名 {len(files)} 张图片")


if __name__ == "__main__":
    path_list = [
    ]
    for path in path_list:
        rename_images(
            folder_path=path,
            prefix="img",
            start_index=1,
            digits=4
        )

