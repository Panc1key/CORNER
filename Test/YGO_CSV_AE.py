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
enable_price_extraction = False  # 控制是否提取价格信息

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
        log(f"连接测试失败: {e}")
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
    "Creation_Pack_07",
    "Set Card Lists:Alliance Insight (OCG-AE)",
    "Creation_Pack_09",
    "Set_Card_Lists:Doom_of_Dimensions_(OCG-AE)",
    "Doom of Dimensions Complement Pack",
    "Burst_Protocol",
    "Set_Card_Lists:Burst_Protocol_(OCG-AE)",
    "Burst_Protocol_Complement_Pack",
    "Burst_Protocol_%2B1_Assist_Pack",
    "Set_Card_Lists:Blazing_Dominion_(OCG-AE)",
    "Set_Card_Lists:Blazing_Dominion_%2B1_Assist_Pack_(OCG-AE)",
    "Blazing_Dominion_Complement_Pack"
]

# 日志函数
def log(message):
    if 'log_text' in globals():  # 检查 log_text 是否已定义
        log_text.insert(tk.END, message + "\n")
        log_text.see(tk.END)  # 自动滚动到底部
    else:
        print(message)  # 如果 log_text 未定义，则打印到控制台

# 将稀有度转换为首字母缩写
def rarity_to_abbreviation(rarity):
    rarity_map = {
        "Collector's Rare": "CR",
        "Extra Secret Rare": "EXSER",
        "Holographic Rare": "HR",
        "Normal": "N",
        "Quarter Century Secret Rare": "QCSER",
        "Rare": "R",
        "Secret Rare": "SER",
        "Super Rare": "SR",
        "Ultra Rare": "UR",
        "Ultimate Rare": "UL",
        "Common": "N",
        "Parallel Rare": "PR",
        "Gold Rare": "GR",
        "Prismatic Secret Rare": "PSER"
    }
    return rarity_map.get(rarity, rarity)  # 如果找不到对应的缩写，返回原值

def extract_card_urls(series_url):
    global driver
    try:
        log(f"正在提取系列页面中的单品 URL: {series_url}")

        if not driver:
            if not init_driver():
                return []

        # 使用 try-except 捕獲頁面加載超時
        try:
            driver.get(series_url)
            log("頁面加載中，等待 Cloudflare 驗證...")
            time.sleep(15)  # 增加等待時間，讓 Cloudflare 驗證完成
        except Exception as e:
            log(f"頁面加載失敗: {e}")
            log("嘗試繼續處理...")

        # 等待表格元素出現（增加等待時間和更靈活的策略）
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            log("表格元素已加載，頁面加載成功")
        except TimeoutException:
            log("等待表格元素超時，嘗試直接解析頁面內容...")
            # 即使超時也嘗試解析，可能頁面已部分加載
        except Exception as e:
            log(f"等待元素時發生錯誤: {e}")
            log("嘗試直接解析頁面內容...")

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        log("页面解析完成")

        # 保存HTML内容以便检查
        with open("page_content.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        log("已保存页面内容到page_content.html")
        
        # 查找所有标签页
        tabber_divs = soup.find_all('div', class_='tabber')
        log(f"找到 {len(tabber_divs)} 个标签容器")
        
        card_data = []
        
        # 方法1: 查找Asian-English标签页内容
        if len(tabber_divs) > 0:
            # 存在标签页，尝试查找Asian-English标签
            asian_english_tab = None
            for tabber in tabber_divs:
                tabs = tabber.find_all('div', class_='tabbertab')
                for tab in tabs:
                    title = tab.get('title', '')
                    log(f"找到标签页: {title}")
                    if 'Asian-English' in title:
                        asian_english_tab = tab
                        log(f"找到Asian-English标签页")
                        break
                if asian_english_tab:
                    break
            
            # 如果找到Asian-English标签页，尝试从中提取所有表格
            if asian_english_tab:
                # 首先檢查是否為 AJAX 動態加載的標籤頁
                ajax_tab = asian_english_tab.find('div', class_='set-list-ajax-tab')
                if ajax_tab:
                    # AJAX 標籤頁，表格應該已經在頁面中（由 JavaScript 加載）
                    log(f"檢測到 AJAX 標籤頁，直接在標籤頁中查找表格")
                    card_tables = ajax_tab.find_all('table', class_='wikitable')
                    if card_tables:
                        log(f"从 AJAX 標籤頁中找到 {len(card_tables)} 個表格")
                        for idx, card_table in enumerate(card_tables):
                            log(f"正在解析第 {idx + 1} 個表格")
                            table_data = parse_card_table(card_table)
                            if table_data:
                                card_data.extend(table_data)
                        if card_data:
                            log(f"從 AJAX 標籤頁總共獲取 {len(card_data)} 張卡片")
                            return card_data
                    else:
                        # 如果 AJAX 內容還未加載，嘗試從 data-page 屬性獲取頁面名稱並訪問
                        data_page = ajax_tab.get('data-page')
                        if data_page:
                            ae_url = f"https://yugipedia.com/wiki/{data_page.replace(' ', '_')}"
                            log(f"AJAX 內容未加載，訪問頁面: {ae_url}")

                            # 访问Asian-English页面
                            driver.get(ae_url)
                            time.sleep(random.uniform(2, 5))
                            ae_soup = BeautifulSoup(driver.page_source, 'html.parser')
                            card_tables = ae_soup.find_all('table', class_='wikitable')
                            if card_tables:
                                log(f"从Asian-English页面中找到 {len(card_tables)} 個表格")
                                for idx, card_table in enumerate(card_tables):
                                    log(f"正在解析第 {idx + 1} 個表格")
                                    table_data = parse_card_table(card_table)
                                    if table_data:
                                        card_data.extend(table_data)
                                if card_data:
                                    log(f"從頁面總共獲取 {len(card_data)} 張卡片")
                                    return card_data
                else:
                    # 非 AJAX 標籤頁，直接在標籤頁中查找表格
                    card_tables = asian_english_tab.find_all('table', class_='wikitable')
                    if card_tables:
                        log(f"从Asian-English标签页中找到 {len(card_tables)} 個表格")
                        for idx, card_table in enumerate(card_tables):
                            log(f"正在解析第 {idx + 1} 個表格")
                            table_data = parse_card_table(card_table)
                            if table_data:
                                card_data.extend(table_data)
                        if card_data:
                            log(f"從標籤頁總共獲取 {len(card_data)} 張卡片")
                            return card_data
                    else:
                        # 如果在标签页中没有找到表格，尝试查找其他链接
                        ae_link = asian_english_tab.find('a', href=True)
                        if ae_link:
                            ae_url = "https://yugipedia.com" + ae_link['href']
                            log(f"找到Asian-English链接: {ae_url}")

                            # 访问Asian-English页面
                            driver.get(ae_url)
                            time.sleep(random.uniform(2, 5))
                            ae_soup = BeautifulSoup(driver.page_source, 'html.parser')
                            card_tables = ae_soup.find_all('table', class_='wikitable')
                            if card_tables:
                                log(f"从Asian-English页面中找到 {len(card_tables)} 個表格")
                                for idx, card_table in enumerate(card_tables):
                                    log(f"正在解析第 {idx + 1} 個表格")
                                    table_data = parse_card_table(card_table)
                                    if table_data:
                                        card_data.extend(table_data)
                                if card_data:
                                    log(f"從鏈接頁面總共獲取 {len(card_data)} 張卡片")
                                    return card_data
        
        # 方法2: 尝试直接查找包含卡片数据的所有表格
        log("尝试在页面中直接查找卡片数据表格")
        tables = soup.find_all('table', class_='wikitable')
        if tables:
            valid_tables_count = 0
            for idx, table in enumerate(tables):
                th_elements = table.find_all('th')  # 使用th_elements而不是headers
                header_texts = [h.text.strip().lower() for h in th_elements if h.text.strip()]
                if (any('number' in t for t in header_texts) and
                    any('name' in t for t in header_texts) and
                    any('rarity' in t for t in header_texts)):
                    valid_tables_count += 1
                    log(f"找到第 {valid_tables_count} 個包含卡片数据的表格")
                    table_data = parse_card_table(table)
                    if table_data:
                        card_data.extend(table_data)
            if card_data:
                log(f"從 {valid_tables_count} 個表格總共獲取 {len(card_data)} 張卡片")
                return card_data
        
        # 方法3: 尝试在"Card List"部分查找所有表格
        card_list_heading = soup.find(lambda tag: tag.name in ['h2', 'h3'] and 'card list' in tag.text.lower())
        if card_list_heading:
            log("找到Card List部分")
            # 查找该标题下的所有表格
            tables_found = 0
            for tag in card_list_heading.find_next_siblings():
                if tag.name == 'table':
                    tables_found += 1
                    log(f"找到Card List第 {tables_found} 個表格")
                    table_data = parse_card_table(tag)
                    if table_data:
                        card_data.extend(table_data)
                elif tag.name in ['h2', 'h3']:
                    # 遇到下一個標題，停止查找
                    break

            if card_data:
                log(f"從Card List部分總共獲取 {len(card_data)} 張卡片")
                return card_data

        # 方法4: 尝试查找"Set Card Lists"页面链接
        set_card_link = soup.find('a', href=lambda h: h and 'Set_Card_Lists:' in h)
        if set_card_link:
            set_url = "https://yugipedia.com" + set_card_link['href']
            log(f"找到Set Card Lists链接: {set_url}")

            # 访问卡片列表页面
            driver.get(set_url)
            time.sleep(3)
            set_soup = BeautifulSoup(driver.page_source, 'html.parser')
            # 查找页面中的所有表格
            tables = set_soup.find_all('table', class_='wikitable')
            valid_tables = 0
            for table in tables:
                # 检查是否包含卡片编号的表格
                first_row = table.find('tr')
                if first_row and 'number' in ' '.join(th.text.strip().lower() for th in first_row.find_all('th')):
                    valid_tables += 1
                    log(f"在Set Card Lists页面找到第 {valid_tables} 個卡片表格")
                    table_data = parse_card_table(table)
                    if table_data:
                        card_data.extend(table_data)
            if card_data:
                log(f"從Set Card Lists頁面總共獲取 {len(card_data)} 張卡片")
                return card_data
        
        # 如果所有方法都失败，返回空列表
        log("无法找到卡片数据，返回空列表")
        return []
    except Exception as e:
        log(f"提取单品 URL 时发生错误: {e}")
        log(f"错误详情: {str(e)}")
        import traceback
        log(traceback.format_exc())
        return []

# 辅助函数：从表格解析卡片数据
def parse_card_table(card_table):
    try:
        rows = card_table.find_all('tr')
        log(f"表格中找到 {len(rows)} 行")
        
        if len(rows) <= 1:
            log("表格行数太少，可能不是卡片表格")
            return []
        
        # 检查第一行（表头）
        header_row = rows[0]
        table_headers = header_row.find_all('th')
        
        # 确定列索引
        headers_text = [th.text.strip().lower() for th in table_headers]
        log(f"表头: {headers_text}")
        
        card_number_idx = next((i for i, h in enumerate(headers_text) if 'number' in h), 0)
        name_idx = next((i for i, h in enumerate(headers_text) if 'name' in h), 1)
        rarity_idx = next((i for i, h in enumerate(headers_text) if 'rarity' in h), 2)
        category_idx = next((i for i, h in enumerate(headers_text) if 'category' in h or 'type' in h), 3)
        
        log(f"列索引 - 卡号: {card_number_idx}, 名称: {name_idx}, 稀有度: {rarity_idx}, 类型: {category_idx}")

        card_data = []
        data_rows = rows[1:]  # 跳过表头行

        for row in data_rows:
            cells = row.find_all('td')
            if len(cells) <= max(card_number_idx, name_idx, rarity_idx, category_idx):
                log(f"跳过行，列数不足: {len(cells)}")
                continue

            # 提取 Card Number
            card_number_cell = cells[card_number_idx].find('a')
            card_number = card_number_cell.text.strip() if card_number_cell else cells[card_number_idx].text.strip()
            
            # 检查是否是空行（没有卡号或名称的行）或者卡号为空
            if not card_number or not cells[name_idx].text.strip():
                log(f"跳过行: {card_number}")
                continue

            # 提取 Name 和 URL
            name_cell = cells[name_idx]
            name_link = name_cell.find('a', href=True)
            full_name = name_cell.text.strip()
            name = name_link.text.strip() if name_link else full_name
            card_url = "https://yugipedia.com" + name_link['href'] if name_link else None

            # 提取异画信息
            alternate_art_pattern = r"\((.*?) artwork\)"
            match = re.search(alternate_art_pattern, full_name, re.IGNORECASE)
            artwork_type = match.group(1) if match else None
            is_alternate_art = bool(artwork_type)
            if is_alternate_art:
                name = re.sub(alternate_art_pattern, "", name, flags=re.IGNORECASE).strip()

            # 提取 Rarity (稀有度)
            rarity_cell = cells[rarity_idx] if rarity_idx < len(cells) else None
            rarities = []
            if rarity_cell:
                # 处理多个稀有度的情况（用<br>分隔）
                for br in rarity_cell.find_all('br'):
                    br.replace_with('\n')  # 将<br>替换为换行符
                rarity_text = rarity_cell.text.strip()
                rarities = [r.strip() for r in rarity_text.split('\n') if r.strip()]
            if not rarities:
                rarities = ["Common"]  # 默认使用Common

            # 提取 Card Type (卡片类型)
            card_type = cells[category_idx].text.strip() if category_idx < len(cells) else "Unknown"

            # 为每个稀有度单独创建记录
            for rarity in rarities:
                card_data.append({
                    'Card Number': card_number,
                    'Name': name,
                    'Japanese Name': "",  # 这个表格中没有日文名
                    'Rarity': rarity,  # 这是稀有度
                    'Category': card_type,  # 这是卡片类型
                    'URL': card_url,
                    'Is Alternate Art': is_alternate_art,
                    'Artwork Type': artwork_type
                })

        log(f"找到 {len(card_data)} 个单品数据")
        return card_data
    except Exception as e:
        log(f"解析卡片表格时发生错误: {e}")
        return []

# 提取卡片详细信息
def extract_card_details(card_url):
    global driver
    try:
        # 添加随机延迟，避免请求过快
        time.sleep(random.uniform(0.5, 1.5))

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
        
        # 查找包含卡片信息的表格
        inner_table = soup.find('table', class_='innertable')
        if inner_table:
            # 处理表格内容
            for row in inner_table.find_all('tr'):
                # 跳过描述行（有colspan属性的行）
                if row.find('td') and row.find('td').has_attr('colspan'):
                    continue
                    
                header = row.find('th')
                value_cell = row.find('td')
                if header and value_cell:
                    key = header.text.strip()
                    
                    # 对于Types和Effect types字段，特殊处理以保留分隔符
                    if 'types' in key.lower() or 'effect types' in key.lower():
                        # 提取类型并去重
                        type_elements = value_cell.find_all(['a', 'li'])
                        if type_elements:
                            types = [elem.text.strip() for elem in type_elements if elem.text.strip()]
                            # 去重
                            unique_types = []
                            for t in types:
                                if t not in unique_types:
                                    unique_types.append(t)
                            value = ' / '.join(unique_types)
                        else:
                            # 如果没有链接元素，尝试分析文本
                            text = value_cell.text.strip()
                            # 对于连在一起的类型，尝试用正则分割或添加分隔符
                            # 这里可以添加针对特定格式的处理逻辑
                            
                            # 如果有明显的大写字母分界点，按大写字母分割
                            if re.search(r'[a-z][A-Z]', text):
                                # 在小写字母后面跟大写字母的地方插入分隔符
                                value = re.sub(r'([a-z])([A-Z])', r'\1 / \2', text)
                            else:
                                value = text
                    else:
                        value = value_cell.text.strip()
                    
                    # 标准化键名
                    if 'card type' in key.lower():
                        details['Card Type'] = value
                    elif 'attribute' in key.lower():
                        details['Attribute'] = value
                    elif 'types' in key.lower() and 'effect' not in key.lower():
                        details['Types'] = value
                    elif 'effect types' in key.lower():
                        details['Effect Types'] = value
                    elif 'level' in key.lower():
                        # 提取数字部分
                        level_match = re.search(r'(\d+)', value)
                        if level_match:
                            details['Level'] = level_match.group(1)
                        else:
                            details['Level'] = value
                    elif 'atk / def' in key.lower():
                        # 分离ATK和DEF
                        atk_def_parts = value.split('/')
                        if len(atk_def_parts) == 2:
                            atk_match = re.search(r'(\d+)', atk_def_parts[0])
                            def_match = re.search(r'(\d+)', atk_def_parts[1])
                            if atk_match:
                                details['ATK'] = atk_match.group(1)
                            if def_match:
                                details['DEF'] = def_match.group(1)
                        else:
                            details['ATK / DEF'] = value
                    else:
                        # 其他信息保持原样
                        details[key] = value
            
            # 处理描述/lore
            for td in inner_table.find_all('td'):
                if td.has_attr('colspan'):
                    lore_div = td.find('div', class_='lore')
                    if lore_div:
                        # 处理HTML文本，保留适当的空格
                        for a in lore_div.find_all('a'):
                            if a.previous_sibling and not str(a.previous_sibling).endswith(' '):
                                a.insert_before(' ')
                            if a.next_sibling and not str(a.next_sibling).startswith(' '):
                                a.insert_after(' ')
                        
                        text = lore_div.get_text(separator=' ', strip=True)
                        text = re.sub(r'\s+', ' ', text)
                        details['Description'] = text
                        break
        
        # 如果没找到描述，尝试直接查找lore
        if 'Description' not in details:
            lore_div = soup.find('div', class_='lore')
            if lore_div:
                details['Description'] = lore_div.get_text(strip=True)
        
        return details
    except Exception as e:
        log(f"提取卡片详细信息时发生错误: {e}")
        return {}

# 提取单卡描述
def extract_card_description(card_url):
    global driver
    try:
        # 添加随机延迟，避免请求过快
        time.sleep(random.uniform(0.5, 1.5))

        if not driver:
            if not init_driver():
                return None

        driver.get(card_url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 查找lore div
        lore_div = soup.find('div', class_='lore')
        if lore_div:
            # 处理HTML文本，保留适当的空格
            # 在每个链接前后添加一个空格，后续会处理多余的空格
            for a in lore_div.find_all('a'):
                # 在链接前后添加空格（如果不是在句子开头或结尾）
                if a.previous_sibling and not str(a.previous_sibling).endswith(' '):
                    a.insert_before(' ')
                if a.next_sibling and not str(a.next_sibling).startswith(' '):
                    a.insert_after(' ')
            
            # 获取文本，保留所有空格
            text = lore_div.get_text(separator=' ', strip=True)
            # 处理多余的空格
            text = re.sub(r'\s+', ' ', text)
            return text
        
        # 如果未找到，尝试找到包含lore div的td
        for td in soup.find_all('td'):
            if td.has_attr('colspan') and td['colspan'] == '2':
                lore_in_td = td.find('div', class_='lore')
                if lore_in_td:
                    # 处理同上
                    for a in lore_in_td.find_all('a'):
                        if a.previous_sibling and not str(a.previous_sibling).endswith(' '):
                            a.insert_before(' ')
                        if a.next_sibling and not str(a.next_sibling).startswith(' '):
                            a.insert_after(' ')
                    
                    text = lore_in_td.get_text(separator=' ', strip=True)
                    text = re.sub(r'\s+', ' ', text)
                    return text
        
        # 最后尝试查找cardtablespanrow
        cardtablespanrow = soup.find('div', class_='cardtablespanrow')
        if cardtablespanrow:
            # 处理同上
            for a in cardtablespanrow.find_all('a'):
                if a.previous_sibling and not str(a.previous_sibling).endswith(' '):
                    a.insert_before(' ')
                if a.next_sibling and not str(a.next_sibling).startswith(' '):
                    a.insert_after(' ')
                
            text = cardtablespanrow.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text)
            return text

        return None
    except Exception as e:
        log(f"提取单卡描述时发生错误: {e}")
        return None

def extract_card_prices(card_url):
    global driver
    try:
        # 添加随机延迟，避免请求过快
        time.sleep(random.uniform(0.5, 1.5))

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

        # 提取卡片詳細信息
        card['Details'] = extract_card_details(card['URL'])

        # 获取是否为异画及其类型
        is_alternate_art = card.get('Is Alternate Art', False)
        artwork_type = card.get('Artwork Type', None)

        # 去掉卡片名稱中的雙引號
        card_name = card['Name'].replace('"', '')

        # 处理稀有度（可能包含多个稀有度，用换行符分隔）
        rarities = [card['Rarity']] if isinstance(card['Rarity'], str) else card['Rarity']
        rarities = [rarity.strip() for rarity in rarities if rarity.strip()]

        # 初始化返回值
        results = []
        prices_data = []

        # 去重集合
        seen_handles = set()

        for rarity in rarities:
            # 稀有度缩写
            rarity_abbreviation = rarity_to_abbreviation(rarity)
            
            log(f"卡片: {card_name}, 使用稀有度: {rarity} -> {rarity_abbreviation}")

            # 以您期望的格式构建Body
            body_parts = [
                f"{card_name}" + (f" ({artwork_type} Artwork)" if is_alternate_art else ""),
                f"Card Number: {card['Card Number']}",
                f"Card Type: {card['Category']}",
            ]
            
            # 添加等级信息(如果存在)
            if 'Level' in card['Details']:
                body_parts.append(f"Level: {card['Details']['Level']}")
                
            # 添加稀有度信息
            body_parts.append(f"Rarity: {rarity_abbreviation}")
                
            # 添加属性信息
            if 'Attribute' in card['Details']:
                body_parts.append(f"Attribute: {card['Details']['Attribute']}")
                
            # 添加类型信息
            if 'Types' in card['Details']:
                body_parts.append(f"Types: {card['Details']['Types']}")

            # 添加效果类型信息(如果存在)
            if 'Effect Types' in card['Details']:
                body_parts.append(f"Effect Types: {card['Details']['Effect Types']}")

            # 添加ATK和DEF(如果存在)
            if 'ATK' in card['Details'] and 'DEF' in card['Details']:
                body_parts.append(f"ATK: {card['Details']['ATK']}")
                body_parts.append(f"DEF: {card['Details']['DEF']}")
            
            # 添加空行和描述(如果存在)
            if 'Description' in card['Details']:
                body_parts.append("")  # 添加空行
                body_parts.append(f"{card['Details']['Description']}")

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

            # 根据全局设置决定是否提取价格信息
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
            results.append({
                'Handle': handle,
                'Title': title,
                'Body (HTML)': body_html,
                'Vendor': "Konami",
                'Product Category': "",
                'Type': "Cards",
                'Tags': generate_tags(card)
            })

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

    # 添加卡片类型标签
    if 'Category' in card and card['Category']:
        category_cleaned = card['Category']
        # 直接把所有斜杠替換成逗號
        category_cleaned = category_cleaned.replace('/', ', ')

        if 'Monster' in category_cleaned:
            tags.append("Monster")

        # 先按空格分割，然後再按斜杠分割每個部分
        categories = []
        for part in category_cleaned.split():
            if '/' in part:
                # 如果包含斜杠，按斜杠分割
                categories.extend([c.strip() for c in part.split('/')])
            else:
                categories.append(part.strip())

        # 添加所有类型
        for cat in categories:
            if cat and cat not in tags:
                tags.append(cat)

    # 添加等级标签
    if 'Level' in card['Details'] and card['Details']['Level'] != "N/A":
        tags.append(f"LV{card['Details']['Level']}")

    # 添加类型标签
    if 'Types' in card['Details'] and card['Details']['Types'] != "N/A":
        types_text = card['Details']['Types']
        # 替换斜杠为逗号
        types_text = types_text.replace('/', ', ')
        types = [t.strip() for t in types_text.split(',') if t.strip()]
        tags.extend(types)

    # 添加稀有度标签
    if 'Rarity' in card and card['Rarity'] != "N/A":
        rarity_tag = rarity_to_abbreviation(card['Rarity'])
        tags.append(rarity_tag)

    # 添加属性标签
    if 'Attribute' in card['Details'] and card['Details']['Attribute'] != "N/A":
        tags.append(card['Details']['Attribute'])

    # 添加 ATK 和 DEF 到 Tags (用逗号分隔)
    if 'ATK' in card['Details'] and 'DEF' in card['Details']:
        atk = card['Details']['ATK']
        def_ = card['Details']['DEF']
        tags.append(f"ATK{atk}, DEF{def_}")
    elif 'ATK / DEF' in card['Details']:
        atk_def = card['Details']['ATK / DEF'].strip()
        if atk_def:
            parts = atk_def.split('/')
            if len(parts) == 2:
                atk = parts[0].strip()
                def_ = parts[1].strip()
                tags.append(f"ATK{atk}, DEF{def_}")

    # 去重并返回
    unique_tags = []
    for tag in tags:
        if tag and tag not in unique_tags:
            unique_tags.append(tag)

    # 最终处理：把所有残留的斜杠替换成逗号
    result = ", ".join(unique_tags)
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

    # 使用多线程处理每个卡片（减少线程数以降低服务器负载）
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
        # 替換 Windows 不允許的文件名字符: \ / : * ? " < > |
        safe_name = series_name.replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        filename = f"{safe_name}_preview.csv"
        csv_path = os.path.join(csv_dir, filename)
        df.to_csv(csv_path, index=False)
        log(f"数据已保存到: {csv_path}")

    # 跳过价格信息保存以加快处理速度
    # if price_data:
    #     price_df = pd.DataFrame(price_data)
    #     price_filename = f"{series_name.replace('/', '_')}_Price.csv"
    #     price_csv_path = os.path.join(csv_dir, price_filename)
    #     price_df.to_csv(price_csv_path, index=False)
    #     log(f"价格信息已保存到: {price_csv_path}")
    # else:
    #     log(f"系列 {series_name} 无价格信息")

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
            price_filename = f"{series_name.replace('/', '_')}_Price.csv"
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

# 选择系列
def select_series(series_name, var):
    if var.get() == 1:
        selected_series.append(series_name)
    else:
        selected_series.remove(series_name)

# 更新Cookie的GUI函数
def update_cookie_gui():
    """显示更新Cookie的对话框（已不再需要，因為使用瀏覽器）"""
    messagebox.showinfo("提示", "現在使用瀏覽器模式，不需要手動更新Cookie")

# 切换价格提取功能
def toggle_price_extraction():
    global enable_price_extraction
    enable_price_extraction = not enable_price_extraction
    status = "启用" if enable_price_extraction else "禁用"
    log(f"价格提取功能已{status}")

# 创建 GUI 窗口
def create_gui():
    global log_text, left_frame, download_button, price_button  # 声明 price_button 为全局变量

    root = tk.Tk()
    root.title("Yugipedia 卡片下载器 (Asian-English)")
    root.geometry("900x700")

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

    # 下载按钮
    button_frame = tk.Frame(right_frame)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

    download_button = ttk.Button(button_frame, text="下载选中系列", command=start_download)
    download_button.pack(side=tk.LEFT, padx=5)

    all_button = ttk.Button(button_frame, text="下载全部系列", command=download_all)
    all_button.pack(side=tk.LEFT, padx=5)

    # 价格功能已禁用以提高速度
    # price_button = ttk.Button(button_frame, text="下载选中系列价格", command=download_selected_prices)
    # price_button.pack(side=tk.LEFT, padx=5)

    # 测试连接按钮
    test_button = ttk.Button(button_frame, text="测试连接", command=test_connection)
    test_button.pack(side=tk.LEFT, padx=5)

    # 更新Cookie按钮
    cookie_button = ttk.Button(button_frame, text="更新Cookie", command=update_cookie_gui)
    cookie_button.pack(side=tk.LEFT, padx=5)

    # 价格提取切换按钮
    price_toggle_button = ttk.Button(button_frame, text="切换价格提取", command=toggle_price_extraction)
    price_toggle_button.pack(side=tk.LEFT, padx=5)

    # 显示当前价格提取状态
    status = "启用" if enable_price_extraction else "禁用"
    log(f"价格提取功能当前状态: {status}")

    # 窗口關閉時清理瀏覽器
    def on_closing():
        close_driver()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


# 启动 GUI
if __name__ == "__main__":
    create_gui()