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
        await page.wait_for_timeout(8000)

        items = await page.locator("a").all()
        m3u = ["#EXTM3U"]

        for a in items:
            href = await a.get_attribute("href")
            text = await a.inner_text()
            if not href or not text:
                continue
            if href.startswith("http") and (".m3u8" in href or "php?" in href):
                name = clean_name(text)
                m3u.append(f"#EXTINF:-1,{name}")
                m3u.append(href)

        await browser.close()

        with open(OUTPUT, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))

        print(f"✅ 共抓到 {len(m3u)//2} 个频道")

if __name__ == "__main__":
    asyncio.run(main())
