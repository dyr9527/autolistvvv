import requests

SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"

LOGO_BASE_URL = "https://cdn.jsdelivr.net/gh/fanmingming/live@main/tv/"

def get_logo_filename(channel_name):
    """
    根据频道名生成台标文件名
    优先用规则转换，转换不了的直接用原名
    """
    name = channel_name.strip()
    
    # CCTV频道：CCTV-1 综合 -> CCTV1
    if name.upper().startswith("CCTV"):
        cctv_name = name.upper().replace("-", "").replace(" ", "")
        # 提取CCTV数字部分
        import re
        match = re.match(r"CCTV(\d+\+?)", cctv_name)
        if match:
            num = match.group(1).replace("+", "PLUS")
            return f"CCTV{num}.png"
    
    # 其他频道：直接用原名（卫视、地方台大多是中文原名）
    return f"{name}.png"

def get_group_and_logo(channel_name):
    name = channel_name.strip()
    group = "其他"
    
    if name.upper().startswith("CCTV"):
        group = "央视频道"
    elif "卫视" in name:
        group = "卫视频道"
    elif "河北" in name:
        group = "河北地方频道"
    
    logo_filename = get_logo_filename(name)
    logo_url = f"{LOGO_BASE_URL}{logo_filename}"
    
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
