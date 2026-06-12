import re
import asyncio
from playwright.async_api import async_playwright

URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT = "kaniptv.m3u"

def clean_name(name):
    return re.sub(r'[\n\r\t]+', '', name).strip()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")
        await page.goto(URL, timeout=60000)
        await page.wait_for_timeout(10000)  # 延长等待时间，确保JS加载完成

        # 直接找页面里所有带链接的a标签，更宽泛地抓取
        links = await page.evaluate('''() => {
            return Array.from(document.links).map(link => {
                return { href: link.href, text: link.textContent };
            });
        }''')

        m3u = ["#EXTM3U"]

        for link in links:
            href = link['href']
            text = link['text']
            if not href or not text:
                continue
            # 只保留http开头，并且是直播源格式的链接
            if href.startswith("http") and (".m3u8" in href or "php?" in href or ".ts" in href):
                name = clean_name(text)
                if name:
                    m3u.append(f"#EXTINF:-1,{name}")
                    m3u.append(href)

        await browser.close()

        # 写入文件，如果没抓到频道，也保留#EXTM3U头，避免文件完全为空
        if len(m3u) == 1:
            m3u.append("#EXTINF:-1,暂无有效频道")
            m3u.append("http://example.com/empty")

        with open(OUTPUT, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))

        print(f"✅ 共抓到 {len(m3u)//2} 个频道")

if __name__ == "__main__":
    asyncio.run(main())
