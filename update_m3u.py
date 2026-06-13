import os
import re
import requests
from bs4 import BeautifulSoup

# 配置基础常量
TARGET_URL = "http://nn.7x9d.cn/xzjd2.php?id=%E6%B2%B3%E5%8C%97"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"
LOGO_BASE_URL = "https://raw.githubusercontent.com/fanmingming/live/main/tv/" # GitHub 原始文件加速路径
OUTPUT_FILENAME = "hebei_iptv.m3u"

# 定义常见频道的标准台标和tvg-id映射（可根据需要在此处自行扩充）
# 建议映射参考范明明(fanmingming)的台标文件名，例如 CCTV1综合.png -> CCTV1综合
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
    """从主页解析指定条件的第一个蓝色按钮链接"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            print("无法访问主页")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 寻找包含“运营商：河北-电信”的文本节点
        text_nodes = soup.find_all(text=re.compile("运营商.*河北-电信"))
        
        for node in text_nodes:
            # 找到该节点所在的容器（通常是包含这些文本的 div 或 p）
            parent = node.parent
            # 在其上方寻找紧邻的蓝色按钮。根据前端常见设计，可能在同级前一个，或父级的上一个元素中
            # 这里通过寻找带有 IP 格式按钮的 a 标签或通过特定的样式定位
            # 网页通常结构是：[蓝色IP按钮] -> [运营商文本]
            # 我们向上遍历寻找符合 IP:Port 特征的链接
            sibling = parent.find_previous('a')
            if not sibling:
                # 尝试直接在全网找第一个包含符合按钮特征的a标签
                sibling = soup.find('a', class_=re.compile("btn|blue")) 
                
            if sibling or (parent.name == 'div' and 'href' in parent.attrs):
                href = sibling.get('href') if sibling else None
                # 如果 href 只是一个相对路径或IP文本，将其拼接成完整URL
                btn_text = sibling.text.strip() if sibling else ""
                
                # 如果href是链接则直接用，如果只是文本，网页通常点击跳转形式为：xzjd2.php?ip=... 或直接跳转
                if href and not href.startswith('http'):
                    # 补全相对路径
                    if href.startswith('/'):
                        href = "http://nn.7x9d.cn" + href
                    else:
                        href = "http://nn.7x9d.cn/" + href
                elif not href and re.match(r'\d+\.\d+\.\d+\.\d+:\d+', btn_text):
                    # 如果a标签里面只有IP:Port文本，没有href，则尝试拼接默认跳转
                    href = f"http://nn.7x9d.cn/xzjd2.php?ip={btn_text}" # 视网站实际跳转逻辑而定
                
                # 兜底逻辑：如果该网站直接以 IP:Port 按钮作为文本，且点击直接进入下级页
                # 很多此类网站下级链接形式直接就是按钮上的链接
                if href:
                    print(f"成功定位到下级链接: {href}")
                    return href

        # 兜底：如果上面的复杂文本定位失败，直接抓取页面第一个符合IP:Port格式的a标签
        all_links = soup.find_all('a')
        for link in all_links:
            if re.match(r'\d+\.\d+\.\d+\.\d+:\d+', link.text.strip()):
                href = link.get('href')
                if href:
                    return "http://nn.7x9d.cn/" + href if not href.startswith('http') else href
                else:
                    # 如果只有文本，尝试将其作为参数
                    return f"http://nn.7x9d.cn/xzjd2.php?ip={link.text.strip()}"

    except Exception as e:
        print(f"解析主页发生错误: {e}")
    return None

def fetch_raw_streams(sub_link):
    """访问下级链接获取直播源纯文本内容"""
    if not sub_link:
        return ""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        res = requests.get(sub_link, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        return res.text
    except Exception as e:
        print(f"获取下级页面失败: {e}")
        return ""

def process_to_m3u(raw_text):
    """将原始文本加工成带台标和EPG的M3U文件"""
    if not raw_text:
        print("没有获取到任何直播源内容。")
        return
    
    lines = raw_text.split('\n')
    m3u_content = f'#EXTM3U x-tvg-url="{EPG_URL}"\n'
    
    count = 0
    for line in lines:
        line = line.strip()
        if not line or "#genre#" in line: # 过滤空行和可能存在的分类标签
            continue
        
        # 常见的txt格式直播源通常为：频道名称,直播源链接 或 频道名称#直播源链接
        if ',' in line:
            parts = line.split(',', 1)
        elif '#' in line and 'http' in line:
            parts = line.split('#', 1)
        else:
            continue
            
        channel_name = parts[0].strip()
        stream_url = parts[1].strip()
        
        # 清理频道名称中的特殊无用杂质（如高清、FHD、[蓝光]等，便于匹配台标）
        clean_name = re.sub(r'\[.*?\]|\(.*?\)|\-.*?|高清|标清|超清|HD|FHD|频道', '', channel_name).strip().upper()
        
        # 默认匹配信息
        tvg_id = clean_name
        tvg_logo = ""
        group_title = "其他频道"
        
        # 匹配自定义的台标和EPG库
        matched = False
        for key, info in CHANNEL_MAP.items():
            if key in clean_name or clean_name in key:
                tvg_id = info["id"]
                tvg_logo = LOGO_BASE_URL + info["logo"]
                group_title = info["group"]
                matched = True
                break
                
        # 如果没有在预设字典中，尝试自动化组装台标
        if not matched:
            # 默认为 名字.png
            tvg_logo = f"{LOGO_BASE_URL}{clean_name}.png"
            if "CCTV" in clean_name:
                group_title = "央视频道"
            elif "卫视" in clean_name:
                group_title = "卫视频道"
            elif "河北" in clean_name:
                group_title = "河北地方"
        
        # 组装 M3U 格式
        m3u_content += f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{tvg_logo}" group-title="{group_title}",{channel_name}\n'
        m3u_content += f'{stream_url}\n'
        count += 1
        
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    print(f"M3U生成完毕，共收录 {count} 个频道。文件已保存为 {OUTPUT_FILENAME}")

if __name__ == "__main__":
    print("开始获取酒店源...")
    link = get_sub_link()
    if link:
        raw_data = fetch_raw_streams(link)
        process_to_m3u(raw_data)
    else:
        print("未能成功获取到指定的下级按钮链接。")
