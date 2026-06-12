import requests
import re

SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"

# EPG 节目单源地址
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

LOGO_BASE_URL = "https://cdn.jsdelivr.net/gh/fanmingming/live@main/tv/"

# 需要过滤掉的后缀词
SUFFIX_WORDS = [
    "高清", "HD", "hd", "4K", "超清", "标清", "SD",
    "频道", "电视台", "综合", "财经", "综艺", "体育",
    "电影", "电视剧", "纪录", "少儿", "军事", "农业",
    "科教", "戏曲", "社会与法", "新闻", "音乐", "少儿"
]

def generate_tvg_id(channel_name):
    """
    生成标准化的 tvg-id，用于匹配 EPG 数据
    """
    name = channel_name.strip()
    
    # 1. 处理 CCTV 频道
    if name.upper().startswith("CCTV"):
        match = re.search(r"CCTV[-\s]?(\d+)", name)
        if match:
            return f"CCTV{match.group(1)}"
        # 处理 CCTV-Plus 等特殊情况
        return name.replace("-", "").replace(" ", "")
    
    # 2. 处理 卫视/地方台
    if "卫视" in name:
        # 提取省份名称，如 "河北卫视高清" -> "河北"
        for word in ["卫视", "高清", "HD"]:
            name = name.replace(word, "")
        return f"{name}卫视"
    
    # 3. 默认返回清理后的名称
    return name

def extract_logo_name(channel_name):
    """
    从频道名中提取台标文件名
    """
    name = channel_name.strip()
    
    # 1. CCTV频道特殊处理
    if name.upper().startswith("CCTV"):
        match = re.search(r"CCTV[-\s]?(\d+\+?)", name.upper())
        if match:
            num = match.group(1).replace("+", "PLUS")
            return f"CCTV{num}"
    
    # 2. 去除后缀词
    clean_name = name
    for word in SUFFIX_WORDS:
        clean_name = clean_name.replace(word, "")
    clean_name = clean_name.strip()
    
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
    # 修改点1: 在头部添加 x-tvg-url 指向 EPG 源
    m3u_lines = [f'#EXTM3U x-tvg-url="{EPG_URL}"']
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
                
                # 修改点2: 使用更规范的 tvg-id
                tvg_id = generate_tvg_id(name)
                
                extinf = f'#EXTINF:-1 group-title="{group}" tvg-id="{tvg_id}" tvg-name="{name}" tvg-logo="{logo}",{name}'
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
