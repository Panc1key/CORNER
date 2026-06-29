import requests
import pandas as pd
import os
from bs4 import BeautifulSoup

# 设置请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 基 URL 和 API URL
base_url = "https://yugipedia.com/wiki/"
API_BASE_URL = "https://yugipedia.com/api.php?action=tcgplayerprices&format=json&card="

# 汇率（可以动态获取，但这里先写死）
USD_TO_HKD = 7.8  # 美元到港元的汇率
USD_TO_JPY = 110  # 美元到日元的汇率

# CSV保存目录
csv_dir = os.path.join(os.path.expanduser("~"), "Desktop", "YugipediaCardPrices")
if not os.path.exists(csv_dir):
    os.makedirs(csv_dir)  # 如果目录不存在，则创建

# 提取系列页面中的卡片名称和 URL
def extract_card_urls(series_url):
    try:
        print(f"正在提取系列页面中的卡片 URL: {series_url}")
        response = requests.get(series_url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"网页出错，返回值: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        print("页面解析完成")

        card_data = []
        table = soup.find('table', class_='wikitable')
        if not table:
            print(f"未找到表格: {series_url}")
            return []

        rows = table.find_all('tr')[1:]  # 跳过表头行

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue

            # 提取卡片名称和 URL
            name_cell = cells[1]  # 第二列是卡片名称
            name_link = name_cell.find('a', href=True)  # 查找 <a> 标签

            if name_link:
                card_name = name_link.text.strip()
                card_url = "https://yugipedia.com" + name_link['href']
                card_data.append({
                    "Name": card_name,
                    "URL": card_url
                })

        print(f"找到 {len(card_data)} 张卡片")
        return card_data
    except Exception as e:
        print(f"提取卡片 URL 时发生错误: {e}")
        return []

# 提取卡片价格
def fetch_card_prices(card_name):
    try:
        # 构造 API URL
        card_url = API_BASE_URL + card_name.replace(" ", "%20")
        response = requests.get(card_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"请求失败，状态码: {response.status_code}")
            return None

        # 解析 JSON 数据
        data = response.json()
        if "tcgplayerprices" not in data:
            print(f"未找到价格数据: {card_name}")
            return None

        # 提取价格信息
        prices = []
        for entry in data["tcgplayerprices"]:
            if "results" in entry:
                for result in entry["results"]:
                    product_id = result.get("productId", "N/A")
                    edition = result.get("subTypeName", "Unknown Edition")
                    low_price = result.get("lowPrice", None)
                    mid_price = result.get("midPrice", None)
                    high_price = result.get("highPrice", None)
                    market_price = result.get("marketPrice", None)

                    # 跳过无效数据
                    if all(price is None for price in [low_price, mid_price, high_price, market_price]):
                        continue

                    # 转换为港元和日元
                    prices.append({
                        "Card Name": card_name,
                        "Product ID": product_id,
                        "Edition": edition,
                        "Low Price (USD)": low_price,
                        "Mid Price (USD)": mid_price,
                        "High Price (USD)": high_price,
                        "Market Price (USD)": market_price,
                        "Low Price (HKD)": round(low_price * USD_TO_HKD, 2) if low_price else None,
                        "Mid Price (HKD)": round(mid_price * USD_TO_HKD, 2) if mid_price else None,
                        "High Price (HKD)": round(high_price * USD_TO_HKD, 2) if high_price else None,
                        "Market Price (HKD)": round(market_price * USD_TO_HKD, 2) if market_price else None,
                        "Low Price (JPY)": round(low_price * USD_TO_JPY, 2) if low_price else None,
                        "Mid Price (JPY)": round(mid_price * USD_TO_JPY, 2) if mid_price else None,
                        "High Price (JPY)": round(high_price * USD_TO_JPY, 2) if high_price else None,
                        "Market Price (JPY)": round(market_price * USD_TO_JPY, 2) if market_price else None,
                    })

        return prices
    except Exception as e:
        print(f"提取价格时发生错误: {e}")
        return None

# 自定义样式函数
def highlight_currency(x):
    """根据列名为不同货币设置背景颜色"""
    if "USD" in x.name:
        return ['background-color: lightblue'] * len(x)
    elif "HKD" in x.name:
        return ['background-color: lightcoral'] * len(x)
    elif "JPY" in x.name:
        return ['background-color: white'] * len(x)
    else:
        return [''] * len(x)

# 下载系列中的所有卡片价格
def download_series_prices(series_name):
    series_url = base_url + series_name
    print(f"开始处理系列: {series_name}")

    # 提取系列中的所有卡片
    card_data = extract_card_urls(series_url)
    if not card_data:
        print(f"未提取到系列 {series_name} 的卡片数据")
        return

    # 提取所有卡片的价格
    all_prices = []
    for card in card_data:
        print(f"正在提取卡片价格: {card['Name']}")
        prices = fetch_card_prices(card['Name'])
        if prices:
            all_prices.extend(prices)

    # 保存价格数据到 CSV
    if all_prices:
        df = pd.DataFrame(all_prices)

        # 应用样式
        styled_df = df.style.apply(highlight_currency, axis=0)

        # 保存为 Excel 文件（支持样式）
        filename = f"{series_name.replace('/', '_')}_Prices.xlsx"
        csv_path = os.path.join(csv_dir, filename)
        styled_df.to_excel(csv_path, index=False, engine='openpyxl')
        print(f"价格数据已保存到: {csv_path}")
    else:
        print(f"系列 {series_name} 无价格数据")

# 主函数
if __name__ == "__main__":
    # 输入系列名称列表
    SERIES_LIST = [
        "Structure_Deck:_Salamangreat_Sanctum",
        "Age_of_Overlord",
        "Legacy_of_Destruction"
    ]

    for series in SERIES_LIST:
        download_series_prices(series)
