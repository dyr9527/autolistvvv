import requests
from bs4 import BeautifulSoup
import re
import time
import random
import sys

# ==================== 配置区 ====================
# 目标源地址 (河北)
BASE_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "iptv.m3u"

# ✅ EPG 节目单地址
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# ✅ 台标源 (Fanmingming Live TV Logo) - 自动转换 Raw 格式
LOGO_BASE_URL = "https://raw.githubusercontent.com/fanmingming/live/main/tv/"

# ✅ 筛选条件
TARGET_ISP_KEYWORD = "电信"      # 运营商关键词
TARGET_DATE = "2026-06-12"       # 收录时间 (严格匹配)

# ✅ 请求头池 (模拟真实浏览器，防止被拦截)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Referer': 'http://nn.7x9d.cn/',
    'Upgrade-Insecure-Requests': '1'
}

# ==================== 频道分类规则 ====================
def get_category(channel_name):
    """根据频道名称返回分类组名"""
    name = channel_name.upper()

    if any(kw in name for kw in ['CCTV', '中央']):
        return '📺 央视综合'
    if 'CGTN' in name:
        return '🌍 国际频道'
    if any(kw in name for kw in ['卫视']):
        return '📡 卫视频道'
    if any(kw in name for kw in ['河北', '石家庄', '保定', '唐山', '邯郸', '邢台', '沧州', '廊坊', '衡水', '张家口', '承德', '秦皇岛']):
        return '🏠 河北本地'
    if any(kw in name for kw in ['电影', '影院']):
        return '🎬 影视剧场'
    if any(kw in name for kw in ['体育', '赛事']):
        return '⚽ 体育赛事'
    if any(kw in name for kw in ['少儿', '动画', '卡通']):
        return '🧸 少儿动漫'
    if any(kw in name for kw in ['新闻', '资讯']):
        return '📰 新闻资讯'
    if any(kw in name for kw in ['综艺', '娱乐']):
        return '🎭 综艺娱乐'
    if any(kw in name for kw in ['科教', '纪实', '记录']):
        return '📚 科教纪实'

    return '📺 其他频道'

# ==================== 核心逻辑 ====================

def fetch_page(url, max_retries=3):
    """带重试机制的请求函数"""
    for attempt in range(max_retries):
        try:
            print(f"正在请求: {url} (尝试 {attempt + 1}/{max_retries})")
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            # 尝试检测编码，防止乱码
            response.encoding = response.apparent_encoding
            return response.text
        except Exception as e:
            print(f"请求失败: {e}")
            if attempt < max_retries - 1:
                wait_time = random.uniform(2, 5)
                print(f"等待 {wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)
            else:
                print("达到最大重试次数，放弃请求。")
                return None

def parse_list_page(html):
    """解析列表页，提取符合条件的详情页链接"""
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    links = []

    # 寻找包含日期的父级容器 (通常是 div, p 或 li)
    # 这里的逻辑是：找到包含日期的标签 -> 检查是否包含“电信” -> 找里面的 a 标签
    all_tags = soup.find_all(True) # 查找所有标签

    for tag in all_tags:
        text = tag.get_text(strip=True)

        # 1. 检查日期
        if TARGET_DATE not in text:
            continue

        # 2. 检查运营商 (简单判断文本中是否包含关键词)
        # 注意：有些网站结构可能是 日期在上一行，运营商在下一行，或者都在同一行
        # 这里假设它们在同一文本块或邻近兄弟节点，为简化逻辑，我们检查当前标签及其父级
        parent_text = tag.parent.get_text() if tag.parent else ""
        combined_text = text + " " + parent_text

        if TARGET_ISP_KEYWORD not in combined_text:
            continue

        # 3. 提取蓝色框框内的链接 (a 标签)
        a_tag = tag.find('a', href=True)
        if not a_tag:
            # 如果当前标签不是 a，看看父级是不是，或者子级是不是
            a_tag = tag.find_parent('a', href=True) or tag.find('a', href=True)

        if a_tag:
            link = a_tag['href']
            # 处理相对路径
            if link.startswith('/'):
                link = "http://nn.7x9d.cn" + link
            elif not link.startswith('http'):
                link = "http://nn.7x9d.cn/" + link

            # 去重
            if link not in [l for l, _ in links]:
                links.append((link, a_tag.get_text(strip=True)))
                print(f"✅ 发现有效入口: {a_tag.get_text(strip=True)} -> {link}")

    return links

def extract_real_stream(detail_url):
    """进入详情页提取真实 m3u8 地址"""
    html = fetch_page(detail_url)
    if not html:
        return None

    # 常见的直播流正则
    patterns = [
        r'(https?://[^\s\'"]+\.m3u8)',
        r'(https?://[^\s\'"]+\.ts)',
        r'url["\']?\s*[:=]\s*["\']?(https?://[^\s\'"]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)

    return None

def generate_m3u(channels):
    """生成 M3U 文件内容"""
    lines = [
        '#EXTM3U',
        f'#EXTINF:-1 tvg-logo="{LOGO_BASE_URL}cctv1.png" group-title="EPG",EPG Source', # 占位符
        EPG_URL,
    ]

    for name, url, category in channels:
        # 构造台标链接：尝试使用频道名拼音或通用图标
        # 由于没有拼音库，这里统一使用一个默认图标，或者你可以手动映射几个常用的
        logo_name = "cctv1.png" # 默认
        if "卫视" in name: logo_name = "weishi.png"
        if "河北" in name: logo_name = "hebei.png"

        logo_url = f"{LOGO_BASE_URL}{logo_name}"

        lines.append(f'#EXTINF:-1 tvg-id="" tvg-name="{name}" tvg-logo="{logo_url}" group-title="{category}",{name}')
        lines.append(url)

    return '\n'.join(lines)

def main():
    print("=" * 50)
    print("🚀 酒店源抓取脚本启动")
    print(f"🎯 目标URL: {BASE_URL}")
    print(f"📅 筛选日期: {TARGET_DATE}")
    print(f"📶 筛选运营商: {TARGET_ISP_KEYWORD}")
    print("=" * 50)

    # 1. 获取列表页
    list_html = fetch_page(BASE_URL)
    if not list_html:
        print("❌ 致命错误：无法获取主列表页，脚本终止。")
        sys.exit(1)

    # 2. 解析入口链接
    detail_links = parse_list_page(list_html)
    if not detail_links:
        print("⚠️ 未找到符合条件的入口链接，请检查筛选条件或网页结构是否变更。")
        # 即使没找到也不报错退出，生成空文件即可
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
        return

    print(f"\n🔍 共找到 {len(detail_links)} 个待解析入口，开始提取真实流...")

    valid_channels = []

    # 3. 遍历提取真实流
    for url, raw_name in detail_links:
        # 简单的清洗名称，去掉可能存在的日期后缀
        clean_name = re.sub(r'\d{4}-\d{2}-\d{2}.*', '', raw_name).strip()
        if not clean_name:
            clean_name = raw_name

        print(f"   🕷️ 正在解析: {clean_name}")

        stream_url = extract_real_stream(url)
        if stream_url:
            category = get_category(clean_name)
            valid_channels.append((clean_name, stream_url, category))
            print(f"      ✅ 成功: {stream_url[:50]}...")
        else:
            print(f"      ❌ 失败: 未找到播放地址")

        # 礼貌爬取，随机延时
        time.sleep(random.uniform(1, 3))

    # 4. 生成文件
    if valid_channels:
        content = generate_m3u(valid_channels)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n🎉 抓取完成！共获取 {len(valid_channels)} 个频道。")
        print(f"💾 文件已保存至: {OUTPUT_FILE}")
    else:
        print("\n⚠️ 抓取结束，但未获得任何有效频道。")
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n# 暂无数据")

if __name__ == "__main__":
    main()
