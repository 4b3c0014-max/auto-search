import requests
from bs4 import BeautifulSoup
import time
import json

# ==========================================
# 1. 設定區
# ==========================================
CHANNEL_ACCESS_TOKEN ='rw6UNrtRRVpVjmiYZZZiAS/QVusSgN19UiI28GKmvSh7CU7xrTGqnEtu3gIQFEZW5xz8b8imN3MIaipYuS7v9/Y5TvRd8E4S77WmIY4gzHhGHiUVrUrKmfE9t3WfseqFsbBvO7Lu7L7DiyGzivuuOwdB04t89/1O/w1cDnyilFU='
USER_ID = 'U5d7a9bb44750f59c9df5b7f2a6a780cc'

# 用來「記憶」已經通知過的文章網址，避免重複轟炸
seen_urls = set()

# ==========================================
# 新增功能：從 config.json 讀取最新關鍵字
# ==========================================
def get_latest_keywords():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('keywords', [])
    except Exception as e:
        print(f"⚠️ 讀取 config.json 失敗（可能是檔案還沒建立）：{e}")
        # 如果讀不到檔案，就用你原本預設的關鍵字當備案
        return ['二手', '筆電', 'macbook', '主機']

# ==========================================
# 2. 傳送 LINE 訊息的功能
# ==========================================
def send_line_message(msg):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {CHANNEL_ACCESS_TOKEN}'
    }
    payload = {
        'to': USER_ID,
        'messages': [{'type': 'text', 'text': msg}]
    }
    try:
        requests.post(url, headers=headers, data=json.dumps(payload))
    except Exception as e:
        print(f"傳送 LINE 訊息失敗：{e}")

# ==========================================
# 3. 爬蟲功能：去 PTT 抓資料並過濾
# ==========================================
def check_ptt():
    # ⭐ 關鍵改裝：每次巡邏前，先看一眼手機有沒有新增關鍵字
    KEYWORDS = get_latest_keywords()
    
    print(f"[{time.strftime('%H:%M:%S')}] 正在掃描 PTT... 當前監控：{KEYWORDS}")
    
    if not KEYWORDS:
        print("目前沒有任何監控關鍵字，休息中...")
        return

    url = 'https://www.ptt.cc/bbs/HardwareSale/index.html'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        cookies = {'over18': '1'}
        response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        titles = soup.find_all('div', class_='title')
        
        for t in titles:
            if t.a:
                title_text = t.a.text
                article_url = 'https://www.ptt.cc' + t.a['href']
                title_lower = title_text.lower()
                
                # 比對最新讀進來的 KEYWORDS
                for keyword in KEYWORDS:
                    if keyword.lower() in title_lower:
                        if article_url not in seen_urls:
                            print(f"👀 發現目標：{title_text}")
                            msg = f"🚨 發現二手情報！\n關鍵字：#{keyword}\n標題：{title_text}\n連結：{article_url}"
                            send_line_message(msg)
                            seen_urls.add(article_url)
                        break 
    except Exception as e:
        print(f"爬蟲發生錯誤：{e}")

# ==========================================
# 4. 主程式
# ==========================================
if __name__ == "__main__":
    print("🤖 全自動 PTT 二手雷達 (手機連動版) 已啟動！")
    send_line_message("雷達已成功啟動，現在可以透過 LINE 直接控制監控清單了！")

    while True:
        check_ptt()
        print("掃描完畢，進入休眠...")
        
        # 建議測試時可以把時間改短（例如 60 秒），成功後再改回 3600
        time.sleep(1800)