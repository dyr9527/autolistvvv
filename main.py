import requests
import re

# 源站地址
SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"

# --- 1. 卫视名称映射表 (用于生成正确的图片文件名) ---
WEISHI_MAPPING = {
    "北京卫视": "BTVWS", "东方卫视": "DFWS", "天津卫视": "TJWS", "重庆卫视": "CQWS",
    "黑龙江卫视": "HLJWS", "辽宁卫视": "LNWS", "河北卫视": "HEBWS", "山东卫视": "SDWS",
    "安徽卫视": "AHWS", "河南卫视": "HNWS", "湖北卫视": "HBWS", "湖南卫视": "HUNWS",
    "江西卫视": "JXWS", "江苏卫视": "JSWS", "浙江卫视": "ZJWS", "东南卫视": "DNWS",
    "广东卫视": "GDWS", "深圳卫视": "SZWS", "广西卫视": "GXWS", "云南卫视": "YNWS",
    "贵州卫视": "GZWS", "四川卫视": "SCWS", "康巴卫视": "KBWS", "西藏卫视": "XZWS",
    "陕西卫视": "SXTVS", "甘肃卫视": "GSW", "青海卫视": "QHWS", "宁夏卫视": "NXWS",
    "新疆卫视": "XJWS", "内蒙古卫视": "NMWS", "海南卫视": "HANWS"
}

# --- 2. 河北地方台映射表 (新增部分) ---
HEBEI_LOCAL_MAPPING = {
    "河北经济生活": "HEB2",      # 对应 HEB2.png
    "河北都市": "HEB3",          # 对应 HEB3.png
    "河北影视剧": "HEB4",        # 对应 HEB4.png
    "河北少儿科教": "HEB5",      # 对应 HEB5.png
    "河北农民": "HEB6",          # 对应 HEB6.png
    "河北公共": "HEB7",          # 对应 HEB7.png
    "河北交通": "HEB8",          # 对应 HEB8.png
    "河北移动": "HEB9"           # 对应 HEB9.png
}


def get_group_and_logo(channel_name):
    """根据频道名自动匹配分组和台标"""
    name_clean = channel_name.strip()
    name_upper = name_clean.upper()

    group = "其他"
    logo_file = ""

    # --- A. 央视频道 ---
    if name_upper.startswith("CCTV"):
        group = "央视频道"
        # 去除连字符，例如 CCTV-1 -> CCTV1
        clean_cctv = name_upper.replace("-", "").replace(" ", "")
        logo_file = f"{clean_cctv}.png"

    # --- B. 卫视频道 ---
    elif "卫视" in name_clean:
        group = "卫视频道"
        # 遍历映射表查找匹配
        matched = False
        for key, value in WEISHI_MAPPING.items():
            if key in name_clean:
                logo_file = f"{value}.png"
                matched = True
                break
        # 如果没在表里，尝试用拼音首字母或原名兜底（这里简单处理为原名）
        if not matched:
            safe_name = name_clean.replace("卫视", "WS").replace("高清", "")
            logo_file = f"{safe_name}.png"

    # --- C. 河北地方频道 ---
    elif "河北" in name_clean and "卫视" not in name_clean:
        group = "河北地方频道"
        matched = False
        for key, value in HEBEI_LOCAL_MAPPING.items():
            if key in name_clean:
                logo_file = f"{value}.png"
                matched = True
                break
        # 兜底逻辑：如果是河北卫视但没匹配到上面，或者是其他河北台
        if not matched:
             if "河北卫视" in name_clean:
                 logo_file = "HEBWS.png"
             else:
                 # 尝试直接用名字，防止完全找不到
                 logo_file = f"{name_clean.replace('高清','')}.png"

    # --- D. 其他 ---
    else:
        group = "其他"
        logo_file = f"{name_clean.replace('高清','')}.png"

    # 拼接完整的 Gitee 图标链接
    # 注意：Gitee raw 链接格式
    final_logo_url = f"https://gitee.com/nmt88/tvlogo/raw/master/{logo_file}"

    return group, final_logo_url


def main():
    print(f"🚀 开始抓取: {SOURCE_URL}")
    m3u_lines = ['#EXTM3U']
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
                    # 写入 M3U 条目
                    extinf = f'#EXTINF:-1 group-title="{group_title}" tvg-id="{name}" tvg-name="{name}" tvg-logo="{tvg_logo}",{name}'
                    m3u_lines.append(extinf)
                    m3u_lines.append(url)
                    count += 1

        print(f"✅ 成功处理 {count} 个频道")

    except Exception as e:
        print(f"❌ 失败: {e}")
        m3u_lines.append('#EXTINF:-1 group-title="其他",抓取失败')
        m3u_lines.append("http://example.com/empty")

    # 强制使用 \n 换行符，防止 Windows 下生成的文件无法被播放器识别
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline='') as f:
        f.write("\n".join(m3u_lines))

    print(f"💾 已保存: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
