import requests
import json

CHANNEL_ACCESS_TOKEN ='ftClLPqkKvTl11Fy8hmNL3aZwWQz06/N167XvG36jpCirlj3f/3Qel6py9JEoP2J5xz8b8imN3MIaipYuS7v9/Y5TvRd8E4S77WmIY4gzHgKUC5uj3VTeRY5e8/b9BeGe+mHuTW2q4bZcfSUATiBygdB04t89/1O/w1cDnyilFU='
USER_ID = 'U5d7a9bb44750f59c9df5b7f2a6a780cc'

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