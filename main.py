import requests
from bs4 import BeautifulSoup
import re
import time
import os
import random

# ==================== 配置区 ====================
BASE_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "kaniptv.m3u"

# ✅ 台标源：使用 jsDelivr CDN 加速
LOGO_BASE_URL = "https://cdn.jsdelivr.net/gh/fanmingming/live@main/tv/"

# ✅ EPG 节目单地址
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# ✅ 筛选条件
TARGET_REGION = "河北"
TARGET_ISP = "电信"
TARGET_DATE = "2026-06-12"

SUFFIX_WORDS = [
    "高清", "HD", "hd", "4K", "超清", "标清", "SD",
    "频道", "电视台", "综合", "财经", "综艺", "体育",
    "电影", "电视剧", "纪录", "少儿", "军事", "农业",
    "科教", "戏曲", "社会与法", "新闻", "音乐"
]

# ✅ 增强版请求头：模拟真实浏览器，包含 Referer 等字段
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def fetch_with_retry(url, max_retries=3):
    """
    带重试机制的请求函数
    解决 GitHub Actions 偶尔网络波动或目标站响应慢的问题
    """
    for attempt in range(max_retries):
        try:
            print(f"  -> 正在尝试连接 (第 {attempt + 1} 次)...")
            # 设置超时时间为 15 秒，避免无限等待
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8' # 强制指定编码，防止乱码
            return response.text
        except Exception as e:
            print(f"  -> 第 {attempt + 1} 次尝试失败: {e}")
            if attempt < max_retries - 1:
                wait_time = random.uniform(2, 5) # 随机等待 2-5 秒
                print(f"  -> 等待 {wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"  -> ❌ 最终失败，无法访问: {url}")
                return None

def clean_channel_name(name):
    """清理频道名称中的后缀"""
    for word in SUFFIX_WORDS:
        name = name.replace(word, "")
    return name.strip()

def get_logo_url(channel_name):
    """生成台标链接"""
    # 简单的文件名映射逻辑，实际可能需要更复杂的字典匹配
    filename = f"{channel_name}.png"
    return f"{LOGO_BASE_URL}{filename}"

def main():
    print("="*50)
    print("开始抓取酒店源...")
    print(f"目标地址: {BASE_URL}")
    print("="*50)

    # 1. 获取列表页内容
    html_content = fetch_with_retry(BASE_URL)

    if not html_content:
        print("❌ 无法获取页面内容，请检查网络或 URL 是否正确。")
        return

    soup = BeautifulSoup(html_content, 'html.parser')

    # 假设结构：每个源在一个 div 或 li 中，包含蓝色按钮(a标签)和信息文本
    # 这里需要根据实际 HTML 结构调整选择器。
    # 根据截图推测，可能是遍历所有的 a 标签或者包含特定 class 的容器
    # 为了通用性，我们查找所有包含 href 的 a 标签，并检查其周围的文本

    valid_sources = []

    # 尝试寻找包含信息的容器，或者直接遍历所有链接
    # 这里的逻辑是：找到所有链接 -> 获取链接下方的文本 -> 判断是否符合条件
    # 注意：BeautifulSoup 解析 HTML 结构比较严格，如果网页结构不规范可能需要调整

    # 假设每个源块是一个 div 或者 p，或者链接和文本紧挨着
    # 这里采用一种比较稳健的方法：遍历所有 a 标签，看它后面跟着的文本是否符合要求

    links = soup.find_all('a', href=True)

    for link in links:
        detail_url = link.get('href')

        # 补全相对路径
        if detail_url and not detail_url.startswith('http'):
            detail_url = BASE_URL.rsplit('/', 1)[0] + '/' + detail_url

        # 获取该链接附近的文本信息（通常是兄弟节点或父节点的文本）
        # 截图显示文本在按钮下方，可能是同一个父容器内的文本
        parent = link.parent
        text_content = parent.get_text() if parent else ""

        # --- 核心筛选逻辑 ---
        # 必须同时满足三个条件
        if TARGET_REGION in text_content and \
           TARGET_ISP in text_content and \
           TARGET_DATE in text_content:

            print(f"\n✅ 发现符合条件的源:")
            print(f"   链接: {detail_url}")
            print(f"   信息: {text_content.strip()}")

            # 2. 进入详情页获取真实播放地址
            # 注意：如果详情页也是动态加载的，requests 可能拿不到，需要 Selenium
            # 但通常这种简单 PHP 站是静态渲染的
            detail_html = fetch_with_retry(detail_url)

            if detail_html:
                detail_soup = BeautifulSoup(detail_html, 'html.parser')
                # 这里需要猜测详情页的结构。通常是 input value, video src, 或者直接文本
                # 假设真实链接在某个 input 框里，或者是页面里唯一的 http 链接
                # 这里做一个通用的正则提取 m3u8 或 ts 链接
                real_link_match = re.search(r'(http[s]?://[^\'"\s<>]+(?:\.m3u8|\.ts))', detail_html)

                if real_link_match:
                    real_link = real_link_match.group(1)
                    channel_name = clean_channel_name(text_content.split('\n')[0]) # 简单取第一行做名字

                    valid_sources.append({
                        'name': channel_name,
                        'url': real_link,
                        'logo': get_logo_url(channel_name)
                    })
                    print(f"   🎉 提取到真实地址: {real_link}")
                else:
                    print("   ⚠️ 未能在详情页找到播放地址")

            # 爬取间隔，防止被封
            time.sleep(random.uniform(1, 3))

    # 3. 生成 M3U 文件
    if valid_sources:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(f'#EXTM3U url-tvg="{EPG_URL}"\n')
            for source in valid_sources:
                f.write(f'#EXTINF:-1 tvg-logo="{source["logo"]}" group-title="酒店源",{source["name"]}\n')
                f.write(f'{source["url"]}\n')
        print(f"\n🎉 成功！已保存 {len(valid_sources)} 个源到 {OUTPUT_FILE}")
    else:
        print("\n😭 没有找到符合条件的源，或者全部抓取失败。")

if __name__ == "__main__":
    main()
