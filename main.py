import requests
from bs4 import BeautifulSoup
import re
import time
import random
import os

# ==================== 配置区 ====================
BASE_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "kaniptv.m3u"

# ✅ 台标源 (jsDelivr CDN)
LOGO_BASE_URL = "https://cdn.jsdelivr.net/gh/fanmingming/live@main/tv/"

# ✅ EPG 节目单地址
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# ✅ 筛选条件
TARGET_REGION = "河北"
TARGET_ISP = "电信"
TARGET_DATE = "2026-06-12"

# ✅ 请求头伪装 (模拟真实浏览器，防止被拦截)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

def get_page_content(url, retries=3):
    """
    获取页面内容，包含重试机制和随机延时
    """
    for attempt in range(1, retries + 1):
        try:
            print(f"  -> 正在尝试连接 (第 {attempt} 次)...")
            # 增加 timeout 到 20秒，给 GitHub Actions 更多反应时间
            response = requests.get(url, headers=HEADERS, timeout=20)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                return response.text
            else:
                print(f"  -> 状态码异常: {response.status_code}")

        except Exception as e:
            print(f"  -> 第 {attempt} 次失败: {str(e)[:100]}...")

        # 如果不是最后一次尝试，则等待随机时间后重试
        if attempt < retries:
            wait_time = random.uniform(2, 5)  # 随机等待 2-5 秒
            print(f"  -> 等待 {wait_time:.1f} 秒后重试...")
            time.sleep(wait_time)

    return None

def parse_channel_name(ip_text):
    """从IP文本中提取频道名称"""
    # 去除可能的端口号、空格等干扰字符
    name = ip_text.strip()
    # 简单清洗，保留汉字、字母、数字
    name = re.sub(r'[^\w\u4e00-\u9fa5]', '', name)
    if not name:
        name = "未知频道"
    return name

def main():
    print("=" * 50)
    print("开始抓取酒店源...")
    print(f"目标地址: {BASE_URL}")
    print("=" * 50)

    # 1. 获取列表页内容
    html = get_page_content(BASE_URL)
    if not html:
        print("❌ 无法获取列表页内容，请检查网络或 URL 是否正确。")
        # 即使失败也生成一个空文件，防止 GitHub Actions 报错找不到文件
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
        return

    soup = BeautifulSoup(html, 'html.parser')

    # 查找所有包含链接的蓝色按钮区域
    # 根据截图结构，通常是 div 包裹着 a 标签，或者 a 标签本身
    # 这里我们寻找所有的 <a> 标签，检查其父级或自身是否包含关键信息
    items = soup.find_all('div', class_=re.compile(r'item|list|box')) # 尝试匹配常见的类名，如果不确定就遍历所有 div

    # 如果上面的类名匹配不到，我们采用更暴力的遍历方式：
    # 遍历所有包含 href 的 a 标签
    links = soup.find_all('a', href=True)

    m3u_content = '#EXTM3U\n'
    found_count = 0

    for link_tag in links:
        href = link_tag.get('href', '')
        text = link_tag.get_text(strip=True)

        # 初步判断：链接必须看起来像详情页 (包含 id 或 php)
        if not ('xzjd2.php' in href or 'detail' in href or len(href) > 10):
            continue

        # 获取该链接周围的上下文文本（运营商、时间通常在下方的 div 中）
        # 由于 BeautifulSoup 很难直接获取“下方兄弟节点”的纯文本而不带标签，
        # 我们假设结构是：<a>...</a> <div>运营商...</div> <div>时间...</div>
        parent = link_tag.parent
        context_text = parent.get_text() if parent else ""

        # === 核心筛选逻辑 ===
        # 1. 检查运营商 (支持 "河北-电信" 或 "河北电信")
        is_target_isp = (TARGET_REGION in context_text) and (TARGET_ISP in context_text)

        # 2. 检查日期
        is_target_date = TARGET_DATE in context_text

        if is_target_isp and is_target_date:
            print(f"\n✅ 发现匹配项: {text}")
            print(f"   链接: {href}")

            # 拼接完整 URL (如果是相对路径)
            if href.startswith('/'):
                detail_url = "http://nn.7x9d.cn" + href
            elif href.startswith('http'):
                detail_url = href
            else:
                # 处理类似 ?id=xxx 的情况
                detail_url = BASE_URL.split('?')[0] + href

            # 2. 进入详情页获取真实播放地址
            detail_html = get_page_content(detail_url)
            if detail_html:
                detail_soup = BeautifulSoup(detail_html, 'html.parser')

                # 尝试提取真实播放地址 (通常在 video 标签、source 标签或特定的 div 中)
                # 这里需要根据实际详情页源码调整，假设是在 <video src="..."> 或 <a class="download">
                real_url = ""

                # 尝试方案 A: 查找 video 标签
                video_tag = detail_soup.find('video')
                if video_tag and video_tag.get('src'):
                    real_url = video_tag['src']

                # 尝试方案 B: 查找包含 .m3u8 或 .ts 的链接
                if not real_url:
                    all_links = detail_soup.find_all('a', href=True)
                    for l in all_links:
                        h = l['href']
                        if '.m3u8' in h or '.ts' in h or 'play' in h:
                            real_url = h
                            break

                # 尝试方案 C: 查找 iframe
                if not real_url:
                    iframe = detail_soup.find('iframe', src=True)
                    if iframe:
                        real_url = iframe['src']

                if real_url:
                    # 补全绝对路径
                    if real_url.startswith('/'):
                        real_url = "http://nn.7x9d.cn" + real_url

                    channel_name = parse_channel_name(text)
                    logo_url = f"{LOGO_BASE_URL}{channel_name}.png"

                    line = f'#EXTINF:-1 tvg-name="{channel_name}" tvg-logo="{logo_url}" group-title="{TARGET_REGION}{TARGET_ISP}",{channel_name}\n{real_url}\n'
                    m3u_content += line
                    found_count += 1
                    print(f"   🎉 成功提取播放地址: {real_url[:50]}...")
                else:
                    print("   ⚠️ 未能从详情页解析出播放地址")
            else:
                print("   ❌ 详情页无法访问")

            # 每次抓取后稍微停顿，避免被封
            time.sleep(random.uniform(1, 3))

    # 保存文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(m3u_content)

    print("\n" + "=" * 50)
    print(f"抓取完成！共找到 {found_count} 个有效源。")
    print(f"文件已保存为: {OUTPUT_FILE}")
    print("=" * 50)

if __name__ == "__main__":
    main()
