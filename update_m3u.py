import os
import re
import requests
import time
from bs4 import BeautifulSoup

# 配置基础常量（采用 allorigins 跨域解封跳板）
PROXY_PREFIX = "https://api.allorigins.win/raw?url="
ORIGINAL_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
TARGET_URL = f"{PROXY_PREFIX}{ORIGINAL_URL}"

EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"
LOGO_BASE_URL = "https://raw.githubusercontent.com/fanmingming/live/main/tv/" 
OUTPUT_FILENAME = "hebei_iptv.m3u"

# 频道映射字典保持不变
CHANNEL_MAP = {
    "CCTV1": {"id": "CCTV1", "logo": "CCTV1.png", "group": "央视频道"},
    "CCTV1综合": {"id": "CCTV1", "logo": "CCTV1综合.png", "group": "央视频道"},
    "CCTV2": {"id": "CCTV2", "logo": "CCTV2.png", "group": "央视频道"},
    "CCTV2财经": {"id": "CCTV2", "logo": "CCTV2财经.png", "group": "央视频道"},
    "CCTV3": {"id": "CCTV3", "logo": "CCTV3.png", "group": "央视频道"},
    "CCTV3综艺": {"id": "CCTV3", "logo": "CCTV3综艺.png", "group": "央视频道"},
    "CCTV4": {"id": "CCTV4", "logo": "CCTV4.png", "group": "央视频道"},
    "CCTV5": {"id": "CCTV5", "logo": "CCTV5.png", "group": "央视频道"},
    "CCTV5+": {"id": "CCTV5+", "logo": "CCTV5+.png", "group": "央视频道"},
    "CCTV6": {"id": "CCTV6", "logo": "CCTV6.png", "group": "央视频道"},
    "CCTV7": {"id": "CCTV7", "logo": "CCTV7.png", "group": "央视频道"},
    "CCTV8": {"id": "CCTV8", "logo": "CCTV8.png", "group": "央视频道"},
    "CCTV9": {"id": "CCTV9", "logo": "CCTV9.png", "group": "央视频道"},
    "CCTV10": {"id": "CCTV10", "logo": "CCTV10.png", "group": "央视频道"},
    "CCTV11": {"id": "CCTV11", "logo": "CCTV11.png", "group": "央视频道"},
    "CCTV12": {"id": "CCTV12", "logo": "CCTV12.png", "group": "央视频道"},
    "CCTV13": {"id": "CCTV13", "logo": "CCTV13.png", "group": "央视频道"},
    "CCTV13新闻": {"id": "CCTV13", "logo": "CCTV13新闻.png", "group": "央视频道"},
    "CCTV14": {"id": "CCTV14", "logo": "CCTV14.png", "group": "央视频道"},
    "CCTV15": {"id": "CCTV15", "logo": "CCTV15.png", "group": "央视频道"},
    "CCTV16": {"id": "CCTV16", "logo": "CCTV16.png", "group": "央视频道"},
    "CCTV17": {"id": "CCTV17", "logo": "CCTV17.png", "group": "央视频道"},
    "湖南卫视": {"id": "湖南卫视", "logo": "湖南卫视.png", "group": "卫视频道"},
    "浙江卫视": {"id": "浙江卫视", "logo": "浙江卫视.png", "group": "卫视频道"},
    "东方卫视": {"id": "东方卫视", "logo": "东方卫视.png", "group": "卫视频道"},
    "江苏卫视": {"id": "江苏卫视", "logo": "江苏卫视.png", "group": "卫视频道"},
    "北京卫视": {"id": "北京卫视", "logo": "北京卫视.png", "group": "卫视频道"},
    "广东卫视": {"id": "广东卫视", "logo": "广东卫视.png", "group": "卫视频道"},
    "深圳卫视": {"id": "深圳卫视", "logo": "深圳卫视.png", "group": "卫视频道"},
    "安徽卫视": {"id": "安徽卫视", "logo": "安徽卫视.png", "group": "卫视频道"},
    "山东卫视": {"id": "山东卫视", "logo": "山东卫视.png", "group": "卫视频道"},
    "天津卫视": {"id": "天津卫视", "logo": "天津卫视.png", "group": "卫视频道"},
    "重庆卫视": {"id": "重庆卫视", "logo": "重庆卫视.png", "group": "卫视频道"},
    "河北卫视": {"id": "河北卫视", "logo": "河北卫视.png", "group": "河北地方"},
}

def get_sub_link():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    }
    for attempt in range(1, 4):
        try:
            print(f"正在尝试通过代理请求主页 (第 {attempt} 次)...")
            response = requests.get(TARGET_URL, headers=headers, timeout=25)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                text_nodes = soup.find_all(text=re.compile("运营商.*河北-电信"))
                
                for node in text_nodes:
                    parent = node.parent
                    sibling = parent.find_previous('a')
                    if not sibling:
                        sibling = soup.find('a', class_=re.compile("btn|blue")) 
                        
                    if sibling:
                        href = sibling.get('href')
                        btn_text = sibling.text.strip()
                        
                        if href and not href.startswith('http'):
                            href = "http://nn.7x9d.cn" + href if href.startswith('/') else "http://nn.7x9d.cn/" + href
                        elif not href and re.match(r'\d+\.\d+\.\d+\.\d+:\d+', btn_text):
                            href = f"http://nn.7x9d.cn/xzjd2.php?ip={btn_text}"
                        
                        if href:
                            # 同样为下级链接套上代理前缀
                            final_link = f"{PROXY_PREFIX}{href}"
                            print(f"成功定位并拼接代理下级链接: {final_link}")
                            return final_link

                all_links = soup.find_all('a')
                for link in all_links:
                    if re.match(r'\d+\.\d+\.\d+\.\d+:\d+', link.text.strip()):
                        href = link.get('href')
                        url = "http://nn.7x9d.cn/" + href if href and not href.startswith('http') else f"http://nn.7x9d.cn/xzjd2.php?ip={link.text.strip()}"
                        return f"{PROXY_PREFIX}{url}"
        except Exception as e:
            print(f"第 {attempt} 次代理尝试失败: {e}")
            if attempt < 3:
                time.sleep(3)
    return None

def fetch_raw_streams(sub_link):
    if not sub_link:
        return ""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    }
    for attempt in range(1, 4):
        try:
            print(f"正在通过代理请求下级页面 (第 {attempt} 次)...")
            res = requests.get(sub_link, headers=headers, timeout=25)
            res.encoding = 'utf-8'
            if res.status_code == 200:
                return res.text
        except Exception as e:
            print(f"请求下级页面第 {attempt} 次失败: {e}")
            if attempt < 3:
                time.sleep(3)
    return ""

def process_to_m3u(raw_text):
    if not raw_text:
        print("错误：未能成功获取到有效的直播源数据，无法生成 M3U 文件。")
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(f'#EXTM3U x-tvg-url="{EPG_URL}"\n# 暂未获取到有效的直播源更新\n')
        return
    
    lines = raw_text.split('\n')
    m3u_content = f'#EXTM3U x-tvg-url="{EPG_URL}"\n'
    
    count = 0
    for line in lines:
        line = line.strip()
        if not line or "#genre#" in line: 
            continue
        
        if ',' in line:
            parts = line.split(',', 1)
        elif '#' in line and 'http' in line:
            parts = line.split('#', 1)
        else:
            continue
            
        channel_name = parts[0].strip()
        stream_url = parts[1].strip()
        
        clean_name = re.sub(r'\[.*?\]|\(.*?\)|\-.*?|高清|标清|超清|HD|FHD|频道', '', channel_name).strip().upper()
        
        tvg_id = clean_name
        tvg_logo = ""
        group_title = "其他频道"
        
        matched = False
        for key, info in CHANNEL_MAP.items():
            if key in clean_name or clean_name in key:
                tvg_id = info["id"]
                tvg_logo = LOGO_BASE_URL + info["logo"]
                group_title = info["group"]
                matched = True
                break
                
        if not matched:
            tvg_logo = f"{LOGO_BASE_URL}{clean_name}.png"
            if "CCTV" in clean_name:
                group_title = "央视频道"
            elif "卫视" in clean_name:
                group_title = "卫视频道"
            elif "河北" in clean_name:
                group_title = "河北地方"
        
        m3u_content += f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{tvg_logo}" group-title="{group_title}",{channel_name}\n'
        m3u_content += f'{stream_url}\n'
        count += 1
        
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"M3U生成完毕，共收录 {count} 个频道。")

if __name__ == "__main__":
    print("开始获取酒店源...")
    link = get_sub_link()
    if link:
        raw_data = fetch_raw_streams(link)
        process_to_m3u(raw_data)
    else:
        print("未能成功获取到指定的下级按钮链接。")
        process_to_m3u("")
