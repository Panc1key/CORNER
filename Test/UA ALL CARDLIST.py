import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
import os

# 设置请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

base_url = "https://www.unionarena-tcg.com/jp/cardlist/detail_iframe.php?card_no="
image_base_url = "https://www.unionarena-tcg.com"  # 图像的基URL

# 多个初始代码
initial_codes = [
    "UA01ST/CGH-1-001",
    "UA01BT/CGH-1-001",
    "EX02BT/CGH-2-001",
    "UA02ST/JJK-1-045",
    "UA02BT/JJK-1-001",
    "EX04BT/JJK-3-001",
    "UA02NC/JJK-2-001",
    "UA03ST/HTR-1-070",
    "UA03BT/HTR-1-001",
    "EX01BT/HTR-1-030",
    "UA04ST/IMS-1-001",
    "UA04BT/IMS-1-001",

    "EX03BT/IMS-2-001",
    "UA05ST/KMY-1-001",
    "UA05BT/KMY-1-001",
    "EX05BT/KMY-1-017",
    "UA01NC/KMY-2-001",
    "UA06ST/TOA-1-068",
    "UA06BT/TOA-1-001",
    "UA07ST/TSK-1-035",
    "UA07BT/TSK-1-001",
    "UA08ST/BLC-1-034",
    "UA08BT/BLC-1-001",
    
    "EX07BT/BLC-2-001",
    "UA09ST/BTR-1-006",
    "UA09BT/BTR-1-001",
    "UA10ST/MHA-1-034",
    "UA10BT/MHA-1-001",
    "EX06BT/MHA-2-001",
    "UA11ST/GNT-1-070",
    "UA11BT/GNT-1-001",
    "UA12ST/BLK-1-035",
    "UA12BT/BLK-1-001",
    "UA03NC/BLK-2-001",
    "UA13ST/TKN-1-068",
    "UA13BT/TKN-1-001",
    "UA14ST/DST-1-069",
    "UA14BT/DST-1-001",
    "UA15ST/SAO-1-036",
    "UA15BT/SAO-1-001",
    "UA16ST/SYN-1-002",
    "UA16BT/SYN-1-001",
    "UA17ST/TRK-1-041",
    "UA17BT/TRK-1-001",
    "UA18ST/NIK-1-001",
    "UA18BT/NIK-1-001",
    "UA19ST/HIQ-1-068",
    "UA19BT/HIQ-1-001",
    "UA20ST/BCV-1-068",
    "UA20BT/BCV-1-001",
    "UA21ST/YYH-1-035",
    "UA21BT/YYH-1-001",
    "UA22BT/GMR-1-001",
    "UA23ST/AOT-1-068",
    "UA23BT/AOT-1-001",
    "UA24BT/SHY-1-001",
    "UA25BT/AND-1-001",
    "UA26BT/RLY-1-001",
    "UA27BT/GIM-1-001",
    "UA28BT/KJ8-1-001",
    "UA29ST/KMR-1-016",
    "UA29BT/KMR-1-001",
    "UA01PC/WBK-1-001",
    "UA01PB/CGH-1-016",
    
    "UA04BT/IMS-1-AP01",
    "EX03BT/IMS-2-AP01",
    "UA05ST/KMY-1-AP01",
    "UA05BT/KMY-1-AP01",
    "EX05BT/KMY-1-AP01",
    "UA01NC/KMY-2-AP01",
    "UA06ST/TOA-1-AP01",
    "UA06BT/TOA-1-AP01",
    "UA07ST/TSK-1-AP01",
    "UA07BT/TSK-1-AP01",
    "UA08ST/BLC-1-AP01",
    "UA08BT/BLC-1-AP01",
    "EX07BT/BLC-2-AP01",
    "UA09ST/BTR-1-AP01",
    "UA09BT/BTR-1-AP01",
    "UA10ST/MHA-1-AP01",
    "UA10BT/MHA-1-AP01",
    "EX06BT/MHA-2-AP01",
    "UA11ST/GNT-1-AP01",
    "UA11BT/GNT-1-AP01",
    "UA12ST/BLK-1-AP01",
    "UA12BT/BLK-1-AP01",
    "UA03NC/BLK-2-AP01",
    "UA13ST/TKN-1-AP01",
    "UA13BT/TKN-1-AP01",
    "UA14ST/DST-1-AP01",
    "UA14BT/DST-1-AP01",
    "UA15ST/SAO-1-AP01",
    "UA15BT/SAO-1-AP01",
    "UA16ST/SYN-1-AP01",
    "UA16BT/SYN-1-AP01",
    "UA17ST/TRK-1-AP01",
    "UA17BT/TRK-1-AP01",
    "UA18ST/NIK-1-AP01",
    "UA18BT/NIK-1-AP01",
    "UA19ST/HIQ-1-AP01",
    "UA19BT/HIQ-1-001",
    "UA20ST/BCV-1-AP01",
    "UA20BT/BCV-1-001",
    "UA21ST/YYH-1-AP01",
    "UA21BT/YYH-1-001",
    "UA22BT/GMR-1-001",
    "UA23ST/AOT-1-AP01",
    "UA23BT/AOT-1-001",
    "UA24BT/SHY-1-AP01",
    "UA25BT/AND-1-AP01",
    "UA26BT/RLY-1-AP01",
    "UA27BT/GIM-1-AP01",
    "UA28BT/KJ8-1-AP01",
    "UA29ST/KMR-1-AP01",
    "UA29BT/KMR-1-001",
    "UA01PC/WBK-1-AP01",
    "UA01PB/CGH-1-AP01"
]

# 遍历每个初始代码
for initial_code in initial_codes:
    data_found = []
    existing_codes = set()  # 记录已经提取过的卡片代码

    # 提取基本信息部分
    parts = initial_code.split('/')
    prefix, base_number = parts

    # 使用正则表达式匹配基本编号格式
    match = re.match(r'([^-]+)-([0-9]+)-([0-9]+)', base_number)
    if match:
        base_num_prefix = match.group(1)  # CGH
        base_num_str = match.group(2)      # 1
        additional_info = match.group(3)   # 001
        base_num = int(base_num_str)        # 将数字部分转为整数
    else:
        print(f"Unexpected format for base number: {base_number}. Please check the input.")
        continue  # 如果遇到不符合格式的号码，继续下一个

    # 循环尝试访问每个页面
    for i in range(170):  # 尝试从001到030
        current_number = base_num + i  # 当前数字
        current_additional_info = f"{current_number:03}"  # 格式化为三位数
        current_code = f"{prefix}/{base_num_prefix}-{base_num_str}-{current_additional_info}"  # 生成当前代码
        url = f"{base_url}{current_code}"

        print(f"Attempting URL: {url}...")

        # 发起请求并获取 HTML 内容
        response = requests.get(url, headers=headers)

        # 检查请求是否成功
        if response.status_code != 200:
            print(f"Request failed with status code: {response.status_code}. Skipping...")
            continue
        
        page_text = response.text
        soup = BeautifulSoup(page_text, 'html.parser')

        # 提取卡片名称和假名
        card_name_element = soup.find('h2', class_='cardNameCol')
        if card_name_element:
            card_name = card_name_element.contents[0].strip()  # 提取卡片名称
            ruby_data_element = card_name_element.find('span', class_='rubyData')
            ruby_data = ruby_data_element.text.strip() if ruby_data_element else ""
        else:
            card_name = ""
            ruby_data = ""

        # 提取卡片编号和稀有度
        card_num_element = soup.find('span', class_='cardNumData')
        rarity_element = soup.find('span', class_='rareData')
        card_num = card_num_element.text.strip() if card_num_element else ""
        rarity = rarity_element.text.strip() if rarity_element else ""

        # 提取其他详细数据
        consume_ap = ""
        card_type = ""
        effect = ""
        trigger = ""  # 添加 trigger 变量
        bp = ""  # BP 变量
        energy = ""  # 发生エナジー 变量
        attribute = ""  # 特徴
        image_url = ""  # 卡片图像URL

        # 提取必要エナジー（消耗 AP）
        consume_ap_element = soup.find('dl', class_='cardDataCol needEnergyData')
        if consume_ap_element:
            consume_ap_image = consume_ap_element.find('dd', class_='cardDataContents').img
            consume_ap = consume_ap_image['alt'] if consume_ap_image else ""

        # 提取カード種類（卡片类型）
        card_type_element = soup.find('dl', class_='cardDataCol categoryData')
        if card_type_element:
            card_type = card_type_element.find('dd', class_='cardDataContents').text.strip()

        # 提取効果（效果）
        effect_element = soup.find('dt', text=re.compile('効果'))
        if effect_element:
            effect = effect_element.find_next('dd').text.strip()

        # 提取トリガー（触发器）
        trigger_element = soup.find('dt', text=re.compile('トリガー'))
        if trigger_element:
            trigger = trigger_element.find_next('dd').text.strip()

        # 提取BP
        bp_element = soup.find('dt', text=re.compile('BP'))
        if bp_element:
            bp = bp_element.find_next('dd').text.strip()

        # 提取发生成エナジー（产出エナジー）
        energy_element = soup.find('dl', class_='cardDataCol generatedEnergyData')
        if energy_element:
            energy_image = energy_element.find('dd', class_='cardDataContents').img
            energy = energy_image['alt'] if energy_image else ""

        # 提取特徴（特征）
        attribute_element = soup.find('dl', class_='cardDataCol attributeData')
        if attribute_element:
            attribute = attribute_element.find('dd', class_='cardDataContents').text.strip()

        # 提取卡片图像
        image_element = soup.find('dl', class_='cardImgTitleCol')
        if image_element:
            img_tag = image_element.find('dd', class_='cardDataImgCol').find('img')
            image_url = img_tag['src'] if img_tag else ""

        # 如果当前卡片代码已存在，则跳过
        if current_code in existing_codes:
            print(f"Card code {current_code} already exists. Skipping...")
            continue
        else:
            existing_codes.add(current_code)  # 添加为已存在代码

        # 收集数据
        data_found.append({
            'Card Code': current_code,
            'Card Name': card_name,
            'Ruby Data': ruby_data,
            'Card Number': card_num,
            'Rarity': rarity,
            'Consume AP': consume_ap,
            'Card Type': card_type,
            'Effect': effect,
            'Trigger': trigger,  # 将 trigger 添加到数据字典中
            'BP': bp,            # 将 BP 添加到数据字典中
            '発生エナジー': energy,  # 将发生成エナジー添加到数据字典中
            '特徴': attribute,     # 将特征添加到数据字典中
            'Image URL': f"{image_base_url}{image_url}"  # 将图片链接添加到数据字典中
        })
        print(f"Found card for {current_code}: {card_name}, {ruby_data}")

    # 创建 DataFrame
    df = pd.DataFrame(data_found)

    # 将数据输出到以 initial_code 为基础的 Excel 文件名
    filename = initial_code.replace('/', '_')  # 将斜杠替换为下划线
    excel_file = os.path.join(os.getcwd(), f"{filename}.xlsx")
    df.to_excel(excel_file, index=False)

    print(f"Data saved to {excel_file}")