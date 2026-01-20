# -*- coding: utf-8 -*-
# @Time    : 2026/1/6 16:07
# @File    : rename_image.py
# @Project : PaddleOCR-VL-master
# @Author  : daixun
import os


def rename_images(
        folder_path,
        prefix="img",
        start_index=1,
        digits=4,
        extensions=(".jpg", ".jpeg", ".png", ".bmp", ".webp")
):
    files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(extensions)
    ]

    files.sort()  # 保证顺序稳定

    for i, filename in enumerate(files, start=start_index):
        ext = os.path.splitext(filename)[1]
        new_name = f"{prefix}_{str(i).zfill(digits)}{ext}"

        old_path = os.path.join(folder_path, filename)
        new_path = os.path.join(folder_path, new_name)

        if old_path != new_path:
            os.rename(old_path, new_path)

    print(f"完成：共重命名 {len(files)} 张图片")


if __name__ == "__main__":
    path_list = [
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第一章 勾股定理/1 探索勾股定理',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第一章 勾股定理/2 一定是直角三角形吗',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第一章 勾股定理/3 勾股定理的应用',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第二章 实数/1 认识实数',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第二章 实数/2 平方根与立方根',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第二章 实数/3 二次根式',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第三章 位置与坐标/1 确定位置',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第三章 位置与坐标/2 平面直角坐标系',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第三章 位置与坐标/3 轴对称与坐标变化',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第四章 一次函数/1 函数',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第四章 一次函数/2 认识一次函数',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第四章 一次函数/3 一次函数的图象',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第四章 一次函数/4 一次函数的应用',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第五章 二元一次方程组/1 认识二元一次方程组',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第五章 二元一次方程组/2 二元一次方程组的解法',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第五章 二元一次方程组/3 二元一次方程组的应用',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第五章 二元一次方程组/4 二元一次方程与一次函数',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第五章 二元一次方程组/5 三元一次方程组',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第六章 数据的分析/1 平均数与方差',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第六章 数据的分析/2 中位数与箱线图',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第六章 数据的分析/3 哪个团队成绩大',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第七章 证明/1 为什么要证明',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第七章 证明/2 认识证明',
        '/home/gjh/datasets/中考真题/广东省/数学/八年级/北师大版/上册/第七章 证明/3 平行线的证明'
    ]
    for path in path_list:
        rename_images(
            folder_path=path,
            prefix="img",
            start_index=1,
            digits=4
        )

