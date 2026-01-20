import argparse
import base64
import json
import logging
import os
import threading
import warnings
from pathlib import Path
from typing import List, Dict, Set

import cv2
from dotenv import load_dotenv
from openai import OpenAI
from paddleocr import PaddleOCRVL

from templates import json_data

_PIPELINE_INSTANCE = None
_PIPELINE_LOCK = threading.Lock()
logger = logging.getLogger("paddleocr_vl")


def _init_pipeline() -> PaddleOCRVL:
    """
    初始化PaddleOCRVL管道实例，采用单例模式确保全局只有一个实例

    该函数使用双重检查锁定模式来确保线程安全的单例实例创建。
    首先检查全局实例是否存在，如果不存在则在锁保护下创建新实例。
    创建实例时会配置布局检测模型、视觉语言识别模型等路径，
    并加载环境变量配置。

    Returns:
        PaddleOCRVL: 返回初始化的PaddleOCRVL管道实例
    """
    global _PIPELINE_INSTANCE
    if _PIPELINE_INSTANCE is not None:
        return _PIPELINE_INSTANCE
    with _PIPELINE_LOCK:
        if _PIPELINE_INSTANCE is not None:
            return _PIPELINE_INSTANCE
        warnings.filterwarnings("ignore")
        layout_model_path = "models/PaddlePaddle/PP-DocLayoutV2"
        vl_rec_model_path = "models/PaddlePaddle/PaddleOCR-VL"

        # 创建模型目录
        os.makedirs(layout_model_path, exist_ok=True)
        os.makedirs(vl_rec_model_path, exist_ok=True)

        # 加载环境变量配置
        load_dotenv()

        # 初始化PaddleOCRVL实例
        _PIPELINE_INSTANCE = PaddleOCRVL(
            layout_detection_model_dir=layout_model_path,
            vl_rec_model_dir=vl_rec_model_path,
            doc_orientation_classify_model_dir=layout_model_path,
            doc_unwarping_model_dir=layout_model_path,
        )
        return _PIPELINE_INSTANCE


def _is_pdf(p: Path) -> bool:
    """
    判断路径是否为 PDF 文件。

    Args:
        p (Path): 要检查的文件路径对象

    Returns:
        bool: 如果文件扩展名为 .pdf 则返回 True，否则返回 False
    """
    return p.suffix.lower() == ".pdf"


def _is_image(p: Path) -> bool:
    """
    判断路径是否为常见图片格式文件。

    Args:
        p (Path): 要检查的文件路径对象

    Returns:
        bool: 如果文件扩展名为常见图片格式（.png, .jpg, .jpeg, .bmp, .tif, .tiff, .webp）则返回 True，否则返回 False
    """
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
    return p.suffix.lower() in exts


def _collect_images_from_dir(d: Path) -> List[Path]:
    """
    从目录中收集所有图片文件路径（不递归）。

    Args:
        d (Path): 要搜索的目录路径

    Returns:
        List[Path]: 目录中所有图片文件的路径列表，按字母顺序排序
    """
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
    return sorted([p for p in d.iterdir() if p.is_file() and p.suffix.lower() in exts])


def _save_markdown_images(items: List[Dict[str, "object"]], output_dir: Path) -> None:
    """
    将 Markdown 聚合信息中记录的图片对象保存到输出目录的相对路径位置。

    Args:
        items (List[Dict[str, "object"]]): 包含图片对象的列表，每个元素为 {relative_path: PIL.Image} 的字典
        output_dir (Path): 输出目录路径
    """
    for item in items:
        if not item:
            continue
        # 遍历每个图片项，保存到对应的相对路径位置
        for rel_path, image in item.items():
            save_path = output_dir / rel_path
            # 创建必要的父目录
            save_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(save_path)


def _process_pdf(pipeline: PaddleOCRVL, pdf_path: Path, output_dir: Path) -> Path:
    """
    处理单个 PDF 文件：
    - 调用管线预测，聚合多页 Markdown 文本
    - 将对应的页面图片按相对路径保存到输出目录
    - 返回生成的 Markdown 文件路径

    Args:
        pipeline (PaddleOCRVL): OCR处理管线对象
        pdf_path (Path): PDF文件的路径
        output_dir (Path): 输出目录的路径

    Returns:
        Path: 生成的Markdown文件路径
    """
    output = pipeline.predict(input=str(pdf_path))
    markdown_list = []
    markdown_images = []

    # 遍历输出结果，提取markdown文本和图片信息
    for res in output:
        md = res.markdown
        markdown_list.append(md)
        markdown_images.append(md.get("markdown_images", {}))

    # 拼接多页的markdown文本
    texts = pipeline.concatenate_markdown_pages(markdown_list)

    # 生成markdown文件路径并写入文件
    md_path = output_dir / f"{pdf_path.stem}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(texts)

    # 保存markdown中引用的图片
    _save_markdown_images(markdown_images, output_dir)
    logger.info("Markdown 文档生成完成")
    return md_path


def _process_images(
        pipeline: PaddleOCRVL, image_paths: List[Path], output_dir: Path, markdown_filename: str
) -> Path:
    """
    处理一组图片（单张或多张）：
    - 对每张图片调用管线预测并收集 Markdown 片段与页面图片
    - 合并为一个 Markdown 文件
    - 返回生成的 Markdown 文件路径

    Args:
        pipeline (PaddleOCRVL): OCR视觉语言处理管线对象
        image_paths (List[Path]): 待处理的图片文件路径列表
        output_dir (Path): 输出目录路径
        markdown_filename (str): 生成的markdown文件名

    Returns:
        Path: 生成的Markdown文件的完整路径
    """
    markdown_list = []
    markdown_images = []
    for p in image_paths:
        img = cv2.imread(str(p))
        if img is None:
            continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        output = pipeline.predict(img)
        for res in output:
            md = res.markdown
            markdown_list.append(md)
            markdown_images.append(md.get("markdown_images", {}))

    # 合并所有markdown页面内容
    texts = pipeline.concatenate_markdown_pages(markdown_list)
    md_path = output_dir / markdown_filename
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(texts)

    # 保存markdown中引用的图片
    _save_markdown_images(markdown_images, output_dir)
    logger.info("Markdown 文档生成完成")
    return md_path


def extract_content(text: str) -> str:
    """
    调用大模型从 Markdown 文本中抽取结构化 JSON 字符串。
    - 使用 templates.json_data 作为严格的输出模板参考
    - 仅返回纯 JSON 字符串（去除可能的代码块标记）
    """
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("LLM_MODEL_URL"),
    )
    system_prompt = f"""
        你是一个严格的结构化题目信息抽取助手。
        请从给定的 Markdown 文本中抽取题目信息，并【严格按照指定 JSON Schema 输出】。
        只输出 JSON，不允许任何解释、注释、代码块或多余文字。
        ========================
        【总原则（最高优先级，新增细节）】
        ========================
        1. 所有输出字段必须来源于原始 Markdown 明文，包括但不限于：题目开头、题干、选项、解析、答案、题目末尾标注等，需全面扫描文本，不遗漏任何显性信息。
        2. 严禁补全、总结、推理、改写、概括、猜测；但允许“显性信息的直接提取与拼接”（如将分散在题干前后的知识点标签合并）。
        3. 未明确出现的信息：
           - 字符串字段使用 ""
           - 数组字段使用 []
        4. 保留原始 Markdown 与 LaTeX（$...$、$$...$$、\( \)、\[ \]），禁止任何形式改写（包括公式换行、符号替换）；图片、表格、HTML 标签原样保留。
        5. 输出 JSON 必须可被严格解析（无尾逗号、无非法转义，键值对顺序与模板完全一致）。
        ========================
        一、题目拆分与结构判定规则（新增“分隔符”“子问识别”细节，避免漏拆）
        ========================
        1. 【多题拆分判断】：以下情况视为“多道题”，必须拆分为独立 JSON 对象：
           - 文本中出现明确题号（如“1.”“(1)”“第1题”“Question 1”），且题号不连续（如从1跳到2）；
           - 出现空行分隔（连续2个及以上换行符），且前后内容为独立题目（无公共材料关联）；
           - 出现题型/来源标识分隔（如“【选择题】”“2024·北京·期末”后接新题目内容）。
        2. 【单体题】
           满足以下全部条件：
            - 题干中无显式子问编号（(1)(2)、①②③、第1问/小题、Part 1/2）；
            - 题目可整体独立作答（无需要共享的材料，或材料与问题直接绑定不可拆分）；
            → 使用【单体题结构】，sub_questions = []。
        3. 【组合题（母题 + 子题）】
           满足以下任一条件，必须拆分子题，不得遗漏：
            - 题干中出现子问编号：(1)(2)(3)…、①②③…、“第1问/小题”“Part 1/2”“Question 1/2”；
            - 有明确“公共材料”标识（如“材料一”“阅读下列文本”“实验背景”“完形填空文段”），且材料后跟随多个独立问题；
            - 题型为：阅读理解、完形填空、材料分析、实验探究、综合题（含多个子问）；
           → 母题 question_content = 公共材料（含文本、图表、表格，直至子问出现前的所有内容）；
           → 子问拆分要求：
              - 每个子问（含编号）独立拆为 sub_questions 数组中的一个对象；
              - 子问编号需完整保留（如“(1)”“①”“第3小题”），作为子题 question_id 的核心依据；
              - 子问内容包含“问题描述 + 对应选项（若为选择题）”，不得遗漏子问中的选项或图表。
        ========================
        二、JSON 模板（字段顺序不可修改，新增“必检字段”标注）
        ========================
        模板示例：
        {json_data}
        注：标★的字段为“高频遗漏字段”，需重点扫描提取。
        ========================
        三、字段抽取规则（逐字段强化“查找范围”“判断标志”“提取优先级”，解决遗漏）
        ========================
        所有字段均需从 Markdown 全文扫描提取，优先按“提取优先级”查找，不遗漏任何显性信息：
        
        | 字段名          | 提取优先级 | 查找范围                          | 判断标志与提取规则                                                                 |
        |-----------------|------------|-----------------------------------|----------------------------------------------------------------------------------|
        | question_id     | 1          | 题目开头、题干前、子问前          | 1. 优先提取明确题号（如“1.”“(2)”“第3题”），去除标点保留核心编号（如“1”“2”“3”）；<br>2. 无明确题号时，按题目出现顺序编号（“1”“2”…）；<br>3. 子题 question_id：提取子问编号（如“(1)”→“1”，“①”→“1”，“第2小题”→“2”）。 |
        | grade           | -          | 无（固定填充）                    | 固定为 ""（不可修改）。                                                           |
        | volume          | -          | 无（固定填充）                    | 固定为 ""（不可修改）。                                                           |
        | chapter         | -          | 无（固定填充）                    | 固定为 ""（不可修改）。                                                           |
        | section         | -          | 无（固定填充）                    | 固定为 ""（不可修改）。                                                           |
        | subject         | -          | 无（固定填充）                    | 固定为 ""（不可修改）。                                                           |
        | question_content| 2（★高频漏）| 题目核心内容（不含选项、子问）    | 1. 单体题：从题目开头到选项前（无选项则到答案前）的所有内容（含文本、LaTeX、图表描述）；<br>2. 组合题：公共材料（含“材料X”“阅读下列文本”等引导语 + 材料内容，直至第一个子问出现前）；<br>3. 若题干包含表格，表格原样纳入 question_content（同时同步到 question_tables 字段）。 |
        | question_options| 3（★高频漏）| 题干中、子问中                    | 1. 识别标志：“A.”“B.”“C.”“D.”“A、”“B、”“①”“②”（选项前缀）；<br>2. 提取范围：从“A.”到最后一个选项（如“D.”）的完整内容，保留原始格式（含 LaTeX、图片标签、括号）；<br>3. 子题选项：仅对应子问下的选项，独立提取到该子题的“option”字段；<br>4. 多选/不定项：按原样提取，不改变顺序（如“A、B”需拆分为["A. XXX","B. XXX"]）。 |
        | question_images | 4（★高频漏）| 题干全文、子问内容                | 1. 识别标志：Markdown 图片语法（![alt](path)）、HTML 图片标签（<img src="path">）；<br>2. 提取规则：仅提取“path”（相对路径原样保留），每一个图片路径对应一个数组元素；<br>3. 子题图片：提取到该子题的“image”字段（同时不重复纳入母题 question_images）。 |
        | question_tables | 5（★高频漏）| 题干全文、子问内容                | 1. 识别标志：Markdown 表格语法（| 表头 | 内容 |）；<br>2. 提取规则：完整保留表格原始字符串，每一个表格对应一个数组元素；<br>3. 子题表格：同步纳入该子题的“question”字段和母题 question_tables。 |
        | analysis_images | 6          | 解析部分（resolve 对应内容）      | 同 question_images 提取规则，仅提取解析中的图片路径。                               |
        | difficulty      | 7（★高频漏）| 题目开头、题目末尾、解析前        | 1. 识别标志：“容易”“中等”“困难”“较易”“较难”+ 括号内数值（如“(0.85)”“(0.6)”）；<br>2. 提取格式：保留原始表述（如“容易(0.85)”“中等”），无则为 ""。 |
        | question_type   | 8（★高频漏）| 题目开头、题目末尾、题型标签      | 1. 识别标志：“【选择题】”“【填空题】”“【解答题】”“【实验探究题】”“阅读题”“完形填空”；<br>2. 提取规则：直接提取标志中的题型名称（如“选择题”“填空题”），无则为 ""；<br>3. 子题题型：若子问有明确题型（如“(1) 选择题”），提取到该子题的“question_type”字段。 |
        | source          | 9（★高频漏）| 题目开头、题目末尾、括号内        | 1. 识别标志：“·”分隔符（如“2024·江苏·期末”）、“真题”“期末”“月考”“模拟”（来源关键词）；<br>2. 提取范围：包含年份、地区、考试类型的完整字符串（如“23-24年七年级上·江苏南京·期末”“2025年广东省广州市中考数学真题”）；<br>3. 无明确来源则为 ""。 |
        | knowledge_points| 10（★高频漏）| 题目开头、题目末尾、标签栏、解析  | 1. 识别标志：“知识点：”“考查知识点：”“关键词：”（引导语）、中文逗号/顿号分隔的学科术语（如“欧姆定律、电路实验”）；<br>2. 提取规则：拆分单个知识点为数组元素（如“科学实验方法、数据分析”→["科学实验方法","数据分析"]）；<br>3. 解析中出现的知识点（如“本题考查欧姆定律”），可直接提取术语（“欧姆定律”）纳入数组；<br>4. 无明确知识点则为 []。 |
        | sub_questions   | 11（★高频漏）| 组合题中、公共材料后              | 1. 识别标志：子问编号（(1)(2)、①②③、第1问/小题、Part 1/2）；<br>2. 拆分规则：<br>   - 每个子问独立为一个对象，按出现顺序排列；<br>   - 子题“question”：子问编号 + 问题描述（如“(1) 简述控制变量的方法”），含该子问下的文本、LaTeX、图表；<br>   - 子题“option”：仅该子问下的选项（同 question_options 提取规则）；<br>   - 子题“image”：仅该子问下的图片路径（同 question_images 提取规则）；<br>3. 完形填空：每个空格视为一个子题（question_id 按“1”“2”…编号，“question”为空字符串，“option”为该空格的选项）。 |
        | answer          | 12（★高频漏）| 题目末尾、“答案：”“参考答案：”后  | 1. 识别标志：“答案：”“参考答案：”“正确答案：”（引导语）；<br>2. 提取规则：<br>   - 选择题：直接提取选项字母（如“A”“A,C”，小写转大写）；<br>   - 子题答案：按子题编号对应提取（如“(1)A (2)B”→“1.A,2.B”）；<br>   - 非选择题：提取引导语后的完整内容（含文本、LaTeX、公式）；<br>3. 无明确答案则为 ""。 |
        | resolve         | 13         | 题目末尾、“解析：”“解题步骤：”后  | 1. 识别标志：“解析：”“解题步骤：”“思路分析：”（引导语）；<br>2. 提取范围：从引导语到下一道题/文本结束的所有内容（含 LaTeX、图表、公式）；<br>3. 无解析则为 ""。 |
        | source_year     | 14（★高频漏）| source 字段、题目开头             | 1. 识别标志：四位数数字（如“2024”“2025”）；<br>2. 提取规则：从 source 字段或题目开头直接提取四位数年份（如“23-24年”→“2024”，“2025年中考”→“2025”）；<br>3. 无明确四位数年份则为 ""。 |
        | source_province | 15（★高频漏）| source 字段、题目开头             | 1. 识别标志：省级行政区名称（如“江苏”“广东”“北京”）、市级名称（如“南京”“广州”）；<br>2. 提取规则：从 source 字段中提取地区名称（如“江苏南京”→“江苏”，“广东省广州市”→“广东”）；<br>3. 无明确地区则为 ""。 |
        ========================
        四、多题处理强化规则（避免漏拆/合并）
        ========================
        1. 多题分隔符优先级（按顺序判断）：
           - 明确题号（如“1.”“(2)”“第3题”）；
           - 空行（连续2个及以上 \n）；
           - 题型标识（如“【填空题】”“【解答题】”）；
           - 来源标识（如“2024·浙江·期末”“2025·广东·真题”）。
        2. 若题目间无明显分隔符，但内容独立（如无公共材料、题型不同），按“答案/解析结束”为分隔点拆分。
        3. 严禁将多道题合并为一个 JSON 对象，严禁遗漏任何一道题（包括末尾无答案/解析的题目）。
        ========================
        五、常见遗漏场景专项处理（新增，强制覆盖）
        ========================
        1. 选项中包含图片/LaTeX：完整保留，不得删除或迁移到其他字段；
        2. 题干中隐藏的知识点（如解析首句“本题考查XXX”）：必须提取到 knowledge_points；
        3. 子问中包含独立选项/图片：单独提取到该子题的“option”“image”字段，不得遗漏；
        4. 组合题中子问无编号但有明确分隔（如“请回答以下问题：1. XXX 2. XXX”）：按顺序拆分为子题；
        5. 来源字段分散（如“2024年 江苏 期末”）：拼接为完整字符串（“2024·江苏·期末”）；
        6. 难度仅含数值（如“0.7”）：直接提取为“0.7”（无需补充“中等”等文字）；
        7. 答案为公式/表达式（如“$x=3$”）：原样保留，不得简化。
        ========================
        六、输出校验要求（新增，强制执行）
        ========================
        1. 字段完整性校验：所有 JSON 对象必须包含模板中的全部字段（无缺失字段）；
        2. 高频漏字段校验：question_options、question_images、question_tables、difficulty、question_type、source、knowledge_points、source_year、source_province 必须再次扫描确认，不得无故为空；
        3. 格式合法性校验：JSON 无尾逗号、无非法转义（如 \n 保留，不转为 \\n）、数组/对象闭合；
        4. 内容一致性校验：question_tables 与 question_content 中的表格一致，question_images 与题干中的图片路径一致，无重复/遗漏。

    """
    user_prompt = """
    请从以下文本中提取出用户感兴趣的内容：
    """ + text
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL_NAME"),
        # model="qwen3-next-80b-a3b-instruct",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    content = response.choices[0].message.content
    try:
        import re
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if m:
            return m.group(1).strip()
        return content.strip()
    except Exception:
        return content


def _to_base64(fp: str) -> str:
    """
    将本地文件读取为 base64 编码字符串（ASCII）。

    Args:
        fp (str): 本地文件路径

    Returns:
        str: base64编码的ASCII字符串
    """
    # 以二进制模式打开文件并读取内容，然后进行base64编码并解码为ASCII字符串
    with open(fp, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _convert_paths(paths, base_dir: str, cache: Dict[str, str] | None = None, to_delete: Set[str] | None = None):
    """
    将路径数组中的本地图片路径转换为 base64。
    - http/https/data: 开头的字符串保持原样
    - 相对路径按 base_dir 拼接
    - 文件不存在则保留原字符串

    Args:
        paths: 路径列表，包含各种类型的路径字符串
        base_dir: 基础目录路径，用于拼接相对路径
        cache: 可选的缓存字典，用于存储已转换的文件路径和对应的base64编码
        to_delete: 可选的集合，用于记录需要删除的文件路径

    Returns:
        转换后的路径列表，本地图片路径被转换为base64格式，其他路径保持不变
    """
    result = []
    for p in paths:
        if not isinstance(p, str):
            result.append(p)
            continue
        # 检查是否为网络路径或data URI，如果是则直接保留
        if p.startswith("http://") or p.startswith("https://") or p.startswith("data:"):
            result.append(p)
            continue
        # 构建完整路径，绝对路径直接使用，相对路径与base_dir拼接
        full = p if os.path.isabs(p) else os.path.join(base_dir, p)
        # 检查文件是否存在
        if os.path.isfile(full):
            # 检查缓存中是否已有该文件的base64编码
            if cache is not None and full in cache:
                b64 = cache[full]
            else:
                # 转换文件为base64并更新缓存
                b64 = _to_base64(full)
                if cache is not None:
                    cache[full] = b64
                # 记录需要删除的文件路径
                if to_delete is not None:
                    to_delete.add(full)
            result.append(b64)
        else:
            # 文件不存在则保留原路径
            result.append(p)
    return result


def _transform_item(item, base_dir: str, cache: Dict[str, str] | None = None, to_delete: Set[str] | None = None):
    """
    对单个题目项进行转换：
    - question_images / analysis_images 转为 base64
    - 递归处理 sub_questions

    Args:
        item: 待转换的题目项，可以是字典或其他类型
        base_dir (str): 基础目录路径，用于文件路径转换
        cache (Dict[str, str] | None): 缓存字典，用于存储已转换的路径映射关系，默认为None
        to_delete (Set[str] | None): 待删除的文件路径集合，默认为None

    Returns:
        转换后的题目项，如果输入不是字典则直接返回原值
    """
    if not isinstance(item, dict):
        return item
    # 处理题目图片列表，将路径转换为base64格式
    if "question_images" in item and isinstance(item["question_images"], list):
        item["question_images"] = _convert_paths(item["question_images"], base_dir, cache, to_delete)
    # 处理解析图片列表，将路径转换为base64格式
    if "analysis_images" in item and isinstance(item["analysis_images"], list):
        item["analysis_images"] = _convert_paths(item["analysis_images"], base_dir, cache, to_delete)
    # 递归处理子题目列表
    if "sub_questions" in item and isinstance(item["sub_questions"], list):
        item["sub_questions"] = [_transform_item(x, base_dir, cache, to_delete) for x in item["sub_questions"]]
    return item


def _mime_from_ext(fp: str) -> str:
    ext = os.path.splitext(fp)[1].lower()
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    if ext in {".bmp"}:
        return "image/bmp"
    if ext in {".gif"}:
        return "image/gif"
    if ext in {".tif", ".tiff"}:
        return "image/tiff"
    return "application/octet-stream"


def _inline_convert_images_in_text(s: str, base_dir: str, cache: Dict[str, str] | None = None,
                                   to_delete: Set[str] | None = None) -> str:
    try:
        import re
        def _convert_path(path: str) -> str:
            if not isinstance(path, str):
                return path
            if path.startswith("http://") or path.startswith("https://") or path.startswith("data:"):
                return path
            full = path if os.path.isabs(path) else os.path.join(base_dir, path)
            if os.path.isfile(full):
                if cache is not None and full in cache:
                    b64 = cache[full]
                else:
                    b64 = _to_base64(full)
                    if cache is not None:
                        cache[full] = b64
                if to_delete is not None:
                    to_delete.add(full)
                mime = _mime_from_ext(full)
                return f"data:{mime};base64,{b64}"
            return path

        def _html_double(m):
            pre, path, post = m.group(1), m.group(2), m.group(3)
            if path.startswith("imgs/") or os.path.isabs(path):
                return pre + _convert_path(path) + post
            return m.group(0)

        def _html_single(m):
            pre, path, post = m.group(1), m.group(2), m.group(3)
            if path.startswith("imgs/") or os.path.isabs(path):
                return pre + _convert_path(path) + post
            return m.group(0)

        def _markdown(m):
            pre, path, post = m.group(1), m.group(2), m.group(3)
            if path.startswith("imgs/") or os.path.isabs(path):
                return pre + _convert_path(path) + post
            return m.group(0)

        s = re.sub(r'(<img\b[^>]*\bsrc\s*=\s*")([^"]+)(")', _html_double, s, flags=re.IGNORECASE)
        s = re.sub(r"(<img\b[^>]*\bsrc\s*=\s*')([^']+)(')", _html_single, s, flags=re.IGNORECASE)
        s = re.sub(r'(!\[[^\]]*\]\()([^)]+)(\))', _markdown, s)
        return s
    except Exception:
        return s


def _transform_strings(value, base_dir: str, cache: Dict[str, str] | None = None, to_delete: Set[str] | None = None):
    if isinstance(value, str):
        return _inline_convert_images_in_text(value, base_dir, cache, to_delete)
    if isinstance(value, list):
        return [_transform_strings(x, base_dir, cache, to_delete) for x in value]
    if isinstance(value, dict):
        return {k: _transform_strings(v, base_dir, cache, to_delete) for k, v in value.items()}
    return value


def convert_images_in_json(json_input: str, base_dir: str = ".") -> str:
    """
    将 JSON 字符串中的图片路径批量转换为 base64 字符串。
    支持顶层对象为列表或字典；解析失败时返回原始输入。

    参数:
        json_input (str): 包含图片路径的JSON字符串
        base_dir (str): 图片文件的基础目录，默认为当前目录

    返回:
        str: 将图片路径替换为base64编码后的JSON字符串
    """
    try:
        data = json.loads(json_input)
    except json.JSONDecodeError:
        try:
            import re
            s = _inline_convert_images_in_text(json_input, base_dir)

            def _to_b64_text(m):
                rel = m.group(1)
                full = rel if os.path.isabs(rel) else os.path.join(base_dir, rel)
                if os.path.isfile(full):
                    return '"' + _to_base64(full) + '"'
                return '"' + rel + '"'

            return re.sub(r'"(imgs/[^"]+)"', _to_b64_text, s)
        except Exception:
            return json_input

    cache: Dict[str, str] = {}
    to_delete: Set[str] = set()

    # 根据数据类型处理图片路径转换
    if isinstance(data, list):
        data = [_transform_item(x, base_dir, cache, to_delete) for x in data]
        data = [_transform_strings(x, base_dir, cache, to_delete) for x in data]
    elif isinstance(data, dict):
        data = _transform_item(data, base_dir, cache, to_delete)
        data = _transform_strings(data, base_dir, cache, to_delete)

    s = json.dumps(data, ensure_ascii=False)

    # 检查转换后的字符串中是否还有未处理的图片路径，如有则用正则表达式处理
    try:
        import re
        if "imgs/" in s:
            def _to_b64_text(m):
                rel = m.group(1)
                full = rel if os.path.isabs(rel) else os.path.join(base_dir, rel)
                if os.path.isfile(full):
                    return '"' + _to_base64(full) + '"'
                return '"' + rel + '"'

            s = re.sub(r'"(imgs/[^"]+)"', _to_b64_text, s)
        s = _inline_convert_images_in_text(s, base_dir, cache, to_delete)
    except Exception:
        pass

    # 清理临时文件
    try:
        for fp in to_delete:
            try:
                os.remove(fp)
            except Exception:
                pass
    finally:
        return s


def run_unified(input_arg: str | List[str], output_dir: str | Path) -> str:
    """
    统一入口：
    - 接受单个路径或路径列表（图片/目录/PDF 混合）
    - 生成合并 Markdown 与图片资源
    - 调用大模型抽取 JSON 并将图片路径转为 base64
    - 删除中间 Markdown 文件
    - 返回最终 JSON 字符串
    """
    # 统一入口：接收路径或路径列表，产出最终 JSON
    logger.info("文件预处理开始")
    # 初始化 OCR-VL 管线与输出目录
    pipeline = _init_pipeline()
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # 聚合 Markdown 文本及页面图片信息
    markdown_list = []
    markdown_images = []
    if isinstance(input_arg, list):
        paths = [Path(x) for x in input_arg]
        # 过滤无效路径
        valid = [p for p in paths if p.exists()]
        if not valid:
            raise ValueError("no valid inputs")
        # 逐项处理：目录 / PDF / 图片
        for p in valid:
            if p.is_dir():
                # 目录：收集图片并逐张推理，累计 Markdown 与图片
                imgs = _collect_images_from_dir(p)
                for ip in imgs:
                    img = cv2.imread(str(ip))
                    if img is None:
                        continue
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    output = pipeline.predict(img)
                    for res in output:
                        md = res.markdown
                        markdown_list.append(md)
                        markdown_images.append(md.get("markdown_images", {}))
            elif p.is_file() and _is_pdf(p):
                # 单个 PDF：直接推理，累计 Markdown 与图片
                output = pipeline.predict(input=str(p))
                for res in output:
                    md = res.markdown
                    markdown_list.append(md)
                    markdown_images.append(md.get("markdown_images", {}))
            elif p.is_file() and _is_image(p):
                # 单张图片：推理，累计 Markdown 与图片
                img = cv2.imread(str(p))
                if img is None:
                    continue
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                output = pipeline.predict(img)
                for res in output:
                    md = res.markdown
                    markdown_list.append(md)
                    markdown_images.append(md.get("markdown_images", {}))
            else:
                continue
        # 所有输入均无有效内容，抛错
        if not markdown_list:
            raise ValueError("no valid image or pdf content")
        md_name = "combined.md"
        # 合并 Markdown 文本
        texts = pipeline.concatenate_markdown_pages(markdown_list)
        md_path = out_dir / md_name
        # 写入合并 Markdown 并保存页面图片
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(texts)
        _save_markdown_images(markdown_images, out_dir)
        logger.info("Markdown 文档生成完成")
        # 从 Markdown 抽取结构化 JSON
        content = extract_content(texts)
        logger.info("大模型推理并输出结构化结果完成")
        logger.info("图片资源 Base64 转换开始")
        # 图片路径转 Base64
        converted = convert_images_in_json(content, base_dir=str(out_dir))
        logger.info("图片 Base64 转换完成")
        try:
            # 清理中间 Markdown 文件
            os.remove(md_path)
        except Exception:
            pass
        logger.info("临时缓存文件清理完成")
        # 返回最终 JSON 字符串
        return converted
    p = Path(input_arg)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if p.is_file():
        if _is_pdf(p):
            # 处理单个文件：PDF
            md_path = _process_pdf(pipeline, p, out_dir)
            with open(md_path, "r", encoding="utf-8") as f:
                texts = f.read()
            content = extract_content(texts)
            logger.info("大模型推理并输出结构化结果完成")
            logger.info("图片资源 Base64 转换开始")
            # 抽取 JSON 并进行 Base64 转换
            converted = convert_images_in_json(content, base_dir=str(out_dir))
            logger.info("图片 Base64 转换完成")
            try:
                # 清理中间文件
                os.remove(md_path)
            except Exception:
                pass
            logger.info("临时缓存文件清理完成")
            return converted
        if _is_image(p):
            # 处理单个文件：图片
            md_path = _process_images(pipeline, [p], out_dir, f"{p.stem}.md")
            with open(md_path, "r", encoding="utf-8") as f:
                texts = f.read()
            content = extract_content(texts)
            logger.info("大模型推理并输出结构化结果完成")
            logger.info("图片资源 Base64 转换开始")
            # 抽取 JSON 并进行 Base64 转换
            converted = convert_images_in_json(content, base_dir=str(out_dir))
            logger.info("图片 Base64 转换完成")
            try:
                # 清理中间文件
                os.remove(md_path)
            except Exception:
                pass
            logger.info("临时缓存文件清理完成")
            return converted
        raise ValueError("unsupported file type")
    if p.is_dir():
        # 处理目录：收集图片并生成 Markdown
        imgs = _collect_images_from_dir(p)
        if not imgs:
            raise ValueError("no images found in directory")
        name = f"{p.name}.md" if len(imgs) > 1 else f"{imgs[0].stem}.md"
        md_path = _process_images(pipeline, imgs, out_dir, name)
        with open(md_path, "r", encoding="utf-8") as f:
            texts = f.read()
        content = extract_content(texts)
        logger.info("大模型推理并输出结构化结果完成")
        logger.info("图片资源 Base64 转换开始")
        # 抽取 JSON 并进行 Base64 转换
        converted = convert_images_in_json(content, base_dir=str(out_dir))
        logger.info("图片 Base64 转换完成")
        try:
            # 清理中间文件
            os.remove(md_path)
        except Exception:
            pass
        logger.info("临时缓存文件清理完成")
        return converted
    raise ValueError("invalid input")


def _build_arg_parser() -> argparse.ArgumentParser:
    """
    构建命令行参数解析器：
    - input 支持多个路径
    - output 指定资源输出目录
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, nargs="+")
    parser.add_argument("-o", "--output", default=str(Path(__file__).parent / "output"))
    return parser


def main() -> None:
    """
    CLI 入口：解析参数并调用 run_unified，打印最终 JSON。
    """
    parser = _build_arg_parser()
    args = parser.parse_args()
    input_arg = args.input if len(args.input) > 1 else args.input[0]
    result_json = run_unified(input_arg, args.output)
    try:
        paths = [Path(x) for x in args.input]
        if len(paths) > 1:
            dirs = [p for p in paths if p.is_dir()]
            save_dir = dirs[0] if dirs else paths[0].parent
            json_name = "combined.json"
        else:
            p = paths[0]
            save_dir = p if p.is_dir() else p.parent
            json_name = (p.name if p.is_dir() else p.stem) + ".json"
        save_dir.mkdir(parents=True, exist_ok=True)
        with open(save_dir / json_name, "w", encoding="utf-8") as f:
            f.write(result_json)
    except Exception:
        pass
    print(result_json)


if __name__ == "__main__":
    main()
