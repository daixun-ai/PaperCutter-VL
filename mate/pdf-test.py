import os
from pathlib import Path
import warnings

from paddleocr import PaddleOCRVL

# 忽略不影响运行的 warning
warnings.filterwarnings("ignore")

# 模型路径
layout_model_path = '../models/PaddlePaddle/PP-DocLayoutV2'
vl_rec_model_path = '../models/PaddlePaddle/PaddleOCR-VL'

# 初始化 PaddleOCRVL pipeline
pipeline = PaddleOCRVL(
    layout_detection_model_dir=layout_model_path,
    vl_rec_model_dir=vl_rec_model_path,
    doc_orientation_classify_model_dir=layout_model_path,
    doc_unwarping_model_dir=layout_model_path
)

# 指定单个 PDF 文件路径
pdf_path = Path(os.path.dirname(__file__)) / "pdf" / "2.pdf"

# 输出目录
output_dir = Path(os.path.dirname(__file__)) / "output"
output_dir.mkdir(parents=True, exist_ok=True)

print(f"Processing {pdf_path.name}...")

# 调用 pipeline predict，batch=1
output = pipeline.predict(input=str(pdf_path))

markdown_list = []
markdown_images = []

for res in output:
    md_info = res.markdown
    markdown_list.append(md_info)
    markdown_images.append(md_info.get("markdown_images", {}))

# 合并多页 Markdown
markdown_texts = pipeline.concatenate_markdown_pages(markdown_list)

# 保存 Markdown 文件
mkd_file_path = output_dir / f"{pdf_path.stem}.md"
with open(mkd_file_path, "w", encoding="utf-8") as f:
    f.write(markdown_texts)

# 保存每页对应图片
for item in markdown_images:
    if item:
        for path, image in item.items():
            file_path = output_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(file_path)

print(f"Finished processing {pdf_path.name}, output saved to {output_dir}")
