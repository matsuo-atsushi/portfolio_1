
import json
import csv
import os
import sys
import shutil
from datetime import datetime

from strategy_analyzer_app.io_operations.print_processing import big_print, suppress_print

def copy_data_for_error_directory(save_error_dir, original_path_list, error_type):
    """
    エラーが起きたとき、その場でデータのコピーをディレクトリに追加する
    - args:
        - save_error_dir: エラーデータを保存するディレクトリ
        - original_path_list: コピーしたいデータの元リンク
        - error_type: dir_nameの中に作るフォルダの名前(ex, 1, name_error)
        - *time*: error_typeにこれを追加したら、そこを現在時刻に置き換える
    """
    # 保存ディレクトリを用意する
    if not os.path.exists(save_error_dir):
        os.makedirs(save_error_dir)

    if '*time*' in error_type:
        error_type = error_type.replace('*time*', str(get_now()))

    # このエラーを保存するディレクトリを作成する
    save_error_dir = os.path.join(save_error_dir, error_type)
    if not os.path.exists(save_error_dir):
        os.makedirs(save_error_dir)

    for originl_path in original_path_list:
        data_name = os.path.basename(originl_path)
        move_data_path = os.path.join(save_error_dir, data_name)
        shutil.copy(originl_path, move_data_path)

    big_print(f'怪しいデータがあったので、データのコピーを作成しました -> {save_error_dir}', 'red')

def get_now():
    # 現在時刻を取得
    now = datetime.now()
    # 時間:分をフォーマットして出力
    formatted_time = now.strftime("%y%m%d-%H%M%S")

    return formatted_time