import base64
import json
import os
import re
import uuid
from io import BytesIO
from urllib.parse import quote

import requests
from PIL import Image

# ======================================================
# 1. Base64 -> 文件 -> 上传（你原有逻辑，微调安全性）
# ======================================================

def base64_to_file_and_upload(base64_str, file_field_name='file', ext='jpg'):
    temp_filename = f"{uuid.uuid4().hex}.{ext}"
    api_url = "http://222.85.202.67:689/school-api/public-resource/uploadNuoen"
    auth_token = "RAuwGBaukHPcsU3FprBQxwaMdx3GVdENzmF74WTNM6VHcmADSU"

    try:
        # 去 data:image 前缀
        pure_base64 = re.sub(r'^data:image/.+;base64,', '', base64_str, flags=re.I)

        image_data = base64.b64decode(pure_base64)
        image = Image.open(BytesIO(image_data))
        image.save(temp_filename)

        headers = {'AI-token': auth_token}
        with open(temp_filename, 'rb') as f:
            files = {file_field_name: f}
            resp = requests.post(api_url, headers=headers, files=files)

        if resp.status_code != 200:
            print(f"上传失败: {resp.status_code}")
            return None

        result = resp.json()
        if isinstance(result, dict) and 'url' in result:
            url = result['url'].replace(
                'http://127.0.0.1:48180',
                'http://222.85.202.67:689/school-api'
            )

            if '://' in url:
                proto, rest = url.split('://', 1)
                if '/' in rest:
                    domain, path = rest.split('/', 1)
                    path = quote(path, safe='/:@!$&\'()*+,;=')
                    return f"{proto}://{domain}/{path}"

            return url

        return None

    except Exception as e:
        print(f"上传异常: {e}")
        return None

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


# ======================================================
# 2. Base64 识别规则（纯 / data URI）
# ======================================================

DATA_URI_PATTERN = re.compile(
    r'^data:image/(png|jpe?g|gif|webp);base64,',
    re.I
)

PURE_BASE64_PATTERN = re.compile(
    r'^[A-Za-z0-9+/=\s]{200,}$'
)

def is_pure_base64_image(s: str) -> bool:
    if not isinstance(s, str):
        return False
    s = s.strip()
    if s.startswith('/9') and PURE_BASE64_PATTERN.match(s):
        return True
    return False


# ======================================================
# 3. HTML <img src="base64"> 替换
# ======================================================

IMG_BASE64_PATTERN = re.compile(
    r'(<img[^>]+src=["\'])(data:image/[^"\']+|/9[^"\']+)(["\'])',
    re.I
)

_base64_cache = {}

def replace_base64_in_html(html: str) -> str:
    def _repl(match):
        prefix, base64_data, suffix = match.groups()

        if base64_data in _base64_cache:
            return f"{prefix}{_base64_cache[base64_data]}{suffix}"

        print("发现 HTML Base64，开始上传...")
        url = base64_to_file_and_upload(base64_data)

        if url:
            _base64_cache[base64_data] = url
            return f"{prefix}{url}{suffix}"

        return match.group(0)

    return IMG_BASE64_PATTERN.sub(_repl, html)


# ======================================================
# 4. JSON 递归：任意位置替换
# ======================================================

def replace_base64_in_json(obj):

    if isinstance(obj, dict):
        return {k: replace_base64_in_json(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [replace_base64_in_json(v) for v in obj]

    if isinstance(obj, str):

        # 1️⃣ HTML 内嵌 base64
        if '<img' in obj and ('base64' in obj or obj.strip().startswith('/9')):
            obj = replace_base64_in_html(obj)

        # 2️⃣ 整个字符串就是 base64
        if DATA_URI_PATTERN.match(obj) or is_pure_base64_image(obj):
            if obj in _base64_cache:
                return _base64_cache[obj]

            print("发现纯 Base64，开始上传...")
            url = base64_to_file_and_upload(obj)
            if url:
                _base64_cache[obj] = url
                return url

        return obj

    return obj


# ======================================================
# 5. JSON 文件 / 文件夹处理
# ======================================================

def process_json_file(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    new_data = replace_base64_in_json(data)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)


def process_json_folder(input_dir, output_dir):
    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('.json'):
                continue

            in_path = os.path.join(root, file)
            rel = os.path.relpath(in_path, input_dir)
            out_path = os.path.join(output_dir, rel)

            print(f"处理文件: {in_path}")
            process_json_file(in_path, out_path)

if __name__ == "__main__":
    # 单文件
    # process_json_file("output/separate/2.json", "output.json")
    #
    # 文件夹output
    process_json_folder(
        input_dir="./images",
        output_dir="./images"
    )
