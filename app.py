from flask import Flask, request, abort, render_template, jsonify
import requests
from pathlib import Path
import os
import sqlite3
import threading
from dotenv import load_dotenv
from google import genai
from init_db import create_and_seed_db

# 匯入 LINE Message API v3
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    LocationAction,
    QuickReply,
    QuickReplyItem
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, LocationMessageContent

# 讀取 .env 變數
load_dotenv()

# 自動確保 SQLite 資料庫與表格已建立
create_and_seed_db()

# 初始化 Flask (指定 template 資料夾)
app = Flask(__name__, template_folder='templates')

# 讀取變數內容
configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

DB_NAME = "store.db"

# 設定外網 URL
SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:5000')

# 初始化 Google GenAI Client
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 設定 Gemini 的 System Instruction
SYSTEM_INSTRUCTION = """
你是一個親切且專業的茶葉專賣店客服助手「茶香小幫手」。
你的任務是以客氣、親切且熱情的語氣回答顧客的各種問題。
若顧客詢問與茶葉沖泡、茶種介紹、禮盒推薦相關的問題，請提供專業建議。
請使用繁體中文回覆，訊息簡明扼要，適合在 LINE 通訊軟體中閱讀。
"""

def get_services_from_db():
    """從 SQLite 讀取所有服務項目"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT title, description FROM services')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "目前尚無服務項目資訊。"

    msg_lines = ["【 服務項目 】\n"]
    for idx, (title, desc) in enumerate(rows, 1):
        msg_lines.append(f"{idx}. {title}\n   說明：{desc}\n")
    return "\n".join(msg_lines).strip()

def get_prices_from_db():
    """從 SQLite 讀取所有價目表並加上訂購連結"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT category, item_name, price FROM prices ORDER BY category')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return f"目前尚無價目表資訊。\n\n👉 前往訂購：\n{SERVER_URL}/cart"

    msg_lines = ["【 產品與服務價目表 】\n"]
    current_cat = None
    for category, item_name, price in rows:
        if category != current_cat:
            current_cat = category
            msg_lines.append(f"\n◈ {current_cat} ◈")
        msg_lines.append(f" • {item_name}：{price}")

    msg_lines.append(f"\n👉 前往訂購：\n{SERVER_URL}/cart")

    return "\n".join(msg_lines)

def reply_text(reply_token, text, quick_reply=None):
    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text, quick_reply=quick_reply)]
            ),
            _request_timeout=(3, 10)
        )

@app.get('/')
def index():
    return 'status:ok'

@app.get('/cart')
def cart_page():
    return render_template('cart.html')

@app.get('/api/prices')
def api_prices():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, category, item_name, price FROM prices')
    rows = cursor.fetchall()
    conn.close()

    products = [
        {"id": r[0], "category": r[1], "item_name": r[2], "price": r[3]}
        for r in rows
    ]
    return jsonify(products)

@app.route('/callback', methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    try:
        # 使用背景線程非同步處理事件，讓 Flask 立刻回傳 OK 避開 LINE 5秒逾時
        threading.Thread(target=handler.handle, args=(body, signature)).start()
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event):
    command = event.message.text.strip()

    if command in {'服務項目'}:
        reply_msg = get_services_from_db()
        reply_text(event.reply_token, reply_msg)
    elif command in {'價目表', "menu", '菜單'}:
        reply_msg = get_prices_from_db()
        reply_text(event.reply_token, reply_msg)
    elif command in {'訂購', '我要買茶葉'}:
        reply_msg = f"請點選連結進入線上訂購頁面：\n👉 前往訂購：\n{SERVER_URL}/cart"
        reply_text(event.reply_token, reply_msg)
    elif command in {'預約', '立即預約'}:
        reply_text(event.reply_token, '如需預約茶藝體驗或專人導覽，請直接告知我們您預計過來的時間與人數！')
    elif command in {'茶品集', '作品'}:
        reply_text(event.reply_token, '我們提供精選阿里山烏龍茶、日月潭紅玉紅茶等多款優質茶品，您可以輸入「價目表」查看詳細清單與訂購！')
    elif command in {'最新顧客評價', '評價', '推薦'}:
        reply_text(event.reply_token, '⭐ 顧客好評推薦：\n「茶香濃郁順口，包裝非常精美！」\n「手沖體驗課收穫很多，極力推薦！」')
    elif command in {'位置資訊', 'GPS', '地點', '店面位置'}:
        reply_text(event.reply_token, '#請點擊下方{傳送位置}，在 LINE 地圖選擇目前位置並確認傳送。\n',
                   QuickReply(items=[QuickReplyItem(action=LocationAction(label='傳送位置'))]))
    else:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=command,
                config={
                    "system_instruction": SYSTEM_INSTRUCTION,
                }
            )
            ai_reply = response.text.strip()
            reply_text(event.reply_token, ai_reply)
        except Exception as e:
            import traceback
            print(f"Gemini API Error: {e}")
            traceback.print_exc()
            reply_text(event.reply_token, "抱歉，小幫手暫時無法回答，請稍後再試！")

@handler.add(MessageEvent, message=LocationMessageContent)
def on_location(event):
    message = event.message
    latitude, longitude = message.latitude, message.longitude
    lines = [
        '你的位置',
        f'緯度：{latitude:.6f}',
        f'經度：{longitude:.6f}',
        f'Google 地圖: https://www.google.com/maps/search/?api=1&query={latitude},{longitude}'
    ]
    reply_text(event.reply_token, '\n'.join(lines))

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)