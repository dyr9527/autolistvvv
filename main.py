import requests
from bs4 import BeautifulSoup
import re
import time
import os
import random

# --- 配置区 ---
BASE_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C97" # 注意：这里最好确认一下你的目标URL是否完整，之前的截图里好像被截断了，如果是河北电信，应该是 %E6%B2%B3%E5%8C%97%E7%94%B5%E4%BF%A1
# 修正：通常这类网站的参数是完整的，如果上面的不行，请尝试补全或保持你原本能抓取的URL
TARGET_ID = "%E6%B2%B3%E5%8C%97" # 假设这是河北
FULL_URL = f"http://nn.7x9d.cn/xzjd2.php?id={TARGET_ID}"

OUTPUT_FILE = "kaniptv.m3u"

# 台标CDN地址 (保持不变)
LOGO_BASE_URL = "https://cdn.jsdelivr.net/gh/fanmingming/live@main/tv/"

# 用于频道名称清洗的后缀词
SUFFIX_WORDS = [
    "高清", "HD", "hd", "4K", "超清", "标清", "SD",
    "频道", "电视台", "综合", "财经", "综艺", "体育",
    "电影", "电视剧", "纪录", "少儿", "军事", "农业",
    "科教", "戏曲", "社会与法", "新闻", "音乐"
]

# --- 网络配置 ---
# 核心策略：GitHub在海外，连接国内源很慢。
# 设置超时时间为 5秒。如果5秒没反应，大概率你看着也卡，或者根本连不上。
# 如果你觉得过滤太狠，可以把这里改成 8 或 10。
TIMEOUT_SECONDS = 5

# 伪装浏览器请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}

def get_proxy():
    """
    尝试获取免费代理。
    为了稳定性，这里使用一个简单的列表轮询，或者你可以接入付费API。
    如果所有代理都失败，将返回 None (直连)。
    """
    # 这里使用一个公开的免费代理API作为示例 (可能会失效，需经常更换)
    # 也可以硬编码几个你知道能用的代理
    try:
        # 尝试从某个免费接口获取 (仅作演示，实际使用建议找稳定的源)
        # 如果没有代理可用，requests 会自动走直连
        return None
    except:
        return None

def check_stream_validity(url):
    """
    检测直播源是否有效。
    使用 HEAD 请求，速度快，不消耗流量。
    """
    try:
        # 发送 HEAD 请求，只获取头部信息，不下载视频流
        # allow_redirects=True 允许重定向，因为很多源是 302 跳转
        response = requests.head(url, headers=HEADERS, timeout=TIMEOUT_SECONDS, allow_redirects=True)

        # 状态码 200 OK 表示资源存在且可访问
        if response.status_code == 200:
            return True
        else:
            # 403, 404, 500 等都视为无效
            return False
    except requests.exceptions.Timeout:
        # 超时，说明源太慢或连不上 -> 判定为卡顿/无效
        return False
    except requests.exceptions.ConnectionError:
        # 连接错误 -> 无效
        return False
    except Exception as e:
        # 其他错误
        return False

def clean_channel_name(name):
    """清洗频道名称"""
    for word in SUFFIX_WORDS:
        name = name.replace(word, "")
    return name.strip()

def get_logo_url(channel_name):
    """简单的台标匹配逻辑"""
    # 这里可以根据你的 fanmingming 仓库结构完善
    # 暂时返回一个默认值或空
    return ""

def main():
    print(f"开始抓取: {FULL_URL}")

    # 1. 获取页面内容
    try:
        resp = requests.get(FULL_URL, headers=HEADERS, timeout=10)
        resp.encoding = 'utf-8' # 根据网站实际情况调整编码，可能是 gbk
        soup = BeautifulSoup(resp.text, 'html.parser')
    except Exception as e:
        print(f"无法访问源站: {e}")
        return

    # 2. 解析 M3U 内容
    # 假设网站直接返回 m3u 文本，或者在 pre/code 标签里
    # 如果是网页表格形式，需要改解析逻辑。
    # 根据之前的经验，这类站通常直接吐出文本或者在特定区域。
    # 这里假设它是纯文本 m3u 格式，或者我们需要提取其中的 http 链接

    content = resp.text
    lines = content.split('\n')

    valid_channels = []
    current_name = ""

    print("开始验证直播源有效性 (这可能需要几分钟)...")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 识别 #EXTINF 行 (包含频道名)
        if line.startswith("#EXTINF"):
            # 提取名字，通常在 tvg-name="xxx" 或逗号后面
            match = re.search(r'tvg-name="(.*?)"', line)
            if match:
                current_name = match.group(1)
            else:
                # 兼容没有 tag 的情况，取逗号后的内容
                if "," in line:
                    current_name = line.split(",")[-1]

        # 识别 URL 行 (http...)
        elif line.startswith("http"):
            url = line

            # --- 核心过滤逻辑 ---
            is_valid = check_stream_validity(url)

            if is_valid:
                print(f"[OK] {current_name}")
                # 构造标准的 m3u 条目
                logo = get_logo_url(current_name)
                entry = f'#EXTINF:-1 tvg-name="{current_name}" tvg-logo="{logo}",{current_name}\n{url}'
                valid_channels.append(entry)
            else:
                # 静默丢弃，或者打印日志
                # print(f"[Skip] {current_name} (超时或无效)")
                pass

    # 3. 写入文件
    if valid_channels:
        m3u_header = '#EXTM3U x-tvg-url="http://epg.51zmt.top:8000/e.xml"\n'
        final_content = m3u_header + "\n".join(valid_channels)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(final_content)

        print(f"\n成功! 共保留了 {len(valid_channels)} 个有效频道。")
        print(f"文件已保存为: {OUTPUT_FILE}")
    else:
        print("\n失败! 没有找到任何有效的直播源。可能是网络问题或源站反爬。")

if __name__ == "__main__":
    main()
