import os
import pandas as pd
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import urljoin
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import traceback
import concurrent.futures

# 全局瀏覽器對象
driver = None

# Battle Spirits Wiki 基礎 URL
base_url = "https://battle-spirits.fandom.com"

# CSV 保存目錄
csv_dir = os.path.join(os.path.expanduser("~"), "Desktop", "BattleSpiritsList")
if not os.path.exists(csv_dir):
    os.makedirs(csv_dir)

# 系列列表（可以根據需要添加）
# 格式：(系列代碼, 系列名稱)
SERIES_LIST = [

    ("26RCB01", "Collaboration 06"),
]

# 是否提取詳細信息（如效果文本）
# 使用 YGO 架構：1 個全局瀏覽器 + 2 個線程，簡單高效
FETCH_DETAILS = True

# 線程數（無頭模式可用 8-10，有頭模式建議 2-5）
NUM_THREADS = 5

# 是否使用無頭模式（True = 無頭模式節省資源，False = 有頭模式用於調試）
HEADLESS = False

def log(message):
    """日誌輸出函數"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

# Battle Spirits 稀有度縮寫（電商/CSV 用）
# Common=C, Uncommon=UC, Rare=R, Master Rare=MR
RARITY_MAP = {
    "10th X-Rare": "10X",
    "10th X Rare": "10X",
    "Mythic X-Rare": "MX",
    "Mythic X Rare": "MX",
    "Rebirth X-Rare": "RX",
    "Rebirth X Rare": "RX",
    "Rebirth Rare": "RR",
    "Master Rare": "MR",
    "XX-Rare": "XX",
    "XX Rare": "XX",
    "X-Rare": "X",
    "X Rare": "X",
    "Uncommon": "UC",
    "Common": "C",
    "Rare": "R",
    "Secret": "S",
    "Over Secret": "OS",
    "OVER SECRET": "OS",
    "Promo": "P",
    "Promotion": "P",
}

def rarity_to_abbreviation(rarity):
    """將稀有度全名轉為官方縮寫（Common -> C, Rare -> R）"""
    if not rarity:
        return rarity
    rarity_clean = rarity.strip()
    if rarity_clean in RARITY_MAP:
        return RARITY_MAP[rarity_clean]
    for key, abbr in RARITY_MAP.items():
        if key.lower() == rarity_clean.lower():
            return abbr
    return rarity_clean

def init_driver():
    """初始化 undetected_chromedriver（全局）- 仿照 YGO 的方式"""
    global driver
    try:
        mode_str = "無頭模式" if HEADLESS else "有頭模式"
        log(f"正在初始化瀏覽器（{mode_str}）...")
        options = uc.ChromeOptions()

        # 基本配置
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')

        # 隱藏自動化特徵（幫助無頭模式通過檢測）
        options.add_argument('--disable-automation')
        options.add_argument('--enable-automation=false')

        # 無頭模式特殊配置
        if HEADLESS:
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            # 無頭模式下強制啟用 JavaScript 渲染
            options.add_argument('--disable-features=TranslateUI')

        # 禁用圖片加載（加快頁面）
        options.add_argument('--blink-settings=imagesEnabled=false')

        # 指定 Chrome 版本為 148
        driver = uc.Chrome(options=options, version_main=148, headless=HEADLESS, use_subprocess=False)

        # 設置超時
        driver.set_page_load_timeout(300)
        driver.set_script_timeout(60)
        driver.implicitly_wait(10)

        log("瀏覽器初始化成功")
        return True
    except Exception as e:
        log(f"瀏覽器初始化失敗: {e}")
        return False

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

def extract_card_list(set_url):
    """從系列頁面提取卡片列表"""
    global driver
    try:
        log(f"正在提取卡片列表: {set_url}")

        if not driver:
            if not init_driver():
                return []

        driver.get(set_url)
        log("頁面加載中，等待表格加載...")
        time.sleep(8)  # Battle Spirits Wiki 需要較長時間加載 JavaScript

        # 等待表格出現
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            log("表格已加載")
        except TimeoutException:
            log("等待表格超時")
            return []

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        card_list = []

        # 保存 HTML 以便調試
        debug_file = os.path.join(csv_dir, "debug_page.html")
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        log(f"已保存調試 HTML 到: {debug_file}")

        # 查找卡片列表表格 - 選擇行數最多的表格（卡片列表最大）
        all_tables = soup.find_all('table')
        log(f"頁面中總共有 {len(all_tables)} 個表格")

        if not all_tables:
            log("頁面中沒有找到任何表格")
            return []

        # 找出行數最多的表格
        table = None
        max_rows = 0
        max_table_idx = -1

        for i, t in enumerate(all_tables):
            table_class = t.get('class', [])
            table_id = t.get('id', '')
            rows = len(t.find_all('tr'))
            log(f"  表格 {i}: class={table_class}, id={table_id}, rows={rows}")

            # 記錄行數最多的表格
            if rows > max_rows:
                max_rows = rows
                table = t
                max_table_idx = i

        if not table or max_rows < 5:
            log(f"未找到合適的卡片列表表格（最大行數: {max_rows}）")
            return []

        log(f"選擇表格 {max_table_idx}（{max_rows} 行）作為卡片列表")
        
        rows = table.find_all('tr')[1:]  # 跳過表頭
        log(f"找到 {len(rows)} 行卡片數據")
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue
            
            # 提取卡號
            card_number = cells[0].text.strip()
            if not card_number:
                continue
            
            # 提取卡片名稱和 URL
            name_link = cells[1].find('a', href=True)
            if not name_link:
                continue
            
            card_name = name_link.text.strip()
            card_url = urljoin(base_url, name_link['href'])
            
            # 提取顏色
            color = cells[2].text.strip()
            
            # 提取類型
            card_type = cells[3].text.strip()
            
            # 提取稀有度
            rarity = cells[4].text.strip()
            
            card_list.append({
                'Card Number': card_number,
                'Name': card_name,
                'Color': color,
                'Type': card_type,
                'Rarity': rarity,
                'URL': card_url
            })
            
            # 隨機延遲，避免請求過快
            time.sleep(random.uniform(0.5, 1))
        
        log(f"成功提取 {len(card_list)} 張卡片")
        return card_list

    except Exception as e:
        log(f"提取卡片列表時出錯: {e}")
        import traceback
        log(f"詳細錯誤: {traceback.format_exc()}")
        return []



def extract_detail_from_infobox(soup):
    """從 Infobox 表格提取詳細信息"""
    details = {}

    # 查找 infobox-bordered 的表格
    infobox = soup.find('table', class_='infobox-bordered')
    if infobox:
        rows = infobox.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            ths = row.find_all('th')

            if ths and cells:
                # 標題在 th，內容在 td
                key = ths[0].text.strip() if ths else ""
                value = cells[0].text.strip() if cells else ""
                if key and value:
                    details[key] = value
            elif len(cells) >= 2:
                # 兩個 td 的格式
                key = cells[0].text.strip()
                value = cells[1].text.strip()
                if key and value:
                    details[key] = value

    return details

def extract_card_effects(soup):
    """提取卡牌效果部分（從表格中提取）"""
    effects = {}

    # 方法 1：查找 info-extra effect div 中的表格
    effect_divs = soup.find_all('div', class_=lambda x: x and 'effect' in x.lower())

    for effect_div in effect_divs:
        # 在這個 div 中查找所有表格
        tables = effect_div.find_all('table', recursive=True)

        for table in tables:
            # 從表格的第一行找到標題
            th = table.find('th')
            if not th:
                continue

            th_text = th.text.strip()

            # 跳過無關的表格標題
            if 'Card Effects' not in th_text and 'Effect' not in th_text:
                continue

            # 從表格的 <td> 找到內容（第一個 <td>）
            td = table.find('td')
            if not td:
                continue

            # 提取 td 中的所有文本
            effect_text = td.get_text()

            # 去掉「Show」、「Hide」等無用文本
            effect_text = effect_text.replace('Show', '').replace('Hide', '').strip()

            # 去掉多餘空白行和換行符
            lines = [line.strip() for line in effect_text.split('\n') if line.strip()]
            effect_text = "\n".join(lines)

            if effect_text:
                # 跳過日文效果，只保留英文
                if 'JP' in th_text or '日本' in th_text or '日本語' in th_text:
                    continue
                effects['Card Effects'] = effect_text

    return effects

def extract_card_details(card_url):
    """提取卡片詳細信息（仿照 YGO 的方式）"""
    global driver
    try:
        # 添加隨機延遲，避免請求過快
        time.sleep(random.uniform(0.5, 1.0))

        if not driver:
            if not init_driver():
                return {}

        driver.get(card_url)
        time.sleep(3)  # 詳情頁面也需要時間加載

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        details = {}

        # 提取詳細信息（從 Infobox）
        details.update(extract_detail_from_infobox(soup))

        # 提取卡牌效果
        effects = extract_card_effects(soup)
        details.update(effects)

        # 調試：如果沒有提取到效果，保存 HTML 檢查
        if not effects:
            debug_file = os.path.join(csv_dir, f"debug_no_effects_{card_url.split('/')[-1]}.html")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            log(f"未找到效果，已保存 HTML: {debug_file}")

        return details

    except Exception as e:
        log(f"提取卡片詳情時出錯: {e}")
        return {}


def process_card(card):
    """處理單張卡片（用於多線程）- 仿照 YGO 的方式"""
    try:
        log(f"正在提取詳情: {card['Name']}")

        # 提取詳細信息
        details = extract_card_details(card['URL'])

        # 提取日文名稱
        kanji_name = details.get('Kanji (漢字)', '')

        # 提取卡牌屬性
        card_type = details.get('Card Type', card['Type'])
        cost = details.get('Cost', '')
        reductions = details.get('Reductions', '')
        symbols = details.get('Symbols', '')
        families = details.get('Families', card['Color'])
        levels = details.get('Levels', '')

        rarity_abbr = rarity_to_abbreviation(card['Rarity'])

        # 組合詳細的 Body (HTML) - 無多餘空白行
        body_parts = [
            f"{card['Name']}",
        ]

        # 添加日文名稱
        if kanji_name:
            body_parts.append(kanji_name)

        body_parts.append(f"{card['Card Number']}")

        # 添加詳細信息（只添加有值的字段）
        info_fields = [
            ('Card Type', card_type),
            ('Color', card['Color']),
            ('Cost', cost),
            ('Reductions', reductions),
            ('Symbols', symbols),
            ('Families', families),
            ('Levels', levels),
            ('Rarity', rarity_abbr),
        ]

        for field_name, field_value in info_fields:
            if field_value:
                body_parts.append(f"{field_name}: {field_value}")

        # 只保留英文效果
        if 'Card Effects' in details:
            body_parts.append(f"Card Effects: {details['Card Effects']}")

        body_html = "\n".join(body_parts)

        # 生成 Handle 和 Title
        handle = f"{card['Card Number']} ({rarity_abbr})"
        title = f"{card['Card Number']} {card['Name']} ({rarity_abbr})"
        if kanji_name:
            title = f"{card['Card Number']} {card['Name']} ({kanji_name})"

        # 生成 Tags（包含所有卡片屬性，不包括 BattleSpirits）
        tags_list = []

        # 添加基本屬性
        if rarity_abbr:
            tags_list.append(rarity_abbr)
        if card_type:
            tags_list.append(card_type)
        if card['Color']:
            tags_list.append(card['Color'])

        # 添加家族/顏色（如果有）
        if families and families != card['Color']:
            tags_list.append(families)

        # 添加成本
        if cost:
            tags_list.append(f"Cost{cost}")

        # 添加減少費用
        if reductions:
            tags_list.append(f"Reductions{reductions}")

        # 添加符號
        if symbols:
            tags_list.append(symbols)

        # 添加等級
        if levels:
            tags_list.append(f"Levels{levels}")

        tags = ", ".join(tags_list)

        result = {
            'Handle': handle,
            'Title': title,
            'Body (HTML)': body_html,
            'Vendor': "Bandai",
            'Product Category': "Cards",
            'Type': card_type,
            'Tags': tags
        }

        log(f"✓ 完成卡片: {handle}")
        return result

    except Exception as e:
        log(f"處理卡片 {card.get('Name', 'Unknown')} 時發生錯誤: {e}")
        import traceback
        log(f"詳細錯誤: {traceback.format_exc()}")
        return None

def download_set(set_code, set_name):
    """下載整個系列"""
    log(f"開始下載系列: {set_code} - {set_name}")

    try:
        # 構建系列頁面 URL
        set_url = f"{base_url}/wiki/{set_code}"

        # 提取卡片列表
        card_list = extract_card_list(set_url)
        if not card_list:
            log(f"系列 {set_code} 未找到任何卡片")
            return

        # 處理卡片數據
        data_found = []

        if FETCH_DETAILS:
            # 模式 1: 提取詳細信息（仿照 YGO，使用全局瀏覽器 + 2 個線程）
            log(f"詳細模式：使用 {NUM_THREADS} 個線程並行處理 {len(card_list)} 張卡片...")

            # 使用多線程處理卡片（仿照 YGO 的方式）
            with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
                futures = [executor.submit(process_card, card) for card in card_list]
                for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    try:
                        result = future.result()
                        if result:
                            data_found.append(result)
                            log(f"完成卡片 {i}/{len(card_list)}: {result['Handle']}")
                    except Exception as e:
                        log(f"處理卡片時發生錯誤: {e}")
        else:
            # 模式 2: 快速模式（只用列表信息）
            log(f"快速模式：直接使用列表信息生成 CSV...")
            for i, card in enumerate(card_list, 1):
                log(f"處理卡片 {i}/{len(card_list)}: {card['Name']}")

                rarity_abbr = rarity_to_abbreviation(card['Rarity'])
                # 直接從列表信息生成結果
                result = {
                    'Handle': f"{card['Card Number']} ({rarity_abbr})",
                    'Title': f"{card['Card Number']} {card['Name']} ({rarity_abbr})",
                    'Body (HTML)': f"Card Number: {card['Card Number']}\nCard Type: {card['Type']}\nColor: {card['Color']}\nRarity: {rarity_abbr}",
                    'Vendor': "Bandai",
                    'Product Category': "Cards",
                    'Type': card['Type'],
                    'Tags': f"{rarity_abbr}, {card['Type']}, {card['Color']}"
                }
                data_found.append(result)

        # 創建系列文件夾（仿照遊戲王的組織方式）
        # 替換 Windows 不允許的文件名字符: \ / : * ? " < > |
        safe_series_name = set_name.replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        series_folder = f"{set_code}_{safe_series_name}"
        series_folder_path = os.path.join(csv_dir, series_folder)

        # 如果資料夾不存在，則創建
        if not os.path.exists(series_folder_path):
            os.makedirs(series_folder_path)

        # 保存為 CSV
        if data_found:
            df = pd.DataFrame(data_found)
            # CSV 檔名格式：{系列代碼}_preview.csv（仿照遊戲王）
            csv_filename = f"{set_code}_preview.csv"
            csv_path = os.path.join(series_folder_path, csv_filename)
            df.to_csv(csv_path, index=False, encoding='utf-8')
            log(f"數據已保存到: {csv_path}")
            log(f"成功處理 {len(data_found)} 張卡片")
        else:
            log(f"系列 {set_code} 未找到任何有效卡片數據")

    except Exception as e:
        log(f"下載系列 {set_code} 時發生錯誤: {e}")
        log(f"錯誤詳情: {traceback.format_exc()}")

if __name__ == "__main__":
    log("Battle Spirits 卡片爬蟲開始運行")

    try:
        for series_code, series_name in SERIES_LIST:
            download_set(series_code, series_name)
            time.sleep(random.uniform(2, 5))

        log("所有系列下載完成")
    except Exception as e:
        log(f"爬蟲運行出錯: {e}")
        log(traceback.format_exc())
    finally:
        # 確保關閉瀏覽器
        close_driver()
