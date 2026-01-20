import pypandoc


def markdown2pdf(md_text, pdf_path):
    extra_args = [
        "--pdf-engine=xelatex",
        # 中文字体配置
        "-V", "mainfont=Noto Sans CJK SC",
        "-V", "sansfont=Noto Sans CJK SC",
        "-V", "monofont=Noto Mono",
        "-V", "CJKmainfont=Noto Sans CJK SC",
        # 可选：字体大小和页面边距
        "-V", "fontsize=12pt",
        "-V", "geometry:margin=1in"
    ]
    pypandoc.convert_text(
        md_text,
        to="pdf",
        format="md",
        outputfile=pdf_path,
        extra_args=extra_args
    )


if __name__ == '__main__':
    with open("../存题标准.md", "r", encoding="utf-8") as f:
        md_text = f.read()
    markdown2pdf(md_text, "存题标准.pdf")
