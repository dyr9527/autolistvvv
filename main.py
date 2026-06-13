import requests
import gzip
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import date
import os

# ===================== 全局配置 =====================
MAIN_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
BASE_DOMAIN = "http://nn.7x9d.cn"
FILTER_OPERATOR = "河北-电信"
FILTER_DATE = "2026-06-12"

# 台标 & EPG
LOGO_BASE = "https://raw.githubusercontent.com/fanmingming/live/main/tv/"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}

# 分类关键词
RULE_CCTV = ["央视", "CCTV"]
RULE_WEISHI = ["卫视"]
RULE_HEBEI = ["河北"]
# ====================================================

def get_sub_links():
    """抓取符合条件的下级链接"""
    try:
        res = requests.get(MAIN_URL, headers=HEADERS, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        sub_links = []

        for elem in soup.find_all(True):
            txt = elem.get_text(strip=True)
            if FILTER_OPERATOR in txt and FILTER_DATE in txt:
                a_tag = elem.find_previous("a") or elem.find("a")
                if a_tag and a_tag.get("href"):
                    full_url = urljoin(BASE_DOMAIN, a_tag["href"])
                    sub_links.append(full_url)
        return list(set(sub_links))
    except Exception as e:
        print(f"抓取下级链接失败: {e}")
        return []

def extract_live_source(link):
    """【修改点】纯文本整行提取，不判断协议，只取有效非空行"""
    try:
        res = requests.get(link, headers=HEADERS, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        sources = []
        # 遍历所有文本节点，提取每行纯文本
        all_text = soup.get_text(separator="\n")
        for line in all_text.splitlines():
            line = line.strip()
            # 过滤空行、注释行
            if line and not line.startswith(("#", "//")):
                sources.append(line)
        return sources
    except Exception as e:
        print(f"解析 {link} 失败: {e}")
        return []

def get_logo_url(channel_name):
    """拼接台标地址"""
    clean_name = channel_name.replace(" ", "").replace("(", "").replace(")", "")
    return f"{LOGO_BASE}{clean_name}.png"

def classify_channel(name):
    """频道分组：央视 > 卫视 > 河北 > 其他"""
    name_low = name.lower()
    if any(k in name_low for k in RULE_CCTV):
        return "📺 央视频道"
    elif any(k in name_low for k in RULE_WEISHI):
        return "📡 卫视频道"
    elif any(k in name_low for k in RULE_HEBEI):
        return "🏠 河北本地"
    else:
        return "🔍 其他频道"

def download_epg():
    """加载EPG地址"""
    try:
        resp = requests.get(EPG_URL, timeout=20)
        with open("epg_temp.xml.gz", "wb") as f:
            f.write(resp.content)
        return EPG_URL
    except:
        return ""

def parse_name_and_url(raw_line):
    """拆分 频道名,直播源（适配 名称,地址 格式纯文本）"""
    if "," in raw_line:
        name, url = raw_line.split(",", 1)
        return name.strip(), url.strip()
    # 无逗号时，频道名=该行内容
    return raw_line.strip(), raw_line.strip()

def main():
    today = date.today().strftime("%Y-%m-%d")
    out_dir = "output"
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    out_file = os.path.join(out_dir, f"live_{today}.m3u")

    # 1. 获取下级链接
    sub_links = get_sub_links()
    print(f"获取下级链接数量: {len(sub_links)}")
    if not sub_links:
        print("未找到目标链接，程序退出")
        return

    # 2. 纯文本提取所有直播源
    all_raw_lines = []
    for url in sub_links:
        lines = extract_live_source(url)
        all_raw_lines.extend(lines)
    # 去重
    all_raw_lines = list(set(all_raw_lines))
    print(f"纯文本提取直播源总数: {len(all_raw_lines)}")

    # 3. 获取EPG
    epg_link = download_epg()

    # 4. 初始化分组
    group_dict = {
        "📺 央视频道": [],
        "📡 卫视频道": [],
        "🏠 河北本地": [],
        "🔍 其他频道": []
    }

    # 解析每行、分类、匹配台标
    for line in all_raw_lines:
        ch_name, live_url = parse_name_and_url(line)
        group = classify_channel(ch_name)
        logo = get_logo_url(ch_name)
        group_dict[group].append((ch_name, logo, live_url))

    # 5. 生成标准M3U（带分组、台标、EPG）
    m3u_content = [
        "#EXTM3U",
        f'#EXT-X-STREAM-INF:tvg-url="{epg_link}"',
        ""
    ]

    for group_title, items in group_dict.items():
        if not items:
            continue
        m3u_content.append(f"# ===== {group_title} =====")
        for name, logo, src in items:
            ext_inf = f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group_title}",{name}'
            m3u_content.append(ext_inf)
            m3u_content.append(src)
        m3u_content.append("")

    # 写入文件
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_content))

    print(f"✅ 完成！文件已输出至: {out_file}")

if __name__ == "__main__":
    main()
