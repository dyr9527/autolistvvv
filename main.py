import requests
import re

# 源站地址
SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"

# --- 核心配置：使用 gcore.jsdelivr.net（国内最稳的jsDelivr节点）---
# fanmingming/live 仓库的台标文件是全大写命名的，必须严格匹配
LOGO_BASE_URL = "https://gcore.jsdelivr.net/gh/fanmingming/live/tv/"

# 卫视名称映射表（值必须与fanmingming仓库中的文件名完全一致，全大写）
WEISHI_MAPPING = {
    "北京卫视": "BTVWS", "东方卫视": "DFWS", "天津卫视": "TJWS", "重庆卫视": "CQWS",
    "黑龙江卫视": "HLJWS", "辽宁卫视": "LNWS", "河北卫视": "HEBWS", "山东卫视": "SDWS",
    "安徽卫视": "AHWS", "河南卫视": "HNWS", "湖北卫视": "HUBWS", "湖南卫视": "HUNWS",
    "江西卫视": "JXWS", "江苏卫视": "JSWS", "浙江卫视": "ZJWS", "东南卫视": "DNWS",
    "广东卫视": "GDWS", "深圳卫视": "SZWS", "广西卫视": "GXWS", "云南卫视": "YNWS",
    "贵州卫视": "GZWS", "四川卫视": "SCWS", "康巴卫视": "KBWS", "西藏卫视": "XZWS",
    "陕西卫视": "SXWS", "甘肃卫视": "GSWS", "青海卫视": "QHWS", "宁夏卫视": "NXWS",
    "新疆卫视": "XJWS", "内蒙古卫视": "NMGWS", "吉林卫视": "JLWS", "海南卫视": "HINWS"
}

def get_group_and_logo(channel_name):
    """根据频道名自动匹配分组和台标"""
    name_clean = channel_name.strip()
    name_upper = name_clean.upper()

    group = "其他"
    logo_filename = ""

    # --- 1. 央视频道 (CCTV) ---
    if name_upper.startswith("CCTV"):
        group = "央视频道"
        # fanmingming仓库中CCTV台标为全大写，如CCTV1.png、CCTV5PLUS.png
        clean_cctv = name_upper.replace("-", "").replace(" ", "")
        if "CCTV5+" in clean_cctv:
            clean_cctv = "CCTV5PLUS"
        logo_filename = f"{clean_cctv}.png"

    # --- 2. 卫视频道 ---
    elif "卫视" in name_clean:
        group = "卫视频道"
        matched = False
        for key, value in WEISHI_MAPPING.items():
            if key in name_clean:
                logo_filename = f"{value}.png"
                matched = True
                break
        # 如果映射表没查到，尝试通用规则（全大写）
        if not matched:
            ws_name = name_upper.replace("卫视", "WS")
            logo_filename = f"{ws_name}.png"

    # --- 3. 河北地方频道 ---
    elif "河北" in name_clean:
        group = "河北地方频道"
        hb_name = name_upper.replace("河北", "")
        hb_name = re.sub(r'高清|HD', '', hb_name).strip()
        # fanmingming仓库中河北台标命名如 HEBJJSH.png
        logo_filename = f"HEB{hb_name}.png"

    # --- 4. 兜底 ---
    else:
        group = "其他"
        logo_filename = ""

    # 拼接完整链接
    full_logo_url = f"{LOGO_BASE_URL}{logo_filename}" if logo_filename else ""

    return group, full_logo_url

def main():
    print(f"🚀 开始抓取: {SOURCE_URL}")

    m3u_lines = ['#EXTM3U']
    count = 0

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(SOURCE_URL, headers=headers, timeout=20)
        response.raise_for_status()

        # 预处理文本，将HTML换行符转换为真正的换行符
        text = response.text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')

        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if ',' in line:
                parts = line.split(',', 1)
                name = parts.strip()
                url = parts.strip()[[source_group_web_2]]

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

    # 使用 newline='' 确保生成 Unix 换行符
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline='') as f:
        f.write("\n".join(m3u_lines))

    print(f"💾 已保存: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
