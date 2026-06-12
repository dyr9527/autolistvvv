import requests
import re

# 源站地址
SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"

# --- 核心配置：更换为 TV-Logo 源 ---
LOGO_BASE_URL = "https://cdn.jsdelivr.net/gh/yuanzl77/tv-logo@latest/logo/"

# 卫视名称映射表
WEISHI_MAPPING = {
    "北京卫视": "btvws", "东方卫视": "dfws", "天津卫视": "tjws", "重庆卫视": "cqws",
    "黑龙江卫视": "hljws", "辽宁卫视": "lnws", "河北卫视": "hebws", "山东卫视": "sdws",
    "安徽卫视": "ahws", "河南卫视": "hnws", "湖北卫视": "hubws", "湖南卫视": "hunws",
    "江西卫视": "jxws", "江苏卫视": "jsws", "浙江卫视": "zjws", "东南卫视": "dnws",
    "广东卫视": "gdws", "深圳卫视": "szws", "广西卫视": "gxws", "云南卫视": "ynws",
    "贵州卫视": "gzws", "四川卫视": "scws", "康巴卫视": "kbws", "西藏卫视": "xzws",
    "陕西卫视": "sxws", "甘肃卫视": "gs", "青海卫视": "qhws", "宁夏卫视": "nxws",
    "新疆卫视": "xjws", "内蒙古卫视": "nmws", "海南卫视": "hinws", "三沙卫视": "ssws",
    "福建东南卫视": "dnws", "海峡卫视": "hxws", "厦门卫视": "xmws"
}

def get_group_and_logo(channel_name):
    """根据频道名自动匹配分组和台标"""
    name_clean = channel_name.strip()
    name_upper = name_clean.upper()
    name_lower = name_clean.lower()

    group = "其他"
    logo = ""

    # --- 1. 央视频道 (CCTV) ---
    if name_upper.startswith("CCTV"):
        group = "央视频道"
        clean_cctv = name_lower.replace("-", "").replace(" ", "")
        if "5+" in clean_cctv:
            clean_cctv = clean_cctv.replace("5+", "5plus")
        logo = f"{LOGO_BASE_URL}{clean_cctv}.png"

    # --- 2. 卫视频道 ---
    elif "卫视" in name_clean:
        group = "卫视频道"
        matched_key = None
        for key in WEISHI_MAPPING:
            if key in name_clean:
                matched_key = key
                break

        if matched_key:
            logo = f"{LOGO_BASE_URL}{WEISHI_MAPPING[matched_key]}.png"
        else:
            short_name = name_lower.replace("卫视", "").replace("电视台", "")[:2]
            logo = f"{LOGO_BASE_URL}{short_name}ws.png"

    # --- 3. 河北地方频道 ---
    elif "河北" in name_clean:
        group = "河北地方频道"
        hb_suffix = name_lower.replace("河北", "").replace("频道", "").replace("电视台", "")
        logo = f"{LOGO_BASE_URL}hebei{hb_suffix}.png"

    # --- 4. 兜底 ---
    else:
        group = "其他"
        logo = ""

    return group, logo

def main():
    print(f"🚀 开始抓取: {SOURCE_URL}")

    m3u_lines = ['#EXTM3U']
    count = 0

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(SOURCE_URL, headers=headers, timeout=20)
        response.raise_for_status()

        # 修复：'\n' 才是真正的换行符
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
                    extinf = f'#EXTINF:-1 group-title="{group_title}" tvg-id="{name}" tvg-name="{name}" tvg-logo="{tvg_logo}",{name}'
                    m3u_lines.append(extinf)
                    m3u_lines.append(url)
                    count += 1

        print(f"✅ 成功处理 {count} 个频道")

    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        m3u_lines.append('#EXTINF:-1 group-title="Error",抓取失败请检查源')
        m3u_lines.append("http://example.com/empty")

    # 修复："\n" 才是真正的换行符
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline='') as f:
        f.write("\n".join(m3u_lines))

    print(f"💾 已保存: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
