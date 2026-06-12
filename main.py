import requests
import re

SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"

LOGO_BASE_URL = "https://cdn.jsdelivr.net/gh/fanmingming/live@main/tv/"

# 需要过滤掉的后缀词
SUFFIX_WORDS = [
    "高清", "HD", "hd", "4K", "超清", "标清", "SD",
    "频道", "电视台", "综合", "财经", "综艺", "体育",
    "电影", "电视剧", "纪录", "少儿", "军事", "农业",
    "科教", "戏曲", "社会与法", "新闻", "音乐", "少儿"
]

def extract_logo_name(channel_name):
    """
    从频道名中提取台标文件名
    """
    name = channel_name.strip()
    
    # 1. CCTV频道特殊处理
    if name.upper().startswith("CCTV"):
        # 提取CCTV+数字，如CCTV-1 综合 -> CCTV1
        match = re.search(r"CCTV[-\s]?(\d+\+?)", name.upper())
        if match:
            num = match.group(1).replace("+", "PLUS")
            return f"CCTV{num}"
    
    # 2. 去除后缀词
    clean_name = name
    for word in SUFFIX_WORDS:
        clean_name = clean_name.replace(word, "")
    clean_name = clean_name.strip()
    
    # 3. 如果去除后缀后为空，则用原名
    if not clean_name:
        clean_name = name
    
    return clean_name

def get_group_and_logo(channel_name):
    name = channel_name.strip()
    group = "其他"
    
    if name.upper().startswith("CCTV"):
        group = "央视频道"
    elif "卫视" in name:
        group = "卫视频道"
    elif "河北" in name:
        group = "河北地方频道"
    
    logo_name = extract_logo_name(name)
    logo_url = f"{LOGO_BASE_URL}{logo_name}.png"
    
    return group, logo_url

def main():
    print(f"🚀 开始抓取: {SOURCE_URL}")
    m3u_lines = ['#EXTM3U']
    count = 0

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(SOURCE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        text = response.text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
        
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#') or ',' not in line:
                continue
            
            name, url = [x.strip() for x in line.split(',', 1)]
            if url.startswith('http'):
                group, logo = get_group_and_logo(name)
                extinf = f'#EXTINF:-1 group-title="{group}" tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}",{name}'
                m3u_lines.append(extinf)
                m3u_lines.append(url)
                count += 1
        
        print(f"✅ 成功处理 {count} 个频道")
        
    except Exception as e:
        print(f"❌ 抓取失败: {e}")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline='') as f:
        f.write("\n".join(m3u_lines))
    
    print(f"💾 已保存: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
