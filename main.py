import requests
from bs4 import BeautifulSoup
import re
import time
import random

# ==================== 配置区 ====================
BASE_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
OUTPUT_FILE = "kaniptv.m3u"

# ✅ 台标源 (转换为 raw 格式)
LOGO_BASE_URL = "https://raw.githubusercontent.com/fanmingming/live/main/tv/"

# ✅ EPG 节目单地址
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# ✅ 筛选条件
TARGET_ISP = "河北-电信"
TARGET_DATE = "2026-06-12"

# ✅ 频道分类规则
CATEGORY_RULES = [
    (r'^(CCTV|中央)', '📺 央视'),
    (r'卫视', '📡 卫视'),
    (r'河北', '🏠 河北本地'),
    (r'北京|天津|上海|重庆|广东|深圳|浙江|江苏|湖南|湖北|山东|河南|四川|福建|安徽|辽宁|黑龙江|吉林|山西|陕西|江西|云南|广西|贵州|海南|内蒙古|新疆|西藏|青海|宁夏|甘肃', '🌐 地方台'),
    (r'(电影|影院|影视频道)', '🎬 电影'),
    (r'(综艺|娱乐)', '🎭 综艺'),
    (r'(体育|赛事)', '⚽ 体育'),
    (r'(新闻|资讯)', '📰 新闻'),
    (r'(少儿|卡通|动画)', '🧸 少儿'),
    (r'(音乐|戏曲)', '🎵 音乐戏曲'),
    (r'(纪实|记录|科教)', '📚 科教纪实'),
]

# ✅ 请求头池
HEADERS_POOL = [
    {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
    {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
]

def get_random_header():
    """获取随机请求头"""
    return random.choice(HEADERS_POOL)

def get_page_content(url, retries=3):
    """带重试机制的页面获取"""
    for attempt in range(1, retries + 1):
        try:
            time.sleep(random.uniform(1, 2))
            headers = get_random_header()
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                response.encoding = 'utf-8'
                return response.text
        except Exception as e:
            if attempt < retries:
                time.sleep(random.uniform(2, 4))
    return None

def extract_real_stream_url(detail_url):
    """从详情页提取真实的流媒体地址"""
    html = get_page_content(detail_url)
    if not html:
        return None

    patterns = [
        r'(http[s]?://[^\s"\'>]+\.m3u8)',
        r'(http[s]?://[^\s"\'>]+\.ts)'
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def classify_channel(channel_name):
    """根据频道名称进行分类"""
    for pattern, category in CATEGORY_RULES:
        if re.search(pattern, channel_name, re.IGNORECASE):
            return category
    return '📺 其他频道'

def get_logo_url(channel_name):
    """根据频道名称生成台标URL"""
    # 提取频道核心名称用于匹配台标
    logo_name = channel_name
    
    # 特殊处理：CCTV系列
    cctv_match = re.search(r'(CCTV\d+)', channel_name, re.IGNORECASE)
    if cctv_match:
        logo_name = cctv_match.group(1).upper() + '.png'
    # 卫视
    elif '卫视' in channel_name:
        # 提取卫视前的省份名，如"湖南卫视" -> "湖南.png"
        province = channel_name.replace('卫视', '')
        logo_name = province + '.png'
    # 河北本地
    elif '河北' in channel_name:
        logo_name = '河北.png'
    # 默认使用电信图标
    else:
        logo_name = '电信.png'
    
    return f"{LOGO_BASE_URL}{logo_name}"

def main():
    print("="*50)
    print("🚀 酒店源抓取脚本启动")
    print(f"目标URL: {BASE_URL}")
    print("="*50)

    html = get_page_content(BASE_URL)
    if not html:
        print("❌ 无法获取主列表页")
        return

    soup = BeautifulSoup(html, 'html.parser')
    link_tags = soup.find_all('a', href=True)

    # 按分类存储频道
    channels_by_category = {}

    for tag in link_tags:
        ip_text = tag.get_text(strip=True)
        if ':' not in ip_text:
            continue

        parent_text = tag.find_parent().get_text() if tag.find_parent() else ""

        # 筛选：河北-电信 且 2026-06-12
        if TARGET_ISP in parent_text and TARGET_DATE in parent_text:
            print(f"\n✅ 匹配成功: {ip_text}")
            
            # 构建详情页URL
            href = tag['href']
            if href.startswith('http'):
                detail_url = href
            else:
                base = BASE_URL.rsplit('/', 1)[0]
                detail_url = f"{base}/{href.lstrip('/')}"
            
            print(f"  -> 详情页: {detail_url}")

            # 获取真实播放地址
            real_url = extract_real_stream_url(detail_url)
            
            if real_url:
                # 频道名称
                channel_name = f"河北电信-{ip_text.split(':')[0]}"
                
                # 分类
                category = classify_channel(channel_name)
                
                # 台标
                logo_url = get_logo_url(channel_name)
                
                # 存入对应分类
                if category not in channels_by_category:
                    channels_by_category[category] = []
                
                channels_by_category[category].append({
                    'name': channel_name,
                    'url': real_url,
                    'logo': logo_url
                })
                
                print(f"  -> ✅ 分类: {category} | {real_url[:40]}...")
            else:
                print("  -> ❌ 未找到真实播放地址")

    # 写入M3U文件（按分类顺序输出）
    category_order = ['📺 央视', '📡 卫视', '🏠 河北本地', '🌐 地方台', '🎬 电影', '🎭 综艺', '⚽ 体育', '📰 新闻', '🧸 少儿', '🎵 音乐戏曲', '📚 科教纪实', '📺 其他频道']
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f'#EXTM3U url-tvg="{EPG_URL}"\n')
        
        for category in category_order:
            if category in channels_by_category:
                # 写入分类注释
                f.write(f'\n# {category}\n')
                for ch in channels_by_category[category]:
                    f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="{category}",{ch["name"]}\n')
                    f.write(f'{ch["url"]}\n')
    
    total = sum(len(v) for v in channels_by_category.values())
    print(f"\n🎉 抓取完成！共找到 {total} 个有效源，分为 {len(channels_by_category)} 个类别。")
    print(f"文件已保存为: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
