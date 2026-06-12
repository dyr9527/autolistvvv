import requests
import re

# 源站地址
SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"


def get_group_and_logo(channel_name):
    """根据频道名自动匹配分组和台标"""
    # 清洗频道名，去除首尾空格
    name_clean = channel_name.strip()
    name_upper = name_clean.upper()

    group = "其他"
    logo = ""

    # --- 1. 央视频道 (CCTV) ---
    if name_upper.startswith("CCTV"):
        group = "央视频道"
        # 尝试构建标准文件名，例如 CCTV-1 -> CCTV1.png, CCTV5+ -> CCTV5PLUS.png
        # fanmingming图床通常不需要连字符
        clean_cctv = name_upper.replace("-", "").replace(" ", "")
        logo = f"https://live.fanmingming.com/tv/{clean_cctv}.png"

    # --- 2. 卫视频道 ---
    elif "卫视" in name_clean:
        group = "卫视频道"
        # 提取卫视名称，例如 "湖南卫视" -> HUNANWS.png (需根据图床实际规则调整)
        # 这里采用通用策略：直接拼接，如果不行则留空
        ws_name = name_upper.replace("卫视", "WS")
        logo = f"https://live.fanmingming.com/tv/{ws_name}.png"

    # --- 3. 河北地方频道 ---
    elif "河北" in name_clean:
        group = "河北地方频道"
        # 尝试匹配河北台标
        hb_name = name_upper.replace("河北", "")
        logo = f"https://live.fanmingming.com/tv/HEBEI{hb_name}.png"

    # --- 4. 兜底策略 ---
    else:
        group = "其他"
        # 对于无法识别的频道，不强行指定logo，避免显示错误的占位符
        # 如果OK影视支持默认图标，这里可以留空
        logo = ""

    return group, logo


def main():
    print(f"🚀 开始抓取: {SOURCE_URL}")

    # 核心修复：移除 x-tvg-url，避免网络加载时解析异常
    m3u_lines = ['#EXTM3U']
    count = 0

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(SOURCE_URL, headers=headers, timeout=20)
        response.raise_for_status()

        # 预处理文本，将HTML换行符转换为Python换行符
        text = response.text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')

        for line in text.splitlines():
            line = line.strip()
            # 跳过空行或注释行
            if not line or line.startswith('#'):
                continue

            # 简单的解析逻辑：假设格式为 "频道名,url"
            if ',' in line:
                parts = line.split(',', 1)
                name = parts[0].strip()
                url = parts[1].strip()

                if url.startswith('http'):
                    group_title, tvg_logo = get_group_and_logo(name)

                    # 构建 EXTINF 行
                    # 注意：属性之间必须有空格，且顺序尽量标准
                    extinf = f'#EXTINF:-1 group-title="{group_title}" tvg-id="{name}" tvg-name="{name}" tvg-logo="{tvg_logo}",{name}'

                    m3u_lines.append(extinf)
                    m3u_lines.append(url)
                    count += 1

        print(f"✅ 成功处理 {count} 个频道")

    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        # 即使失败也写入一个占位符，防止文件为空导致订阅报错
        m3u_lines.append('#EXTINF:-1 group-title="Error",抓取失败请检查源')
        m3u_lines.append("http://example.com/empty")

    # 核心修复：使用 newline='\n' 确保生成的 M3U 文件是 Unix 换行符
    # 这对 OK影视/TvBox 网络订阅至关重要
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline='') as f:
        f.write("\n".join(m3u_lines))

    print(f"💾 已保存: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
