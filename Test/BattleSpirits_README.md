# Battle Spirits 卡片爬蟲

## 功能說明

這個爬蟲用於從 Battle Spirits Wiki 抓取卡片數據，並輸出為標準的 CSV 格式。

## 爬蟲工作流程

1. **訪問系列頁面**
   - URL: `https://battle-spirits.fandom.com/wiki/{SET_CODE}`
   - 例如: `https://battle-spirits.fandom.com/wiki/26RBS01`

2. **提取卡片列表**
   - 從表格中讀取所有卡片的摘要信息
   - 卡號、名稱、顏色、類型、稀有度
   - 提取卡片詳情頁的 URL

3. **提取卡片詳情**
   - 訪問每張卡片的詳情頁面
   - 讀取完整的屬性信息
   - 提取卡牌效果文本

4. **保存為 CSV**
   - 輸出標準格式：Handle, Title, Body (HTML), Vendor, Product Category, Type, Tags
   - 保存位置：`~/Desktop/BattleSpiritsList/{SET_CODE}.csv`

## CSV 輸出格式

| 欄位 | 說明 | 示例 |
|------|------|------|
| Handle | 卡號+稀有度 | 26RSD02-001 (Common) |
| Title | 卡號+名稱+稀有度 | 26RSD02-001 Sclouse (Common) |
| Body (HTML) | 完整卡片信息 | Card Type: Spirit\nColor: Purple\n... |
| Vendor | 供應商 | Bandai |
| Product Category | 產品分類 | Cards |
| Type | 卡片類型 | Spirit |
| Tags | 標籤（用逗號分隔） | BattleSpirits, Spirit, Purple, Common |

## 使用方法

### 1. 添加要下載的系列

編輯 `SERIES_LIST` 列表，添加系列代碼：

```python
SERIES_LIST = [
    "26RBS01",  # Blazing Dominion
    "26RSD02",  # Sclouse Set
    "26RST01",  # 其他系列
]
```

### 2. 運行爬蟲

```bash
python BattleSpirits_Crawler.py
```

### 3. 查看結果

CSV 文件會保存在：`C:\Users\{你的用戶名}\Desktop\BattleSpiritsList\`

## 注意事項

1. **請求延遲**
   - 列表提取：隨機 0.5-1 秒
   - 詳情提取：隨機 1-2 秒
   - 避免對服務器造成過大壓力

2. **錯誤處理**
   - 網絡錯誤會記錄在日誌中
   - 爬蟲會繼續處理其他卡片

3. **編碼**
   - 使用 UTF-8 編碼
   - 支持中文、日文等字符

## 可能需要調整的地方

1. **HTML 解析選擇器**
   - 如果網頁結構改變，需要更新 BeautifulSoup 查詢
   - 當前使用：`class='wikitable'`, `class='info-main'`, `class='cardtablespanrow'`

2. **表格行解析**
   - 需要驗證表格結構是否與提供的示例一致
   - 調整 `cells` 索引

3. **顏色和類型識別**
   - 可能需要正則表達式來清理文本
   - 提取圖標時可能需要特殊處理

## 下一步改進

- [ ] 添加 GUI 界面（類似 YGO 爬蟲）
- [ ] 支持增量更新（只下載新卡片）
- [ ] 添加代理支持（如需要）
- [ ] 圖片下載功能
- [ ] 效果文本的更智能解析
