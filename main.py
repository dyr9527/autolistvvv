import requests
import re
import os

# 配置部分
URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"

def main():
    print(f"🚀 开始抓取: {URL}")
    m3u_content = ["#EXTM3U"]
    count = 0

    try:
        # 设置超时时间和 User-Agent，模拟正常访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()  # 如果状态码不是200，抛出异常

        # 尝试解析文本内容
        # 很多直播源接口返回的是纯文本格式：频道名,url
        lines = response.text.splitlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # 简单的分割逻辑：假设用逗号分隔 频道名 和 URL
            # 如果你的源是其他格式（如 tvg-name="xxx" group-title="xxx"），需要调整这里
            parts = line.split(',')
            if len(parts) >= 2:
                name = parts[0].strip()
                url = ','.join(parts[1:]).strip() # 防止URL里也有逗号

                # 简单的校验：URL必须以 http 开头
                if url.startswith('http'):
                    m3u_content.append(f"#EXTINF:-1,{name}")
                    m3u_content.append(url)
                    count += 1

        print(f"✅ 成功抓取到 {count} 个频道")

    except Exception as e:
        print(f"❌ 抓取失败: {str(e)}")
        # 即使失败，也写入一个占位符，防止文件为空
        m3u_content.append("#EXTINF:-1,抓取失败-暂无数据")
        m3u_content.append("http://example.com/empty")

    # 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_content))

    print(f"💾 已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
