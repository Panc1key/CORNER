import re
import pandas as pd
from bs4 import BeautifulSoup
import os
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import threading
from datetime import datetime
import time
import concurrent.futures
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# 全局瀏覽器對象
driver = None

# 初始化瀏覽器（有頭模式，更容易繞過 Cloudflare）
def init_driver():
    """初始化 undetected_chromedriver（有頭模式）"""
    global driver
    try:
        log("正在初始化瀏覽器（有頭模式）...")
        options = uc.ChromeOptions()

        # 不使用無頭模式，Cloudflare 更難檢測
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')

        # 指定 Chrome 版本為 148
        driver = uc.Chrome(options=options, version_main=148, headless=False, use_subprocess=False)

        # 設置超時時間，防止無限等待
        driver.set_page_load_timeout(300)  # 頁面加載超時：5分鐘
        driver.set_script_timeout(60)       # 腳本執行超時：1分鐘
        driver.implicitly_wait(10)          # 隱式等待：10秒

        log("瀏覽器初始化成功（有頭模式）")
        return True
    except Exception as e:
        log(f"瀏覽器初始化失敗: {e}")
        return False

# 關閉瀏覽器
def close_driver():
    """關閉瀏覽器"""
    global driver
    if driver:
        try:
            driver.quit()
            driver = None
            log("瀏覽器已關閉")
        except Exception as e:
            log(f"關閉瀏覽器時出錯: {e}")

# 基 URL
base_url = "https://yugipedia.com/wiki/"

# CSV保存目录
csv_dir = os.path.join(os.path.expanduser("~"), "Desktop", "YugipediaCardGameList")
if not os.path.exists(csv_dir):
    os.makedirs(csv_dir)  # 如果目录不存在，则创建

# 全局变量
selected_series = []
enable_price_extraction = False  # 默认禁用价格提取以加快速度

# 测试连接的函数
def test_connection():
    """测试与yugipedia的连接"""
    global driver
    try:
        log("开始测试连接...")

        if not driver:
            if not init_driver():
                return False

        # 测试主页
        log("测试访问主页...")
        driver.get("https://yugipedia.com")
        time.sleep(5)

        if "Yugipedia" in driver.page_source:
            log("主页访问成功！")

            # 测试具体页面
            test_url = "https://yugipedia.com/wiki/Creation_Pack_09"
            log(f"测试访问页面: {test_url}")
            driver.get(test_url)
            time.sleep(5)

            if "Creation Pack 09" in driver.page_source or "Card Number" in driver.page_source:
                log("页面访问成功！连接正常。")
                return True
            else:
                log("页面访问失败：未找到预期内容")
                return False
        else:
            log("主页访问失败")
            return False

    except Exception as e:
        log(f"测试连接时发生错误: {e}")
        return False

# 系列列表（从你提供的选项中提取）
SERIES_LIST = [
    "Tournament_Pack_2024_Vol.1_(Asian-English)",
    "Rarity_Collection_Quarter_Century_Edition",
    "Creation_Pack_02",
    "Creation_Pack_02_+1_Bonus_Pack",
    "Age_of_Overlord",
    "Age_of_Overlord_+1_Bonus_Pack",
    "Creation_Pack_03",
    "Creation_Pack_03_+1_Bonus_Pack",
    "Stainless_Steel_Egyptian_God_Cards",
    "Phantom_Nightmare",
    "Phantom_Nightmare_+1_Bonus_Pack",
    "Tournament_Pack_2024_Vol.2_(Asian-English)",
    "Challenger_Cup_2024_Qualifiers_prize_card",
    "Creation_Pack_04",
    "Creation_Pack_04_+1_Bonus_Pack",
    "Structure_Deck:_Salamangreat_Sanctum",
    "Structure_Deck:_Salamangreat_Sanctum_Transcend_Power-Up_Pack",
    "Legacy_of_Destruction",
    "Legacy_of_Destruction_+1_Bonus_Pack",
    "Tournament_Pack_2024_Vol.3_(Asian-English)",
    "Essential_Selection_01",
    "Creation_Pack_05",
    "Creation_Pack_05_+1_Bonus_Pack",
    "Infinite_Forbidden_+1_Bonus_Pack",
    "The_Infinite_Forbidden",
    "Yu-Gi-Oh!_Open_Tournament_Singapore_2024_prize_card",
    "Tournament_Pack_2024_Vol.4_(Asian-English)",
    "Bonus_Pack:_Awakened_by_the_Primites",
    "Rage_of_the_Abyss",
    "Rage_of_the_Abyss_+1_Bonus_Pack",
    "Duel-Ignition_Deck:_HERO",
    "Duel-Ignition_Deck:_Swordsoul",
    "Selection_5:_Quarter_Century_Edition",
    "Tournament_Pack_2024_Vol.5_(Asian-English)",
    "Creation_Pack_06",
    "Supreme_Darkness",
    "Deck_Build_Pack:_Crossover_Breakers",
    "Creation_Pack_07",
    "Alliance_Insight",
    "Supreme_Darkness",
    "Quarter_Century_Art_Collection",
    "Crossover_Breakers",
    "Justice_Hunters",
    "Tactical-Try_Pack:_Dark_Magic_/_HERO_/_Mikanko#google_vignette",
    "Creation_Pack_09",
    "Burst_Protocol",
    "Terminal_World_3",
    "Special Pack: Stamp Edition",
    "Duelist Box: Prismatic Summon",
    "Creation_Pack_10",
    "Blazing_Dominion",
    "Blazing_Dominion_%2B1_Assist_Pack",
    "THE_CHRONICLES_DECK:_Spirit_Charmers_(All-Foil_Edition)",
    "Set_Card_Lists:Deck-Build_Pack:_Phantom_Revengers_(OCG-AE)",
    "Limit_Over_Collection:_The_Heroes",
    "Limit_Over_Collection:_The_Rivals",
    "Burst_Protocol",
    "Creation_Pack_11",
    "Set_Card_Lists:Blazing_Dominion_(OCG-AE)",
    "Set_Card_Lists:Blazing_Dominion_%2B1_Assist_Pack_(OCG-AE)",
    "Revolution Booster: Toon / Witchcrafter / Unchained",
    "Essential_Selection_02",
    "World_Premiere_Pack_2026"
]

# 日志函数
def log(message):
    if 'log_text' in globals():  # 检查 log_text 是否已定义
        log_text.insert(tk.END, message + "\n")
        log_text.see(tk.END)  # 自动滚动到底部
    else:
        print(message)  # 如果 log_text 未定义，则打印到控制台

# 清理文件名，移除Windows不支持的字符
def clean_filename(filename):
    # Windows文件名不支持的字符: < > : " | ? * / \
    invalid_chars = '<>:"|?*/\\'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    # 移除井号和其他可能有问题的字符
    filename = filename.replace('#', '_')
    return filename

# 稀有度縮寫（與店鋪實際使用一致）
RARITY_OPTION_COLUMNS = [
    "[N]", "[R]", "[SR]", "[UR]", "[SER]", "[PSER]", "[HR]", "[CR]",
    "[EXSER]", "[QCSR]", "[UL]"
]

CSV_BASE_COLUMNS = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Product Category", "Type", "Tags"
]

RARITY_MAP = {
    "Collector's Rare": "CR",
    "Extra Secret Rare": "EXSER",
    "Holographic Rare": "HR",
    "Normal": "N",
    "Common": "N",
    "Prismatic Secret Rare": "PSER",
    "Quarter Century Secret Rare": "QCSR",
    "Rare": "R",
    "Secret Rare": "SER",
    "Super Rare": "SR",
    "Ultimate Rare": "UL",
    "Ultra Rare": "UR",
}

def rarity_to_abbreviation(rarity):
    if not rarity:
        return rarity
    rarity_clean = rarity.strip()
    if rarity_clean in RARITY_MAP:
        return RARITY_MAP[rarity_clean]
    for key, abbr in RARITY_MAP.items():
        if key.lower() == rarity_clean.lower():
            return abbr
    return rarity_clean

def generate_rarity_option_columns(rarity_abbr):
    """在 Tags 後生成稀有度選項欄，匹配欄位標記 TRUE"""
    columns = {col: "" for col in RARITY_OPTION_COLUMNS}
    bracket_col = f"[{rarity_abbr}]"
    if bracket_col in columns:
        columns[bracket_col] = "TRUE"
    return columns

def extract_card_urls(series_url):
    global driver
    try:
        log(f"正在提取系列页面中的单品 URL: {series_url}")

        if not driver:
            if not init_driver():
                return []

        driver.get(series_url)
        log("頁面加載中，等待 Cloudflare 驗證...")
        time.sleep(8)  # 等待 Cloudflare 自動驗證

        # 等待表格元素出現
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            log("表格元素已加載，頁面加載成功")
        except TimeoutException:
            log("等待表格元素超時")
            return []

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        log("页面解析完成")

        card_data = []

        # 尝试找到所有表格
        all_tables = soup.find_all('table')
        log(f"页面中找到 {len(all_tables)} 个表格")

        # 列出所有表格的class属性
        for i, t in enumerate(all_tables):
            table_class = t.get('class', [])
            log(f"表格 {i}: class={table_class}")

        # 首先尝试找所有wikitable
        tables = soup.find_all('table', class_='wikitable')
        if not tables:
            log(f"未找到class='wikitable'的表格，尝试查找其他表格")
            # 尝试找所有表格
            tables = soup.find_all('table')
            if not tables:
                log(f"未找到任何表格: {series_url}")
                return []
            else:
                log(f"找到 {len(tables)} 个其他表格，继续处理")
        else:
            log(f"找到 {len(tables)} 个wikitable表格")

        # 只处理第1个有效的卡片列表表格
        processed_count = 0
        for table_index, table in enumerate(tables):
            # 只处理第1个表格
            if processed_count >= 1:
                break

            log(f"正在检查第 {table_index + 1} 个表格")

            # 检查表头，确认是否是卡片列表表格
            header_row = table.find('tr')
            if not header_row:
                log(f"表格 {table_index + 1} 没有表头，跳过")
                continue

            # 获取表头文本
            header_cells = header_row.find_all(['th', 'td'])
            header_texts = [cell.get_text().strip() for cell in header_cells]
            header_text_lower = ' '.join([text.lower() for text in header_texts])

            # 检查是否是卡片列表表格（必须包含 card number 和 rarity）
            if 'card number' not in header_text_lower or 'rarity' not in header_text_lower:
                log(f"表格 {table_index + 1} 不是卡片列表表格，跳过")
                continue

            log(f"表格 {table_index + 1} 是有效的卡片列表表格，开始处理")
            log(f"表头: {header_texts}")
            processed_count += 1

            # 建立列索引映射
            col_map = {}
            for i, header in enumerate(header_texts):
                header_lower = header.lower()
                if 'card number' in header_lower:
                    col_map['card_number'] = i
                elif 'name' in header_lower and 'japanese' not in header_lower and 'chinese' not in header_lower and 'localized' not in header_lower:
                    # 匹配 "Name" 或 "English name"，但排除 "Japanese name", "Chinese name", "Localized name"
                    col_map['name'] = i
                elif 'rarity' in header_lower:
                    col_map['rarity'] = i
                elif 'category' in header_lower:
                    col_map['category'] = i
                elif 'print' in header_lower:
                    col_map['print'] = i

            log(f"列索引映射: {col_map}")

            rows = table.find_all('tr')[1:]  # 跳过表头行
            log(f"表格 {table_index + 1} 中找到 {len(rows)} 行数据")

            for row in rows:
                cells = row.find_all('td')

                # 检查列数
                if len(cells) < len(col_map):
                    log(f"跳过行，列数不足: {len(cells)}")
                    continue

                # 提取 Card Number
                if 'card_number' not in col_map:
                    log(f"表格缺少 Card Number 列，跳过")
                    break

                card_number_cell = cells[col_map['card_number']].find('a')
                card_number = card_number_cell.text.strip() if card_number_cell else cells[col_map['card_number']].text.strip()

                # 检查是否是空行
                if not card_number or card_number.strip() == "":
                    log(f"跳过空行")
                    continue

                # 提取 Name 和 URL
                if 'name' not in col_map:
                    log(f"表格缺少 Name 列，跳过")
                    break

                name_cell = cells[col_map['name']]
                name_link = name_cell.find('a', href=True)
                full_name = name_cell.text.strip()
                # 移除引号
                full_name = full_name.replace('"', '').strip()
                name = name_link.text.strip() if name_link else full_name
                name = name.replace('"', '').strip()
                card_url = "https://yugipedia.com" + name_link['href'] if name_link else None

                # 提取异画信息
                alternate_art_pattern = r"\((.*?) artwork\)"
                match = re.search(alternate_art_pattern, full_name, re.IGNORECASE)
                artwork_type = match.group(1) if match else None
                is_alternate_art = bool(artwork_type)
                if is_alternate_art:
                    name = re.sub(alternate_art_pattern, "", name, flags=re.IGNORECASE).strip()

                # 提取 Rarity
                rarities = []
                if 'rarity' in col_map:
                    rarity_cell = cells[col_map['rarity']]
                    # 处理多个稀有度（用 <br/> 分隔）
                    rarity_links = rarity_cell.find_all('a')
                    if rarity_links:
                        rarities = [link.text.strip() for link in rarity_links]
                    else:
                        # 如果没有链接，直接获取文本并按换行符分割
                        rarity_text = rarity_cell.get_text(separator='|').strip()
                        rarities = [r.strip() for r in rarity_text.split('|') if r.strip()]

                if not rarities:
                    rarities = [""]

                # 提取 Category
                card_type = ""
                if 'category' in col_map:
                    category_cell = cells[col_map['category']]
                    card_type_links = category_cell.find_all('a')
                    card_type = " ".join([link.text.strip() for link in card_type_links]) if card_type_links else category_cell.text.strip()

                # 打印调试信息
                log(f"卡片: {name}, 稀有度: {rarities}, 卡片类型: {card_type}")

                # 为每个稀有度单独创建记录
                for rarity in rarities:
                    card_data.append({
                        'Card Number': card_number,
                        'Name': name,
                        'Japanese Name': None,  # 这个系列没有日文名
                        'Rarity': rarity,
                        'Category': card_type,
                        'URL': card_url,
                        'Is Alternate Art': is_alternate_art,
                        'Artwork Type': artwork_type
                    })

        log(f"找到 {len(card_data)} 个单品数据")
        return card_data
    except Exception as e:
        log(f"提取单品 URL 时发生错误: {e}")
        log(f"错误详情: {str(e)}")
        import traceback
        log(traceback.format_exc())
        return []

# 提取卡片详细信息
def extract_card_details(card_url):
    global driver
    try:
        # 添加随机延迟，避免请求过快
        time.sleep(random.uniform(0.5, 1.0))

        if not driver:
            if not init_driver():
                return {}

        driver.get(card_url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        details = {}

        # 提取卡片名称
        card_name_element = soup.select_one('.heading')
        if card_name_element:
            details['name'] = card_name_element.text.strip()

        # 提取卡片的详细信息
        table = soup.find('table', class_='innertable')
        if table:
            for row in table.find_all('tr'):
                header = row.find('th')
                if header:
                    key = header.text.strip()
                    value = row.find('td').text.strip()
                    details[key] = value

        # 确保稀有度字段存在
        if 'Rarity' not in details or not details['Rarity']:
            # 尝试从其他地方提取稀有度
            rarity_text = soup.select_one('th:-soup-contains("Rarity") + td')
            if rarity_text:
                details['Rarity'] = rarity_text.text.strip()

        # 提取效果文本
        effect_text = soup.find('div', class_='cardtablespanrow')
        if effect_text:
            details['Effect'] = effect_text.text.strip()

        return details
    except Exception as e:
        log(f"提取卡片详细信息时发生错误: {e}")
        return {}

# 提取单卡描述
def extract_card_description(card_url):
    global driver
    try:
        # 添加随机延迟，避免请求过快
        time.sleep(random.uniform(0.5, 1.0))

        if not driver:
            if not init_driver():
                return None

        driver.get(card_url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 提取单卡描述
        lore_div = soup.find('div', class_='lore')
        if lore_div:
            return lore_div.text.strip()
        return None
    except Exception as e:
        log(f"提取单卡描述时发生错误: {e}")
        return None

def extract_card_prices(card_url):
    global driver
    try:
        # 添加随机延迟，避免请求过快
        time.sleep(random.uniform(0.5, 1.0))

        log(f"正在提取价格信息: {card_url}")

        if not driver:
            if not init_driver():
                return None

        driver.get(card_url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 提取价格表格
        price_table = soup.find('table', class_='wikitable plainlinks tcgplayer__data')
        if not price_table:
            log(f"未找到价格表格: {card_url}")
            return None

        prices = {}
        rows = price_table.find_all('tr')[1:]  # 跳过表头
        log(f"找到 {len(rows)} 行价格数据")

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                log(f"跳过不完整的行: {row}")
                continue

            # 提取版本
            edition = row.find('th').text.strip()

            # 提取价格信息（从 <a> 标签中获取文本）
            low_price = cells[0].find('a').text.strip() if cells[0].find('a') else "N/A"
            mid_price = cells[1].find('a').text.strip() if cells[1].find('a') else "N/A"
            high_price = cells[2].find('a').text.strip() if cells[2].find('a') else "N/A"

            log(f"提取到价格信息 - 版本: {edition}, 低价: {low_price}, 中价: {mid_price}, 高价: {high_price}")
            prices[edition] = {
                'Low': low_price,
                'Medium': mid_price,
                'High': high_price
            }

        log(f"成功提取价格信息: {prices}")
        return prices
    except Exception as e:
        log(f"提取价格信息时发生错误: {e}")
        return None


def process_card(card):
    try:
        log(f"處理卡片: {card['Name']}")

        # 如果 Card Number 不存在，跳過
        if not card['Card Number'] or card['Card Number'].strip() == "":
            log(f"跳過無編號的卡片: {card['Name']}")
            return None, None

        # 如果卡片名称为空，跳过（这是空行）
        if not card['Name'] or card['Name'].strip() == "":
            log(f"跳過空行卡片: {card['Card Number']}")
            return None, None

        # 提取卡片詳細信息
        card['Details'] = extract_card_details(card['URL'])

        # 提取單卡描述
        description = extract_card_description(card['URL'])

        # 获取是否为异画及其类型
        is_alternate_art = card.get('Is Alternate Art', False)
        artwork_type = card.get('Artwork Type', None)

        # 去掉卡片名稱中的雙引號
        card_name = card['Name'].replace('"', '')

        # 处理稀有度（可能包含多个稀有度，用换行符分隔）
        rarities = [card['Rarity']] if isinstance(card['Rarity'], str) else card['Rarity']
        rarities = [rarity.strip() for rarity in rarities if rarity.strip()]

        # 如果没有稀有度，使用空字符串作为默认值
        if not rarities:
            rarities = [""]

        # 初始化返回值
        results = []
        prices_data = []

        # 去重集合
        seen_handles = set()

        for rarity in rarities:
            # 稀有度缩写
            rarity_abbreviation = rarity_to_abbreviation(rarity)
            
            log(f"卡片: {card_name}, 使用稀有度: {rarity} -> {rarity_abbreviation}")

            # 格式化 Body (HTML)
            body_parts = [
                f"{card_name} {'(' + artwork_type + ' Artwork)' if is_alternate_art else ''}".strip(),
                f"Card Number: {card['Card Number']}",
                f"Card Type: {card['Category']}",  # 使用卡片类型
                f"Rarity: {rarity_abbreviation}",  # 使用稀有度缩写
                f"Attribute: {card['Details'].get('Attribute', '')}",
            ]

            # 處理 ATK 和 DEF
            if 'ATK / DEF' in card['Details']:
                atk_def = card['Details']['ATK / DEF'].strip()
                if atk_def:
                    atk, def_ = atk_def.split(' / ')
                    body_parts.append(f"ATK: {atk}")
                    body_parts.append(f"DEF: {def_}")

            # 添加描述
            if description:
                body_parts.append(f"Description: {description}")

            # 用換行符分隔每個部分
            body_html = "\n".join(body_parts)

            # 生成 Handle
            handle = f"{card['Card Number']} ({rarity_abbreviation})"
            if is_alternate_art and artwork_type:
                handle += f" ({artwork_type} Artwork)"

            # 检查是否重复
            if handle in seen_handles:
                continue
            seen_handles.add(handle)

            # 生成 Title
            title = f"{card['Card Number']} {card_name} ({rarity_abbreviation})"
            if is_alternate_art and artwork_type:
                title += f" ({artwork_type} Artwork)"

            # 提取價格信息 - 根据全局设置决定是否提取
            if enable_price_extraction:
                prices = extract_card_prices(card['URL'])
                if prices:
                    for edition, price_info in prices.items():
                        prices_data.append({
                            'Card Number': handle,
                            'Edition': edition,
                            'Low': price_info['Low'],
                            'Medium': price_info['Medium'],
                            'High': price_info['High']
                        })

            # 添加结果
            result = {
                'Handle': handle,
                'Title': title,
                'Body (HTML)': body_html,
                'Vendor': "Konami",
                'Product Category': "",
                'Type': "Cards",
                'Tags': generate_tags(card)
            }
            result.update(generate_rarity_option_columns(rarity_abbreviation))
            results.append(result)

        return results, prices_data
    except Exception as e:
        log(f"處理卡片時發生錯誤: {e}")
        log(f"错误详情: {str(e)}")
        import traceback
        log(traceback.format_exc())
        return None, None


# 生成标签
def generate_tags(card):
    tags = ["YGO"]

    # 处理 Category (卡片类型)
    if 'Category' in card and card['Category']:
        category_cleaned = re.sub(r'<.*?>', '', card['Category'])  # 清除任何HTML标签
        # 直接把所有斜杠替换成逗号，然后按逗号和空格分割
        category_cleaned = category_cleaned.replace('/', ', ')
        categories = [c.strip() for c in category_cleaned.replace(',', ' ').split() if c.strip()]

        for cat in categories:
            if cat in ["Effect", "Monster"]:
                if "Monster" not in tags:
                    tags.append("Monster")
            elif cat not in ["Card", "a", "an", "the", ""]:  # 排除常见无意义词和空字符串
                tags.append(cat)

    # 处理 Level/Rank
    if 'Details' in card and 'Level' in card['Details'] and card['Details']['Level'] not in ["N/A", ""]:
        level_text = card['Details']['Level'].replace("★", "").strip()  # 移除星星符号
        if level_text.isdigit():
            tags.append(f"LV{level_text}")

    # 处理 Types
    if 'Details' in card and 'Types' in card['Details'] and card['Details']['Types'] not in ["N/A", ""]:
        types = card['Details']['Types'].split(' / ')
        for type_name in types:
            type_name = type_name.strip()
            if type_name and type_name not in tags:
                tags.append(type_name)

    # 处理 Rarity (真实的稀有度)
    if 'Rarity' in card and card['Rarity'] not in ["N/A", ""]:
        rarity_abbr = rarity_to_abbreviation(card['Rarity'])
        if rarity_abbr not in tags:
            tags.append(rarity_abbr)

    # 处理 Attribute
    if 'Details' in card and 'Attribute' in card['Details'] and card['Details']['Attribute'] not in ["N/A", ""]:
        attribute = card['Details']['Attribute'].strip()
        if attribute and attribute not in tags:
            tags.append(attribute)

    # 处理 ATK 和 DEF
    if 'Details' in card and 'ATK / DEF' in card['Details']:
        atk_def = card['Details']['ATK / DEF'].strip()
        if atk_def and ' / ' in atk_def:
            try:
                atk, def_ = atk_def.split(' / ')
                tags.append(f"ATK{atk.strip()}, DEF{def_.strip()}")
            except ValueError:
                # 如果分割失败，使用原始值
                if atk_def not in ["", "N/A"]:
                    tags.append(f"STATS:{atk_def}")

    # 最终处理：把所有残留的斜杠替换成逗号
    result = ", ".join(tags)
    result = result.replace('/', ', ')
    return result

# 修改后的 download_series 函数
def download_series(series_name):
    log(f"开始下载系列: {series_name}...")

    data_found = []
    price_data = []

    # 访问系列页面
    series_url = base_url + series_name
    card_data = extract_card_urls(series_url)

    # 使用多线程处理每个卡片 - 降低并发数以避免429错误
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_card, card) for card in card_data]
        for future in concurrent.futures.as_completed(futures):
            try:
                results, prices = future.result()
                if results:
                    data_found.extend(results)  # 添加所有结果
                if prices:
                    price_data.extend(prices)  # 添加所有价格数据
            except Exception as e:
                log(f"处理卡片时发生错误: {e}")

    # 按 Card Number 排序
    if data_found:
        data_found.sort(key=lambda x: x['Handle'])

        # 创建 DataFrame
        df = pd.DataFrame(data_found)
        df = df.reindex(columns=CSV_BASE_COLUMNS + RARITY_OPTION_COLUMNS)
        # 清理文件名，移除Windows不支持的字符
        clean_series_name = clean_filename(series_name)
        filename = f"{clean_series_name}_preview.csv"
        csv_path = os.path.join(csv_dir, filename)
        df.to_csv(csv_path, index=False)
        log(f"数据已保存到: {csv_path}")

    # 保存价格信息
    if price_data:
        price_df = pd.DataFrame(price_data)
        # 清理文件名，移除Windows不支持的字符
        clean_series_name = clean_filename(series_name)
        price_filename = f"{clean_series_name}_Price.csv"
        price_csv_path = os.path.join(csv_dir, price_filename)
        price_df.to_csv(price_csv_path, index=False)
        log(f"价格信息已保存到: {price_csv_path}")
    else:
        log(f"系列 {series_name} 无价格信息")

    log(f"系列 {series_name} 下载完成。")


# 下载选中的系列
def start_download():
    if not selected_series:
        messagebox.showwarning("警告", "请先选择要下载的系列！")
        return

    # 禁用交互
    for widget in left_frame.winfo_children():
        if isinstance(widget, ttk.Checkbutton):
            widget.configure(state=tk.DISABLED)
    download_button.configure(state=tk.DISABLED)

    # 使用多线程下载
    download_thread = threading.Thread(target=download_selected_series)
    download_thread.start()

# 下载选中的系列卡片价格
def download_selected_prices():
    if not selected_series:
        messagebox.showwarning("警告", "请先选择要下载的系列！")
        return

    # 禁用交互
    for widget in left_frame.winfo_children():
        if isinstance(widget, ttk.Checkbutton):
            widget.configure(state=tk.DISABLED)
    price_button.configure(state=tk.DISABLED)

    # 使用多线程下载价格
    price_thread = threading.Thread(target=process_selected_prices)
    price_thread.start()

# 处理选中的系列卡片价格
def process_selected_prices():
    for series_name in selected_series:
        log(f"开始下载系列 {series_name} 的卡片价格...")
        series_url = base_url + series_name
        card_data = extract_card_urls(series_url)

        # 提取每张卡片的价格并保存
        price_data = []
        for card in card_data:
            prices = extract_card_prices(card['URL'])
            if prices:
                for edition, price_info in prices.items():
                    price_data.append({
                        'Card Number': card['Card Number'],
                        'Name': card['Name'],
                        'Edition': edition,
                        'Low': price_info['Low'],
                        'Medium': price_info['Medium'],
                        'High': price_info['High']
                    })

        # 保存价格信息
        if price_data:
            price_df = pd.DataFrame(price_data)
            # 清理文件名，移除Windows不支持的字符
            clean_series_name = clean_filename(series_name)
            price_filename = f"{clean_series_name}_Price.csv"
            price_csv_path = os.path.join(csv_dir, price_filename)
            price_df.to_csv(price_csv_path, index=False)
            log(f"价格信息已保存到: {price_csv_path}")
        else:
            log(f"系列 {series_name} 无价格信息")

    # 启用交互
    for widget in left_frame.winfo_children():
        if isinstance(widget, ttk.Checkbutton):
            widget.configure(state=tk.NORMAL)
    price_button.configure(state=tk.NORMAL)

    log("卡片价格下载完成。")


# 下载全部系列
def download_all():
    confirm = messagebox.askyesno("确认", "确定要下载全部系列吗？这将消耗较长时间。")
    if confirm:
        # 禁用交互
        for widget in left_frame.winfo_children():
            if isinstance(widget, ttk.Checkbutton):
                widget.configure(state=tk.DISABLED)
        download_button.configure(state=tk.DISABLED)

        # 使用多线程下载
        download_thread = threading.Thread(target=download_all_series)
        download_thread.start()

# 下载选中的系列（多线程）
def download_selected_series():
    for series_name in selected_series:
        download_series(series_name)

    # 启用交互
    for widget in left_frame.winfo_children():
        if isinstance(widget, ttk.Checkbutton):
            widget.configure(state=tk.NORMAL)
    download_button.configure(state=tk.NORMAL)

# 下载全部系列（多线程）
def download_all_series():
    for series_name in SERIES_LIST:
        download_series(series_name)

    # 启用交互
    for widget in left_frame.winfo_children():
        if isinstance(widget, ttk.Checkbutton):
            widget.configure(state=tk.NORMAL)
    download_button.configure(state=tk.NORMAL)

# 切换价格提取功能
def toggle_price_extraction():
    global enable_price_extraction
    enable_price_extraction = not enable_price_extraction
    status = "启用" if enable_price_extraction else "禁用"
    log(f"价格提取功能已{status}")

# 选择系列
def select_series(series_name, var):
    if var.get() == 1:
        selected_series.append(series_name)
    else:
        selected_series.remove(series_name)

# 创建 GUI 窗口
def create_gui():
    global log_text, left_frame, download_button, price_button  # 声明 price_button 为全局变量

    root = tk.Tk()
    root.title("Yugipedia 卡片下载器")
    root.geometry("800x600")

    # 左侧框架（选择系列）
    left_frame = tk.Frame(root)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

    # 添加滚动条
    canvas = tk.Canvas(left_frame)
    scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # 添加系列选择按钮
    for series_name in SERIES_LIST:
        var = tk.IntVar()
        check_button = ttk.Checkbutton(scrollable_frame, text=series_name, variable=var,
                                       command=lambda name=series_name, v=var: select_series(name, v))
        check_button.pack(anchor=tk.W)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # 右侧框架（日志和按钮）
    right_frame = tk.Frame(root)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 日志框
    log_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, width=60, height=25)
    log_text.pack(fill=tk.BOTH, expand=True)

    # 初始化日志
    log("初始化日志：")

    # 显示当前价格提取状态
    status = "启用" if enable_price_extraction else "禁用"
    log(f"价格提取功能当前状态: {status}")
    log("提示: 禁用价格提取可以大幅加快处理速度")

    # 下载按钮
    button_frame = tk.Frame(right_frame)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

    download_button = ttk.Button(button_frame, text="下载选中系列", command=start_download)
    download_button.pack(side=tk.LEFT, padx=5)

    all_button = ttk.Button(button_frame, text="下载全部系列", command=download_all)
    all_button.pack(side=tk.LEFT, padx=5)

    # 下载价格按钮
    price_button = ttk.Button(button_frame, text="下载选中系列价格", command=download_selected_prices)
    price_button.pack(side=tk.LEFT, padx=5)

    # 价格提取切换按钮
    price_toggle_button = ttk.Button(button_frame, text="切换价格提取", command=toggle_price_extraction)
    price_toggle_button.pack(side=tk.LEFT, padx=5)

    # 更新Cookie按钮
    # 测试连接按钮
    def test_connection_gui():
        threading.Thread(target=test_connection).start()

    test_button = ttk.Button(button_frame, text="测试连接", command=test_connection_gui)
    test_button.pack(side=tk.LEFT, padx=5)

    # 窗口关闭时清理瀏覽器
    def on_closing():
        close_driver()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


# 启动 GUI
if __name__ == "__main__":
    create_gui()