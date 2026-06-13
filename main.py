import os
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_and_generate_m3u():
    # 1. 配置无头浏览器模式 (适用于 GitHub Actions)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        target_url = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
        driver.get(target_url)
        
        # 2. 精准定位目标按钮并点击
        # 寻找包含指定文本的元素，并向上查找最近的蓝色链接按钮
        xpath_query = "//a[contains(@class, 'blue') and contains(text(), ':')][following::text()[contains(., '运营商：河北-电信')]][1]"
        wait = WebDriverWait(driver, 15)
        button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_query)))
        button.click()
        
        # 等待新页面加载完成
        time.sleep(5) 
        page_text = driver.page_source
        
        # 3. 提取纯文本中的 IP/URL (请根据实际网页内容微调正则)
        stream_pattern = r'(?:http|rtsp|rtmp)://[^\s<>\'"]+'
        streams = list(set(re.findall(stream_pattern, page_text)))
        
        # 4. 组装标准 M3U 格式
        m3u_content = ["#EXTM3U"]
        for stream in streams:
            # 简单处理频道名称（截取域名或路径作为默认名称）
            channel_name = re.sub(r'.*/', '', stream).split('.')[0] 
            
            # TODO: 这里可以接入外部台标库和 EPG 接口进行匹配
            tvg_logo = "" 
            epg_id = ""
            
            extinf_line = f'#EXTINF:-1 tvg-id="{epg_id}" tvg-name="{channel_name}" tvg-logo="{tvg_logo}", {channel_name}'
            m3u_content.append(extinf_line)
            m3u_content.append(stream)
            
        # 5. 写入本地文件
        with open("output.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_content))
            
        print(f"M3U 生成成功，共包含 {len(streams)} 个有效频道！")
        
    except Exception as e:
        print(f"抓取过程发生错误: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_and_generate_m3u()
