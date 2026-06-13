import requests
from bs4 import BeautifulSoup
import re
import time
import sys
import random

# ==================== 配置区 ====================
TARGET_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "iptv.m3u"
MAX_RETRIES = 3
RETRY_DELAY = 10  # 秒

# 请求头伪装
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# ==================== 辅助函数 ====================

def get_free_proxy():
    """尝试获取一个免费的公共代理"""
    proxy_url = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
    try:
        print("🔍 正在扫描免费代理...")
        resp = requests.get(proxy_url, timeout=10)
        if resp.status_code == 200:
            proxies_list = resp.text.strip().split('\r\n')
            if proxies_list:
                proxy_ip = random.choice(proxies_list)
                return {"http": f"http://{proxy_ip}", "https": f"http://{proxy_ip}"}
    except Exception as e:
        print(f"⚠️ 获取代理失败: {e}")
    return None

def fetch_content(url, use_proxy=True):
    """带重试和代理支持的抓取函数"""
    retries = 0
    proxy = None

    # 如果需要代理，先尝试获取一次
    if use_proxy:
        proxy = get_free_proxy()
        if proxy:
            print(f"✅ 获取到代理: {proxy['http']}")
        else:
            print("⚠️ 未获取到有效代理，将尝试直连...")

    while retries < MAX_RETRIES:
        try:
            print(f"\n🌐 正在请求 (第 {retries + 1}/{MAX_RETRIES} 次)...")
            # 设置超时时间：连接5秒，读取15秒
            response = requests.get(
                url,
                headers=HEADERS,
                proxies=proxy,
                timeout=(5, 15)
            )
            response.raise_for_status()
            response.encoding = 'utf-8'  # 强制指定编码防止乱码
            return response.text

        except requests.exceptions.ProxyError:
            print("❌ 代理连接失败，清除代理并重试...")
            proxy = None  # 下次循环不再使用代理
            retries += 1
            time.sleep(RETRY_DELAY)

        except requests.exceptions.ConnectionError as e:
            print(f"❌ 连接超时或被拒绝: {str(e)[:50]}...")
            retries += 1
            time.sleep(RETRY_DELAY)

        except Exception as e:
            print(f"❌ 未知错误: {e}")
            retries += 1
            time.sleep(RETRY_DELAY)

    return None

def parse_iptv(html_content):
    """解析网页内容提取直播源 (需根据实际网页结构调整)"""
    results = []
    if not html_content:
        return results

    soup = BeautifulSoup(html_content, 'html.parser')

    # ⚠️ 注意：这里需要根据 nn.7x9d.cn 的实际 HTML 结构修改选择器
    # 假设链接在 <a> 标签中，或者文本直接包含 .m3u8/.ts 地址
    # 这是一个通用的正则匹配示例：

    # 方法 A: 查找所有链接
    links = soup.find_all('a', href=True)
    for link in links:
        href = link.get('href', '')
        title = link.get_text(strip=True) or "Channel"
        if '.m3u8' in href or '.ts' in href or 'http' in href:
            # 简单的 M3U 格式拼接
            line = f'#EXTINF:-1 tvg-logo="" group-title="IPTV",{title}\n{href}'
            results.append(line)

    # 方法 B: 如果页面全是纯文本链接，可以用正则
    # urls = re.findall(r'(http[s]?://\S+)', html_content)
    # for url in urls:
    #     results.append(f'#EXTINF:-1,Channel\n{url}')

    return results

# ==================== 主程序 ====================
if __name__ == "__main__":
    print("🚀 IPTV 抓取任务开始...")

    # 1. 获取网页内容 (开启自动代理检测)
    html = fetch_content(TARGET_URL, use_proxy=True)

    if html:
        print("\n✅ 网页获取成功，开始解析...")
        data = parse_iptv(html)

        if data:
            print(f"📦 解析到 {len(data)} 个频道，正在写入文件...")
            # ✅ 修复了之前的语法错误：确保括号正确闭合
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                f.write('\n'.join(data))  # 这里的括号必须成对出现

            print(f"💾 成功保存到 {OUTPUT_FILE}")
        else:
            print("⚠️ 未解析到任何频道链接，请检查 parse_iptv 逻辑。")
            sys.exit(1)
    else:
        print("\n💀 彻底失败：无法连接到目标网站，且无可用代理。")
        sys.exit(1)
