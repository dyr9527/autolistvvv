import requests
import re

URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT = "kaniptv.m3u"

def fetch_live_sources():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "http://www.kaniptv.cn/"
    }

    try:
        response = requests.get(URL, headers=headers, timeout=15)
        response.encoding = 'utf-8' # 确保中文不乱码
        content = response.text
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return []

    lines = content.split('\n')
    results = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 情况 A: 已经是标准的 M3U 格式 (#EXTINF)
        if line.startswith('#EXTINF'):
            results.append(line)
            continue

        # 情况 B: 纯文本格式 (频道名,链接)
        # 假设逗号分隔，且链接包含 http
        if ',' in line and 'http' in line:
            parts = line.split(',', 1) # 只分割第一个逗号
            name = parts[0].strip()
            url = parts[1].strip()

            # 简单的清洗，防止名字里有换行符
            name = re.sub(r'[\r\n\t]', '', name)

            if name and url.startswith('http'):
                results.append(f"#EXTINF:-1,{name}")
                results.append(url)

        # 情况 C: 直接就是链接 (没有名字的情况，较少见但存在)
        elif line.startswith('http'):
             # 这种情况下很难自动命名，通常可以跳过或用文件名做名字
             pass

    return results

def main():
    sources = fetch_live_sources()

    m3u_content = ["#EXTM3U"]

    if sources:
        m3u_content.extend(sources)
        print(f"✅ 成功抓取到 {len(sources)//2} 个频道")
    else:
        print("⚠️ 未抓取到有效内容，生成默认文件")
        m3u_content.append("#EXTINF:-1,暂无有效频道")
        m3u_content.append("http://example.com/empty")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_content))

    print(f"💾 已保存至 {OUTPUT}")

if __name__ == "__main__":
    main()
