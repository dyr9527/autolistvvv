import requests
from bs4 import BeautifulSoup
import re
import time
import os
import random
import gzip
import io

# --- 配置区 ---
BASE_URL = "http://nn.7x9d.cn/xzjd2.php?id=河北"
OUTPUT_FILE = "kaniptv.m3u"
LOGO_BASE_URL = "https://raw.githubusercontent.com/fanmingming/live/main/tv/"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

SUFFIX_WORDS = [
    "高清", "HD", "hd", "4K", "超清", "标清", "SD",
    "频道", "电视台", "综合", "财经", "综艺", "体育",
    "电影", "电视剧", "纪录", "少儿", "军事", "农业",
    "科教", "戏曲", "社会与法", "新闻", "音乐"
]

# 模拟更真实的浏览器头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# ==================== 核心网络模块（优化版） ====================

def safe_request(url, max_retries=5):
    """
    增强版请求函数：
    1. 优先直连（GitHub IP 有时反而不被墙）
    2. 失败后尝试简单的延时重试
    3. 增加 Referer 伪装
    """
    # 动态设置 Referer，假装是从首页点进去的
    headers = HEADERS.copy()
    if "xzjd2.php" in url:
        headers['Referer'] = "http://nn.7x9d.cn/"
    else:
        headers['Referer'] = "http://nn.7x9d.cn/xzjd2.php?id=河北"

    for attempt in range(max_retries):
        try:
            print(f"   🔄 正在请求 (尝试 {attempt+1}/{max_retries})...")

            # 这里的 timeout 设置大一点，防止稍微卡顿就断开
            resp = requests.get(url, headers=headers, timeout=20)

            if resp.status_code == 200:
                # 简单的内容校验
                if len(resp.text) > 100:
                    return resp.text
                else:
                    print(f"   ⚠️ 响应内容过短，可能被拦截...")
            else:
                print(f"   ⚠️ 状态码: {resp.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"   ❌ 请求失败: {e}")

        # 每次失败后随机等待 2-5 秒，避免触发频率限制
        wait_time = random.uniform(2, 5)
        print(f"   💤 等待 {wait_time:.1f} 秒后重试...")
        time.sleep(wait_time)

    return None

# ==================== 业务逻辑 ====================

def get_telecom_links(page_url):
    print(f"🔍 正在分析入口页面: {page_url}")
    html = safe_request(page_url)

    if not html:
        print("❌ 无法访问入口页面，请检查网络或代理")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    telecom_links = []

    # 筛选条件：运营商为"河北-电信"
    operator_tags = soup.find_all(string=re.compile("河北-电信"))

    for tag in operator_tags:
        btn = tag.find_previous(name='a')
        if btn and btn.get('href'):
            link = btn['href']
            if not link.startswith('http'):
                base_domain = "http://nn.7x9d.cn"
                link = base_domain + "/" + link.lstrip('/')

            # 简单的去重和打印
            ip_text = btn.get_text(strip=True)
            print(f"✅ 发现河北电信源: [{ip_text}] -> {link}")
            telecom_links.append(link)

    return list(set(telecom_links))

def fetch_playlist(url):
    print(f"   📡 正在抓取子源: {url}")
    content = safe_request(url)

    if not content:
        print(f"   ❌ 子源抓取失败")
        return ""

    if len(content) < 50:
        print(f"   ⚠️ 内容过少，跳过")
        return ""

    return content

def parse_raw_content(content):
    channels = []
    lines = content.replace('<br>', '\n').replace('<br/>', '\n').splitlines()
    current_extinf = ""

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#!') or line.startswith('//'):
            continue

        if line.startswith('#EXTINF'):
            current_extinf = line
            continue

        if not line.startswith('#') and current_extinf:
            url = line
            if ',' in current_extinf:
                channel_name = current_extinf.split(',')[-1].strip()
            else:
                channel_name = "未知频道"

            if channel_name and url.startswith('http'):
                channels.append({'name': channel_name, 'url': url})
            current_extinf = ""
            continue

        if ',' in line and not line.startswith('#'):
            parts = line.split(',', 1)
            if len(parts) == 2:
                channel_name, url = [x.strip() for x in parts]
                if channel_name and url.startswith('http'):
                    channels.append({'name': channel_name, 'url': url})

    return channels

def extract_logo_name(channel_name):
    name = channel_name.strip()
    if name.upper().startswith("CCTV"):
        match = re.search(r"CCTV[-\s]?(\d+?)", name.upper())
        if match:
            num = match.group(1).replace("+", "PLUS")
            return f"CCTV{num}"
    if "卫视" in name:
        match = re.search(r"(.+?)卫视", name)
        if match:
            return match.group(1).strip()

    clean_name = name
    for word in SUFFIX_WORDS:
        clean_name = clean_name.replace(word, "")
    return clean_name.strip() if clean_name.strip() else name

def get_channel_group(channel_name):
    name = channel_name.strip()
    if name.upper().startswith("CCTV"): return "央视频道"
    elif "卫视" in name: return "卫视频道"
    elif "河北" in name: return "河北地方"
    elif any(x in name for x in ["电影", "影院"]): return "影视频道"
    elif any(x in name for x in ["体育", "赛事"]): return "体育频道"
    elif any(x in name for x in ["少儿", "卡通"]): return "少儿频道"
    else: return "其他"

def get_epg_id(channel_name):
    name = channel_name.strip().upper()
    if name.startswith("CCTV"):
        match = re.search(r"CCTV[-\s]?(\d+?)", name)
        if match: return f"CCTV{match.group(1).replace('+', 'PLUS')}"
    if "卫视" in name:
        match = re.search(r"(.+?)卫视", name)
        if match:
            province = match.group(1).strip()
            p_map = {"北京":"BTV","上海":"东方卫视","天津":"天津卫视","重庆":"重庆卫视","湖南":"湖南卫视","浙江":"浙江卫视","江苏":"江苏卫视","广东":"广东卫视","山东":"山东卫视","河南":"河南卫视","河北":"河北卫视","四川":"四川卫视","湖北":"湖北卫视","辽宁":"辽宁卫视","黑龙江":"黑龙江卫视","吉林":"吉林卫视","安徽":"安徽卫视","福建":"福建卫视","江西":"江西卫视","山西":"山西卫视","陕西":"陕西卫视","甘肃":"甘肃卫视","青海":"青海卫视","宁夏":"宁夏卫视","新疆":"新疆卫视","西藏":"西藏卫视","内蒙古":"内蒙古卫视","广西":"广西卫视","贵州":"贵州卫视","云南":"云南卫视","海南":"海南卫视"}
            return p_map.get(province, f"{province}卫视")
    if "河北" in name: return name.replace("高清","").replace("HD","").strip()
    return name

def enrich_channels(raw_channels):
    merged = {}
    for ch in raw_channels:
        name = ch['name']
        url = ch['url']
        if name not in merged:
            merged[name] = {
                'group': get_channel_group(name),
                'logo': f"{LOGO_BASE_URL}{extract_logo_name(name).replace(' ', '').replace('-', '')}.png",
                'epg': get_epg_id(name),
                'urls': []
            }
        if url not in merged[name]['urls']:
            merged[name]['urls'].append(url)
    return merged

def generate_m3u(enriched_channels, output_file):
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        f.write(f'#EXTM3U x-tvg-url="{EPG_URL}"\n')
        total_count = 0
        for name, info in enriched_channels.items():
            for idx, url in enumerate(info['urls']):
                suffix = f" 源{idx+1}" if len(info['urls']) > 1 else ""
                display_name = f"{name}{suffix}"
                extinf = (
                    f'#EXTINF:-1 '
                    f'group-title="{info["group"]}" '
                    f'tvg-id="{info["epg"]}" '
                    f'tvg-name="{name}" '
                    f'tvg-logo="{info["logo"]}",'
                    f'{display_name}'
                )
                f.write(f"{extinf}\n{url}\n")
                total_count += 1
    return total_count

def main():
    print("=" * 50)
    print("🚀 河北电信直播源抓取工具 (收录时间: 2026-06-12)")
    print("=" * 50)

    links = get_telecom_links(BASE_URL)
    if not links:
        print("❌ 未找到任何链接，程序终止")
        with open(OUTPUT_FILE, 'w') as f: f.write("#EMPTY\n")
        return

    all_raw_channels = []
    for i, link in enumerate(links, 1):
        print(f"\n--- [{i}/{len(links)}] ---")
        content = fetch_playlist(link)
        if content:
            channels = parse_raw_content(content)
            print(f"   ✅ 解析出 {len(channels)} 个频道")
            all_raw_channels.extend(channels)
        time.sleep(2) # 抓取间隔加长，防止被封

    if not all_raw_channels:
        print("\n⚠️ 未能解析出任何频道数据，生成空文件")
        with open(OUTPUT_FILE, 'w') as f: f.write("#EMPTY\n")
        return

    enriched = enrich_channels(all_raw_channels)
    total = generate_m3u(enriched, OUTPUT_FILE)

    print("\n" + "=" * 50)
    print(f"🎉 完成！唯一频道: {len(enriched)}, 总线路: {total}")
    print("=" * 50)

if __name__ == '__main__':
    main()
