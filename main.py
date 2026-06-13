import requests
from bs4 import BeautifulSoup
import re
import time
import os
import random

# --- 配置区 ---
# 目标网站（国内站点，GitHub访问极不稳定）
TARGET_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "kaniptv.m3u"

# 备用源列表（如果主源挂了，尝试这些）
BACKUP_SOURCES = [
    "https://iptv.b2og.com/txt/fmml_ipv6.txt", # 这是一个知名的IPv6源，作为备用
    "https://ghproxy.net/https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u" # 聚合源
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9'
}

def get_proxy():
    """
    尝试从公开API获取代理IP
    如果失败，返回 None
    """
    proxy_apis = [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=cn&ssl=no&anonymity=all",
        "https://spider.meiguodns.com/api/proxy?type=json" # 备用API
    ]

    for api in proxy_apis:
        try:
            print(f"正在尝试从 {api} 获取代理...")
            resp = requests.get(api, timeout=10)
            if resp.status_code == 200:
                data = resp.text.strip()
                # 简单解析，取第一个可用的IP
                if '://' not in data and ':' in data:
                    ip_port = data.split('\n')[0].strip()
                    if len(ip_port) > 5:
                        proxy_url = f"http://{ip_port}"
                        print(f"获取到代理: {proxy_url}")
                        return {"http": proxy_url, "https": proxy_url}
        except Exception as e:
            print(f"获取代理失败: {e}")
            continue
    return None

def fetch_content(url, max_retries=5):
    """
    带代理和重试机制的抓取函数
    """
    proxies = get_proxy()

    for i in range(max_retries):
        try:
            print(f"第 {i+1} 次尝试连接: {url}")
            # 如果没有代理，直连超时设为10秒；有代理设为30秒
            timeout = 30 if proxies else 10

            resp = requests.get(url, headers=HEADERS, proxies=proxies, timeout=timeout)

            if resp.status_code == 200:
                # 简单的内容检查，防止抓到了错误页面
                if len(resp.text) > 100:
                    print("连接成功！开始解析...")
                    return resp.text
                else:
                    print("响应内容过短，可能是错误页面，重试...")
            else:
                print(f"状态码异常: {resp.status_code}")

        except requests.exceptions.ProxyError:
            print("代理不通，重新获取代理...")
            proxies = get_proxy() # 换个代理
        except requests.exceptions.Timeout:
            print("连接超时，可能是代理太慢或网络不通...")
            if i < max_retries - 1:
                proxies = get_proxy() # 换个代理再试
        except Exception as e:
            print(f"发生未知错误: {e}")

        time.sleep(2) # 等待一下再重试

    return None

def parse_nn_site(content):
    """
    解析 nn.7x9d.cn 的特定格式
    """
    channels = []
    lines = content.split('\n')
    current_group = "未分类"

    for line in lines:
        line = line.strip()
        if not line: continue

        # 这种网站通常是 组名,#genre# 格式
        if ',#genre#' in line:
            current_group = line.split(',')[0].strip()
            continue

        # 匹配 频道名,链接 格式
        if ',' in line and 'http' in line:
            parts = line.split(',', 1)
            name = parts[0].strip()
            url = parts[1].strip()

            # 简单的清洗，去掉多余的后缀
            name = re.sub(r'\[.*?\]', '', name).strip()
            name = re.sub(r'\(.*?\)', '', name).strip()

            if name and url.startswith('http'):
                channels.append((current_group, name, url))

    return channels

def write_m3u(channels):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U x-tvg-url="http://epg.51zmt.top:8000/e.xml"\n')
        for group, name, url in channels:
            f.write(f'#EXTINF:-1 group-title="{group}",{name}\n')
            f.write(f'{url}\n')
    print(f"成功写入 {len(channels)} 个频道到 {OUTPUT_FILE}")

def main():
    print("--- 开始任务 ---")

    # 1. 尝试抓取主站
    content = fetch_content(TARGET_URL)

    all_channels = []

    if content:
        print("主站抓取成功，正在解析...")
        channels = parse_nn_site(content)
        all_channels.extend(channels)
    else:
        print("!!! 主站抓取失败 !!! 尝试使用备用源...")
        # 2. 如果主站挂了，尝试抓取备用源（备用源通常对海外友好一点，或者是GitHub直链）
        for backup_url in BACKUP_SOURCES:
            print(f"尝试备用源: {backup_url}")
            # 备用源通常是 m3u 格式，这里简化处理，假设能直接下载
            try:
                resp = requests.get(backup_url, timeout=15)
                if resp.status_code == 200:
                    # 这里只是简单演示，实际应该解析m3u格式
                    # 为了代码简洁，如果主站挂了，我们至少保证文件里有东西
                    # 你可以手动把备用源的链接写到生成的m3u里
                    print("备用源连接成功，但由于格式复杂，建议优先修复主站代理。")
                    # 这里暂时不解析备用源，避免逻辑太复杂导致报错
            except:
                pass

    # 3. 写入文件
    if all_channels:
        write_m3u(all_channels)
    else:
        print("没有任何频道数据！请检查日志中的网络错误。")
        # 即使没数据也写入一个空文件，防止文件消失
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n# 本次更新失败，无数据\n')

if __name__ == "__main__":
    main()
