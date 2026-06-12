import requests
import re

# 源站地址
SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"

# --- 核心配置：更换为国内高速稳定的 TV-Logo 源 ---
# 这个源体积小，不会被 jsDelivr 限速或拦截
LOGO_BASE_URL = "https://cdn.jsdelivr.net/gh/yuanzl77/tv-logo@latest/logo/"

# 卫视名称映射表 (解决卫视台标显示为首字的问题)
# 格式: '频道名关键词': '图床对应的文件名(不含后缀)'
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
    name_upper = name_clean.upper() # 统一转大写用于判断
    name_lower = name_clean.lower() # 统一转小写用于生成文件名

    group = "其他"
    logo = ""

    # --- 1. 央视频道 (CCTV) ---
    if name_upper.startswith("CCTV"):
        group = "央视频道"
        # 处理 CCTV-1 -> cctv1, CCTV5+ -> cctv5plus
        clean_cctv = name_lower.replace("-", "").replace(" ", "")
        # 特殊处理 CCTV5+
        if "5+" in clean_cctv:
            clean_cctv = clean_cctv.replace("5+", "5plus")
        logo = f"{LOGO_BASE_URL}{clean_cctv}.png"

    # --- 2. 卫视频道 (优先查表) ---
    elif "卫视" in name_clean:
        group = "卫视频道"
        matched_key = None
        # 遍历映射表查找匹配
        for key in WEISHI_MAPPING:
            if key in name_clean:
                matched_key = key
                break

        if matched_key:
            logo = f"{LOGO_BASE_URL}{WEISHI_MAPPING[matched_key]}.png"
        else:
            # 如果不在表中，尝试通用规则：取前两个字 + ws
            # 例如 "吉林卫视" -> jlws.png (成功率较低，建议用表)
            short_name = name_lower.replace("卫视", "").replace("电视台", "")[:2]
            logo = f"{LOGO_BASE_URL}{short_name}ws.png"

    # --- 3. 河北地方频道 ---
    elif "河北" in name_clean:
        group = "河北地方频道"
        # 尝试匹配河北台标，例如 "河北经济生活" -> hebeijjsh.png
        # 注意：yuanzl77 的河北台标命名可能不完全统一，这里做几种常见尝试
        hb_suffix = name_lower.replace("河北", "").replace("频道", "").replace("电视台", "")

        # 常见的河北台标文件名猜测
        possible_names = [
            f"hebei{hb_suffix}",      # hebeijjsh
            f"hebei_{hb_suffix}",     # hebei_jjsh
            f"hb{hb_suffix}",         # hbjjsh
            "hebeiws"                 # 兜底河北卫视
        ]

        # 简单起见，我们先用最可能的一个，或者你可以手动修正
        # 这里假设图床使用的是 hebei + 拼音缩写
        # 为了稳妥，如果不确定具体文件名，可以先留空，避免显示错误的红叉
        # 但为了尽量显示，我们尝试拼接
        logo = f"{LOGO_BASE_URL}hebei{hb_suffix}.png"

    # --- 4. 兜底策略 ---
    else:
        group = "其他"
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
                    extinf = f'#EXTINF:-1 group-title="{group_title}" tvg-id="{name}" tvg-name="{name}" tvg-logo="{tvg_logo}",{name}'

                    m3u_lines.append(extinf)
                    m3u_lines.append(url)
                    count += 1

        print(f"✅ 成功处理 {count} 个频道")

    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        m3u_lines.append('#EXTINF:-1 group-title="Error",抓取失败请检查源')
        m3u_lines.append("http://example.com/empty")

    # 核心修复：使用 newline='' 确保生成的 M3U 文件是 Unix 换行符
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline='') as f:
        f.write("\n".join(m3u_lines))

    print(f"💾 已保存: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
