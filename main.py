import requests
from bs4 import BeautifulSoup
import re
import time
import os

# ==================== 配置区 ====================
# 你的目标网址
BASE_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C97"
OUTPUT_FILE = "kaniptv.m3u"

# ✅ 台标源：使用 jsDelivr CDN 加速 (比 raw.githubusercontent.com 更稳定)
LOGO_BASE_URL = "https://cdn.jsdelivr.net/gh/fanmingming/live@main/tv/"

# ✅ EPG 节目单地址
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# ✅ 筛选条件配置
TARGET_REGION = "河北"       # 地区关键词
TARGET_ISP = "电信"          # 运营商关键词 (对应截图中的 河北-电信)
TARGET_DATE = "2026-06-12"   # 收录时间 (精确到日)

SUFFIX_WORDS = [
    "高清", "HD", "hd", "4K", "超清", "标清", "SD",
    "频道", "电视台", "综合", "财经", "综艺", "体育",
    "电影", "电视剧", "纪录", "少儿", "军事", "农业",
    "科教", "戏曲", "社会与法", "新闻", "音乐"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

# 代理池（可选，用于防止IP被封）
PROXIES = {
    # 'http': 'http://127.0.0.1:7890',
    # 'https': 'http://127.0.0.1:7890'
}


def get_page_content(url):
    """通用页面获取函数"""
    try:
        resp = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=10)
        resp.encoding = 'utf-8'
        return resp.text
    except Exception as e:
        print(f"[错误] 无法访问 {url}: {e}")
        return None


def extract_real_link(detail_url):
    """
    进入详情页提取真实播放地址
    这里假设详情页里包含 .m3u8 或 .ts 链接
    """
    html = get_page_content(detail_url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # --- 尝试多种常见的播放地址提取方式 ---
    real_link = None

    # 1. 查找 video 标签
    video_tag = soup.find('video')
    if video_tag and video_tag.get('src'):
        real_link = video_tag['src']

    # 2. 查找 source 标签
    if not real_link:
        source_tag = soup.find('source')
        if source_tag and source_tag.get('src'):
            real_link = source_tag['src']

    # 3. 正则匹配 .m3u8 或 .ts 链接
    if not real_link:
        # 匹配 http(s)://...m3u8 或相对路径 ...m3u8
        match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
        if match:
            real_link = match.group(1)
        else:
            match = re.search(r'(https?://[^\s"\']+\.ts[^\s"\']*)', html)
            if match:
                real_link = match.group(1)

    # 处理相对路径
    if real_link and not real_link.startswith('http'):
        from urllib.parse import urljoin
        real_link = urljoin(detail_url, real_link)

    return real_link


def clean_channel_name(name):
    """清理频道名称，去除后缀干扰"""
    for word in SUFFIX_WORDS:
        name = name.replace(word, "")
    # 去除特殊字符
    name = re.sub(r'[^\w\s\u4e00-\u9fff]', '', name).strip()
    return name if name else "未知频道"


def generate_m3u(links_data):
    """生成 M3U 文件内容"""
    lines = [
        '#EXTM3U',
        f'#EXTINF:-1 tvg-logo="{LOGO_BASE_URL}" group-title="IPTV",{EPG_URL}',  # 全局设置通常放在头部或单独处理，这里主要写入条目
        ''
    ]

    for item in links_data:
        # 构建 Logo URL
        logo_url = f"{LOGO_BASE_URL}{item['name']}.png"

        line = (
            f'#EXTINF:-1 tvg-id="{item["name"]}" '
            f'tvg-name="{item["name"]}" '
            f'tvg-logo="{logo_url}" '
            f'group-title="{item["isp"]}",'
            f'{item["display_name"]}\n'
            f'{item["url"]}'
        )
        lines.append(line)

    return '\n'.join(lines)


def main():
    print(f"[*] 正在访问列表页: {BASE_URL}")
    html = get_page_content(BASE_URL)
    if not html:
        return

    soup = BeautifulSoup(html, 'html.parser')
    valid_links = []

    # 寻找包含信息的容器
    # 根据截图结构，每个IP块可能在一个 div 或 li 中，我们遍历所有包含日期的块
    # 这里使用 findAll 查找所有可能包含 "收录时间" 的父级元素
    # 注意：具体的 class 名需要根据实际网页源码调整，这里假设没有特定 class，直接全文搜索逻辑
    all_text_blocks = soup.find_all(string=re.compile(TARGET_DATE))

    print(f"[*] 找到包含日期 '{TARGET_DATE}' 的文本块数量: {len(all_text_blocks)}")

    for text_block in all_text_blocks:
        parent_div = text_block.find_parent(['div', 'li', 'td'])
        if not parent_div:
            continue

        full_text = parent_div.get_text()

        # 1. 筛选运营商 (必须包含 河北 和 电信)
        if TARGET_REGION not in full_text or TARGET_ISP not in full_text:
            continue

        # 2. 再次确认日期 (防止误判)
        if TARGET_DATE not in full_text:
            continue

        # 3. 提取蓝色框框的链接 (href)
        # 假设蓝色框框是一个 <a> 标签，且里面包含 IP 格式文本
        link_tag = parent_div.find('a', string=re.compile(r'\d+\.\d+\.\d+\.\d+'))

        if link_tag and link_tag.get('href'):
            detail_url = link_tag['href']
            # 处理相对路径
            if not detail_url.startswith('http'):
                from urllib.parse import urljoin
                detail_url = urljoin(BASE_URL, detail_url)

            display_ip = link_tag.get_text().strip()
            print(f"[发现] 目标IP: {display_ip} -> 详情页: {detail_url}")

            # 4. 进入详情页获取真实播放地址
            real_url = extract_real_link(detail_url)

            if real_url:
                # 尝试从详情页标题或周围文本获取频道名，如果没有则用IP代替
                channel_name = clean_channel_name(display_ip.split(':')[0]) # 简单用IP前段做名字，或者你可以优化提取逻辑

                valid_links.append({
                    'name': channel_name,
                    'display_name': f"{TARGET_REGION}{TARGET_ISP}_{display_ip}",
                    'isp': f"{TARGET_REGION}{TARGET_ISP}",
                    'url': real_url
                })
            else:
                print(f"  [警告] 无法从详情页提取播放地址: {detail_url}")
        else:
            print(f"  [警告] 在文本块中未找到有效的链接标签: {full_text[:50]}...")

    # 保存文件
    if valid_links:
        m3u_content = generate_m3u(valid_links)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        print(f"\n[成功] 已生成 {OUTPUT_FILE}，共收录 {len(valid_links)} 个源。")
    else:
        print("\n[失败] 未找到符合条件的源，请检查筛选条件或网页结构是否变更。")


if __name__ == "__main__":
    main()
