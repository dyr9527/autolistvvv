import re
import asyncio
from playwright.async_api import async_playwright

URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT = "kaniptv.m3u"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
        await page.goto(URL, timeout=60000)
        await page.wait_for_timeout(12000)  # 延长等待时间，确保所有JS加载完成

        # 用更精准的方式提取所有带直播源的链接
        items = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href');
                const text = a.textContent.trim();
                if (href && text && href.startsWith('http')) {
                    results.push({href, text});
                }
            });
            return results;
        }''')

        m3u = ["#EXTM3U"]

        for item in items:
            href = item['href']
            text = item['text']
            # 只保留直播源格式的链接
            if href.endswith('.m3u8') or href.endswith('.ts') or 'php?' in href:
                name = re.sub(r'[\n\r\t]+', '', text).strip()
                if name:
                    m3u.append(f"#EXTINF:-1,{name}")
                    m3u.append(href)

        await browser.close()

        # 写入文件，如果没抓到频道，也保留#EXTM3U头
        if len(m3u) == 1:
            m3u.append("#EXTINF:-1,暂无有效频道")
            m3u.append("http://example.com/empty")

        with open(OUTPUT, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))

        print(f"✅ 共抓到 {len(m3u)//2} 个频道")

if __name__ == "__main__":
    asyncio.run(main())
