import os
import cv2
from paddleocr import PaddleOCRVL
import warnings
warnings.filterwarnings("ignore")

# 指定不同模型的路径
layout_model_path = '../models/PaddlePaddle/PP-DocLayoutV2'
vl_rec_model_path = '../models/PaddlePaddle/PaddleOCR-VL'

# 确保目录存在
os.makedirs(layout_model_path, exist_ok=True)
os.makedirs(vl_rec_model_path, exist_ok=True)

# 使用正确的参数名称和对应的模型路径
pipeline = PaddleOCRVL(
    # 布局检测模型使用PP-DocLayoutV2
    layout_detection_model_dir=layout_model_path,
    # VL识别模型使用PaddleOCR-VL
    vl_rec_model_dir=vl_rec_model_path,
    # 文档方向分类和文档校正模型也使用PP-DocLayoutV2
    doc_orientation_classify_model_dir=layout_model_path,
    doc_unwarping_model_dir=layout_model_path
)
# pipeline = PaddleOCRVL()

# 构建img目录下test1.png的路径
img_path = os.path.join(os.path.dirname(__file__), "../images", "img_0001.png")
# 读取图片为 ndarray，确保 RGB 格式
img = cv2.imread(img_path)
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

output = pipeline.predict(img)
for res in output:
    print(res)
    res.save_to_json(save_path="../output")  ## 保存当前图像的结构化json结果
    res.save_to_markdown(save_path="../output")  ## 保存当前图像的markdown格式的结果