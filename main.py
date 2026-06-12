import requests
import re

# 源站地址和输出文件
SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u" # 恢复为 m3u 格式

def get_group_and_logo(channel_name):
    """
    根据频道名称判断分类和台标
    """
    # 统一转为大写便于匹配
    name_upper = channel_name.upper()
    
    # 1. 河北地方频道 (包含"河北"或"HEBEI")
    if "河北" in channel_name or "HEBEI" in name_upper:
        group = "河北地方频道"
        logo = f"https://live.fanmingming.com/tv/{name_upper}.png"
    
    # 2. 央视频道 (以 CCTV 开头)
    elif name_upper.startswith("CCTV"):
        group = "央视频道"
        logo = f"https://live.fanmingming.com/tv/{name_upper}.png"
    
    # 3. 卫视频道 (包含"卫视")
    elif "卫视" in channel_name:
        group = "卫视频道"
        logo = f"https://live.fanmingming.com/tv/{name_upper}.png"
    
    # 4. 其他
    else:
        group = "其他"
        logo = f"https://live.fanmingming.com/tv/{name_upper}.png"
    
    return group, logo

def main():
    print(f"🚀 开始抓取源站: {SOURCE_URL}")
    m3u_lines = ["#EXTM3U"] # M3U 文件头
    count = 0

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(SOURCE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        # 处理 HTML 换行标签
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
                    # 获取分类和台标
                    group_title, tvg_logo = get_group_and_logo(name)
                    
                    # 构建标准 M3U 行
                    # 格式: #EXTINF:-1 tvg-id="NAME" tvg-name="NAME" tvg-logo="URL" group-title="GROUP",NAME
                    extinf = f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{tvg_logo}" group-title="{group_title}",{name}'
                    
                    m3u_lines.append(extinf)
                    m3u_lines.append(url)
                    count += 1

        print(f"✅ 成功处理 {count} 个频道")

    except Exception as e:
        print(f"❌ 抓取或处理失败: {str(e)}")
        # 如果出错，写入一个错误提示频道
        error_line = '#EXTINF:-1 tvg-id="抓取失败" tvg-name="抓取失败" tvg-logo="https://live.fanmingming.com/tv/ERROR.png" group-title="其他",抓取失败-请检查源站'
        m3u_lines.append(error_line)
        m3u_lines.append("http://example.com/empty")

    # 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    print(f"💾 已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
