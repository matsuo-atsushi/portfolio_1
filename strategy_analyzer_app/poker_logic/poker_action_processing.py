
import random
import time

from termcolor import colored, cprint

from strategy_analyzer_app.text_processing.text_extraction import convert_number
from strategy_analyzer_app.io_operations.print_processing import big_print, suppress_print
from strategy_analyzer_app.poker_logic.action_report_control import fix_action
import strategy_analyzer_app.global_vars as glbvar


def change_myhand_to_wizard(myhand):
    """
    porkerscreenから抽出したmyhandを、wizardの入力で使えるように変換する
    """
    number1 = None
    number2 = None

    mark1 = None
    mark2 = None

    about_hand = None
    detail_hand = None

    number_order = 'AKQJT98765432'
    suite_order = 'shdc'

    def custom_sort(char1, char2, order):
        order_index = {char: index for index, char in enumerate(order)}
        char1, char2 = sorted([char1, char2], key=lambda x: order_index.get(x, float('inf')))
        return char1, char2

    # カードの数字とマークをばらす
    for hand in myhand:
        if number1 is None:
            number1 = hand[0]
            mark1 = hand[1]
        elif number2 is None:
            number2 = hand[0]
            mark2 = hand[1]
    # まず、ポケットペアを判断する
    if number1 == number2:
        about_hand = f'{number1}{number2}'
        sort_mark1, sort_mark2 = custom_sort(mark1, mark2, suite_order)
        detail_hand = f'{number1}{sort_mark1}{number2}{sort_mark2}'
        return about_hand, detail_hand
    # スーテッドを判断
    elif mark1 == mark2:
        sort_number1, sort_number2 = custom_sort(number1, number2, number_order)
        about_hand = f'{sort_number1}{sort_number2}s'
        detail_hand = f'{sort_number1}{mark1}{sort_number2}{mark2}'
        return about_hand, detail_hand
    # オフスーテッドを判断
    else:
        sort_number1, sort_number2 = custom_sort(number1, number2, number_order)
        about_hand = f'{sort_number1}{sort_number2}o'
        if sort_number1 == number1:
            detail_hand = f'{sort_number1}{mark1}{sort_number2}{mark2}'
        else:
            detail_hand = f'{sort_number1}{mark2}{sort_number2}{mark1}'
        return about_hand, detail_hand

