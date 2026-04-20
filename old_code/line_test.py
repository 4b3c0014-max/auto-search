import os
import requests
import json
from dotenv import load_dotenv

# 1. 載入 .env 檔案裡的變數 (打開保險箱)
load_dotenv()

# 2. 改為從保險箱讀取，絕對不要再把密碼明文貼在這裡！
CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
USER_ID = os.getenv('LINE_USER_ID')

def send_line_message(msg):
    # LINE 推播訊息的 API 網址
    url = 'https://api.line.me/v2/bot/message/push'
    
    # 準備 HTTP 標頭（跟 LINE 證明你是誰）
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {CHANNEL_ACCESS_TOKEN}'
    }
    
    # 準備訊息內容（打包成 JSON 格式）
    payload = {
        'to': USER_ID,
        'messages': [{'type': 'text', 'text': msg}]
    }

    # 發送 POST 請求給 LINE 的伺服器
    print("正在發送訊息給 LINE 伺服器...")
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    # 檢查結果
    if response.status_code == 200:
        print("太棒了！訊息發送成功，快看一下手機有沒有收到！")
    else:
        print(f"哎呀，出錯了：錯誤代碼 {response.status_code}")
        print("錯誤訊息：", response.text)

# 執行測試！
send_line_message("Hello World！彥廷，這是你的雷達機器人第一次發聲！🤖")