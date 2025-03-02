
import requests

from strategy_analyzer_app.io_operations.print_processing import big_print
import strategy_analyzer_app.utils.thread_utils as thred
import strategy_analyzer_app.global_vars as glbvar

@thred.thread_func
def send_msg_with_telegram(MESSAGE):

    TOKEN = glbvar.TOKEN  # BotFatherで取得したTOKEN
    CHAT_ID = glbvar.CHAT_ID  # getUpdatesで取得したチャットID

    # Telegram APIを使ってメッセージを送信
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": MESSAGE}

    try:
        response = requests.get(url, params=params)
    except:
        big_print(f'メッセージ送信に失敗しました\nMESSAGE: {MESSAGE}', 'red')
        return

    # 送信結果を確認
    if response.status_code == 200:
        print("通知が送信されました")
    else:
        print(f"⚠️ エラー: {response.status_code}")
