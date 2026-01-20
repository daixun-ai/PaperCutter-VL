# -*- coding: utf-8 -*-
# @Time    : 2026/1/5 20:49
# @File    : test.py
# @Project : PaddleOCR-VL-master
# @Author  : daixun
import os

def list_json_files(root_dir):
    json_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(".json"):
                json_files.append(os.path.join(root, file))
    return json_files


if __name__ == "__main__":
    folder_path = "/home/datasets/中考真题/广东省/语文/七年级/统编版/上册"  # ← 改成你的文件夹路径
    json_paths = list_json_files(folder_path)

    for path in json_paths:
        print(path)
