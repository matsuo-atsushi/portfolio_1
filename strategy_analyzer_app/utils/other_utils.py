
from strategy_analyzer_app.io_operations.print_processing import big_print, suppress_print
import strategy_analyzer_app.utils.send_msg as sendmsg

def input_y_or_n(message, send=False):
    """
    inputで y or n で答えさせる
    - Args:
        - send: Trueにするとtelegramを送る
    """
    # メッセージを送信
    if send:
        # sendmsg.send_msg_with_telegram(message)
        pass

    judge = None
    while judge != 'y' and judge != 'n':
        judge = input(f' - {message}(y ,n)')
        if judge != 'y' and judge != 'n':
            big_print(f'"y"か、"n"で答えてください', 'red')
    # 異なるとき、continueする
    if judge == 'n':
        return False
    else:
        return True


