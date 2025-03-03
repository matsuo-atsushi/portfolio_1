
from datetime import datetime
import os
import csv
import json
import sys
import shutil
import time
import gzip
import zstandard as zstd
import pandas as pd

from termcolor import colored, cprint

from strategy_analyzer_app.io_operations.print_processing import big_print, suppress_print
from strategy_analyzer_app.poker_logic.action_report_control import fix_action
import strategy_analyzer_app.poker_logic.modify_allreport_logic as allrepo
import strategy_analyzer_app.poker_logic.poker_action_processing as pkac
import strategy_analyzer_app.global_vars as glbvar
import strategy_analyzer_app.utils.other_utils as oths
import strategy_analyzer_app.get_stradata.convert_data_for_analyze_stradata as cnvstra
import strategy_analyzer_app.display_processing.get_data_from_screen as ctlscr


def make_json_data(path, data, alert=True):
    """
    pathとdataを受取り、jsonを作成する
    親ディレクトリがなければ作成する
    - Args:
        - alert: True(default)のとき、作成しようとしているjsonがあるとき、警告する
    """
    # 親ディレクトリがなければ作成する
    parent_dir = os.path.dirname(path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
        big_print('親ディレクトリを新規作成しました', 'yellow')

    # 既にjsonがあるとき、警告する
    if alert and os.path.exists(path):
        big_print(f'============================================\n - {path}\n', 'yellow')
        judge = None
        while judge != 'y' and judge != 'n':
            judge = input(f' - 上記のデータは既に存在しています。上書きしてよいですか(y, n)\n   y: 上書きする,  n: 中止する')
            if judge != 'y' and judge != 'n':
                big_print(f'"y"か、"n"で答えてください', 'red')
        if judge == 'n':
            big_print(f'jsonファイルをの作成を中止しました', 'on_red')
            return

    # JSON形式で保存
    with open(path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    big_print(f'jsonファイルを作成しました -> {path}', 'yellow')

def update_json_data(json_path, new_dict):
    """
    jsonパスと、辞書データを受け取り、
    存在しなければ、新規作成し、存在するときは、データを追加する
    """

    # JSONファイルを読み込んで辞書として取得
    try:
        with open(json_path, "r", encoding='utf-8') as file:
            print(f'jsonファイルが見つかりました(2) -> {json_path}')
            existing_data = json.load(file)  # JSONファイルの内容を辞書に変換
    except FileNotFoundError:
        print(f'jsonファイルが存在しません(2) -> {json_path}')
        existing_data = {}  # ファイルが存在しない場合は空の辞書を初期化

    # 辞書データを追加
    existing_data.update(new_dict)

    # ディレクトリのパスを取得
    directory = os.path.dirname(json_path)
    # ディレクトリが存在しない場合は作成
    if not os.path.exists(directory):
        os.makedirs(directory)

    # 更新した辞書をJSONファイルに書き戻す
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(existing_data, json_file, ensure_ascii=False, indent=4)  # 見やすく保存する場合は indent を使用

    print(f"データが追加されました: {new_dict}")

def add_value_to_csv(csv_path, fieldnames, new_data):
    """
    csvにデータを追加する
    - ディレクトリがなければ作成する
    - csvがなければ作成する
    """
    # ディレクトリのパスを取得
    directory = os.path.dirname(csv_path)
    # ディレクトリが存在しない場合は作成
    if not os.path.exists(directory):
        os.makedirs(directory)

    # csvがなければ作成する
    if not os.path.exists(csv_path):
        # dirを新規作成したなら、csvも作成する
        with open(csv_path, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            # ヘッダーを書き込む
            writer.writeheader()
        big_print(f'csvを新規作成しました -> {csv_path}', 'yellow')

    # csvにデータを追加する
    with open(csv_path, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(new_data)

    big_print(f'csvにデータを追加しました -> {new_data}', 'yellow')

def read_data(path, *, file_type):
    """
    csvを読み込んだデータを返す
    - Args:
        - file_type: csv, json, gzip(jsonのみ), json-zstd を指定する
    """
    if file_type == 'csv':
        with open(path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            data = [row for row in reader]
        return data

    if file_type == 'json':
        with open(path, "r", encoding='utf-8') as file:
            data = json.load(file)
        return data

    if file_type == 'gzip':
        # Gzipで圧縮されたJSONファイルを開く
        with gzip.open(path, "rt", encoding="utf-8") as file:
            data = json.load(file)
        return data

    if file_type == 'json-zstd':
        # 解凍
        dctx = zstd.ZstdDecompressor()
        with open(path, "rb") as f:
            decompressed = dctx.decompress(f.read())
        json_data = json.loads(decompressed.decode())
        return json_data

def save_new_data(path, data, fieldnames=None, *, file_type=None, alert=True):
    """
    データを新規作成する
    - Args:
        - file_type: csv,
    """
    if file_type == 'csv':
        if alert:
            if os.path.exists(path):
                judge = oths.input_y_or_n(f'path: {path}\ncsvが存在しています。上書きして良いですか', send=True)
            if judge is False:
                big_print('csvの保存を中止しました', 'on_red')
                return

        # fieldnames がなければcsvの作成ができない
        if fieldnames is None:
            input('input: fieldnamesが指定されていないのでcsvを作成できません')
            return
        # csvを作成する
        with open(path, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            # ヘッダーを書き込む
            writer.writeheader()
            # データがなければヘッダーだけにする
            if data:
                writer.writerows(data)
        big_print(f'csvを新規作成しました -> {path}', 'yellow')

    else:
        input('input: データを作成できません')

def get_csv_file_name(directory_path):
    """
    ディレクトリにあるcsvファイル名を返す
    """
    for root, _, files in os.walk(directory_path):
        for file in files:
            # CSVファイルのみを対象とする
            if file.endswith(".csv"):
                return file

def save_zstd(save_path, data):
    """
    zstdデータで保存する
    """
    json_str = json.dumps(data)  # JSONを文字列に変換

    # 圧縮
    cctx = zstd.ZstdCompressor(level=22)  # 最大圧縮率
    compressed = cctx.compress(json_str.encode())

    # 保存
    with open(save_path, "wb") as f:
        f.write(compressed)

def read_data_with_make_data(path, *, file_type, fieldnames=None):
    """
    データを読み込む。もしそのデータがなければ、新規作成する
    - Args:
        - file_type: csv, json, gzip, を指定する
    """
    # 親ディレクトリがなければ作成する
    parent_dir = os.path.dirname(path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    if file_type == 'csv':
        if not os.path.exists(path):
            # fieldnames がなければcsvの作成ができない
            if fieldnames is None:
                return
            # csvを作成する
            with open(path, mode='w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                # ヘッダーを書き込む
                writer.writeheader()
            big_print(f'csvを新規作成しました -> {path}', 'yellow')

    # jsonでデータがないときNoneを返す
    if file_type in ('json', 'gzip'):
        if not os.path.exists(path):
            return

    return read_data(path, file_type=file_type)

