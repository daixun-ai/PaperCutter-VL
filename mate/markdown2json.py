import os
import json
import base64

from dotenv import load_dotenv
from openai import OpenAI

from templates import json_data

load_dotenv()


def extract_content(text: str) -> str:
    """
    从用户输入的文本中提取出用户感兴趣的内容。
    """
    client = OpenAI(
        api_key=os.getenv("LLM_MODEL_API_KEY"),
        base_url=os.getenv("LLM_MODEL_URL"),
    )

    system_prompt = f"""
    你是一个结构化信息抽取助手。请从给定的 Markdown 文本中抽取题目相关信息，并严格按照下述 JSON 模板输出，且仅输出 JSON（不要额外的解释、不要代码块、不要反引号）。
    模板（字段与顺序必须一致）：
    {json_data}
    
    字段解释与抽取规则：
    - question_id：题目唯一编号，优先从题号中提取；缺失时按出现顺序编号（字符串）。
    - grade：年级信息，如“七年级”“八年级”等；缺失则为空字符串。
    - required_optional：必修/选修或类似属性；缺失则为空字符串。
    - chapter：所属章节，如“第六章 实数”；从标题或上下文提取；缺失则为空字符串。
    - section：所属小节，如“6.1 平方根、立方根”；缺失则为空字符串。
    - question_content：题干全文，保留原有格式与 LaTeX（例如 $...$ 或 \\(...\\)）。
    - question_options：选项数组，按 A/B/C/D 等顺序列出，保留 LaTeX 与原格式；没有选项则为空数组。
    - question_images：题干中的图片路径数组，从 Markdown 的图片语法中提取（如 ![alt](imgs/xxx.png)），保持相对路径不改写；没有则为空数组。
    - question_tables：题干中的表格，若存在，用 Markdown 表格字符串表示，每张表一个字符串放入数组；没有则为空数组。
    - analysis_images：解析部分涉及的图片路径数组，保持相对路径；没有则为空数组。
    - difficulty：难度等级，如“简单”“中等”“困难”等；无法判断则为空字符串。
    - question_type：题型，如“选择题”“填空题”“判断题”“解答题”等；无法判断则为空字符串。
    - sub_questions：若题干包含(1)(2)…等子问，按出现顺序提取子问题干文本，作为字符串数组；不存在则为空数组。
    - answer：标准答案，选择题用“A”“B”或“C”等；多选用逗号分隔如“A,C”；非选择题直接填文字或表达式；缺失则为空字符串。
    - resolve：解析或解题过程，保留 LaTeX 与原格式；缺失则为空字符串。
    - source_year：来源年份（四位数），缺失则为空字符串。
    - source_province：来源省份或地区或试卷名称，缺失则为空字符串。
    
    抽取要求：
    - 若 Markdown 中包含多道题，请输出为一个 JSON 数组，数组中每个元素为一题的结构化结果。
    - 保留所有 LaTeX 表达式与数学符号，不要转义或改写。
    - 所有图片路径使用文中出现的相对路径（例如 imgs/xxx.png），不要转换为绝对路径。
    - 缺失信息使用空字符串 "" 或空数组 []，不要编造。
    - 严格输出为可解析的 JSON（无多余文字、无解释、无代码块标记）。
    """
    user_prompt = """
    请从以下文本中提取出用户感兴趣的内容：
    """ + text

    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL_NAME"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    return response.choices[0].message.content.replace("```", "").replace("```json", "").replace("json", "")

def _to_base64(fp: str) -> str:
    with open(fp, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def _convert_paths(paths, base_dir: str):
    result = []
    for p in paths:
        if not isinstance(p, str):
            result.append(p)
            continue
        if p.startswith("http://") or p.startswith("https://") or p.startswith("data:"):
            result.append(p)
            continue
        full = p if os.path.isabs(p) else os.path.join(base_dir, p)
        if os.path.isfile(full):
            result.append(_to_base64(full))
        else:
            result.append(p)
    return result

def _transform_item(item, base_dir: str):
    if not isinstance(item, dict):
        return item
    if "question_images" in item and isinstance(item["question_images"], list):
        item["question_images"] = _convert_paths(item["question_images"], base_dir)
    if "analysis_images" in item and isinstance(item["analysis_images"], list):
        item["analysis_images"] = _convert_paths(item["analysis_images"], base_dir)
    if "sub_questions" in item and isinstance(item["sub_questions"], list):
        item["sub_questions"] = [_transform_item(x, base_dir) for x in item["sub_questions"]]
    return item

def convert_images_in_json(json_input: str, base_dir: str = ".") -> str:
    try:
        data = json.loads(json_input)
    except json.JSONDecodeError:
        return json_input
    if isinstance(data, list):
        data = [_transform_item(x, base_dir) for x in data]
    elif isinstance(data, dict):
        data = _transform_item(data, base_dir)
    return json.dumps(data, ensure_ascii=False)

with open("output/1.md", "r", encoding="utf-8") as f:
    text = f.read()
    content = extract_content(text)
    print(content)
    print("\n\n+\n\n")
    print(convert_images_in_json(content, base_dir="../output"))
