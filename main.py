#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re
import os

# ================= 配置区 =================
TARGET_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "output/live_channels.m3u"

# 严格的筛选条件
REQUIRED_ISP = "河北-电信"
REQUIRED_DATE = "2026-06-12"

# 模拟浏览器请求头 (非常重要，否则会被网站拦截导致超时)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'http://nn.7x9d.cn/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def fetch_target_link():
    """
    访问列表页，寻找符合条件的蓝色框链接
    """
    print(f"正在尝试连接: {TARGET_URL}")

    try:
        # 设置 timeout=15 防止无限等待
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8' # 确保中文不乱码
        soup = BeautifulSoup(response.text, 'html.parser')

        # 查找所有蓝色的按钮 (根据网页结构通常是 a 标签或 button)
        # 这里我们假设蓝色框是 <a> 标签，且包含 IP 地址文本
        all_links = soup.find_all('a', href=True)

        valid_url = None

        for link in all_links:
            # 获取链接的文本内容（即显示的 IP）
            ip_text = link.get_text(strip=True)

            # 简单的正则判断是否是 IP 格式 (例如 106.115.24.7:19901)
            # 如果不是 IP 格式的链接直接跳过，提高效率
            if not re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', ip_text):
                continue

            # --- 核心筛选逻辑 ---
            # 找到该按钮的父级容器，通常信息都在同一个 div 里
            parent_div = link.find_parent('div')

            if parent_div:
                parent_text = parent_div.get_text()

                # 严格检查：必须同时包含 运营商 和 日期
                if REQUIRED_ISP in parent_text and REQUIRED_DATE in parent_text:
                    print(f"[成功] 找到目标链接: {ip_text}")
                    print(f"      详情: {REQUIRED_ISP}, 收录于 {REQUIRED_DATE}")
                    valid_url = link['href']
                    break # 找到第一个就停止，如果需要找所有可以去掉 break
                else:
                    # 调试用：打印不匹配的项，方便排查
                    # print(f"[跳过] {ip_text} -> 不匹配条件")
                    pass

        if valid_url:
            return valid_url
        else:
            print(f"[失败] 未找到同时满足 [{REQUIRED_ISP}] 和 [{REQUIRED_DATE}] 的链接。")
            return None

    except Exception as e:
        print(f"[错误] 抓取页面失败: {e}")
        return None

def generate_m3u(target_url):
    """
    生成 M3U 文件
    """
    if not target_url:
        print("没有有效的链接，无法生成文件。")
        return False

    # 构建 M3U 内容
    # 注意：这里只是生成了一个指向该 IP 的条目
    # 如果你需要解析该 IP 里的真实频道列表，需要再次请求 target_url
    m3u_content = f"""#EXTM3U url-tvg="{target_url}"
#EXTINF:-1 tvg-logo="" group-title="酒店源",河北电信_{REQUIRED_DATE}
{target_url}
"""
    # 确保 output 目录存在
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(m3u_content)

    print(f"M3U 文件已生成: {OUTPUT_FILE}")
    return True

if __name__ == "__main__":
    print("=== 直播源精确抓取脚本 ===")
    link = fetch_target_link()
    generate_m3u(link)
