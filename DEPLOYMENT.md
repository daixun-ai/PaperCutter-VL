# 部署文档

本文档描述 PaperCutter-VL 的服务化部署流程，适用于对外提供 `/parse-docs` 接口的场景。


## 部署目标
- 对外提供 FastAPI 服务
- 支持上传图片或单个 PDF
- 返回结构化 JSON（图片为 Base64/data URI）


## 环境准备
- Python 运行环境（建议使用虚拟环境）
- 网络可访问的大模型推理服务（OpenAI 兼容）
- 模型文件：PP-DocLayoutV2、PaddleOCR-VL


## 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install paddleocr modelscope opencv-python pillow python-dotenv fastapi uvicorn openai requests
```

如使用 GPU，请参考 `libs/paddlepaddle_gpu下载地址` 安装匹配版本的 PaddlePaddle-GPU。


## 下载模型

```bash
python models/downloads-models.py
```

下载完成后应存在以下目录：
- models/PaddlePaddle/PP-DocLayoutV2
- models/PaddlePaddle/PaddleOCR-VL


## 配置环境变量
使用 `.env` 文件或系统环境变量配置：
- OPENAI_API_KEY=你的密钥
- LLM_MODEL_URL=兼容 OpenAI 的推理服务地址
- LLM_MODEL_NAME=模型名称


## 启动服务

```bash
uvicorn app:app --host 0.0.0.0 --port 8080 --workers 4 --log-level info
```

验证服务：

```bash
curl http://127.0.0.1:8080/health
```


## 接口说明
- POST /parse-docs
  - Content-Type: multipart/form-data
  - 参数名：files
  - 允许：多张图片或单个 PDF

示例：

```bash
curl -X POST "http://127.0.0.1:8080/parse-docs" \
  -F "files=@/path/to/your-image.jpg"
```


## 目录与权限
- output/：解析结果缓存目录（会生成临时 markdown 与图片）
- uploads/：API 上传临时目录（按 request_id 分类）

建议保证服务进程对以上目录具有读写权限。


## 生产部署建议
- 将服务进程交给进程管理器（systemd/supervisor）
- 使用反向代理（如 Nginx）进行端口转发与限流
- 若模型推理耗时较长，合理调节 `--workers` 与机器资源


## 更新流程（推荐）
1) 拉取最新代码并进入虚拟环境  
2) 更新依赖（如有新增）  
3) 重新下载或更新模型（如有变更）  
4) 重启服务进程  


## 重要文件参考
- API 服务入口：[app.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/app.py)
- 主流程逻辑：[main.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/main.py)
- 模型下载脚本：[models/downloads-models.py](file:///home/gjh/workspace/github-project/PaperCutter-VL/models/downloads-models.py)
