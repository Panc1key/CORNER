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
import traceback
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# 全局浏览器对象
driver = None

# 基 URL
base_url = "https://yugioh.fandom.com"

# CSV 保存目錄
csv_dir = os.path.join(os.path.expanduser("~"), "Desktop", "YugiohCardGameList")
if not os.path.exists(csv_dir):
    os.makedirs(csv_dir)  # 如果目錄不存在，則創建

# 全局變量
selected_series = []

# 系列列表（亞洲英文版）
SERIES_LIST = [
    "Alliance_Insight-AE",
    "Duelist_of_Glorious_Arms-AE",
    "Structure_Deck:_Onslaught_of_Legends-AE",
    "Phantom_Pulse-AE",
    "Set Card Lists:Duelist's Advance (OCG-AE)",
    "The Fallen & The Virtuous",
    "THE_CHRONICLES_DECK:_Spirit_Charmers_(All-Foil_Edition)",
    "Limit_Over_Collection:_The_Rivals",
    "Chaos_Origins"
]

# 初始化浏览器（无头模式）
def init_driver():
    """初始化 undetected_chromedriver（无头模式）"""
    global driver
    try:
        log("正在初始化浏览器（无头模式）...")
        options = uc.ChromeOptions()

        # 无头模式配置
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-extensions')
        options.add_argument('--dns-prefetch-disable')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-infobars')

        # 指定 Chrome 版本為 148
        driver = uc.Chrome(options=options, version_main=148, headless=True, use_subprocess=False)

        # 設置超時時間，防止無限等待
        driver.set_page_load_timeout(300)  # 頁面加載超時：5分鐘
        driver.set_script_timeout(60)       # 腳本執行超時：1分鐘
        driver.implicitly_wait(10)          # 隱式等待：10秒

        log("浏览器初始化成功（无头模式）")
        return True
    except Exception as e:
        log(f"浏览器初始化失败: {e}")
        return False

# 关闭浏览器
def close_driver():
    """关闭浏览器"""
    global driver
    if driver:
        try:
            driver.quit()
            log("浏览器已关闭")
        except Exception as e:
            log(f"关闭浏览器时发生错误: {e}")
        driver = None

# 日誌函數
def log(message):
    if 'log_text' in globals():  # 檢查 log_text 是否已定義
        log_text.insert(tk.END, message + "\n")
        log_text.see(tk.END)  # 自動滾動到底部
    else:
        print(message)  # 如果 log_text 未定義，則打印到控制台

# 稀有度分割函數
def split_rarity(rarity_text):
    # 使用正則表達式分割稀有度
    # 匹配 "Super Rare", "Secret Rare", "Quarter Century Secret Rare" 等
    rarities = re.findall(r'[A-Z][a-zA-Z\s]* Rare', rarity_text)
    return [r.strip() for r in rarities] if rarities else [rarity_text.strip()]

def rarity_to_abbreviation(rarity):
    # 定義稀有度映射
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
        "Common": "N" 
    }
    
    # 如果稀有度包含多个值（用斜杠分隔），则分别转换
    if '/' in rarity:
        rarities = [r.strip() for r in rarity.split('/')]
        return ' '.join([rarity_map.get(r, r) for r in rarities])  # 用空格连接
    else:
        return rarity_map.get(rarity, rarity)

# 提取系列頁面中的單品信息
def extract_card_urls(series_url):
    global driver
    try:
        # 移除 URL 中的錨點（#xxx）
        clean_url = series_url.split('#')[0]
        log(f"正在提取系列頁面中的單品 URL: {clean_url}")

        # 初始化浏览器（如果还没有初始化）
        if driver is None:
            if not init_driver():
                log("浏览器初始化失败，无法继续")
                return []

        # 使用 Selenium 访问页面
        driver.get(clean_url)

        # 等待页面加载完成
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
        except TimeoutException:
            log("页面加载超时")

        time.sleep(1)  # 额外等待确保页面完全加载

        # 获取页面源代码
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        log("頁面解析完成")

        card_data = []
        
        # 尋找卡片列表表格
        table = soup.find('table', class_='wikitable') or soup.find('table', class_='card-list') or soup.find('table', class_='sortable')
        if not table:
            tables = soup.find_all('table')
            if tables:
                table = tables[0]
                log(f"使用第一个表格，class: {table.get('class', 'None')}")
        
        if not table:
            log(f"未找到任何表格: {series_url}")
            return []

        rows = table.find_all('tr')[1:]  # 跳過表頭行
        log(f"找到 {len(rows)} 行數據")

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 4:  # 確保有足夠的列
                continue

            try:
                # 提取 Card Number (在 span 內)
                card_number_span = cells[0].find('span')
                if card_number_span:
                    card_number = card_number_span.text.strip()
                else:
                    card_number = cells[0].text.strip()

                # 提取 English Name (在 a 標籤內)
                name_cell = cells[1]
                name_link = name_cell.find('a')
                if name_link:
                    english_name = name_link.text.strip().strip('"')
                    card_url = base_url + name_link['href']
                else:
                    english_name = name_cell.text.strip().strip('"')
                    card_url = None

                # 提取 Rarity (第3列)
                rarity_cell = cells[2]
                rarity_text = ""
                
                # 檢查是否有多個稀有度（用 <br> 分隔）
                rarity_links = rarity_cell.find_all('a')
                if rarity_links:
                    rarities = [link.text.strip() for link in rarity_links]
                    rarity_text = rarities[0] if rarities else ""  # 使用第一個稀有度
                else:
                    rarity_text = rarity_cell.text.strip()
                
                # 如果稀有度為空，設置為 "Common"
                if not rarity_text or rarity_text == "":
                    rarity_text = "Common"

                # 提取 Category (第4列 - 卡片類型)
                category_cell = cells[3]
                category_links = category_cell.find_all('a')
                if category_links:
                    card_type = ' '.join([link.text.strip() for link in category_links])
                else:
                    card_type = category_cell.text.strip()

                # 創建卡片數據
                card_data.append({
                    'Card Number': card_number,
                    'English Name': english_name,
                    'Japanese Name': "",  # AE版本沒有日文名
                    'Rarity': rarity_text,
                    'Category': card_type,
                    'URL': card_url
                })
                
                log(f"提取卡片: {card_number} - {english_name} - 稀有度: {rarity_text} - 類型: {card_type}")
                
            except Exception as e:
                log(f"處理行時發生錯誤: {e}")
                continue

        log(f"找到 {len(card_data)} 個單品數據")
        return card_data
    except Exception as e:
        log(f"提取單品 URL 時發生錯誤: {e}")
        return []

# 提取卡片詳細信息
def extract_card_details(card_url):
    global driver
    try:
        if not card_url:
            log(f"無效的卡片 URL: {card_url}")
            return {}

        # 使用全局 driver
        if driver is None:
            if not init_driver():
                return {}

        driver.get(card_url)
        time.sleep(1.5)  # 等待頁面加載

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        details = {}

        # 提取卡片的詳細信息 - 使用更通用的方式
        # 方法1: 查找 cardtablerow
        rows = soup.find_all('tr', class_='cardtablerow')

        # 方法2: 如果找不到，查找所有包含 th 和 td 的 tr
        if not rows:
            all_tables = soup.find_all('table')
            for table in all_tables:
                table_rows = table.find_all('tr')
                for row in table_rows:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        rows.append(row)

        for row in rows:
            header = row.find('th')
            data = row.find('td')

            if header and data:
                key = header.get_text(strip=True)
                value = data.get_text(strip=True)

                # 清理一些特殊字符和多余空格
                value = ' '.join(value.split())
                details[key] = value
                
                # 特別處理 ATK/DEF
                if 'ATK' in key and 'DEF' in key:
                    log(f"找到 ATK/DEF: {value}")
                    try:
                        # 直接從原始HTML中提取ATK和DEF的值
                        atk_def_links = data.find_all('a')
                        if len(atk_def_links) >= 2:  # 確保有足夠的鏈接（ATK和DEF）
                            details['ATK'] = atk_def_links[0].text.strip()
                            details['DEF'] = atk_def_links[1].text.strip()
                            log(f"從鏈接提取 ATK: {details['ATK']}, DEF: {details['DEF']}")
                        elif '/' in value:  # 備用方法：如果沒有鏈接，嘗試分割文本
                            atk, def_ = value.split('/')
                            details['ATK'] = atk.strip()
                            details['DEF'] = def_.strip()
                            log(f"從文本分離 ATK: {details['ATK']}, DEF: {details['DEF']}")
                    except Exception as e:
                        log(f"處理 ATK/DEF 時出錯: {e}")

        # 提取效果文本 - 從 Card descriptions 部分
        description_row = soup.find('td', class_='cardtablespanrow')
        if description_row:
            # 尋找英文效果描述
            english_table = description_row.find('table', class_='collapsible expanded navbox-inner')
            if english_table:
                effect_cell = english_table.find('td', class_='navbox-list')
                if effect_cell:
                    # 提取純文本，去除HTML標籤
                    effect_text = effect_cell.get_text(separator=' ', strip=True)
                    # 清理多余的空格和換行
                    effect_text = ' '.join(effect_text.split())
                    details['Description'] = effect_text

        return details
    except Exception as e:
        log(f"提取卡片詳細信息時發生錯誤: {e}")
        return {}

# 提取單卡描述
def extract_card_description(card_url):
    global driver
    try:
        if not card_url:
            log(f"無效的卡片 URL: {card_url}")
            return None

        # 使用全局 driver（與 extract_card_details 共用同一頁面）
        # 這裡不需要重新加載，因為 extract_card_details 已經加載過了
        if driver is None:
            return None

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 從 Card descriptions 部分提取英文描述
        description_row = soup.find('td', class_='cardtablespanrow')
        if description_row:
            # 尋找英文效果描述表格
            english_table = description_row.find('table', class_='collapsible expanded navbox-inner')
            if english_table:
                effect_cell = english_table.find('td', class_='navbox-list')
                if effect_cell:
                    # 提取純文本，去除HTML標籤
                    description = effect_cell.get_text(separator=' ', strip=True)
                    # 清理多余的空格和換行
                    description = ' '.join(description.split())
                    return description
            
        return None
    except Exception as e:
        log(f"提取單卡描述時發生錯誤: {e}")
        return None

# 處理單個卡片
def process_card(card):
    try:
        log(f"處理卡片: {card['English Name']}")
        
        # 如果 Card Number 不存在，跳過
        if not card.get('Card Number') or card['Card Number'].strip() == "":
            log(f"跳過無編號的卡片: {card['English Name']}")
            return None
        
        # 提取卡片詳細信息
        card['Details'] = extract_card_details(card['URL'])
        
        # 提取單卡描述
        description = extract_card_description(card['URL'])
        
        # 使用 English Name
        full_name = card["English Name"]
        
        # 格式化 Body (HTML)
        body_parts = [
            full_name,
            f"Card Number: {card['Card Number']}",
            f"Card Type: {card['Category']}"  # 這裡使用 Category 作為卡片類型
        ]
        
        # 添加 Level
        if 'Level' in card['Details']:
            body_parts.append(f"Level: {card['Details']['Level']}")
        
        # 添加 Attribute
        if 'Attribute' in card['Details']:
            body_parts.append(f"Attribute: {card['Details']['Attribute']}")
        
        # 添加 Types
        if 'Types' in card['Details']:
            body_parts.append(f"Types: {card['Details']['Types']}")
        
        # 添加 Rarity - 使用從表格中提取的真實稀有度
        if 'Rarity' in card and card['Rarity']:
            body_parts.append(f"Rarity: {rarity_to_abbreviation(card['Rarity'])}")
        
        # 處理 ATK 和 DEF - 優先使用單獨提取的值
        if 'ATK' in card['Details'] and 'DEF' in card['Details']:
            body_parts.append(f"ATK: {card['Details']['ATK']}")
            body_parts.append(f"DEF: {card['Details']['DEF']}")
        else:
            # 查找任何包含ATK和DEF的key
            atk_def_key = None
            for key in card['Details']:
                if 'ATK' in key and 'DEF' in key:
                    atk_def_key = key
                    break

            if atk_def_key:
                atk_def = card['Details'][atk_def_key].strip()
                if atk_def:
                    try:
                        if '/' in atk_def:
                            atk, def_ = atk_def.split('/')
                            body_parts.append(f"ATK: {atk.strip()}")
                            body_parts.append(f"DEF: {def_.strip()}")
                        else:
                            body_parts.append(f"ATK/DEF: {atk_def}")
                    except ValueError:
                        body_parts.append(f"ATK/DEF: {atk_def}")
        
        # 添加描述
        if description:
            body_parts.append(f"Description: {description}")
        
        # 用換行符分隔每個部分
        body_html = "\n".join(body_parts)
        
        # 生成 Handle - 使用真實的稀有度
        if 'Rarity' in card and card['Rarity']:
            rarity_abbr = rarity_to_abbreviation(card['Rarity'])
            handle = f"{card['Card Number']} ({rarity_abbr})"
        else:
            handle = f"{card['Card Number']}"
        
        # 生成 Title - 使用真實的稀有度
        if 'Rarity' in card and card['Rarity']:
            rarity_abbr = rarity_to_abbreviation(card['Rarity'])
            title = f'{full_name} ({rarity_abbr})'
        else:
            title = full_name
        
        # 生成 Tags
        tags = generate_tags(card)
        
        # 創建返回數據
        result = {
            'Handle': handle,
            'Title': title,
            'Body (HTML)': body_html,
            'Vendor': "Konami",
            'Product Category': "",
            'Type': "Cards",
            'Tags': tags
        }
        
        log(f"成功處理卡片: {card['English Name']}")
        return result
        
    except Exception as e:
        log(f"處理卡片時發生錯誤: {str(e)}")
        log(f"錯誤詳情: {traceback.format_exc()}")
        return None

# 生成標籤
def generate_tags(card):
    tags = ["YGO"]
    
    # 處理 Category (卡片類型)
    if 'Category' in card and card['Category']:
        category_cleaned = re.sub(r'<.*?>', '', card['Category'])  # 清除任何HTML標籤
        categories = category_cleaned.split()  # 分割可能的多個類型
        for cat in categories:
            if cat in ["Effect", "Monster"]:
                if "Monster" not in tags:
                    tags.append("Monster")
            elif cat not in ["Card", "a", "an", "the"]:  # 排除常見無意義詞
                tags.append(cat)
                
    # 處理 Level/Rank
    if 'Details' in card and 'Level' in card['Details'] and card['Details']['Level'] not in ["N/A", ""]:
        level_text = card['Details']['Level'].replace("★", "").strip()  # 移除星星符號
        if level_text.isdigit():
            tags.append(f"LV{level_text}")
    
    # 處理 Types
    if 'Details' in card and 'Types' in card['Details'] and card['Details']['Types'] not in ["N/A", ""]:
        types = card['Details']['Types'].split(' / ')
        for type_name in types:
            type_name = type_name.strip()
            if type_name and type_name not in tags:
                tags.append(type_name)
    
    # 處理 Rarity (真實的稀有度)
    if 'Rarity' in card and card['Rarity'] not in ["N/A", ""]:
        rarity_abbr = rarity_to_abbreviation(card['Rarity'])
        if rarity_abbr not in tags:
            tags.append(rarity_abbr)
    
    # 處理 Attribute
    if 'Details' in card and 'Attribute' in card['Details'] and card['Details']['Attribute'] not in ["N/A", ""]:
        attribute = card['Details']['Attribute'].strip()
        if attribute and attribute not in tags:
            tags.append(attribute)
    
    # 處理 ATK 和 DEF - 優先使用單獨提取的值
    if 'Details' in card:
        if 'ATK' in card['Details'] and 'DEF' in card['Details']:
            atk = card['Details']['ATK'].strip()
            def_ = card['Details']['DEF'].strip()
            if atk and def_:
                tags.append(f"ATK{atk} DEF{def_}")
        else:
            # 查找任何包含ATK和DEF的key
            atk_def_key = None
            for key in card['Details']:
                if 'ATK' in key and 'DEF' in key:
                    atk_def_key = key
                    break

            if atk_def_key:
                atk_def = card['Details'][atk_def_key].strip()
                if atk_def and '/' in atk_def:
                    try:
                        atk, def_ = atk_def.split('/')
                        tags.append(f"ATK{atk.strip()} DEF{def_.strip()}")
                    except ValueError:
                        # 如果分割失敗，使用原始值
                        if atk_def not in ["", "N/A"]:
                            tags.append(f"STATS:{atk_def}")
    
    return ", ".join(tags)

# 下載系列數據的函數
def download_series(series_name):
    log(f"開始下載系列: {series_name}...")
    data_found = []

    # 訪問系列頁面
    series_url = f"{base_url}/wiki/{series_name}"
    log(f"系列URL: {series_url}")
    
    card_data = extract_card_urls(series_url)
    
    if not card_data:
        log(f"未找到任何卡片數據")
        return

    log(f"開始處理 {len(card_data)} 張卡片")

    # 使用多線程處理每個卡片（降低並發數避免觸發反爬蟲）
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        futures = [executor.submit(process_card, card) for card in card_data]
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    data_found.append(result)
                    log(f"成功添加卡片數據: {result['Title']}")
            except Exception as e:
                log(f"處理卡片時發生錯誤: {e}")

    # 按 Card Number 排序
    if data_found:
        data_found.sort(key=lambda x: x['Handle'])

        # 創建 DataFrame
        df = pd.DataFrame(data_found)
        
        # 安全處理文件名（處理特殊字符）
        safe_name = series_name.replace('/', '_').replace(':', '_').replace(' ', '_')
        filename = f"{safe_name}_preview.csv"
        csv_path = os.path.join(csv_dir, filename)
        
        try:
            # 確保目錄存在
            if not os.path.exists(csv_dir):
                os.makedirs(csv_dir)
                log(f"創建目錄: {csv_dir}")
            
            # 保存為CSV文件，指定UTF-8編碼
            df.to_csv(csv_path, index=False, encoding='utf-8')
            
            # 驗證文件是否成功創建
            if os.path.exists(csv_path):
                file_size = os.path.getsize(csv_path)
                log(f"數據已保存到: {csv_path}")
                log(f"文件大小: {file_size} 字節")
                log(f"成功處理 {len(data_found)} 張卡片")
            else:
                log(f"錯誤：文件未能成功創建: {csv_path}")
        except Exception as e:
            log(f"保存CSV文件時發生錯誤: {str(e)}")
            log(f"錯誤詳情: {traceback.format_exc()}")
    else:
        log(f"未找到任何有效卡片數據")

    log(f"系列 {series_name} 下載完成。")
    close_driver()  # 關閉瀏覽器

# 下載選中的系列
def start_download():
    if not selected_series:
        messagebox.showwarning("警告", "請先選擇要下載的系列！")
        return

    # 禁用交互
    for widget in left_frame.winfo_children():
        if isinstance(widget, ttk.Checkbutton):
            widget.configure(state=tk.DISABLED)
    download_button.configure(state=tk.DISABLED)

    # 使用多線程下載
    download_thread = threading.Thread(target=download_selected_series)
    download_thread.start()

# 下載全部系列
def download_all():
    confirm = messagebox.askyesno("確認", "確定要下載全部系列嗎？這將消耗較長時間。")
    if confirm:
        # 禁用交互
        for widget in left_frame.winfo_children():
            if isinstance(widget, ttk.Checkbutton):
                widget.configure(state=tk.DISABLED)
        download_button.configure(state=tk.DISABLED)

        # 使用多線程下載
        download_thread = threading.Thread(target=download_all_series)
        download_thread.start()

# 下載選中的系列（多線程）
def download_selected_series():
    for series_name in selected_series:
        download_series(series_name)

    # 啟用交互
    for widget in left_frame.winfo_children():
        if isinstance(widget, ttk.Checkbutton):
            widget.configure(state=tk.NORMAL)
    download_button.configure(state=tk.NORMAL)

# 下載全部系列（多線程）
def download_all_series():
    for series_name in SERIES_LIST:
        download_series(series_name)

    # 啟用交互
    for widget in left_frame.winfo_children():
        if isinstance(widget, ttk.Checkbutton):
            widget.configure(state=tk.NORMAL)
    download_button.configure(state=tk.NORMAL)

# 選擇系列
def select_series(series_name, var):
    if var.get() == 1:
        selected_series.append(series_name)
    else:
        selected_series.remove(series_name)

# 創建 GUI 窗口
def create_gui():
    global log_text, left_frame, download_button

    root = tk.Tk()
    root.title("Yugioh 卡片下載器 - 亞洲英文版")
    root.geometry("800x600")

    # 左側框架（選擇系列）
    left_frame = tk.Frame(root)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

    # 添加滾動條
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

    # 添加系列選擇按鈕
    for series_name in SERIES_LIST:
        var = tk.IntVar()
        check_button = ttk.Checkbutton(scrollable_frame, text=series_name, variable=var,
                                       command=lambda name=series_name, v=var: select_series(name, v))
        check_button.pack(anchor=tk.W)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # 右側框架（日誌和按鈕）
    right_frame = tk.Frame(root)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 日誌框
    log_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, width=60, height=25)
    log_text.pack(fill=tk.BOTH, expand=True)

    # 初始化日誌

    log("初始化日誌：")

    # 下載按鈕
    button_frame = tk.Frame(right_frame)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

    download_button = ttk.Button(button_frame, text="下載選中系列", command=start_download)
    download_button.pack(side=tk.LEFT, padx=5)


    all_button = ttk.Button(button_frame, text="下載全部系列", command=download_all)
    all_button.pack(side=tk.LEFT, padx=5)

    # 運行主循環
    root.mainloop()

# 啟動 GUI
if __name__ == "__main__":
    create_gui()




