import requests
from bs4 import BeautifulSoup
import re
import time
import sys
import random
import concurrent.futures
from urllib.parse import urljoin

# ==================== 配置区 ====================
TARGET_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "iptv.m3u"

# ✅ 筛选条件
TARGET_ISP = "电信"
TARGET_DATE = "2026-06-12"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# 用于存储找到的可用代理
VALID_PROXIES = []


# ==================== 1. 代理扫描模块 ====================
def check_proxy(proxy):
    """测试单个代理是否可用"""
    try:
        # 尝试访问百度或目标网站来验证连通性
        r = requests.get("http://www.baidu.com", proxies=proxy, timeout=5)
        if r.status_code == 200:
            print(f"[OK] 发现可用代理: {proxy['http']}")
            return proxy
    except Exception:
        pass
    return None


def scan_proxies():
    """从公开网站抓取并验证代理"""
    print("🔍 正在启动代理扫描器...")
    raw_proxies = []

    # 定义几个提供免费代理的源 (这些源经常变动，如果失效需手动更新 URL)
    sources = [
        "https://www.kuaidaili.com/free/inha/1/",  # 快代理
        "https://www.89ip.cn/index_1.html",       # 89免费代理
    ]

    for source_url in sources:
        try:
            resp = requests.get(source_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 针对不同网站的解析逻辑 (这里以通用表格结构为例，可能需要根据实际网站调整)
            # 简单粗暴的正则提取 IP:Port
            ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', resp.text)
            ports = re.findall(r'<td>(\d{2,5})</td>', resp.text) # 假设端口在 td 标签中

            # 简单的组合逻辑 (注意：不同网站结构不同，这里是简化处理)
            # 实际生产中建议针对特定网站写解析，或者使用专门的代理 API
            count = min(len(ips), len(ports))
            for i in range(count):
                ip_port = f"{ips[i]}:{ports[i]}"
                raw_proxies.append({"http": f"http://{ip_port}", "https": f"http://{ip_port}"})

        except Exception as e:
            print(f"抓取源 {source_url} 失败: {e}")

    if not raw_proxies:
        print("⚠️ 未能从公开源抓取到原始代理，尝试使用硬编码备用列表...")
        # 备用：如果抓取失败，这里可以放一些你之前收集的高存活率代理
        # raw_proxies = [{"http": "http://1.2.3.4:8080"}]

    print(f"📥 获取到 {len(raw_proxies)} 个原始代理，开始验证...")

    # 多线程验证
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(check_proxy, p) for p in raw_proxies[:50]] # 只测前50个，节省时间
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                VALID_PROXIES.append(result)
                if len(VALID_PROXIES) >= 3: # 找到3个够用了就停止
                    break

    if VALID_PROXIES:
        print(f"✅ 扫描完成，获得 {len(VALID_PROXIES)} 个可用代理。")
        return True
    else:
        print("❌ 未找到任何可用代理，程序将尝试直连（可能会失败）。")
        return False


# ==================== 2. 业务爬虫模块 ====================
def get_session():
    """创建一个带有随机代理的 Session"""
    session = requests.Session()
    session.headers.update(HEADERS)

    if VALID_PROXIES:
        proxy = random.choice(VALID_PROXIES)
        session.proxies = proxy
        print(f"🚀 本次请求使用代理: {proxy['http']}")
    else:
        print("🚀 未使用代理，直接连接...")

    return session


def fetch_page(url, max_retries=3):
    """带重试机制的页面获取"""
    for i in range(max_retries):
        try:
            session = get_session() # 每次重试可能换不同的代理
            resp = session.get(url, timeout=10)
            resp.encoding = 'utf-8' # 强制编码，防止乱码
            if resp.status_code == 200:
                return resp.text
            else:
                print(f"状态码异常: {resp.status_code}")
        except Exception as e:
            print(f"请求失败 (尝试 {i+1}/{max_retries}): {e}")
            time.sleep(2)
    return None


def parse_main_page(html):
    """解析主页，寻找符合条件的蓝色框链接"""
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    valid_links = []

    # ⚠️ 关键点：根据截图分析 DOM 结构
    # 假设结构是：每个条目在一个 div 或 li 中，包含 a 标签和文本信息
    # 我们需要遍历所有包含 "运营商" 文本的父级容器

    # 这里的 CSS 选择器需要根据网页实际源码调整
    # 假设所有条目都在 class="item" 的 div 里，或者直接遍历 body 中的特定结构
    # 由于没有源码，这里使用一种通用的文本搜索法

    items = soup.find_all(string=re.compile("运营商"))

    for item_text in items:
        parent = item_text.parent
        # 向上查找包含链接的容器，或者就在附近
        # 假设蓝色链接在文本的上方兄弟节点，或者父节点的第一个 a 标签

        # 检查文本是否符合条件
        if TARGET_ISP in str(item_text) and TARGET_DATE in str(item_text):
            # 寻找链接 (通常是蓝色的 a 标签)
            # 策略：查找该文本块附近的 <a> 标签
            link_tag = parent.find('a') or parent.find_previous('a')

            if link_tag and link_tag.get('href'):
                href = link_tag['href']
                # 补全绝对路径
                if not href.startswith('http'):
                    href = urljoin(TARGET_URL, href)

                print(f"✅ 匹配成功: {link_tag.get_text(strip=True)} -> {href}")
                valid_links.append(href)

    return list(set(valid_links)) # 去重


def parse_detail_page(url):
    """进入详情页提取 m3u8"""
    print(f"👉 正在进入详情页: {url}")
    html = fetch_page(url)
    if not html:
        return None

    # 在详情页源码中寻找 .m3u8 或 .ts 结尾的链接
    # 有时地址在 script 标签的变量里，有时直接在 iframe src 里
    match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
    if match:
        return match.group(1)

    # 如果没找到 m3u8，尝试找 ts 列表或其他播放地址
    match_ts = re.search(r'(https?://[^\s"\']+\.ts[^\s"\']*)', html)
    if match_ts:
        return match_ts.group(1)

    return None


# ==================== 主程序入口 ====================
if __name__ == "__main__":
    print("="*40)
    print("IPTV 自动抓取程序启动")
    print("="*40)

    # 1. 先跑代理扫描
    scan_proxies()

    # 2. 获取主页
    main_html = fetch_page(TARGET_URL)
    if not main_html:
        print("❌ 无法获取主页，程序终止。")
        sys.exit(1)

    # 3. 解析主页找链接
    detail_urls = parse_main_page(main_html)
    print(f"\n共找到 {len(detail_urls)} 个符合条件的详情页链接。")

    # 4. 遍历详情页找直播源
    results = []
    for url in detail_urls:
        stream_url = parse_detail_page(url)
        if stream_url:
            # 构造 M3U 格式
            name = url.split('/')[-1] or "Channel" # 简单命名
            line = f'#EXTINF:-1 tvg-logo="{LOGO_BASE_URL}{name}.png" group-title="河北电信",{name}\n{stream_url}'
            results.append(line)
            print(f"💾 已获取: {name}")
        else:
            print(f"⚠️ 未在详情页找到视频流: {url}")
        time.sleep(1) # 礼貌爬取

    # 5. 写入文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        f.write('\n'.join(results
