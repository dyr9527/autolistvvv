import requests
import re

# 源站地址
SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"  # 👈 改回 .m3u 后缀

def get_group_and_logo(channel_name):
    """根据频道名自动匹配分组和台标"""
    name_upper = channel_name.upper()
    
    # 1. 河北地方频道
    if "河北" in channel_name or "HEBEI" in name_upper:
        group = "河北地方频道"
        logo = f"https://live.fanmingming.com/tv/{name_upper.replace('卫视', 'WS')}.png"
    
    # 2. 央视频道
    elif name_upper.startswith("CCTV"):
        group = "央视频道"
        match = re.match(r'CCTV[0-9A-Z\+]+', name_upper)
        logo_name = match.group() if match else name_upper
        logo = f"https://live.fanmingming.com/tv/{logo_name}.png"
    
    # 3. 卫视频道
    elif "卫视" in channel_name:
        group = "卫视频道"
        logo = f"https://live.fanmingming.com/tv/{name_upper.replace('卫视', 'WS')}.png"
    
    # 4. 其他
    else:
        group = "其他"
        logo = f"https://live.fanmingming.com/tv/{name_upper}.png"
        
    return group, logo

def main():
    print(f"🚀 开始抓取: {SOURCE_URL}")
    m3u_lines = [
        '#EXTM3U x-tvg-url="https://live.fanmingming.com/e.xml.gz"'
    ]
    count = 0

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(SOURCE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        text = response.text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
        
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ',' in line:
                parts = line.split(',', 1)
                name = parts[0].strip()
                url = parts[1].strip()
                
                if url.startswith('http'):
                    group_title, tvg_logo = get_group_and_logo(name)
                    extinf = f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{tvg_logo}" group-title="{group_title}",{name}'
                    m3u_lines.append(extinf)
                    m3u_lines.append(url)
                    count += 1

        print(f"✅ 成功处理 {count} 个频道")

    except Exception as e:
        print(f"❌ 失败: {e}")
        m3u_lines.append('#EXTINF:-1 group-title="其他",抓取失败')
        m3u_lines.append("http://example.com/empty")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    print(f"💾 已保存: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
