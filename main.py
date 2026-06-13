import requests
from bs4 import BeautifulSoup
import re
import time
import os

# --- 配置区 ---
BASE_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "kaniptv.m3u"

# 台标CDN地址
LOGO_BASE_URL = "https://cdn.jsdelivr.net/gh/fanmingming/live@main/tv/"

# EPG节目单地址
EPG_URL = "http://epg.51zmt.top:8000/e.xml"

# 用于频道名称清洗的后缀词
SUFFIX_WORDS = [
    "高清", "HD", "hd", "4K", "超清", "标清", "SD",
    "频道", "电视台", "综合", "财经", "综艺", "体育",
    "电影", "电视剧", "纪录", "少儿", "军事", "农业",
    "科教", "戏曲", "社会与法", "新闻", "音乐"
]

# 获取代理设置 (从环境变量读取)
PROXY = os.environ.get('HTTP_PROXY', None)
proxies = {'http': PROXY, 'https': PROXY} if PROXY else {}

# 伪装浏览器请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

def get_telecom_links(page_url):
    print(f"🔍 正在分析入口页面: {page_url}")
    try:
        # 使用 proxies 参数
        resp = requests.get(page_url, headers=HEADERS, timeout=20, proxies=proxies)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        telecom_links = []
        operator_tags = soup.find_all(string=re.compile("河北-电信"))

        for tag in operator_tags:
            btn = tag.find_previous(name='a')
            if btn and btn.get('href'):
                link = btn['href']
                if not link.startswith('http'):
                    base_domain = "http://nn.7x9d.cn"
                    link = base_domain + "/" + link.lstrip('/')
                ip_text = btn.get_text(strip=True)
                print(f"✅ 发现电信源: [{ip_text}] -> {link}")
                telecom_links.append(link)

        return list(set(telecom_links))

    except Exception as e:
        print(f"❌ 解析入口页面失败: {e}")
        return []

def fetch_playlist(url):
    try:
        headers_with_referer = HEADERS.copy()
        headers_with_referer['Referer'] = BASE_URL

        # 使用 proxies 参数
        resp = requests.get(url, headers=headers_with_referer, timeout=20, proxies=proxies)
        if resp.encoding == 'ISO-8859-1':
            resp.encoding = 'utf-8'

        content = resp.text.strip()
        # 简单的防拦截判断：如果返回内容包含 "verify" 或 "captcha" 等字样，说明被拦截了
        if "verify" in content.lower() or "captcha" in content.lower():
            print(f"⚠️ 触发反爬验证，IP可能被封锁")
            return ""

        if len(content) < 50:
            print(f"⚠️ 返回内容过少，可能被拦截")
            return ""

        return content

    except Exception as e:
        print(f"❌ 获取 {url} 失败: {e}")
        return ""

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
                channel_name = f"未知频道"
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
    clean_name = clean_name.strip()
    return clean_name if clean_name else name

def get_channel_group(channel_name):
    name = channel_name.strip()
    if name.upper().startswith("CCTV"):
        return "央视频道"
    elif "卫视" in name:
        return "卫视频道"
    elif "河北" in name:
        return "河北地方"
    elif any(x in name for x in ["电影", "影院", "影视频道"]):
        return "影视频道"
    elif any(x in name for x in ["体育", "赛事"]):
        return "体育频道"
    elif any(x in name for x in ["少儿", "卡通", "动画"]):
        return "少儿频道"
    elif any(x in name for x in ["纪录", "纪实"]):
        return "纪录频道"
    else:
        return "其他"

def get_epg_id(channel_name):
    name = channel_name.strip().upper()
    if name.startswith("CCTV"):
        match = re.search(r"CCTV[-\s]?(\d+?)", name)
        if match:
            num = match.group(1).replace("+", "PLUS")
            return f"CCTV{num}"
    if "卫视" in name:
        match = re.search(r"(.+?)卫视", name)
        if match:
            province = match.group(1).strip()
            province_map = {
                "北京": "BTV", "上海": "东方卫视", "天津": "天津卫视", "重庆": "重庆卫视",
                "湖南": "湖南卫视", "浙江": "浙江卫视", "江苏": "江苏卫视", "广东": "广东卫视",
                "山东": "山东卫视", "河南": "河南卫视", "河北": "河北卫视", "四川": "四川卫视",
                "湖北": "湖北卫视", "辽宁": "辽宁卫视", "黑龙江": "黑龙江卫视", "吉林": "吉林卫视",
                "安徽": "安徽卫视", "福建": "福建卫视", "江西": "江西卫视", "山西": "山西卫视",
                "陕西": "陕西卫视", "甘肃": "甘肃卫视", "青海": "青海卫视", "宁夏": "宁夏卫视",
                "新疆": "新疆卫视", "西藏": "西藏卫视", "内蒙古": "内蒙古卫视", "广西": "广西卫视",
                "贵州": "贵州卫视", "云南": "云南卫视", "海南": "海南卫视"
            }
            return province_map.get(province, f"{province}卫视")
    if "河北" in name:
        return name.replace("高清", "").replace("HD", "").strip()
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
    print("🚀 河北电信直播源抓取工具")
    if PROXY:
        print(f"🛡️ 当前使用代理: {PROXY}")
    else:
        print("⚠️ 未检测到代理，直连模式可能失败")
    print("=" * 50)

    print("\n【第一阶段】抓取原始直播源...")
    links = get_telecom_links(BASE_URL)

    if not links:
        print("❌ 未找到任何电信源链接")
        return

    print(f"\n✅ 共找到 {len(links)} 个电信源，开始逐个抓取...\n")

    all_raw_channels = []
    for i, link in enumerate(links, 1):
        print(f"--- [{i}/{len(links)}] 正在抓取: {link} ---")
        content = fetch_playlist(link)

        if not content:
            print("   ❌ 获取失败，跳过")
            continue

        channels = parse_raw_content(content)
        print(f"   ✅ 解析出 {len(channels)} 个频道")
        all_raw_channels.extend(channels)
        time.sleep(1)

    if not all_raw_channels:
        print("\n⚠️ 未能解析出任何频道数据")
        return

    print(f"\n✅ 第一阶段完成！共获取原始频道 {len(all_raw_channels)} 条")

    print("\n【第二阶段】正在分类、注入台标和EPG信息...")
    enriched = enrich_channels(all_raw_channels)
    print(f"✅ 第二阶段完成！去重合并后共 {len(enriched)} 个唯一频道")

    print("\n【第三阶段】正在生成M3U文件...")
    total = generate_m3u(enriched, OUTPUT_FILE)
    print(f"✅ 第三阶段完成！")

    print("\n" + "=" * 50)
    print("🎉 全部完成！")
    print(f"   输出文件: {OUTPUT_FILE}")
    print(f"   唯一频道: {len(enriched)} 个")
    print(f"   总线路数: {total} 条")
    print(f"   EPG地址: {EPG_URL}")
    print("=" * 50)

if __name__ == '__main__':
    main()
