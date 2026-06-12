import requests
import re

SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"

def get_logo_name(channel_name):
    """
    从频道名中提取台标文件名（只保留英文和数字）
    """
    name_upper = channel_name.upper()
    
    # CCTV频道：提取CCTV+数字/字母，如CCTV1、CCTV5+
    if name_upper.startswith("CCTV"):
        match = re.match(r'CCTV[0-9A-Z\+]+', name_upper)
        return match.group() if match else None
    
    # 卫视频道：提取卫视前的省份名拼音首字母或英文名
    if "卫视" in channel_name:
        # 去掉"卫视"二字，只保留前面的部分
        prefix = channel_name.replace("卫视", "").strip()
        # 只保留英文和数字
        logo = re.sub(r'[^A-Z0-9]', '', prefix.upper())
        return logo if logo else None
    
    # 河北频道
    if "河北" in channel_name:
        # 河北卫视 -> HEBEIWS, 河北1 -> HEBEI1
        logo = name_upper.replace("卫视", "WS")
        logo = re.sub(r'[^A-Z0-9]', '', logo)
        return logo if logo else None
    
    # 其他：只保留英文和数字
    logo = re.sub(r'[^A-Z0-9]', '', name_upper)
    return logo if logo else None

def get_group(channel_name):
    """
    判断频道分类
    """
    name_upper = channel_name.upper()
    
    if "河北" in channel_name or "HEBEI" in name_upper:
        return "河北地方频道"
    elif name_upper.startswith("CCTV"):
        return "央视频道"
    elif "卫视" in channel_name:
        return "卫视频道"
    else:
        return "其他"

def main():
    print(f"🚀 开始抓取源站: {SOURCE_URL}")
    m3u_lines = [
        '#EXTM3U x-tvg-url="https://live.fanmingming.com/e.xml.gz"',
        ''  # 空行
    ]
    count = 0

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(SOURCE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        text = response.text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
        lines = text.splitlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if ',' in line:
                parts = line.split(',', 1)
                name = parts[0].strip()
                url = parts[1].strip()

                if url.startswith('http'):
                    group_title = get_group(name)
                    logo_name = get_logo_name(name)
                    tvg_logo = f"https://live.fanmingming.com/tv/{logo_name}.png" if logo_name else "https://live.fanmingming.com/tv/DEFAULT.png"
                    
                    # 严格按照参考格式：tvg-id -> tvg-name -> tvg-logo -> group-title
                    extinf = f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{tvg_logo}" group-title="{group_title}",{name}'
                    
                    m3u_lines.append(extinf)
                    m3u_lines.append(url)
                    count += 1

        print(f"✅ 成功处理 {count} 个频道")

    except Exception as e:
        print(f"❌ 抓取或处理失败: {str(e)}")
        error_line = '#EXTINF:-1 tvg-id="抓取失败" tvg-name="抓取失败" tvg-logo="https://live.fanmingming.com/tv/ERROR.png" group-title="其他",抓取失败-请检查源站'
        m3u_lines.append(error_line)
        m3u_lines.append("http://example.com/empty")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    print(f"💾 已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
