import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# ==========================================
# 0. 系統與安全設定初始化
# ==========================================
# 設定專業級日誌輸出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

# 嚴格安全檢查：確保金鑰存在，否則拒絕啟動
REQUIRED_ENVS = ['LINE_CHANNEL_ACCESS_TOKEN', 'LINE_CHANNEL_SECRET', 'LINE_USER_ID']
for env_var in REQUIRED_ENVS:
    if not os.getenv(env_var):
        logger.critical(f"啟動失敗：缺少必要的環境變數 {env_var}，請檢查 .env 檔案！")
        exit(1)

CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
USER_ID = os.getenv('LINE_USER_ID')

app = Flask(__name__) 
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ==========================================
# 1. 本地資料持久化工具
# ==========================================
def load_json_data(filepath: str, default_data: dict) -> dict:
    """安全讀取 JSON 檔案，若不存在則建立預設值"""
    if not os.path.exists(filepath):
        save_json_data(filepath, default_data)
        return default_data
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"讀取 {filepath} 發生錯誤: {e}。系統將套用預設值。")
        return default_data

def save_json_data(filepath: str, data: dict):
    """安全寫入 JSON 檔案"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"寫入 {filepath} 發生錯誤: {e}")

# ==========================================
# 2. 核心爬蟲任務 (背景執行)
# ==========================================
def check_ptt_hardware_sale():
    """去 PTT 二手版抓取文章並過濾關鍵字的任務"""
    config = load_json_data('config.json', {"keywords": ["二手", "筆電"]})
    keywords = config.get('keywords', [])
    
    if not keywords:
        logger.info("目前無監控關鍵字，跳過本次 PTT 掃描。")
        return

    logger.info(f"啟動背景巡邏... 當前監控清單：{keywords}")
    
    history_data = load_json_data('seen_urls.json', {"seen": []})
    seen_urls = set(history_data.get('seen', []))
    new_items_found = False

    url = 'https://www.ptt.cc/bbs/HardwareSale/index.html'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        cookies = {'over18': '1'}
        response = requests.get(url, headers=headers, cookies=cookies, timeout=15)
        response.raise_for_status()  # 確保 HTTP 狀態碼為 200
        soup = BeautifulSoup(response.text, 'html.parser')
        titles = soup.find_all('div', class_='title')
        
        for t in titles:
            if t.a:
                title_text = t.a.text.strip()
                article_url = 'https://www.ptt.cc' + t.a['href']
                title_lower = title_text.lower()
                
                # 排除已被刪除的文章
                if "本文已被刪除" in title_text:
                    continue

                for keyword in keywords:
                    if keyword.lower() in title_lower:
                        if article_url not in seen_urls:
                            logger.info(f"發現新目標：{title_text}")
                            msg = f"🚨 發現二手情報！\n關鍵字：#{keyword}\n標題：{title_text}\n連結：{article_url}"
                            
                            try:
                                line_bot_api.push_message(USER_ID, TextSendMessage(text=msg))
                                seen_urls.add(article_url)
                                new_items_found = True
                            except LineBotApiError as bot_err:
                                logger.error(f"LINE 推播失敗：{bot_err}")
                        break # 單篇文章只要匹配到一個關鍵字就跳出，避免重複推播
        
        # 僅在有更新時寫入檔案，減少 I/O 消耗
        if new_items_found:
            save_json_data('seen_urls.json', {"seen": list(seen_urls)})

    except requests.exceptions.RequestException as req_err:
        logger.warning(f"網路請求發生異常，可能是 PTT 伺服器不穩：{req_err}")
    except Exception as e:
        logger.error(f"爬蟲執行過程中發生未預期錯誤：{e}", exc_info=True)

# ==========================================
# 3. LINE Webhook 伺服器端點
# ==========================================
@app.route("/callback", methods=['POST'])
def callback():
    """LINE 伺服器傳遞訊息的接口"""
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("收到無效的簽章，可能來自非 LINE 官方的攻擊請求。")
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """處理使用者傳送的文字訊息指令"""
    user_msg = event.message.text.strip()
    config = load_json_data('config.json', {"keywords": ["二手", "筆電"]})
    keywords = config.get('keywords', [])
    reply = ""

    if user_msg.startswith("新增:"):
        new_kw = user_msg.replace("新增:", "").strip()
        if new_kw:
            if new_kw not in keywords:
                keywords.append(new_kw)
                save_json_data('config.json', {"keywords": keywords})
                reply = f"✅ 已成功將「{new_kw}」加入雷達監控清單！\n目前清單：{', '.join(keywords)}"
                logger.info(f"使用者新增關鍵字：{new_kw}")
            else:
                reply = f"⚠️ 「{new_kw}」已經在清單裡囉！"
        else:
            reply = "⚠️ 新增的關鍵字不能為空！"
            
    elif user_msg.startswith("刪除:"):
        del_kw = user_msg.replace("刪除:", "").strip()
        if del_kw in keywords:
            keywords.remove(del_kw)
            save_json_data('config.json', {"keywords": keywords})
            reply = f"🗑️ 已將「{del_kw}」從監控清單移除。\n目前清單：{', '.join(keywords) if keywords else '無'}"
            logger.info(f"使用者刪除關鍵字：{del_kw}")
        else:
            reply = f"❓ 找不到「{del_kw}」，請確認是否打錯。"
            
    elif user_msg == "查詢":
        reply = f"🔍 目前雷達監控中的關鍵字有：\n{', '.join(keywords) if keywords else '目前清單為空'}"
        
    else:
        reply = "🤖 指令錯誤！請輸入以下格式：\n「新增:關鍵字」\n「刪除:關鍵字」\n「查詢」"

    if reply:
        try:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        except LineBotApiError as e:
            logger.error(f"回覆使用者訊息失敗: {e}")

# ==========================================
# 4. 主程式入口點
# ==========================================
if __name__ == "__main__":
    # 設定並啟動背景排程 (預設每 30 分鐘執行一次)
    scheduler = BackgroundScheduler(timezone="Asia/Taipei")
    scheduler.add_job(check_ptt_hardware_sale, 'interval', minutes=30)
    scheduler.start()
    
    logger.info("🚀 專屬雷達機器人系統已全面啟動！排程上線，伺服器監聽中...")
    
    # 啟動 Flask 伺服器
    # use_reloader=False 極度重要：防止開發模式下 scheduler 啟動兩次
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)