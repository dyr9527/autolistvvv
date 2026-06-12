import requests
import re

# 源站地址和输出文件
SOURCE_URL = "http://www.kaniptv.cn/%E6%99%AE%E9%80%9A%E9%85%92%E5%BA%97.php?ip=106.115.25.181%3A19901"
OUTPUT_FILE = "kaniptv.txt"  # 输出为 txt 格式

def get_group(channel_name):
    """根据频道名称判断分类"""
    name_upper = channel_name.upper()
    if "河北" in channel_name or "HEBEI" in name_upper:
        return "河北地方频道"
    elif name_upper.startswith("CCTV"):
        return "央视频道"
    elif "卫视" in channel_name:
        return "卫视频道"
    else:
        return "其他"

def main():
    print(f" 开始抓取源站: {SOURCE_URL}")
    txt_lines = []
    count = 0

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(SOURCE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        # 处理 HTML 换行标签
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
                    group_title = get_group(name)
                    # TXT 标准格式：分组名,频道名,播放链接
                    txt_lines.append(f"{group_title},{name},{url}")
                    count += 1

        print(f" 成功处理 {count} 个频道")

    except Exception as e:
        print(f" 抓取或处理失败: {str(e)}")
        txt_lines.append("其他,抓取失败-请检查源站,http://example.com/empty")

    # 写入文件 (确保编码为 UTF-8)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))

    print(f" 已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
