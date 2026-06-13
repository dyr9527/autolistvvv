#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re
import time
import os

# ================= 配置区 =================
TARGET_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"
LOGO_BASE_URL = "https://raw.githubusercontent.com/fanmingming/live/main/tv/"

# 分类关键词
CATEGORY_KEYWORDS = {
    'CCTV': '央视',
    '卫视': '卫视',
    '河北': '河北',
    '石家庄': '河北',
    '唐山': '河北',
    '秦皇岛': '河北',
    '邯郸': '河北',
    '邢台': '河北',
    '保定': '河北',
    '张家口': '河北',
    '承德': '河北',
    '廊坊': '河北',
    '沧州': '河北',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def fetch_blue_box_links(list_url):
    """
    第一步：抓取列表页，找到符合条件的蓝色框链接（下级链接）
    筛选条件：运营商=河北-电信，收录时间=2026-06-12
    """
    try:
        response = requests.get(list_url, headers=HEADERS, timeout=15)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        blue_box_links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            parent_text = a_tag.find_parent().get_text() if a_tag.find_parent() else ""
            
            # 筛选：河北-电信 且 2026-06-12
            if "河北-电信" in parent_text and "2026-06-12" in parent_text:
                full_url = href if href.startswith('http') else requests.compat.urljoin(list_url, href)
                blue_box_links.append({
                    'detail_url': full_url,
                    'box_text': a_tag.get_text(strip=True)
                })
                print(f"找到符合条件的蓝色框: {a_tag.get_text(strip=True)} -> {full_url}")
        
        return blue_box_links
    except Exception as e:
        print(f"抓取列表页失败: {e}")
        return []


def fetch_live_source_from_detail(detail_url):
    """
    第二步：进入下级链接，获取真实的直播源文本
    """
    try:
        response = requests.get(detail_url, headers=HEADERS, timeout=15)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 方式1：查找pre标签
        pre_tag = soup.find('pre')
        if pre_tag:
            return parse_source_text(pre_tag.get_text(strip=False))
        
        # 方式2：查找body文本
        body_text = soup.body.get_text(strip=False) if soup.body else ""
        if body_text:
            return parse_source_text(body_text)
        
        # 方式3：查找所有文本
        return parse_source_text(soup.get_text())
        
    except Exception as e:
        print(f"抓取下级页面失败 {detail_url}: {e}")
        return []


def parse_source_text(text):
    """从纯文本中解析出直播源链接"""
    sources = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配完整URL
        url_match = re.search(r'https?://[^\s]+', line)
        if url_match:
            sources.append(url_match.group())
            continue
        
        # 匹配 IP:Port
        ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}:\d+\b', line)
        if ip_match:
            sources.append(f"http://{ip_match.group()}")
    
    return sources


def classify_channel(channel_name):
    """根据频道名称分类"""
    channel_name_upper = channel_name.upper()
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword.upper() in channel_name_upper:
            return category
    return '其他'


def get_logo_url(channel_name):
    """生成台标URL"""
    logo_name = re.sub(r'[\s\W]+', '_', channel_name.lower())
    return f"{LOGO_BASE_URL}{logo_name}.png"


def extract_channel_name(source_url, source_text=""):
    """从直播源信息中提取频道名称"""
    if source_text:
        name = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}:\d+\b', '', source_text).strip()
        if name:
            return name
    
    url_obj = requests.utils.urlparse(source_url)
    port = url_obj.port
    if port:
        port_map = {
            19901: "CCTV-1", 19902: "CCTV-2", 19903: "CCTV-3", 19904: "CCTV-4",
            19905: "CCTV-5", 19906: "CCTV-5+", 19907: "CCTV-6", 19908: "CCTV-7",
            19909: "CCTV-8", 19910: "CCTV-9", 19911: "CCTV-10", 19912: "CCTV-11",
            19913: "CCTV-12", 19914: "CCTV-13", 19915: "CCTV-14", 19916: "CCTV-15",
            19917: "CCTV-16", 19918: "CCTV-17",
            85: "河北卫视", 86: "石家庄新闻综合", 87: "保定新闻综合",
        }
        if port in port_map:
            return port_map[port]
    
    return f"频道_{port or 'unknown'}"


def generate_m3u(channel_list):
    """生成M3U文件内容"""
    lines = []
    lines.append(f'#EXTM3U x-tvg-url="{EPG_URL}"')
    
    for item in channel_list:
        source_url = item['url']
        channel_name = item['channel_name']
        category = classify_channel(channel_name)
        tvg_logo = get_logo_url(channel_name)
        tvg_id = re.sub(r'[\s\W]+', '', channel_name)
        
        lines.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{channel_name}" tvg-logo="{tvg_logo}" group-title="{category}",{channel_name}')
        lines.append(source_url)
    
    return '\n'.join(lines)


def main():
    print("=== 直播源抓取与M3U生成脚本 ===\n")
    
    # 步骤1：抓取列表页，获取蓝色框的下级链接
    print("【步骤1】正在抓取列表页，筛选蓝色框链接...")
    blue_box_links = fetch_blue_box_links(TARGET_URL)
    
    if not blue_box_links:
        print("❌ 未找到符合条件的蓝色框链接，请检查：")
        print("   - 目标网站是否可访问")
        print("   - 筛选条件（河北-电信、2026-06-12）是否匹配")
        return
    
    print(f"✅ 找到 {len(blue_box_links)} 个符合条件的蓝色框\n")
    
    # 步骤2：逐个进入下级链接，获取真实直播源
    print("【步骤2】正在进入下级链接，提取真实直播源...")
    all_sources = []
    
    for box in blue_box_links:
        print(f"  进入: {box['detail_url']}")
        sources = fetch_live_source_from_detail(box['detail_url'])
        if sources:
            print(f"    提取到 {len(sources)} 个直播源")
            for src in sources:
                all_sources.append({
                    'url': src,
                    'source_text': box['box_text']
                })
        else:
            print("    未提取到直播源")
        time.sleep(1)
    
    if not all_sources:
        print("❌ 未从任何下级页面提取到直播源")
        return
    
    print(f"\n✅ 共提取到 {len(all_sources)} 个直播源\n")
    
    # 步骤3：提取频道名并分类
    print("【步骤3】正在提取频道名并分类...")
    channel_list = []
    for src in all_sources:
        channel_name = extract_channel_name(src['url'], src['source_text'])
        category = classify_channel(channel_name)
        channel_list.append({
            'url': src['url'],
            'channel_name': channel_name,
            'category': category
        })
        print(f"  {channel_name} -> {category}")
    
    # 步骤4：生成M3U文件
    print("\n【步骤4】正在生成M3U文件...")
    m3u_content = generate_m3u(channel_list)
    
    os.makedirs('output', exist_ok=True)
    filename = "output/live_channels.m3u"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(m3u_content)
    
    print(f"\n✅ 生成完成！")
    print(f"   文件路径: {filename}")
    print(f"   频道总数: {len(channel_list)}")
    print(f"   EPG地址: {EPG_URL}")
    print(f"   台标地址: {LOGO_BASE_URL}")


if __name__ == '__main__':
    main()
