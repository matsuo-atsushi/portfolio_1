
import re
import sys
from termcolor import colored, cprint
import traceback

from strategy_analyzer_app.io_operations.print_processing import big_print, suppress_print

def convert_number(num):
    """
    数値を受取り、整数にできるなら変換する。できないなら、少数のまま返す
    """
    # 浮動小数点数で整数値かどうかを確認
    if isinstance(num, float) and num.is_integer():
        return int(num)  # 整数に変換
    return num  # そのまま返す

def delete_non_numbers(text, print_text=True, non_float=False):
    """
    抽出したテキストが''だったり、  数字以外だったときでも、0を返す
    """

    text = str(text) # strに変換しないといけない。intだとエラーになる

    if print_text:
        print(f'delete前:{text}', end="", flush=True)
    if text == '':
        text = 0
        return text
    numbers = re.sub(r'[^0-9.]', '', text)
    if numbers == '' or numbers == '.' or numbers == '$' or numbers == '%':
        numbers = 0

    # 先頭が'.'なら、削除する
    while str(numbers)[0] == '.':
        big_print(f'テキストの先頭が、"."です({numbers})','white')
        numbers = numbers[1:]

    if non_float:
        return numbers
    # ピリオドが複数ある場合は最初の1つだけを残す
    try:
        if str(numbers).count('.') > 1:
            parts = numbers.split('.')
            numbers = parts[0] + '.' + ''.join(parts[1:])
    except Exception as e:
        traceback.print_exc()

    return float(numbers)

def BB_delete_non_numbers(text, print_text=True):
    """
    抽出したテキストが''だったり、  数字以外だったときでも、0を返す
    '2BB'を'28B'と読み間違えるミスを補正する処理を追加
    [返り値]
    Trust_text OCRがうまくできていなくて、調整を行ったとき、Falseにする
    """

    Trust_text = True

    text = str(text) # strに変換しないといけない。intだとエラーになる
    if print_text:
        print(f'delete前:{text}', end="", flush=True)
    if text == '':
        text = 0
        return text, Trust_text

    # Bと数字以外削除する
    numbers_include_BB = re.sub(r'[^0-9.B]', '', text)
    count_b = numbers_include_BB.count('B')
    if numbers_include_BB[-2:] == 'BB':
        if count_b >= 3:
            cprint(f'"BB"を読み間違えています\n"B"が3つ以上あります', "yellow", attrs=["bold"], file=sys.stderr)
            numbers_include_BB = numbers_include_BB.split('B')[0]
            cprint(f'"{text}"を"{numbers_include_BB}"に変換しました', "yellow", attrs=["bold"], file=sys.stderr)
            Trust_text = False
        text = numbers_include_BB
    else:
        cprint(f'"BB"を読み間違えています', "yellow", attrs=["bold"], file=sys.stderr)
        Trust_text = False
        # "2BB"を"268"と読み間違えたときの処理。数字が小さくなるのは、ポットを正とさせるので大丈夫だと思う
        if count_b == 0:
            if len(numbers_include_BB) <= 4:
                # 文字が4文字以下の場合、一文字目のみ取り出す
                numbers_include_BB = numbers_include_BB[0]
                cprint(f'"{text}"を"{numbers_include_BB}"に変換しました(Bが含まれていなくて、4文字以下のため、最初の1文字のみ取り出す。)', "yellow", attrs=["bold"], file=sys.stderr)
            else:
                # 文字が5文字以上は、最初の2文字のみ取り出す
                numbers_include_BB = numbers_include_BB[1]
                cprint(f'"{text}"を"{numbers_include_BB}"に変換しました(Bが含まれていなくて、5文字以上のため、最初の2文字のみ取り出す。ポットを正とする方針)', "yellow", attrs=["bold"], file=sys.stderr)
        # "26B"のような間違いを補正する。または、Bすら読み取れていないのは絶対に間違っている(この処理は上に追加した)
        elif numbers_include_BB[-1:] == 'B':
            # 後ろから2文字消す
            numbers_include_BB = numbers_include_BB[:-2]
            cprint(f'"{text}"を"{numbers_include_BB}"に変換しました', "yellow", attrs=["bold"], file=sys.stderr)
        # 2B66Bのような間違いを補正する
        if 'B' in numbers_include_BB:
            numbers_include_BB = numbers_include_BB.split('B')[0]
            cprint(f'"{text}"を"{numbers_include_BB}"に変換しました', "yellow", attrs=["bold"], file=sys.stderr)
        text = numbers_include_BB

    numbers = re.sub(r'[^0-9.]', '', text)
    if numbers == '' or numbers == '.' or numbers == '$' or numbers == '%':
        numbers = 0

    # 先頭が'.'なら、削除する
    while str(numbers)[0] == '.':
        big_print(f'テキストの先頭が、"."です({numbers})','white')
        numbers = numbers[1:]

    # 更に正規表現を追加。動作未確認(241216)
    normalized_number = normalize_numbers(str(numbers))

    return float(normalized_number), Trust_text

def normalize_numbers(num):
    normalized = []

    # 数値形式に修正する正規表現: 1つ以上の数字と1つの小数点の形式を維持
    match = re.match(r'^\.?(\d+(\.\d+)?).*$', num)
    if match:
        normalized.append(match.group(1))  # 必要な部分のみ取得

    return normalized[0]

