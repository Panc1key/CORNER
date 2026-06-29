import requests
import os
import pandas as pd
from bs4 import BeautifulSoup

# 设置请求头
headers = {
    "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
}

# 更新后的 C_OP 数值列表
C_OP_LIST = [
    '556116'
]

base_url = "https://asia-en.onepiece-cardgame.com/"

# 桌面路径
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

for ICOP in C_OP_LIST:
    print(f"Getting data for C_OP: {ICOP}...")
    url = f"https://asia-en.onepiece-cardgame.com/cardlist/?series={ICOP}"

    # 发起请求并获取 HTML 内容
    response = requests.get(url, headers=headers)

    # 检查请求是否成功
    if response.status_code != 200:
        print(f"Request failed with status code: {response.status_code}")
        continue

    page_text = response.text
    soup = BeautifulSoup(page_text, 'html.parser')

    card_info_list = []
    cards = soup.find_all('dl', class_='modalCol')  # 找到所有的卡片条目

    # 获取系列名称（从第一张卡片的 get_info 中提取）
    first_card = cards[0] if cards else None
    if first_card:
        get_info_temp = first_card.find('div', class_='getInfo').find(text=True, recursive=False).strip() if first_card.find('div', class_='getInfo') else f'C_OP_{ICOP}'
        series_name = get_info_temp.replace('/', '_').replace('\\', '_').replace(':', '_').replace(' ', '_')
    else:
        series_name = f'C_OP_{ICOP}'

    # 创建图片保存文件夹
    image_folder = os.path.join(desktop_path, series_name)
    if not os.path.exists(image_folder):
        os.makedirs(image_folder)
        print(f"创建图片文件夹: {image_folder}")

    # 用于追踪每个卡号出现的次数（处理异画）
    card_no_counter = {}

    for card in cards:
        # 提取信息
        card_no = card.find('span').text if card.find('span') else 'Unknown Number'
        infoCol = card.find('div', class_='infoCol').find_all('span') if card.find('div', class_='infoCol') else []

        rarity = infoCol[1].text if len(infoCol) > 1 else 'Unknown Rarity'
        card_type = infoCol[2].text if len(infoCol) > 2 else 'Unknown Type'
        name = card.find('div', class_='cardName').text if card.find('div', class_='cardName') else 'Unknown Name'

        # 获取费用、属性、力量值、特征和效果
        cost = card.find('div', class_='cost').find(text=True, recursive=False).strip() if card.find('div', class_='cost') else 'Unknown Cost'
        attribute_img = card.find('div', class_='attribute').find('img')
        attribute = attribute_img['alt'] if attribute_img else 'Unknown Attribute'
        power = card.find('div', class_='power').find(text=True, recursive=False).strip() if card.find('div', class_='power') else 'Unknown Power'
        feature = card.find('div', class_='feature').find(text=True, recursive=False).strip() if card.find('div', class_='feature') else 'Unknown Feature'
        effect = card.find('div', class_='text').find(text=True, recursive=False).strip() if card.find('div', class_='text') else 'Unknown Effect'
        get_info = card.find('div', class_='getInfo').find(text=True, recursive=False).strip() if card.find('div', class_='getInfo') else 'Unknown Acquisition Method'

        # 获取图片链接并进行格式化
        image_tag = card.find('div', class_='frontCol').find('img')
        image_url = base_url + image_tag['data-src'] if image_tag else 'Unknown Image URL'

        # 下载图片
        if image_url != 'Unknown Image URL':
            try:
                # 清理卡号，移除特殊字符
                safe_card_no = card_no.replace('/', '_').replace('\\', '_').replace(':', '_').replace(' ', '_')

                # 检查这个卡号是否已经出现过（处理异画）
                if safe_card_no in card_no_counter:
                    # 异画卡片，添加 _p1, _p2 等后缀
                    card_no_counter[safe_card_no] += 1
                    image_filename = f"{safe_card_no}_p{card_no_counter[safe_card_no]}.jpg"
                else:
                    # 第一次出现的卡号
                    card_no_counter[safe_card_no] = 0
                    image_filename = f"{safe_card_no}.jpg"

                image_path = os.path.join(image_folder, image_filename)

                # 下载图片
                img_response = requests.get(image_url, headers=headers, timeout=10)
                if img_response.status_code == 200:
                    with open(image_path, 'wb') as f:
                        f.write(img_response.content)
                    print(f"已下载图片: {image_filename}")
                else:
                    print(f"下载图片失败 {card_no}: 状态码 {img_response.status_code}")
            except Exception as e:
                print(f"下载图片时发生错误 {card_no}: {e}")

        # 提取颜色和 Counter 数值
        color_div = card.find('div', class_='color')
        color = color_div.text.replace('Color', '').strip() if color_div else 'Unknown Color'

        counter_div = card.find('div', class_='counter')
        counter = counter_div.text.replace('Counter', '').strip() if counter_div else 'Unknown Counter'

        # 提取 Trigger 内容
        trigger_div = card.find('div', class_='trigger')
        trigger = trigger_div.text.strip() if trigger_div else '-'

        # 将信息合并到一个字符串中，并用换行符分隔
        combined_info = (
            f"Card Name: {name}\n"
            f"Color: {color}\n"
            f"Type: {card_type}\n"
            f"Cost: {cost}\n"
            f"Power: {power}\n"
            f"Attribute: {attribute}\n"
            f"Counter: {counter}\n"
            f"Feature: {feature}\n"
            f"Effect: {effect}\n"
            f"Trigger: {trigger}\n"
        )

        # 重新组织信息以符合CSV格式
        title = f"{card_no} {name} ({rarity})"
        body = combined_info.replace("<br>", "\n")
        vendor = "Bandai"
        product_category = "Cards"

        # 根据 rarity 设置 Tags 内容
        tags = [color, card_type, rarity, f"Cost{cost}", f"Power{power}", attribute, f"Counter{counter}", feature]

        # 检查是否有 Blocker, Trigger 等字眼
        if "Blocker" in effect:
            tags.append("Blocker")
        if trigger != '-':
            tags.append("Trigger")

        tags = ", ".join(tags)

        card_info = {
            'Title': title,
            'Body (HTML)': body,
            'Vendor': vendor,
            'Product Category': product_category,
            'Type': card_type,
            'Tags': tags
        }

        card_info_list.append(card_info)

    # 检查是否找到卡片信息
    if card_info_list:
        df = pd.DataFrame(card_info_list)

        # 使用获取方式和 C_OP 值作为文件名
        get_info_filename = get_info.replace('/', '_').replace('\\', '_').replace(':', '_').replace(' ', '_')
        filename = f"{get_info_filename}_C_OP_{ICOP}.csv"

        # 保存到 CSV 文件
        df.to_csv(filename, index=False)

        # 保存到桌面路径
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        file_path = os.path.join(desktop_path, filename)
        df.to_csv(file_path, index=False)

        print(f"Information saved to {file_path}")

        print(f"Information saved to {filename}")
    else:
        print(f"C_OP: {ICOP} found no card information.")