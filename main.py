#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re
import os

# ================= 配置区 =================
LIST_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "output/live_channels.m3u"

# 严格的筛选条件
REQUIRED_ISP = "河北-电信"
REQUIRED_DATE = "2026-06-12" # 只匹配收录日期

# 模拟浏览器请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'http://nn.7x9d.cn/',
}

def find_target_detail_url():
    """
    1. 获取列表页
    2. 查找符合条件的 <a> 标签
    3. 返回下级页面的完整 URL
    """
    print(f"正在抓取列表页: {LIST_URL}")
    
    try:
        response = requests.get(LIST_URL, headers=HEADERS, timeout=20)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有 <a> 标签 (蓝色框通常是 a 标签)
        # 根据提供的源码，我们需要遍历所有 a 标签并检查其旁边的文本
        all_a_tags = soup.find_all('a', href=True)
        
        for tag in all_a_tags:
            ip_text = tag.get_text(strip=True)
            parent = tag.find_parent()
            if not parent:
                continue
                
            parent_text = parent.get_text()
            
            # 1. 检查运营商
            if REQUIRED_ISP not in parent_text:
                continue
                
            # 2. 检查收录时间 (严格匹配 REQUIRED_DATE)
            # 使用正则查找 "收录时间：" 后面的内容，确保包含 REQUIRED_DATE
            time_match = re.search(r'收录时间[：:]\s*(\d{4}-\d{2}-\d{2})', parent_text)
            if not time_match or time_match.group(1) != REQUIRED_DATE:
                continue
                
            # --- 找到目标 ---
            # 获取 href (通常是 detail.php?id=xxx 形式)
            href = tag['href']
            
            # 拼接完整 URL
            if href.startswith('http'):
                full_url = href
            else:
                # 假设是相对路径
                base = "http://nn.7x9d.cn/"
                full_url = base + href.lstrip('/')
                
            print(f"✅ 成功匹配目标！")
            print(f"   IP地址: {ip_text}")
            print(f"   运营商: {REQUIRED_ISP}")
            print(f"   收录日期: {REQUIRED_DATE}")
            print(f"   下级链接: {full_url}")
            return full_url
            
        print(f"❌ 未找到满足条件的链接 (运营商: {REQUIRED_ISP}, 收录日期: {REQUIRED_DATE})")
        return None
        
    except Exception as e:
        print(f"❌ 抓取列表页时发生异常: {e}")
        return None

def fetch_and_save_m3u(detail_url):
    """
    2. 访问下级页面，获取纯文本直播源，并保存为 M3U
    """
    if not detail_url:
        return
        
    print(f"\n正在访问下级页面获取直播源: {detail_url}")
    
    try:
        # 在访问下级页面时，可能需要带上 Referer
        response = requests.get(detail_url, headers=HEADERS, timeout=20)
        response.encoding = 'utf-8'
        
        # 假设下级页面直接返回的是纯文本的直播源 (m3u 格式或 txt 格式)
        page_content = response.text.strip()
        
        if not page_content:
            print("❌ 下级页面返回内容为空！")
            return
            
        # --- 生成 M3U 文件 ---
        # 确保输出目录存在
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # 写入 M3U 头部
            f.write(f"#EXTM3U tvg-url=\"{detail_url}\" \n")
            f.write(f"# 源地址: {detail_url}\n")
            f.write(f"# 抓取时间: 2026-06-13\n")
            f.write(f"# 运营商: {REQUIRED_ISP} (收录于 {REQUIRED_DATE})\n")
            f.write(f"# --- 以下是原始内容 ---\n")
            
            # 写入抓取到的纯文本内容
            # 注意：如果抓取到的内容已经是完整的 m3u 格式，可以直接写入
            # 如果是简单的 url 列表，可能需要处理格式，这里假设是标准 m3u
            f.write(page_content)
            
        print(f"✅ 直播源已成功保存到: {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"❌ 获取下级页面内容失败: {e}")

if __name__ == "__main__":
    print("=== 酒店源自动抓取脚本 (精准版) ===")
    target_url = find_target_detail_url()
    fetch_and_save_m3u(target_url)
