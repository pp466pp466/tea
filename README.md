# LINE 茶葉商店客服 Bot

以 Flask 建立的 LINE Messaging API 客服 Bot，提供茶葉服務與價目資訊，並使用 Gemini 回覆顧客問題。訂購頁面位於 `/cart`。

## 環境需求

- Python 3.12 或更新版本
- LINE Messaging API Channel
- Google Gemini API 金鑰

## 安裝與執行

1. 建立並啟用虛擬環境。
2. 安裝套件：`pip install -r requirements.txt`
3. 複製 `.env.example` 為 `.env`，填入 LINE 與 Gemini 金鑰。
4. 初始化資料庫：`python init_db.py`
5. 啟動 Flask：`python app.py`

設定 LINE Webhook 時，使用可從網際網路連線的伺服器網址，並將 `SERVER_URL` 設為該網址。

`store.db` 是本機 SQLite 資料庫，首次啟動時會自動建立並填入範例服務與價目資料。資料庫與 `.env` 不納入版本控制。
