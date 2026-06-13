#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re
import os
import time

# ================= 配置区 =================
LIST_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "output/live_channels.m3u"

# === 筛选条件 (请根据实际情况修改) ===
TARGET_ISP = "河北-电信"
TARGET_DATE = "2026-06-12"  # 只要收录时间是这一天的

# 模拟浏览器请求头 (必须加，否则容易被拦截)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'http://nn.7x9d.cn/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}


def find_and_fetch_source():
    """
    主逻辑：寻找符合条件的条目，并进入下级页面抓取
    """
    print(f"正在连接列表页...")

    try:
        # 增加超时时间到 30 秒，防止 GitHub Actions 网络波动导致直接报错
        response = requests.get(LIST_URL, headers=HEADERS, timeout=30)
        response.encoding = 'utf-8'  # 强制指定编码，防止乱码
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"[错误] 无法连接列表页: {e}")
        return None

    # 假设每个条目都在一个大的容器里，比如 div 或 tr
    # 这里我们遍历所有的 <a> 标签，因为蓝色框通常是链接
    # 如果结构很特殊，可能需要遍历 div
    all_links = soup.find_all('a')

    target_url = None

    for link in all_links:
        # 1. 检查这个链接是否有效 (href 不能为空)
        href = link.get('href')
        if not href:
            continue

        # 2. 获取该链接周围的文本内容，或者其父级容器的文本
        # 很多老网站结构是：<a href="...">蓝色框</a> <br> 河北-电信 ...
        # 所以我们看 link.parent (父级) 的文本内容
        parent_text = link.parent.get_text()

        # 3. 严格匹配条件
        if TARGET_ISP in parent_text and TARGET_DATE in parent_text:
            print(f"[成功] 找到目标！")
            print(f"   运营商: {TARGET_ISP}")
            print(f"   日期: {TARGET_DATE}")
            print(f"   原始链接: {href}")

            # 处理相对路径 (例如 href="xzjd3.php?id=xxx")
            if href.startswith('http'):
                target_url = href
            else:
                # 拼接成完整 URL
                base_url = LIST_URL.rsplit('/', 1)[0]
                target_url = f"{base_url}/{href}"

            break  # 找到第一个就停止

    if not target_url:
        print("[失败] 未找到符合条件的链接，请检查日期或运营商名称是否完全一致。")
        return None

    # --- 第二步：进入下级页面抓取直播源 ---
    print(f"\n正在进入下级页面获取直播源: {target_url}")
    try:
        # 再次请求下级页面
        res_detail = requests.get(target_url, headers=HEADERS, timeout=30)
        res_detail.encoding = 'utf-8'

        # 假设下级页面直接就是 m3u 文本，或者是包含 m3u 链接的网页
        # 这里直接返回内容，你可以根据实际情况解析
        content = res_detail.text

        # 简单的判断：如果内容包含 #EXTM3U，说明直接就是播放列表
        if '#EXTM3U' in content or '.m3u8' in content or '.ts' in content:
            print("[成功] 获取到直播源内容！")
            return content
        else:
            # 如果不是直接文本，可能还需要再次解析 HTML 找链接
            # 这里为了通用，先打印前 200 个字符让你看看是什么
            print(f"[提示] 下级页面内容预览:\n{content[:200]}...")
            return content  # 暂时直接返回，你可以后续优化

    except Exception as e:
        print(f"[错误] 进入下级页面失败: {e}")
        return None


def save_to_file(content):
    """保存文件"""
    if not content:
        return

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n[完成] 直播源已保存到: {OUTPUT_FILE}")


if __name__ == "__main__":
    source_content = find_and_fetch_source()
    save_to_file(source_content)
