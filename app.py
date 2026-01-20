import asyncio
import json
import uuid
from pathlib import Path
from typing import List, Tuple

import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from scipy.special.cython_special import wofz

from main import run_unified
import logging

# 应用初始化
app = FastAPI(
    title="PaddleOCR-VL 文档解析服务",
    description="接收图片或单个 PDF，进行文档解析并输出结构化 JSON（图片以 base64 表示）。",
    version="1.0.0",
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("paddleocr_vl")


def _classify_files(files: List[UploadFile]) -> Tuple[List[UploadFile], List[UploadFile], List[str]]:
    """
    将上传文件按类型分类为图片列表与 PDF 列表，并返回警告列表。
    - 允许的图片后缀：.png/.jpg/.jpeg/.bmp/.tif/.tiff/.webp
    - 允许的 PDF 后缀：.pdf
    """
    allowed_img_exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
    images, pdfs, warnings = [], [], []
    for f in files:
        name = f.filename or ""
        ext = Path(name).suffix.lower()
        if ext in allowed_img_exts:
            images.append(f)
        elif ext == ".pdf":
            pdfs.append(f)
        else:
            warnings.append(f"不支持的文件类型: {name}")
    return images, pdfs, warnings


async def _save_uploads(request_id: str, files: List[UploadFile]) -> List[Path]:
    """
    将上传的文件保存到本地临时目录 uploads/{request_id}/ 并返回本地路径列表。
    """
    base_dir = Path(__file__).parent / "uploads" / request_id
    base_dir.mkdir(parents=True, exist_ok=True)
    local_paths: List[Path] = []
    for idx, f in enumerate(files):
        # 为避免重名覆盖，前缀加序号
        filename = f.filename or f"file_{idx}"
        local_path = base_dir / filename
        content = await f.read()
        local_path.write_bytes(content)
        local_paths.append(local_path)
    return local_paths


def _map_error_to_status(err: Exception) -> int:
    """
    将内部错误映射为 HTTP 状态码。
    """
    msg = str(err).lower()
    if isinstance(err, FileNotFoundError):
        return 400
    if isinstance(err, ValueError):
        return 400
    # 其他异常视为服务端错误
    return 500


@app.get("/health")
async def health():
    """
    健康检查接口。
    """
    return {"status": "ok"}


@app.post("/parse-docs")
async def parse_docs(files: List[UploadFile] = File(...), background_tasks: BackgroundTasks = None):
    """
    文档解析接口（multipart/form-data）：
    - 参数名：files（支持单张/多张图片，或单个 PDF）
    - 返回：结构化 JSON，其中图片字段已转换为 base64
    - 失败场景：文件为空、类型不支持、PDF 数量超限、模型/抽取失败等
    """
    if not files:
        raise HTTPException(status_code=400, detail="未接收到文件")

    # 分类与基本校验
    images, pdfs, warnings = _classify_files(files)
    if not images and not pdfs:
        raise HTTPException(status_code=400, detail="无有效的图片或 PDF 文件")
    if len(pdfs) > 1:
        raise HTTPException(status_code=400, detail="仅支持上传单个 PDF 文件")
    fmt = "图片" if images and not pdfs else "PDF" if pdfs and not images else "图片+PDF"
    logger.info(f"文件接收成功（格式：{fmt}）")

    request_id = uuid.uuid4().hex
    output_dir = Path(__file__).parent / "output" / "api" / request_id
    uploads_dir = Path(__file__).parent / "uploads" / request_id

    try:
        # 将有效文件保存到本地
        to_save = images + pdfs
        saved_paths = await _save_uploads(request_id, to_save)
        # 组装输入：允许图片与单个 PDF 混合
        input_arg = [str(p) for p in saved_paths]
        # 同步调用耗时函数，避免阻塞事件循环
        result_json = await asyncio.to_thread(run_unified, input_arg, output_dir)
        # 解析为对象
        try:
            data = json.loads(result_json)
        except Exception:
            # 若解析失败，原样返回字符串
            data = result_json
        if background_tasks is not None:
            background_tasks.add_task(shutil.rmtree, uploads_dir, ignore_errors=True)
        return JSONResponse(
            {
                "success": True,
                "request_id": request_id,
                "data": data,
                "errors": [],
                "warnings": warnings,
            },
            background=background_tasks,
        )
    except Exception as e:
        status = _map_error_to_status(e)
        if background_tasks is not None:
            background_tasks.add_task(shutil.rmtree, uploads_dir, ignore_errors=True)
        return JSONResponse(
            {
                "success": False,
                "request_id": request_id,
                "data": None,
                "errors": [str(e)],
                "warnings": warnings,
            },
            status_code=status,
            background=background_tasks,
        )

# 启动服务自定义API服务
# uvicorn app:app --host 0.0.0.0 --port 8080 --workers 4 --log-level info
