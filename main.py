import requests
from bs4 import BeautifulSoup
import re
import os
import time

# ================= 配置区 =================
TARGET_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"
LOGO_BASE_URL = "https://raw.githubusercontent.com/fanmingming/live/main/tv/"

# 分类关键词映射
CATEGORY_MAP = {
    'CCTV': '央视',
    'CGTN': '央视',
    '卫视': '卫视',
    '河北': '河北',
    '石家庄': '河北',
    '唐山': '河北',
    '秦皇岛': '河北',
    '邯郸': '河北',
    '邢台': '河北',
    '保定': '河北',
    '张家口': '河北',
    '承德': '河北',
    '廊坊': '河北',
    '沧州': '河北',
    '衡水': '河北',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': TARGET_URL
}

def get_logo_url(channel_name):
    """尝试匹配台标"""
    # 简单的文件名猜测逻辑，实际可能需要更复杂的映射
    name = channel_name.replace(' ', '').lower()
    if 'cctv' in name:
        return f"{LOGO_BASE_URL}logo/CCTV/{name}.png"
    elif '卫视' in name:
        prov = name.split('卫视')[0]
        return f"{LOGO_BASE_URL}logo/{prov}卫视.png"
    return ""

def classify_channel(name):
    for key, category in CATEGORY_MAP.items():
        if key in name:
            return category
    return '其他'

def main():
    print(f"正在访问目标网站: {TARGET_URL}")
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"请求主页失败: {e}")
        save_empty_m3u()
        return

    # 寻找包含特定日期的蓝色框链接 (假设结构为 <a> 标签或类似)
    # 注意：这里需要根据网页实际结构调整选择器，这里模拟查找包含日期的链接
    links_to_visit = []
    target_date = "2026-06-12" # 你指定的日期

    # 遍历所有链接，寻找包含日期且可能是“电信”的入口
    for a_tag in soup.find_all('a'):
        text = a_tag.get_text(strip=True)
        href = a_tag.get('href')
        if href and target_date in text and '电信' in text:
            full_url = href if href.startswith('http') else TARGET_URL.rsplit('/', 1)[0] + '/' + href
            links_to_visit.append(full_url)

    print(f"找到 {len(links_to_visit)} 个符合条件的入口链接")

    all_channels = []

    for link in links_to_visit:
        try:
            print(f"正在解析下级链接: {link}")
            sub_resp = requests.get(link, headers=HEADERS, timeout=10)
            sub_resp.encoding = 'utf-8'

            # 假设下级页面直接包含 m3u 文本或 txt 列表
            # 这里简单按行分割提取 http 开头的链接
            lines = sub_resp.text.split('\n')
            current_name = ""

            for line in lines:
                line = line.strip()
                if line.startswith('#EXTINF'):
                    # 提取频道名
                    match = re.search(r'tvg-name="(.*?)"|,(.*)', line)
                    if match:
                        current_name = match.group(1) or match.group(2)
                elif line.startswith('http'):
                    if current_name:
                        category = classify_channel(current_name)
                        logo = get_logo_url(current_name)
                        all_channels.append({
                            'name': current_name,
                            'url': line,
                            'category': category,
                            'logo': logo
                        })
                        current_name = ""
        except Exception as e:
            print(f"解析链接失败: {e}")

    generate_m3u(all_channels)

def save_empty_m3u():
    """出错时保存空文件，防止Git报错"""
    os.makedirs('output', exist_ok=True)
    with open('output/live_channels.m3u', 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
    print("已生成空文件以维持Git流程。")

def generate_m3u(channels):
    os.makedirs('output', exist_ok=True)
    output_path = 'output/live_channels.m3u'

    # 按照 央视 -> 卫视 -> 河北 -> 其他 排序
    order = {'央视': 1, '卫视': 2, '河北': 3, '其他': 4}
    channels.sort(key=lambda x: order.get(x['category'], 5))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f'#EXTM3U url-tvg="{EPG_URL}"\n')

        last_cat = None
        for ch in channels:
            # 添加分组标题 (可选，为了美观)
            if ch['category'] != last_cat:
                f.write(f'\n#EXTINF:-1 group-title="{ch["category"]}",{ch["category"]}分组\n')
                last_cat = ch['category']

            logo_str = f' tvg-logo="{ch["logo"]}"' if ch['logo'] else ''
            f.write(f'#EXTINF:-1{logo_str} group-title="{ch["category"]}",{ch["name"]}\n')
            f.write(f'{ch["url"]}\n')

    print(f"成功生成 M3U 文件: {output_path}, 共 {len(channels)} 个频道")

if __name__ == '__main__':
    main()
