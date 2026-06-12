import requests
import re

SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"

# --- 核心修改部分开始 ---
def get_group_and_logo(channel_name):
    """根据频道名自动匹配分组和台标"""
    name_upper = channel_name.upper().strip()
    group = "其他"
    logo = "" # 默认留空，防止显示错误的图标

    # 1. 河北地方频道 (尝试匹配常见河北台)
    if "河北" in channel_name:
        group = "河北地方频道"
        # 使用 fanmingming 的源作为首选，如果不行再换
        # 这里为了稳定性，尝试构建通用文件名
        clean_name = name_upper.replace("河北", "").replace("卫视", "")
        logo = f"https://live.fanmingming.com/tv/{name_upper}.png"

    # 2. 央视频道 (CCTV系列)
    elif name_upper.startswith("CCTV"):
        group = "央视频道"
        # 提取 CCTV-1, CCTV-4K 等标准名称
        match = re.match(r'CCTV[-\s]?([0-9A-Z\+]+)', name_upper)
        if match:
            suffix = match.group(1).replace("-", "").replace(" ", "")
            logo = f"https://live.fanmingming.com/tv/CCTV{suffix}.png"

    # 3. 卫视频道 (XX卫视)
    elif "卫视" in channel_name:
        group = "卫视频道"
        # 去掉“卫视”二字去匹配图片，例如“湖南卫视” -> “湖南.png”
        short_name = name_upper.replace("卫视", "")
        logo = f"https://live.fanmingming.com/tv/{short_name}.png"

    # --- 兜底策略：如果上面的链接都不行，可以尝试下面的备用源 ---
    # 如果你发现上面的图还是不出来，把下面这行取消注释，并注释掉上面的 logo 赋值
    # logo = f"https://gcore.jsdelivr.net/gh/tvbw/tv-icon@main/logo/{channel_name}.png"

    return group, logo
# --- 核心修改部分结束 ---

def main():
    try:
        response = requests.get(SOURCE_URL, timeout=10)
        response.encoding = 'utf-8'
        content = response.text
    except Exception as e:
        print(f"获取源失败: {e}")
        return

    lines = content.split('\n')
    m3u_output = ['#EXTM3U']

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # 简单的解析逻辑：假设格式为 "频道名,url"
        if ',' in line:
            parts = line.split(',', 1)
            name = parts[0].strip()
            url = parts[1].strip()

            group, logo = get_group_and_logo(name)

            # 构建标准 M3U 条目
            # 注意：group-title 放在最前面兼容性最好
            ext_line = f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}",{name}'
            m3u_output.append(ext_line)
            m3u_output.append(url)

    # 写入文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_output))

    print(f"成功生成 {OUTPUT_FILE}，共 {len(m3u_output)//2} 个频道")

if __name__ == "__main__":
    main()
