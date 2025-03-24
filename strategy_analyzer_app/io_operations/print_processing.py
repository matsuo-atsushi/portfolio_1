
import sys
import io
import os
from termcolor import colored, cprint

def big_print(text, color='white', style=None):
    """
    色つけたりする。より目立つようにする
    [引数]
    on をつけるとマーカーになる
    色だけだと、太字
    何もなかったら、装飾がつくだけ
    style
        ▲にすると、▲ ▼ ▲ ▼ になる
        なにも無ければ、テキストをprintするだけ
    """

    style_text = None
    if style == '▲':
        style_text = ' ▲ ▼ ▲ ▼ ▲ ▼ ▲ ▼ ▲ ▼ ▲ ▼ ▲ ▼ ▲ ▼ ▲ ▼ ▲ ▼ '
    elif style == '-':
        style_text = '-----------------------------------------'
    elif style == '=':
        style_text = '========================================='

    if 'on' in color:
        if style_text:
            cprint(f'{style_text}', "white", f"{color}")

        # \n があるテキストをon_colorでprintすると変になるので各行ごとにprintする
        if '\n' in text:
            for split_txt in text.split('\n'):
                cprint(f' {split_txt} ', "white", f"{color}")
        else:
            cprint(f' {text} ', "white", f"{color}")

        if style_text:
            cprint(f'{style_text}', "white", f"{color}")

    elif color:
        if style_text:
            cprint(f'{style_text}', f"{color}", attrs=["bold"], file=sys.stderr)

        cprint(f' {text} ', f"{color}", attrs=["bold"], file=sys.stderr)

        if style_text:
            cprint(f'{style_text}', f"{color}", attrs=["bold"], file=sys.stderr)

    else:
        if style_text:
            print(f'{style_text}')

        print(f'{text}')

        if style_text:
            print(f'{style_text}')
    sys.stdout.flush()

def suppress_print(func):
    """
    この関数に引数として渡された関数のprint出力を抑制する
    """
    def wrapper(*args, **kwargs):
        # 標準出力を保存
        original_stdout = sys.stdout
        try:
            # 標準出力をStringIOに変更
            sys.stdout = io.StringIO()
            # cprintのデフォルト出力も変更
            def mock_cprint(*args, **kwargs):
                kwargs['file'] = sys.stdout
                from termcolor import cprint
                cprint(*args, **kwargs)

            # cprint をモックとして置き換え
            original_cprint = cprint
            globals()['cprint'] = mock_cprint

            # 関数を実行
            result = func(*args, **kwargs)
        finally:
            # 標準出力を元に戻す
            sys.stdout = original_stdout
            globals()['cprint'] = original_cprint
        return result
    return wrapper
