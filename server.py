import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# ==========================================
# 請填入你的 LINE 機器人金鑰
# ==========================================
CHANNEL_ACCESS_TOKEN ='ftClLPqkKvTl11Fy8hmNL3aZwWQz06/N167XvG36jpCirlj3f/3Qel6py9JEoP2J5xz8b8imN3MIaipYuS7v9/Y5TvRd8E4S77WmIY4gzHgKUC5uj3VTeRY5e8/b9BeGe+mHuTW2q4bZcfSUATiBygdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '45c7a1d478fed275875bc498c70d272d' 

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 讀取與寫入設定檔的工具
def load_keywords():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)['keywords']

def save_keywords(keywords):
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump({"keywords": keywords}, f, ensure_ascii=False, indent=4)

# 這是讓 LINE 伺服器來敲門的「大門口」
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 當有人傳文字訊息來的時候，會執行這裡
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text
    keywords = load_keywords()

    # 判斷使用者的指令
    if user_msg.startswith("新增:"):
        new_kw = user_msg.replace("新增:", "").strip()
        if new_kw not in keywords:
            keywords.append(new_kw)
            save_keywords(keywords)
            reply = f"✅ 已成功將「{new_kw}」加入雷達監控清單！\n目前清單：{', '.join(keywords)}"
        else:
            reply = f"⚠️ 「{new_kw}」已經在清單裡囉！"
            
    elif user_msg.startswith("刪除:"):
        del_kw = user_msg.replace("刪除:", "").strip()
        if del_kw in keywords:
            keywords.remove(del_kw)
            save_keywords(keywords)
            reply = f"🗑️ 已將「{del_kw}」從監控清單移除。\n目前清單：{', '.join(keywords)}"
        else:
            reply = f"❓ 找不到「{del_kw}」，請確認是否打錯。"
            
    elif user_msg == "查詢":
        reply = f"🔍 目前雷達監控中的關鍵字有：\n{', '.join(keywords)}"
        
    else:
        reply = "🤖 指令錯誤！請輸入以下格式：\n「新增:關鍵字」\n「刪除:關鍵字」\n「查詢」"

    # 把處理好的結果回傳給使用者的手機
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

# 啟動伺服器 (預設開在 5000 port)
if __name__ == "__main__":
    app.run(port=5000)