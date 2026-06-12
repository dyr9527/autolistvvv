import requests

URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.m3u"

def main():
    print(f"🚀 开始抓取: {URL}")
    m3u_content = ["#EXTM3U"]
    count = 0

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()

        # 把 <br> 替换成换行符
        text = response.text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
        lines = text.splitlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if ',' in line:
                parts = line.split(',', 1)
                name = parts[0].strip()
                url = parts[1].strip()

                if url.startswith('http'):
                    # ⭐ 直接写入原始 URL，不做任何编码
                    m3u_content.append(f"#EXTINF:-1,{name}")
                    m3u_content.append(url)
                    count += 1

        print(f"✅ 成功抓取到 {count} 个频道")

    except Exception as e:
        print(f"❌ 抓取失败: {str(e)}")
        m3u_content.append("#EXTINF:-1,抓取失败-暂无数据")
        m3u_content.append("http://example.com/empty")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_content))

    print(f"💾 已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
