import logging
import os
from pathlib import Path

from main import (
    _init_pipeline,
    _collect_images_from_dir,
    _process_images,
    extract_content,
    convert_images_in_json,
)

logger = logging.getLogger("paddleocr_vl")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def process_dir(input_dir: str | Path) -> None:
    pipeline = _init_pipeline()
    in_dir = Path(input_dir)

    if not in_dir.exists() or not in_dir.is_dir():
        raise ValueError(f"input dir not exists or not a directory: {in_dir}")

    imgs = _collect_images_from_dir(in_dir)
    if not imgs:
        raise ValueError("no images found in directory")

    for p in imgs:
        try:
            # json 和图片放在同一个目录
            out_dir = p.parent

            # 临时 md 文件名
            md_name = f"{p.stem}.md"

            md_path = _process_images(
                pipeline,
                [p],
                out_dir,
                md_name,
            )

            with open(md_path, "r", encoding="utf-8") as f:
                texts = f.read()

            content = extract_content(texts)
            converted = convert_images_in_json(
                content,
                base_dir=str(out_dir),
            )

            # 删除临时 md
            try:
                os.remove(md_path)
            except Exception:
                pass

            json_path = out_dir / f"{p.stem}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(converted)

            logger.info(f"saved: {json_path}")

        except Exception as e:
            logger.error(f"failed: {p} ({e})")

def process_image(image_path: str | Path) -> None:
    pipeline = _init_pipeline()
    p = Path(image_path)

    if not p.exists() or not p.is_file():
        raise ValueError(f"image not exists or not a file: {p}")

    try:
        out_dir = p.parent
        md_name = f"{p.stem}.md"

        md_path = _process_images(
            pipeline,
            [p],
            out_dir,
            md_name,
        )

        with open(md_path, "r", encoding="utf-8") as f:
            texts = f.read()

        content = extract_content(texts)
        converted = convert_images_in_json(
            content,
            base_dir=str(out_dir),
        )

        # 删除临时 md
        try:
            os.remove(md_path)
        except Exception:
            pass

        json_path = out_dir / f"{p.stem}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(converted)

        logger.info(f"saved: {json_path}")

    except Exception as e:
        logger.error(f"failed: {p} ({e})")

if __name__ == "__main__":
    path_list = [
        '/home/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第一章 勾股定理/1 探索勾股定理',
    ]
    # for path in path_list:
    #     process_dir(path)
    # # ✅ 在这里直接写图片文件夹路径
    # input_dir = "/your/image/folder/path"
    #
    # process_dir(input_dir)
    path_ = [
        '/home/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第七章 证明/3 平行线的证明/img_0003.png'
    ]
    for p in path_:
        process_image(p)