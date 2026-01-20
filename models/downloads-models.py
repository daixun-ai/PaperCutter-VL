#模型下载.txt
from modelscope import snapshot_download
model_dir = snapshot_download('PaddlePaddle/PP-DocLayoutV2', cache_dir="./PaddlePaddle")
model_dir = snapshot_download('PaddlePaddle/PaddleOCR-VL', cache_dir="./PaddlePaddle")
