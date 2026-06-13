import requests
from bs4 import BeautifulSoup
import re
import time
import os
import random

# --- 配置区 ---
BASE_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "kaniptv.m3u"

# 伪装浏览器请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}

def get_working_proxy():
    """
    尝试从公开代理列表获取一个能用的代理。
    这是解决 GitHub Actions 无法访问国内网站的关键。
    """
    # 这里使用一个公开的免费代理API作为示例，实际生产中建议自建或使用付费服务
    # 为了稳定性，我们尝试几个不同的源
    proxy_sources = [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=cn&ssl=all&anonymity=all",
        # 注意：由于环境限制，这里可能需要更稳定的源，或者你可以手动填入一个你测试过的长期代理
        # 如果下面这个API也访问不了，说明GitHub彻底封锁了该类API，那时只能靠运气
    ]

    for source in proxy_sources:
        try:
            resp = requests.get(source, timeout=10)
            if resp.status_code == 200:
                proxies_list = resp.text.strip().split('\n')
                # 随机取几个试试
                random.shuffle(proxies_list)
                for p in proxies_list[:10]: # 只试前10个
                    if ':' in p:
                        proxy_url = f"http://{p.strip()}"
                        print(f"正在测试代理: {proxy_url}")
                        try:
                            # 测试代理是否能访问百度
                            test = requests.get("http://www.baidu.com", proxies={"http": proxy_url}, timeout=5)
                            if test.status_code == 200:
                                print(f"✅ 找到可用代理: {proxy_url}")
                                return {"http": proxy_url, "https": proxy_url}
                        except:
                            continue
        except Exception as e:
            print(f"获取代理源失败: {e}")
            continue

    print("⚠️ 未找到可用代理，将尝试直连（大概率会失败）...")
    return None

def clean_channel_name(name):
    """清洗频道名称"""
    # 简单的清洗逻辑，去除常见的后缀
    suffixes = ["[", "]", "(", ")", "高清", "HD", "CCTV", "卫视"]
    for s in suffixes:
        name = name.replace(s, "")
    return name.strip()

def main():
    print("🚀 开始 IPTV 更新任务...")

    # 1. 获取代理
    proxies = get_working_proxy()

    # 2. 访问目标网站
    m3u_content = "#EXTM3U x-tvg-url=\"http://epg.51zmt.top:8000/e.xml\"\n"
    success_count = 0

    try:
        print(f"正在访问: {BASE_URL}")
        # 设置超时时间，防止卡死
        response = requests.get(BASE_URL, headers=HEADERS, proxies=proxies, timeout=15)
        response.encoding = 'utf-8' # 强制指定编码，防止乱码

        if response.status_code != 200:
            raise Exception(f"HTTP Error: {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')

        # 3. 解析页面内容 (根据 nn.7x9d.cn 的结构调整)
        # 假设链接在 <a> 标签中，或者特定的 div 里
        # 注意：这里需要根据网页实际结构调整选择器
        links = soup.find_all('a', href=True)

        for link in links:
            url = link['href']
            name = link.get_text(strip=True)

            # 简单的过滤：只保留看起来像直播流的链接
            if '.m3u8' in url or '.ts' in url or 'live' in url:
                clean_name = clean_channel_name(name)
                if not clean_name:
                    clean_name = "未知频道"

                line = f'#EXTINF:-1 tvg-name="{clean_name}" tvg-logo="" group-title="默认",{clean_name}\n{url}\n'
                m3u_content += line
                success_count += 1

        print(f"✅ 成功解析到 {success_count} 个频道")

    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        # 如果抓取失败，保留旧文件或者写入错误提示，防止文件被清空
        if os.path.exists(OUTPUT_FILE):
            print("保留旧文件...")
            return
        else:
            m3u_content = "#EXTM3U\n# 抓取失败，请检查日志"

    # 4. 写入文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(m3u_content)

    print("💾 文件已保存")

if __name__ == "__main__":
    main()
