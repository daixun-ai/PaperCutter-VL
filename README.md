# PaperCutter-VL

PaperCutter-VL 是一个基于 PaddleOCR-VL 的试卷切题与结构化解析工具，面向扫描版试卷/教辅资料等教育场景。通过视觉-语言模型识别试题内容，生成标准化 Markdown，再结合大模型进行结构化信息抽取，最终输出题目级 JSON 数据（内含图片 Base64）。

**核心用途**
- 批量处理 PDF/图片，自动切分为题目粒度数据
- 生成标准 JSON 结构，直接用于题库构建与检索
- 提供 CLI 与 Web API 两种使用方式，便于集成

**基础能力**
- 版面分析与题目内容识别（PaddleOCR-VL + PP-DocLayoutV2）
- Markdown 聚合与图片资源落盘
- 大模型解析（严格模板约束）为结构化 JSON
- JSON 内图片路径一键转换为 Base64 或 data URI


## 功能特性
- 多输入形式：单个图片、图片目录、单个 PDF、图片+PDF 混合
- 严格的 JSON Schema 抽取（避免漏字段、错字段）
- 图片资源自动转换为 Base64，支持内嵌 data URI
- 快速 Web API：上传文件即返回结构化结果
- 实用辅助脚本：批量重命名、目录元信息填充、Base64 转 URL 等


## 架构与流程
1) OCR-VL 识别
- 使用 PaddleOCR-VL 与 PP-DocLayoutV2 对图像/PDF 逐页识别
- 生成页面级 Markdown 与页面图片（相对路径）

2) Markdown 聚合
- 将多页 Markdown 合并为一份整体文本
- 同步保存 markdown_images 到输出目录

3) 结构化抽取
- 通过 OpenAI 兼容接口调用大模型
- 严格按模板 [templates.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/templates.py) 中的 json_data 抽取题目信息

4) 图片处理
- 将 JSON 中的图片路径批量转换为 Base64 或 data URI
- 可进一步用脚本将 Base64 上传为 URL

主要代码入口：
- CLI 主入口：[main.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/main.py#L736-L763)
- Web 服务入口：[app.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/app.py#L84-L149)
- 模型下载脚本：[models/downloads-models.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/models/downloads-models.py)


## 快速开始（CLI）
1) 安装依赖（示例）

```bash
python -m venv .venv && source .venv/bin/activate
pip install paddleocr modelscope opencv-python pillow python-dotenv fastapi uvicorn openai requests
```

如使用 GPU，请安装合适版本的 PaddlePaddle-GPU（参考链接在 libs/paddlepaddle_gpu下载地址）。

2) 准备模型

```bash
python models/downloads-models.py
# 将模型下载到: models/PaddlePaddle/PP-DocLayoutV2 与 models/PaddlePaddle/PaddleOCR-VL
```

3) 配置环境变量（使用 .env）
- OPENAI_API_KEY=你的密钥
- LLM_MODEL_URL=兼容 OpenAI 的推理服务地址
- LLM_MODEL_NAME=模型名称（如 qwen3-next 等）

4) 运行

```bash
# 处理单个图片或 PDF
python main.py -i /path/to/image_or_pdf

# 处理图片目录（不递归）
python main.py -i /path/to/images_dir

# 多输入合并处理（图片/目录/PDF 均可）
python main.py -i /path/to/img1 /path/to/img_dir /path/to/doc.pdf
```

输出说明：
- 程序会在输入同级目录或首个目录下，自动保存 JSON 文件
- 中间生成的 Markdown 文件会在流程结束后自动清理
- 图片资源会写入指定输出目录（默认 ./output）


## Web API
启动服务（开发环境）：

```bash
uvicorn app:app --host 0.0.0.0 --port 8080 --workers 4 --log-level info
```

关键接口：
- GET /health：健康检查
- POST /parse-docs：上传图片或单个 PDF（multipart/form-data，字段名为 files），返回结构化 JSON（图片字段为 Base64/data URI）

服务实现参考：[app.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/app.py)


## 常用脚本
- 批量单图转 JSON（本地推理）：[process_images_separately.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/process_images_separately.py)
- 批量重命名图片：将文件名统一为 img_0001 形式  
  [rename_image.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/rename_image.py)
- 目录元信息填充到 JSON：从目录结构提取年级/章节/节等，回填到 JSON  
  [fill_json.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/fill_json.py)
- 获取指定目录下所有 JSON 路径：[get_path.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/get_path.py)
- 将 JSON 内 Base64 图片上传后替换为 URL（兼容已有平台 API）  
  [Json_Base64_to_URL.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/Json_Base64_to_URL.py)
- 批处理示例脚本（调用 CLI 主入口）：[run_all.sh](file:///home/gjh/workspace/github-project/PaperCutter-VL/run_all.sh)
- 基于远程 API 的处理流水线示例（先重命名，再逐图调用 /parse-docs）：  
  [Pipeline.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/Pipeline.py)


## 模型与依赖
- 模型下载：运行 [models/downloads-models.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/models/downloads-models.py)
- GPU 安装参考：见 [libs/paddlepaddle_gpu下载地址](file:///home/gjh/workspace/github-project/PaperCutter-VL/libs/paddlepaddle_gpu下载地址)
- 主要 Python 依赖（示例）：paddleocr、modelscope、opencv-python、pillow、python-dotenv、fastapi、uvicorn、openai、requests


## 配置项说明
主流程使用的关键环境变量（由 [.env](file:///home/gjh/workspace/github-project/PaperCutter-VL/.env) 加载，文件需自行创建）：
- OPENAI_API_KEY：用于调用大模型服务
- LLM_MODEL_URL：兼容 OpenAI 的推理服务地址
- LLM_MODEL_NAME：模型名称

主入口函数：
- CLI 统一入口：run_unified(input_arg, output_dir)  
  详见 [main.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/main.py#L572-L721)
- 参数解析与保存逻辑：详见 [main.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/main.py#L724-L763)


## 目录约定（示例）
- models/PaddlePaddle/PP-DocLayoutV2：版面分析模型目录
- models/PaddlePaddle/PaddleOCR-VL：视觉-语言识别模型目录
- output/：默认输出目录（可通过 -o 指定）
- uploads/：Web API 临时上传目录（按请求 ID 存放）


## 许可
见 [LICENSE](file:///home/gjh/workspace/github-project/PaperCutter-VL/LICENSE)
