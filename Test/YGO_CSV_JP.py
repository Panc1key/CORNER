import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
import os
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import threading
from datetime import datetime
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import concurrent.futures
import random
import cloudscraper  # 用於繞過 Cloudflare

# 創建 cloudscraper 會話對象
scraper = cloudscraper.create_scraper()

# 設置請求頭
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://yugioh.fandom.com/"
}

# 基 URL
base_url = "https://yugioh.fandom.com"

# CSV 保存目錄
csv_dir = os.path.join(os.path.expanduser("~"), "Desktop", "YugiohCardGameList")
if not os.path.exists(csv_dir):
    os.makedirs(csv_dir)  # 如果目錄不存在，則創建

# 全局變量
selected_series = []

# 系列列表
SERIES_LIST = [
    "Duelist's Advance",
    "Duelist_Advance_%2B1_Assist_Pack",
    "Ultimate_Special_Pack",
    "Tactical-Try_Deck:_Exorcist_Angels_Exosister",
    "Tactical-Try_Deck:_Super_Exo-Armored_Force_Rescue-ACE",
    "Limited_Pack:_Stamp_Edition",
    "Doom_of_Dimensions_%2B1_Assist_Pack",
    "Limit_Over_Collection:_The_Heroes",
    "Limit_Over_Collection:_The_Rivals"
]

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
    try:
        log(f"正在提取系列頁面中的單品 URL: {series_url}")
        scraper.headers.update(headers)
        response = scraper.get(series_url, timeout=15)
        log(f"請求完成，狀態碼: {response.status_code}")
        if response.status_code != 200:
            log(f"網頁出錯，返回值: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        log("頁面解析完成")

        card_data = []

        # 找所有表格行 <tr>，檢查是否包含卡片數據
        # HTML 結構: <tr><td>卡號</td><td>"英文名"</td><td>「日文名」</td><td>稀有度</td><td>類型</td><td>印刷狀態</td></tr>
        all_rows = soup.find_all('tr')
        log(f"找到 {len(all_rows)} 行 tr 元素")

        for row in all_rows:
            cells = row.find_all('td')
            if len(cells) < 4:
                continue

            # 第一列應該是卡號（如 DOOD-JPS01）
            first_cell_text = cells[0].text.strip()
            # 檢查是否是卡號格式（字母+數字+連字符+字母+數字）
            if not re.match(r'^[A-Z0-9]+-[A-Z0-9]+$', first_cell_text):
                continue

            # 只獲取 JP 版本的卡片（卡號包含 JP）
            if 'JP' not in first_cell_text:
                continue

            card_number = first_cell_text

            # 第二列是英文名（帶鏈接）
            english_name_cell = cells[1]
            english_name = english_name_cell.text.strip().strip('"').strip('「').strip('」')

            # 第三列是日文名
            japanese_name = ""
            if len(cells) > 2:
                jp_cell = cells[2]
                japanese_name = jp_cell.text.strip().strip('「').strip('」')

            # 第四列是稀有度
            rarity = "Common"
            if len(cells) > 3:
                rarity = cells[3].text.strip()

            # 第五列是類型
            category = ""
            if len(cells) > 4:
                category = cells[4].text.strip()

            # 找到英文名列中的鏈接
            name_link = english_name_cell.find('a', href=True)
            card_url = None
            if name_link and name_link.get('href'):
                href = name_link['href']
                if href.startswith('/wiki/'):
                    card_url = base_url + href
                elif href.startswith('http'):
                    card_url = href

            card_data.append({
                'Card Number': card_number,
                'English Name': english_name,
                'Japanese Name': japanese_name,
                'Rarity': rarity,
                'Category': category,
                'URL': card_url
            })

        log(f"找到 {len(card_data)} 個單品數據")
        return card_data
    except requests.exceptions.Timeout:
        log(f"請求超時: {series_url}")
        return []
    except Exception as e:
        log(f"提取單品 URL 時發生錯誤: {e}")
        import traceback
        log(traceback.format_exc())
        return []

# 提取卡片詳細信息（從詳情頁面）
def extract_card_details(card_url):
    try:
        if not card_url:
            log(f"無效的卡片 URL: {card_url}")
            return {}

        # 添加隨機延遲，避免請求過快
        time.sleep(random.uniform(0.5, 1.5))

        scraper.headers.update(headers)
        response = scraper.get(card_url, timeout=15)
        if response.status_code == 403:
            log(f"遇到 403 錯誤，等待 10 秒後重試: {card_url}")
            time.sleep(10)
            response = scraper.get(card_url, timeout=15)
        if response.status_code != 200:
            log(f"網頁出錯，返回值: {response.status_code}")
            return {}

        soup = BeautifulSoup(response.text, 'html.parser')
        details = {}

        # Fandom Wiki 使用 aside 標籤存放卡片信息
        aside = soup.find('aside', class_='portable-infobox')
        if aside:
            # 提取所有數據項
            for item in aside.find_all('div', class_='pi-item'):
                label = item.find('h3', class_='pi-data-label')
                value = item.find('div', class_='pi-data-value')
                if label and value:
                    key = label.text.strip()
                    val = value.text.strip()
                    details[key] = val

        # 嘗試從頁面文本中提取信息
        page_text = soup.get_text()

        # 提取 ATK / DEF（格式: ATK / DEF 1000 / 1800）
        atk_def_match = re.search(r'ATK\s*/\s*DEF\s*[\n\s]*(\d+|\?)\s*/\s*(\d+|\?)', page_text)
        if atk_def_match:
            details['ATK'] = atk_def_match.group(1)
            details['DEF'] = atk_def_match.group(2)

        # 提取 Passcode
        passcode_match = re.search(r'Passcode\s*[\n\s]*(\d{8})', page_text)
        if passcode_match:
            details['Passcode'] = passcode_match.group(1)

        # 提取 Attribute（格式: Attribute DARK）
        attr_match = re.search(r'Attribute\s*[\n\s]*(DARK|LIGHT|WATER|FIRE|EARTH|WIND|DIVINE)', page_text, re.IGNORECASE)
        if attr_match:
            details['Attribute'] = attr_match.group(1).upper()

        # 提取 Types（格式: Types Dragon / Tuner / Effect）
        types_match = re.search(r'Types\s*[\n\s]*([A-Za-z\s/]+?)(?:Level|Rank|Link|ATK|$)', page_text)
        if types_match:
            types_val = types_match.group(1).strip()
            # 清理結尾的空格和斜線
            types_val = re.sub(r'\s*$', '', types_val)
            if types_val:
                details['Types'] = types_val

        # 提取 Level/Rank（格式: Level 3 CG Star...）
        level_match = re.search(r'(?:Level|Rank)\s*[\n\s]*(\d+)', page_text)
        if level_match:
            details['Level'] = level_match.group(1)

        # 提取 Link Rating（格式: Link-4）
        link_match = re.search(r'Link[- ](\d+)', page_text)
        if link_match:
            details['Link'] = link_match.group(1)

        # 記錄獲取到的詳情
        if details:
            log(f"獲取到詳情: ATK={details.get('ATK', 'N/A')}, DEF={details.get('DEF', 'N/A')}, Level={details.get('Level', 'N/A')}")
        else:
            log(f"未能獲取詳情: {card_url}")

        return details
    except Exception as e:
        log(f"提取卡片詳細信息時發生錯誤: {e}")
        import traceback
        log(traceback.format_exc())
        return {}

# 提取單卡描述（只提取英文描述）
def extract_card_description(card_url):
    try:
        if not card_url:
            return None

        # 注意：這個函數在 process_card 中被調用，但 extract_card_details 已經請求過頁面了
        # 為了避免重複請求，我們可以在 extract_card_details 中一起提取描述
        # 這裡保留函數但返回 None，讓 process_card 使用 Details 中的描述
        return None
    except Exception as e:
        log(f"提取單卡描述時發生錯誤: {e}")
        return None

# 處理單個卡片
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
        
        # 提取單卡描述（只提取英文描述）
        description = extract_card_description(card['URL'])
        
        # 只使用 English Name
        full_name = card["English Name"]
        
        # 格式化 Body (HTML)
        body_parts = [
            full_name,  # 只顯示英文名字
            f"Card Number: {card['Card Number']}",
            f"Card Type: {card['Category']}"  # 使用 Category 作为 Card Type
        ]
        
        # 添加 Level 或 Link
        if 'Level' in card['Details']:
            body_parts.append(f"Level: {card['Details']['Level']}")
        if 'Link' in card['Details']:
            body_parts.append(f"Link: {card['Details']['Link']}")

        # 添加 Rarity
        if 'Rarity' in card:
            body_parts.append(f"Rarity: {rarity_to_abbreviation(card['Rarity'])}")

        # 添加 Attribute
        if 'Attribute' in card['Details']:
            body_parts.append(f"Attribute: {card['Details']['Attribute']}")

        # 添加 Types
        if 'Types' in card['Details']:
            body_parts.append(f"Types: {card['Details']['Types']}")

        # 處理 ATK 和 DEF
        if 'ATK' in card['Details'] and 'DEF' in card['Details']:
            body_parts.append(f"ATK: {card['Details']['ATK']}")
            body_parts.append(f"DEF: {card['Details']['DEF']}")

        # 添加 Passcode
        if 'Passcode' in card['Details']:
            body_parts.append(f"Passcode: {card['Details']['Passcode']}")
        
        # 添加 Description（只添加英文描述）
        if description:
            body_parts.append(f"Description: {description}")
        
        # 用換行符分隔每個部分
        body_html = "\n".join(body_parts)
        
        # 生成 Handle（只包含当前稀有度）
        rarity_abbr = rarity_to_abbreviation(card['Rarity'])
        handle = f"{card['Card Number']} ({rarity_abbr})"
        
        # 生成 Title（卡號 + 名稱 + 稀有度）
        title = f"{card['Card Number']} {full_name} ({rarity_abbr})"
        
        # 生成 Tags
        tags = generate_tags(card)
        
        return {
            'Handle': handle,
            'Title': title,
            'Body (HTML)': body_html,
            'Vendor': "Konami",
            'Product Category': "",
            'Type': "Cards",
            'Tags': tags
        }
    except Exception as e:
        log(f"處理卡片時發生錯誤: {e}")
        return None

# 生成標籤
def generate_tags(card):
    tags = ["YGO"]
    if card['Category'] == "Effect Monster":
        tags.append("Monster")
    if 'Level' in card['Details'] and card['Details']['Level'] != "N/A":
        tags.append(f"LV{card['Details']['Level']}")
    if 'Types' in card['Details'] and card['Details']['Types'] != "N/A":
        types = card['Details']['Types'].split(' / ')
        tags.extend(types)
    if 'Rarity' in card and card['Rarity'] != "N/A":
        tags.append(rarity_to_abbreviation(card['Rarity']))
    if 'Attribute' in card['Details'] and card['Details']['Attribute'] != "N/A":
        tags.append(card['Details']['Attribute'])
    
    # 添加 ATK 和 DEF 到 Tags
    if 'ATK / DEF' in card['Details']:
        atk_def = card['Details']['ATK / DEF'].strip()
        if atk_def:
            atk, def_ = atk_def.split(' / ')
            tags.append(f"ATK{atk} DEF{def_}")
    
    return ", ".join(tags)

# 下載系列數據的函數
def download_series(series_name):
    log(f"開始下載系列: {series_name}...")
    data_found = []

    # 訪問系列頁面
    series_url = f"{base_url}/wiki/{series_name}"
    card_data = extract_card_urls(series_url)

    # 使用多線程處理每個卡片（減少線程數以避免 403）
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_card, card) for card in card_data]
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    data_found.append(result)
            except Exception as e:
                log(f"處理卡片時發生錯誤: {e}")

    # 按 Card Number 排序
    if data_found:
        data_found.sort(key=lambda x: x['Handle'])

        # 創建 DataFrame
        df = pd.DataFrame(data_found)
        
        # 處理文件名，移除所有非法字符
        safe_filename = series_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        filename = f"{safe_filename}_preview.csv"
        csv_path = os.path.join(csv_dir, filename)
        
        try:
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            log(f"數據已保存到: {csv_path}")
        except Exception as e:
            log(f"保存文件時發生錯誤: {e}")
            # 嘗試使用備用文件名
            backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_filename}_preview.csv"
            backup_path = os.path.join(csv_dir, backup_filename)
            try:
                df.to_csv(backup_path, index=False, encoding='utf-8-sig')
                log(f"數據已保存到備用文件: {backup_path}")
            except Exception as e2:
                log(f"保存備用文件時也發生錯誤: {e2}")

    log(f"系列 {series_name} 下載完成。")

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
    root.title("Yugioh 卡片下載器")
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