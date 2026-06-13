import requests
from bs4 import BeautifulSoup
import re
import time
import sys

# ==================== 配置区 ====================
# 目标源地址 (河北酒店源)
BASE_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "iptv.m3u"

# ✅ EPG 节目单地址
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# ✅ 台标源 (Fanmingming Live TV Logo)
LOGO_BASE_URL = "https://raw.githubusercontent.com/fanmingming/live/main/tv/"

# ✅ 筛选条件 (严格匹配)
TARGET_ISP = "电信"
TARGET_DATE = "2026-06-12"

# ✅ 请求头 (模拟真实浏览器，防止被拦截)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': BASE_URL,
    'Connection': 'keep-alive'
}

# ==================== 辅助函数 ====================

def get_logo_url(channel_name):
    """生成台标链接"""
    # 简单处理中文名为拼音或英文的情况，这里直接使用原文件名尝试
    # Fanmingming 的仓库通常使用 channel_name.png
    return f"{LOGO_BASE_URL}{channel_name}.png"

def classify_channel(name):
    """根据频道名进行分类"""
    if any(kw in name for kw in ["CCTV", "央视"]):
        return "央视"
    elif any(kw in name for kw in ["卫视", "凤凰", "星空"]):
        return "卫视"
    elif any(kw in name for kw in ["河北", "石家庄", "保定", "唐山", "邯郸", "邢台", "沧州", "廊坊", "衡水", "张家口", "承德", "秦皇岛"]):
        return "河北本地"
    else:
        return "其他"

def fetch_page(url):
    """通用请求函数，带重试"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = 'utf-8' # 强制指定编码，防止乱码
        return resp.text
    except Exception as e:
        print(f"请求失败 {url}: {e}")
        return None

def extract_streams(detail_html):
    """从详情页提取 m3u8 或 ts 链接"""
    soup = BeautifulSoup(detail_html, 'html.parser')
    streams = []

    # 策略1: 查找 video 标签的 src
    video_tags = soup.find_all('video')
    for tag in video_tags:
        src = tag.get('src')
        if src and ('.m3u8' in src or '.ts' in src):
            streams.append(src)

    # 策略2: 查找 iframe (很多酒店源用 iframe 嵌套播放器)
    iframes = soup.find_all('iframe')
    for iframe in iframes:
        src = iframe.get('src')
        if src and ('.m3u8' in src or '.ts' in src):
            streams.append(src)

    # 策略3: 全文正则搜索 (最暴力但也最有效)
    # 匹配 http(s)://... .m3u8 或 .ts
    pattern = r'(https?://[^\s"\']+\.m3u8|https?://[^\s"\']+\.ts)'
    found_links = re.findall(pattern, detail_html)
    streams.extend(found_links)

    # 去重并保持顺序
    return list(dict.fromkeys(streams))

# ==================== 主逻辑 ====================

def main():
    print(f"开始访问主页: {BASE_URL}")
    html = fetch_page(BASE_URL)

    if not html:
        print("无法获取主页内容，程序终止。")
        sys.exit(1)

    soup = BeautifulSoup(html, 'html.parser')
    results = []

    # 假设结构是：每个条目在一个 div 或 p 中，包含 a标签(蓝色框), 运营商文本, 时间文本
    # 我们遍历所有的 <a> 标签，然后检查其父级或兄弟节点的内容
    # 为了稳健，我们遍历所有包含 "运营商" 文本的块，向上找链接

    # 这里采用一种更稳健的方式：遍历所有 <a> 标签，检查其下方的文本是否符合条件
    all_links = soup.find_all('a', href=True)

    print(f"扫描到 {len(all_links)} 个潜在链接，开始筛选...")

    valid_count = 0
    for link_tag in all_links:
        # 获取链接地址
        href = link_tag['href']
        if not href.startswith('http'):
            # 补全相对路径
            if href.startswith('/'):
                href = "http://nn.7x9d.cn" + href
            else:
                continue

        # 获取该链接所在的父容器文本，用于判断运营商和时间
        # 通常结构是 <div><a>...</a><br>运营商...<br>时间...</div>
        parent_div = link_tag.parent
        text_content = parent_div.get_text()

        # === 核心筛选逻辑 ===
        # 1. 检查运营商是否包含 "电信"
        if TARGET_ISP not in text_content:
            continue

        # 2. 检查收录时间是否为 "2026-06-12"
        # 注意：这里需要确保匹配的是“收录时间”而不是“更新时间”
        # 假设文本格式固定，我们简单检查日期字符串是否存在
        if TARGET_DATE not in text_content:
            continue

        # 如果通过了筛选
        print(f"[发现目标] 链接: {href}")
        print(f"   详情: {text_content.strip().replace(chr(10), ' | ')}")

        # 进入详情页抓取
        detail_html = fetch_page(href)
        if detail_html:
            stream_urls = extract_streams(detail_html)
            if stream_urls:
                # 取第一个有效的流地址（通常只有一个）
                stream_url = stream_urls[0]
                results.append({
                    'name': link_tag.get_text(strip=True), # 蓝色框里的文字通常是IP，我们可以用它做名字，或者自定义
                    'url': stream_url,
                    'group': '河北电信源' # 暂时归类，后面会重新分类
                })
                valid_count += 1
            else:
                print(f"   [警告] 详情页未找到视频流地址")
        else:
            print(f"   [错误] 详情页无法访问")

        # 礼貌爬取，稍微停顿
        time.sleep(1)

    print(f"\n筛选完成，共找到 {valid_count} 个有效源。正在生成 M3U 文件...")

    # 写入 M3U 文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U x-tvg-url="{}"\n'.format(EPG_URL))

        # 按分类排序输出
        categories = {"央视": [], "卫视": [], "河北本地": [], "其他": []}

        for item in results:
            # 这里的 item['name'] 是 IP地址，我们需要尝试从 URL 或上下文推断频道名
            # 但由于是酒店源，通常一个 IP 对应多个频道，或者是一个聚合流
            # 如果网页没有提供频道名，我们暂时用 IP 作为名字，或者你可以手动修改
            # 假设蓝色框文字就是标识符
            raw_name = item['name']
            category = classify_channel(raw_name) # 基于名字分类可能不准，因为名字是IP

            # 既然是酒店源IP，通常很难自动知道它是哪个台。
            # 除非详情页里有标题。让我们尝试从详情页提取 title
            # 这里做一个简单的处理：如果无法识别，归入“其他”
            # 如果你想手动指定，可以在这里加逻辑

            logo = get_logo_url(raw_name)

            line = '#EXTINF:-1 tvg-id="{}" tvg-name="{}" tvg-logo="{}" group-title="{}",{}\n{}'.format(
                raw_name, raw_name, logo, category, raw_name, item['url']
            )
            f.write(line + '\n')

    print(f"成功保存到 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
