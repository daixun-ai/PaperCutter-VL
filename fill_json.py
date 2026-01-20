# -*- coding: utf-8 -*-
# @Time    : 2026/1/3 15:39
# @File    : test.py
# @Project : PaddleOCR-VL-master
# @Author  : daixun
import json
from pathlib import Path

GRADE_MAP = {
    "七年级": "7",
    "八年级": "8",
    "九年级": "9",
}


def extract_from_path(json_path: Path) -> dict:
    """
    严格从【目录结构】提取字段（不读取文件名）
    """
    # 只取目录部分，不包含文件名
    dir_parts = json_path.resolve().parent.parts

    meta = {
        "grade": "",
        "volume": "",
        "chapter": "",
        "section": "",
        "subject": "",
    }
    import re

    CHAPTER_PATTERNS = [
        re.compile(r"^第.+单元.*"),
        re.compile(r"^第.+章.*"),  # 中文：第三章 概率初步
        re.compile(r"^Unit\s+.+", re.I),  # 英文：Unit 3 The seasons
    ]

    SECTION_PATTERNS = [
        re.compile(r"^\d+\s*.*"),  # 1 xxx / 2xxx
        re.compile(r"^Section\s+.+", re.I),  # Section A / Section 1
    ]

    def is_chapter_dir(name: str) -> bool:
        return any(p.match(name) for p in CHAPTER_PATTERNS)

    def is_section_dir(name: str) -> bool:
        return any(p.match(name) for p in SECTION_PATTERNS)

    for p in dir_parts:
        if p in GRADE_MAP:
            meta["grade"] = GRADE_MAP[p]

        elif p in ("上册", "下册"):
            meta["volume"] = p

        elif is_chapter_dir(p):
            meta["chapter"] = p

        elif is_section_dir(p):
            meta["section"] = p

        elif p in ("数学", "语文", "英语", "物理", "化学", "生物"):
            meta["subject"] = p

    return meta


def fill_json(json_file: Path) -> None:
    with json_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"{json_file} must be a JSON array")

    meta = extract_from_path(json_file)

    for item in data:
        if not isinstance(item, dict):
            continue

        for k, v in meta.items():
            if v != "":
                item[k] = v  # 无条件覆盖

    with json_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"✔ Normalized: {json_file}")


def process_path(path: Path):
    if path.is_file() and path.suffix == ".json":
        fill_json(path)
    elif path.is_dir():
        for jf in path.rglob("*.json"):
            fill_json(jf)
import os

def list_json_files(root_dir):
    json_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(".json"):
                json_files.append(os.path.join(root, file))
    return json_files

if __name__ == "__main__":
    from pathlib import Path

    JSON_FILES = list_json_files(r"/home/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第二章 实数/")
    for json_file in JSON_FILES:
        process_path(Path(json_file))
