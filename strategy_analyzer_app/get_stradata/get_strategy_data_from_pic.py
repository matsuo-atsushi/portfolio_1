"""
ハンド履歴(画像)からゲーム内容を読み込む
"""

import os
import shutil
import numpy as np
import cv2
import json
import csv
from datetime import datetime
import traceback
import hashlib

from strategy_analyzer_app.io_operations.print_processing import big_print, suppress_print
from strategy_analyzer_app.text_processing.text_extraction import convert_number, delete_non_numbers
import strategy_analyzer_app.global_vars as glbvar
import strategy_analyzer_app.image_processing.image_handling as imghdr
import strategy_analyzer_app.display_processing.get_data_from_screen as ctlscr
import strategy_analyzer_app.poker_logic.poker_action_processing as pkac
import strategy_analyzer_app.io_operations.csv_processing as csvproce
import strategy_analyzer_app.io_operations.directory_operations as ctldir
import strategy_analyzer_app.utils.other_utils as oths

stradata_pic_dir = 'resources/3_history_img'
stradata_for_save_dir = 'resources/1_historys/1_anlz'
player_name_dir = 'resources/2_playerdata/name_image/1_anlz'
player_private_dir = 'resources/2_playerdata/IDs/1_anlz'
tmp_save_dir = 'resources/5_tmp_data/1_anlz'
used_pic_dir = 'resources/3_history_img/1_used'
duplicates_dir = 'resources/3_history_img/3_duplicates'
error_data_dir = 'resources/3_history_img/2_error_data'
id_whitelist_csv = 'resources/4_whitelist/anlz_id_whitelist.csv'
ocr_whitelist_csv = 'resources/4_whitelist/anlz_ocr_whitelist.csv'

# 座標データ
ranges = {
    'general': {
        'name': {
            'width': 73,
            'height': 18,
            'trim': {
                'blank': 3*5,
                'width': 67*5,
                'height': 12*5,
            }
        },
        'stack': {
            'width': 73,
            'height': 17,
        },
        'btn': {
            'width': 26,
            'height': 26,
        },
        'other_hand': {
            'width1': 19,
            'width2': 16,
            'height': 30,
        },
        'my_hand': {
            'width1': 19,
            'width2': 19,
            'height': 35,
        },
    },
    'personal': {
        'player_1': {
            'name': {'x': 338, 'y': 92},
            'stack': {'x': 338, 'y': 92+18},
            'btn': {'x': 310, 'y': 116},
            'hand': {'x': 348, 'y': 37},
        },
        'player_2': {
            'name': {'x': 513, 'y': 226},
            'stack': {'x': 513, 'y': 226+18},
            'btn': {'x': 480, 'y': 218},
            'hand': {'x': 522, 'y': 171},
        },
        'player_3': {
            'name': {'x': 513, 'y': 463},
            'stack': {'x': 513, 'y': 463+18},
            'btn': {'x': 488, 'y': 455},
            'hand': {'x': 523, 'y': 408},
        },
        'player_4': {
            'name': {'x': None, 'y': None},
            'stack': {'x': 338, 'y': 675},
            'btn': {'x': 312, 'y': 588},
            'hand': {'x': 404, 'y': 605},
        },
        'player_5': {
            'name': {'x': 160, 'y': 463},
            'stack': {'x': 160, 'y': 463+18},
            'btn': {'x': 235, 'y': 454},
            'hand': {'x': 169, 'y': 408},
        },
        'player_6': {
            'name': {'x': 160, 'y': 226},
            'stack': {'x': 160, 'y': 226+18},
            'btn': {'x': 242, 'y': 216},
            'hand': {'x': 171, 'y': 171},
        },
    },
    'board_card':{
        'general': {
            'width': 24,
            'height': 44,
        },
        'start_range': {
            'flop': {
                'card1':{'x': 238, 'y': 258},
                'card2':{'x': 238+56, 'y': 258},
                'card3':{'x': 238+56+56, 'y': 258},
                },
            'turn': {
                'card4':{'x': 238+56+56+56, 'y': 258},
                },
            'river': {
                'card5':{'x': 238+56+56+56+56, 'y': 258},
                },
            },
    },
}

# 画像データ
template_link = {
    'icon_BB_semibinary': 'strategy_analyzer_app/get_stradata/icon/icon_BB_semibinary.jpg',
    'icon_BB_binary': 'strategy_analyzer_app/get_stradata/icon/icon_BB_binary.jpg',
    'icon_BB_binary_reverse': 'strategy_analyzer_app/get_stradata/icon/icon_BB_binary_reverse.jpg',
    'icon_BB_original': 'strategy_analyzer_app/get_stradata/icon/icon_BB_original.jpg',
    'icon_btn': 'strategy_analyzer_app/get_stradata/icon/icon_BTN.jpg',
    'pot_BB_icon': 'strategy_analyzer_app/get_stradata/icon/strategy/pot_amount/BB.jpg',
    'other_hand': {
        'marks': 'strategy_analyzer_app/get_stradata/icon/hand/enemy/marks',
        'numbers': 'strategy_analyzer_app/get_stradata/icon/hand/enemy/numbers/sharp',
    },
    'my_hand': {
        'marks': 'strategy_analyzer_app/get_stradata/icon/hand/my/marks',
        'numbers': 'strategy_analyzer_app/get_stradata/icon/hand/my/numbers/sharp',
    },
    'board_card': {
        'marks': 'strategy_analyzer_app/get_stradata/icon/board/marks',
        'numbers': 'strategy_analyzer_app/get_stradata/icon/board/numbers/sharp',
    },
    'stradata_dir': {
        'positions': 'strategy_analyzer_app/get_stradata/icon/strategy/positions',
        'my_actions': 'strategy_analyzer_app/get_stradata/icon/strategy/actions/my',
        'my_BB': 'strategy_analyzer_app/get_stradata/icon/strategy/actions/my/BB.jpg',
        'other_actions': 'strategy_analyzer_app/get_stradata/icon/strategy/actions/others',
        'other_BB': 'strategy_analyzer_app/get_stradata/icon/strategy/actions/others/BB.jpg',
    },
    'bet_numbers': 'strategy_analyzer_app/get_stradata/icon/strategy/bet_amount/numbers',
    'pot_numbers': 'strategy_analyzer_app/get_stradata/icon/strategy/pot_amount/numbers',
    'stack_numbers': 'strategy_analyzer_app/get_stradata/icon/strategy/stack_amount/numbers',
}

# stradataを得るための座標
straranges = {
    'general': {
        'y_start': 797,
        'width': 188,
        'actions': {
            'posi_blank': 13,
            'action_width': 110,
            'action_top': 18,
            'action_bottom': 48,
            'bet_blank': 11,
            'posiimg_width': 38,
            'BB_top': 11,
        },
        'my_action': {
            'serch_edge_x_end': 90,
            'serch_edge_y_start': 25,
            'serch_edge_y_end': 55,
            'edge_blank': 28,
            'edge_link': 'strategy_analyzer_app/get_stradata/icon/strategy/actions/my/edge/edge_img.jpg',
        },
        'name': {
            'posi_upper': 21,
            'height': 20,
            'width': 80,
        },
        'pot_display': {
            'width': 178,
            'height': 30,
            'y_start': 759,
            'flop': {'x_start': 195},
            'turn': {'x_start': 385},
            'river': {'x_start': 570},
        },
    },
    'phase': {
        'preflop': {
            'x_start': 0,
        },
        'flop': {
            'x_start': 187,
        },
        'turn': {
            'x_start': 375,
        },
        'river': {
            'x_start': 562,
        },
    },
    'get': {
        'template': {
            'my': 'strategy_analyzer_app/get_stradata/icon/strategy/actions/my/get_BB.jpg',
            'other': 'strategy_analyzer_app/get_stradata/icon/strategy/actions/others/get_BB.jpg',
            },
        'range': {
            'BB': {
                'x_start': 16,
                'upper': 4,
                'bottom': 23,
            },
            'name': {
                'bottom': 9,
                'height': 32,
                'x_start': 46,
                'width': 125,
                },
        }
    },
}

# global変数の宣言
kk_stranumber = None # 画像の名前。エラーディレクトリを作成するときに使用する
template_ocr_error_msg_list = []
some_error_msg_list = []
resent_player_id_list = [] # 最近見つけたIDを追加する。この中から優先して探す
save_error_directory = ''

def main():
    """
    処理:
    1, 画像を順に読み込む
    2, まず、過去に読み込んだ画像かどうか判定をする
    3, 問題なければ、解析に進む
    """

    global kk_stranumber, template_ocr_error_msg_list, some_error_msg_list, resent_player_id_list, save_error_directory

    # 画像を一枚づつ処理する
    sorted_pics = collect_and_sort_files_for_stradata(stradata_pic_dir)

    # stradataの保存先を作成する
    today = datetime.now().strftime("%y%m%d")
    stradata_dir_for_save = os.path.join(stradata_for_save_dir, today)
    if not os.path.exists(stradata_dir_for_save):
        os.makedirs(stradata_dir_for_save)

    # 最新2つのディレクトリ名を取り出す
    latest_dirs = get_latest_stradir()

    for pic in sorted_pics:

        some_error_msg_list = [] # エラーリストを初期化
        template_ocr_error_msg_list = []
        resent_player_id_list = list(dict.fromkeys(resent_player_id_list)) # 見つけたidの重複を除く

        pic_path = os.path.join(stradata_pic_dir, pic)
        kk_stranumber = os.path.splitext(pic)[0]
        stranumber = delete_non_numbers(kk_stranumber, print_text=False, non_float=True)
        # まだ調べていないファイルかどうかチェックする
        if check_exist_stradata_file(latest_dirs, stranumber, pic_path) is False:

            # error_dir_pathの用意
            save_error_directory = os.path.join(error_data_dir, today, kk_stranumber)

            big_print(f'これからstradataを作成します -> stranumber: {stranumber}', 'white')
            sequence_make_stategy_report_from_pic(pic_path, stranumber, stradata_dir_for_save, today)
        else:
            big_print(f'既にstradataを作成していると思われるので処理をパスして、画像を移動させます -> stranumber: {stranumber}', 'red')
            same_name_data_move_to_other_dir(pic_path, stranumber, today)

    print('今回見つけたid:')
    resent_player_id_list = list(set(resent_player_id_list))
    for anlz_id in resent_player_id_list:
        print(anlz_id)

    # エラーディレクトリを振り分ける
    assign_error_dir(today)

def sequence_make_stategy_report_from_pic(pic_path, stranumber, stradata_dir_for_save, today):
    """
    画像のパスを受取り、stradataを作成する
    1, 画像上半分から得られるデータをまとめる
    2, 画像下半分のデータをまとめる
    3, 保存する
    """
    # 画像上半分から得られるデータをまとめる
    strategy_data = make_general_data(pic_path)

    # 画像下半分を読み込んで、データをまとめる
    strategy_data = make_strategy_data(pic_path, strategy_data)

    # 各プレイヤーのディレクトリにstranumberを足す
    abb_stranumber_for_each_ID(strategy_data, stranumber)

    # jsonで保存する
    path_for_save = os.path.join(stradata_dir_for_save, f'{stranumber}.json')
    with open(path_for_save, "w", encoding="utf-8") as file:
        json.dump(strategy_data, file, ensure_ascii=False, indent=4)

    # 画像を移動させる
    # 保存先のディレクトリを用意
    destination_dir_path = os.path.join(used_pic_dir, today)
    if not os.path.exists(destination_dir_path):
        os.makedirs(destination_dir_path)

    # 保存先の画像データのpathを用意
    destination_path = os.path.join(destination_dir_path, f'{stranumber}.jpg')
    # 移動させる
    shutil.move(pic_path, destination_path)

    # 画像サイズを記録する
    add_img_size(destination_path, stranumber, today)

    big_print(f'\nデータの作成が完了しました\n元画像: {destination_path}\nstradata: {path_for_save}\n', 'white', '-')

    # エラーデータを保存するディレクトリを用意する
    parent_dir = os.path.join(error_data_dir, today, kk_stranumber)
    if len(strategy_data['general']['error_message']) >= 1:

        # エラーディレクトリを削除していいか調べる
        should_delete_err_dir = judge_delete_error_dir(strategy_data['general']['error_message'])
        if should_delete_err_dir:
            big_print(f'エラーはすべて解決しているようなので、エラーディレクトリを削除します', 'on_yellow')
            shutil.rmtree(parent_dir)
            big_print(f"ディレクトリ {parent_dir} を削除しました。", 'yellow')
            return

        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        # 画像のコピーを作成
        img_name = os.path.basename(pic_path)
        img_name = os.path.splitext(img_name)[0]
        error_img_path = os.path.join(parent_dir, f'{img_name}.jpg')
        shutil.copy(destination_path, error_img_path)
        # stradataのコピーを作成
        error_stradata_path = os.path.join(parent_dir, f'{img_name}.json')
        shutil.copy(path_for_save, error_stradata_path)

        big_print(f'\nエラーがあったようなので、データのコピーを作成しました\nディレクトリ: {parent_dir}\n', 'red', '▲')
    elif os.path.exists(parent_dir):
        big_print(f'エラーはすべて解決しているようなので、エラーディレクトリを削除します', 'on_yellow')
        shutil.rmtree(parent_dir)
        big_print(f"ディレクトリ {parent_dir} を削除しました。", 'yellow')

def judge_delete_error_dir(error_data, * , negative_target_list = ['<-'], positive_target_list=[]):
    """
    解決したエラーのみのとき、errorディレクトリごと削除する
    - Args:
        - negative_target_list: これを含む値がなければTrueを返す
        - positive_target_list: これを含む値があればTrueを返す
    - 処理:
        - エラーメッセージに、<- が入ったものしかないとき、削除する
    """

    try:
        for error_msg in error_data:
            for msgs in error_msg.values():
                for msg in msgs:
                    for message in msg:
                        # メッセージの中に、targetがないならTrue
                        for not_string in negative_target_list:
                            if not_string not in message:
                                return False
                        # メッセージの中に、targetがあればTrue
                        for posi_string in positive_target_list:
                            if posi_string in message:
                                return True
        # targetのものがないことを確認したとき
        if negative_target_list:
            return True
        # targetのものがなかった
        elif positive_target_list:
            return False
    except Exception as e:
        traceback.print_exc()
        return False

def abb_stranumber_for_each_ID(strategy_data, stranumber):
    """
    各プレイヤーの'history_stranumber.csv'に履歴を足す
    """
    # 各プレイヤーのIDを取り出す
    user_IDs = [data['ID'] for data in strategy_data['general']['all_players'].values() if data['ID'] is not None]
    for target_id in user_IDs:

        # csvのpathを作成
        history_csv_path = os.path.join(player_private_dir, target_id, 'history_stranumber.csv')
        fieldnames = ['stranumber']

        # 各プレイヤーにIDのディレクトリが存在するかチェック
        private_dir = os.path.join(player_private_dir, target_id)
        if not os.path.exists(private_dir):
            os.makedirs(private_dir)
            # dirを新規作成したなら、csvも作成する
            with open(history_csv_path, mode='w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                # ヘッダーを書き込む
                writer.writeheader()
            big_print(f'history_stranumbers.csvを新規作成しました -> ID: {target_id}', 'yellow')
        else:
            big_print(f'既に個人のディレクトリが存在します。ID: {target_id}', 'white')

        # csvにデータを追加
        with open(history_csv_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

            # stranumberが存在するか確認
            if any(row['stranumber'] == stranumber for row in rows):
                print(f'stranumberに "{stranumber}" は既に存在します -> ID: {target_id}')
                continue
            else:
                new_data = {'stranumber':stranumber}
                # CSVファイルを上書き保存
                with open(history_csv_path, mode='a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writerow(new_data)

    big_print(f'stranumberを追加しました -> user_IDs: {user_IDs}', 'white')

# ==========================
# 画像下半分の処理
# ==========================

def make_strategy_data(pic_path, strategy_data):
    """
    画像下半分から、データを取り出す
    """
    # 画像の高さを求める <- トリムに使用する
    imread_pic = cv2.imread(pic_path)
    y_end, _, _ = imread_pic.shape
    # 空席リストを作る。IDがNoneの人で、自分ではない
    absent_list = [data['position'] for player, data in strategy_data['general']['all_players']. items() if data['ID'] is None and player != 'player_4']
    # 初期データ用意
    game_data = {'init_pot': 0, 'pot': 1.5, 'original_Raiser': None, 'most_bet': 1, 'phase': None, 'got_name': glbvar.made_turn_copy.copy(),
                'each_position_bet': {}, 'total_each_bet': glbvar.made_turn_copy.copy(),
                'absent_list': absent_list, 'absent_conver_dict': {}, 'Fold_list': absent_list.copy(),
                'add_totalbet_for_Fold': glbvar.made_turn_copy.copy(), 'Allin_position': []}

    get_amount = {} # 勝者の賞金が入る
    for phase in glbvar.phase_order:

        # フェーズごとにトリムする
        trim_straimg_path = trim_phase_img(pic_path, phase, y_end)
        # ポジションをmatchさせて各ポジションの座標を求める
        position_locations = get_position_locations(trim_straimg_path, strategy_data, game_data)
        # positionの正順をする
        position_locations = sort_position_locations(position_locations)

        # ポジションが2つ以上見つからなかったらパス
        if len(position_locations) >= 1:
            big_print(f'これから"{phase}"を調べます', 'white')

            # ゲーム開始時のデータを更新
            strategy_data['history'][phase]['original_Raiser'] = game_data['original_Raiser']
            strategy_data['history'][phase]['pot'] = game_data['pot']
            # game_dataの更新
            game_data['phase'] = phase
            if phase != 'preflop':
                game_data['init_pot'] = game_data['pot']
                game_data['most_bet'] = 0

            # アクションを求める
            all_report, game_data = make_all_report(trim_straimg_path, position_locations, y_end, game_data)
            # 保存する
            strategy_data['history'][phase]['strategy_history'] = all_report

            # total_each_bet を更新する
            game_data = calcurate_total_each_bet(game_data)

            # ゲーム終了の確認をする <- winnerがいるかどうか
            winner, _ = check_winner_and_alive_list(strategy_data, current_phase_list=True)
            if winner:
                big_print(f'"{phase}"でゲーム終了です', 'white')
                # flopのときsituationを更新する
                if phase == 'flop':
                    strategy_data = check_situation(strategy_data)
                break
        else:
            big_print(f'フェーズ({phase})は既に終わっています', 'cyan')

        # 獲得を調べるときは、winnerが決まってなくて、riverのとき
        if phase == 'river' and winner is None:
            big_print(f'勝者が明確ではないので、"獲得"を探します', 'yellow')
            get_amount = check_winner_with_getimg(trim_straimg_path, strategy_data, game_data)
        # flopのときsituationを更新する
        if phase == 'flop':
            strategy_data = check_situation(strategy_data)

    # 下記のとき変なことになっているので、色々処理を飛ばす
    if 'alive_listが空です' in some_error_msg_list:
        pass
    else:
        # initial_stackを更新する
        strategy_data = calcurate_initial_stack(strategy_data, game_data, winner, get_amount)

    # エラーをstrategy_dataに追加する
    error_mags = []
    for err_msg in some_error_msg_list:
        if err_msg:
            error_mags.append([err_msg])
    if error_mags:
            strategy_data['general']['error_message'].append({'strategy_historys': error_mags})

    # 下記のとき変なことになっているので、色々処理を飛ばす
    if 'alive_listが空です' in some_error_msg_list:
        pass
    else:
        # 読み取ったデータがおかしくないかのチェックをする
        strategy_data = check_wrong_strategy_data(strategy_data, pic_path)

    # エラーをstrategy_dataに追加する
    if template_ocr_error_msg_list:
        strategy_data['general']['error_message'].append({'template_ocr': template_ocr_error_msg_list})

    return strategy_data

def check_wrong_strategy_data(strategy_data, pic_path):
    """
    読み取ったデータがおかしくないかチェックする
    - 処理:
        - Foldした人がアクションしない
        - アクションの順が正しい
        - フェーズが終わる状況が正しい
        - 空席の対応
    """

    print('これからcheck_wrong_strategy_data()を実行します')

    absent_list = [data['position'] for player, data in strategy_data['general']['all_players']. items() if data['ID'] is None and player != 'player_4']

    Fold_list = [] # foldした人を入れる
    absent_conver_dict = {} # 空席のポジションを変換するためのデータを作成する
    Allin_list = []
    error_mags = []

    for phase, data in strategy_data['history'].items():

        print(f'   - "{phase}"を確認します')

        action_report = glbvar.made_turn_copy.copy()
        most_bet = 0
        posi_index = 0 # あるべきポジションを取り出すのに使う
        pre_index = 0 # 前回のポジションのインデックスを入れる。これが、posi_indexよりも大きくなったとき、round_numを+1する
        shold_end_phase = False # ゲームが終わるべきとき、Trueになる。これがTrueのときに次のプレイヤーが取り出されたらおかしい
        modifiy_allreport = {} # 修正するとき、このallreportを使う
        error_report_dict = {} # ポジションを間違えて取り出されたとき、修正するための辞書
        if phase == 'preflop':
            round_num = 0 # UTGまで来たら、1とする
        else:
            round_num = 1

        all_report = data['strategy_history']
        for posidata, action in all_report.items():
            # ポジションを取り出す
            position = posidata.split('_')[1]

            # ポジションの変換
            if position in absent_conver_dict:
                old_posi = position
                position = absent_conver_dict[old_posi]
                big_print(f'stradataでは"{old_posi}"は欠席者としています。ポジションを変換します {old_posi} -> "{position}"', 'white')

            if shold_end_phase:
                big_print(f'フェーズ1つ前で既に終わるべきなのに、次のプレイヤーが取り出されました\n position: {position}\n strategy_data["history"]: {strategy_data["history"]}', 'red', '▲')
                # エラーメッセージを追加
                error_mags.append([f'{phase} | {posidata}: フェーズ1つ前で既に終わるべきなのに、次のプレイヤーが取り出されました position: {position}'])
                # strategy_data['general']['error_message'].append({phase: {posidata: f'フェーズ1つ前で既に終わるべきなのに、次のプレイヤーが取り出されました position: {position}'}})
            # foldした人が取り出されないことを確認
            if position in Fold_list:
                big_print(f'Foldした人がアクションしているようです\n position: {position}\n strategy_data["history"]: {strategy_data["history"]}', 'red', '▲')
                error_mags.append([f'{phase} |  {posidata}: Foldした人がアクションしているようです position: {position}'])
                # strategy_data['general']['error_message'].append({phase:  {posidata: f'Foldした人がアクションしているようです position: {position}'}})

            # 行われるべきポジションを取り出す
            should_position = get_should_position(Fold_list+Allin_list, posi_index)
            #* round_numを更新する
            # 現在のポジションを取り出す
            posi_index = glbvar.postflop_order.index(should_position)
            # round_numを更新すべきか調べる
            round_num = calcurate_round_num(phase, round_num, pre_index, posi_index)

            if should_position != position:
                # ハンド履歴と、stradataで、空席のポジションの扱いが異なるので、変換用データを作成する
                if phase == 'preflop' and round_num == 1 and absent_list:
                    #! allreportを作成するときにポジションの変換を行っているので、下記が行われることはないはず
                    absent_conver_dict = make_absent_conver_dict(should_position, position, absent_list, absent_conver_dict)
                    position = absent_conver_dict[position]
                else:
                    big_print(f'次に行われるべきポジションではない人がreportから取り出されました\n position: {position}, should_position: {should_position}\n strategy_data["history"]: {strategy_data["history"]}', 'red', '▲')
                    # 修正するためのデータを用意する
                    modifiy_allreport[f'{len(modifiy_allreport)}_{should_position}'] = None
                    error_report_dict[posidata] = action
                    error_mags.append([f'{phase} | {posidata}: 次に行われるべきポジションではない人がreportから取り出されました position: {position}, should_position: {should_position}'])
                    # strategy_data['general']['error_message'].append({phase: {posidata: f'次に行われるべきポジションではない人がreportから取り出されました position: {position}, should_position: {should_position}'}})
            else:
                # 修正するときに使う
                modifiy_allreport[f'{len(modifiy_allreport)}_{should_position}'] = action

            # アクションを記録する
            if 'Fold' in action:
                # 正常なとき、追加する
                if should_position == position:
                    Fold_list.append(position)
                else:
                    # 既に、現在のポジションがerrorリストに入っていたらerrorリストのFoldしてる人をすべてFoldリストに追加する
                    if next((True for posidata in error_report_dict if should_position in posidata), False):
                        for error_posidata, error_action in error_report_dict.items():
                            error_position = error_posidata.split('_')[1]
                            if 'Fold' in error_action:
                                Fold_list.append(error_position)

            elif 'Check' in action or 'Call' in action:
                action_report[position] = most_bet
            else:
                # bet額を取り出す
                if '(' in action:
                    amount = float(action.split('(')[0])
                else:
                    amount = delete_non_numbers(action, print_text=False)
                # Raiseなのに、前のbetよりも小さいとき、エラーを出す
                if 'Raise' in action and most_bet >= amount:
                    big_print(f'Raiseなのに、前のプレイヤーよりも額が小さいです', 'red', '▲')
                    error_mags.append([f'{phase} |  {posidata}: Raiseなのに、前のプレイヤーよりも額が小さいです'])
                    # strategy_data['general']['error_message'].append({phase:  {posidata: f'Raiseなのに、前のプレイヤーよりも額が小さいです'}})

                most_bet = max(most_bet, amount)
                action_report[position] = amount
                if 'Allin' in action and position not in Allin_list:
                    Allin_list.append(position)

            # このターンにゲームが終わるべきか調べる
            Fold_list = list(set(Fold_list)) # Foldしてる人の被りを除く
            shold_end_phase = check_shold_end_phase(action_report, Fold_list, Allin_list, posi_index, most_bet, phase, round_num)

            # 現在のposi_indexを記録する
            pre_index = posi_index
            # posi_index の更新
            posi_index += 1
            if posi_index >= 6: # 6以上になるときは0に戻す
                posi_index = 0

        if shold_end_phase is False and all_report:
            big_print(f'フェーズはまだ終わるべきでないのに、終わりました\n action_report: {action_report}, Fold_list: {Fold_list}, most_bet: {most_bet}\n strategy_data["history"]: {strategy_data["history"]}', 'red', '▲')
            error_mags.append([f'{phase}: フェーズはまだ終わるべきでないのに、終わりました'])
            # strategy_data['general']['error_message'].append({f'{phase}': f'フェーズはまだ終わるべきでないのに、終わりました'})
        if error_report_dict:
            big_print(f'エラーがあったようなので、allreportを修正します', 'red')
            error_mags.append(['msg(1): エラーがあったようなので、allreportを修正します'])
            # strategy_data['general']['error_message'].append({'msg(1)': f'エラーがあったようなので、allreportを修正します'})
            strategy_data['history'][phase]['strategy_history'], error_positive = modify_allreport_with_error(modifiy_allreport, error_report_dict)
            if error_positive:
                error_mags.append(['msg(2): allreportを修正するときに、エラーがあったようです'])
                # strategy_data['general']['error_message'].append({'msg(2)': f'allreportを修正するときに、エラーがあったようです'})

    if error_mags:
        strategy_data['general']['error_message'].append({'allreport': error_mags})

    # inital_stackが問題ないか調べる
    strategy_data = check_strange_intial_stack(strategy_data)

    # potをocrして、計算と違いがないか調べる
    strategy_data = check_strange_pot_value(pic_path, strategy_data)

    # handが1つしかない人はエラー出す <- プロフィールをカードと読み間違えている可能性を除きたい
    strategy_data = check_only_one_hand(strategy_data)

    # 確認したカードで被りがないことを確認する
    strategy_data = check_duplicate_card(strategy_data)

    print('check_wrong_strategy_data()が終わりました')

    return strategy_data

def modify_allreport_with_error(modifiy_allreport, error_report_dict):
    """
    最後のチェック時にポジションのエラーがあったとき、allreportを修正する
    """
    # エラーのポジションを取りだす
    error_posidata = [posidata for posidata, action in modifiy_allreport.items() if action is None]
    error_positive = False

    for posidata in error_posidata:
        # 修正するポジションを取り出す
        position = posidata.split('_')[1]
        # そのポジションで最も先頭にあるデータを取り出す
        fix_posidata = next((posidata for posidata in error_report_dict if position in posidata), None)

        if fix_posidata is None:
            error_positive = True
            break

        # allreportを更新する
        modifiy_allreport[posidata] = error_report_dict[fix_posidata]
        # 辞書から削除する
        del error_report_dict[fix_posidata]

    return modifiy_allreport, error_positive

def calcurate_round_num(phase, round_num, pre_index, posi_index):
    """
    position indez からround_numを更新すべきか調べる
    """
    # preflopのとき
    if phase == 'preflop':
        # 前のポジションがUTG~BTNで、現在のポジションが、SB,BB のときは更新しない
        if 2 <= pre_index <= 5 and 0 <= posi_index <= 1:
            return round_num
        # 前のポジションがSB, BB, で、今のポジションが、UTG~BTNのとき、更新する
        if 0 <= pre_index <= 1 and 2 <= posi_index <= 5:
            return round_num + 1
        # それ以外で、前よりも数字が小さくなっていたら、更新
        if pre_index > posi_index:
            return round_num + 1
        return round_num

    # preflop以外は、前よりも数字が小さくなっていたら、更新
    if pre_index > posi_index:
        return round_num + 1
    return round_num

def make_absent_conver_dict(should_position, position, absent_list, absent_conver_dict):
    """
    ハンド履歴とstradataの空席者のポジションの扱いが異なるので、変換用のデータを作成する
    一人目を取り出すときに、齟齬が起きる。多分、それ以外は起きないと思う
    ハンド履歴では、UTGは絶対に存在する。けど、stradataでは、UTGからいないことにする。そこで齟齬が起きる
    TODO 2人以上欠席者がいるときの、ハンド履歴の処理がわからないので、調べる
    - 説明:
        - absent_conver_dict:
            reportから取り出されたpositionをこれを使ってstradataに合わせたポジションに変換する
    """
    absent_conver_dict[position] = should_position
    absent_conver_dict[should_position] = position

    big_print(f'欠席者のポジションをハンド履歴と整合性をあわせるための辞書を作成しました -> {absent_conver_dict}', 'yellow')

    return absent_conver_dict

def check_shold_end_phase(action_report, Fold_list, Allin_list, posi_index, most_bet, phase, round_num):
    """
    このターンでフェーズが終わるべきか調べる
    - 処理:
        - 次のポジションを調べる
        - そのプレイヤーがmost_betと同じなら終了すべき
    """
    posi_index += 1
    if posi_index >= 6: # 6以上になるときは0に戻す
        posi_index = 0

    if len(Fold_list) >= 5:
        return True

    next_position = get_should_position(Fold_list + Allin_list, posi_index)
    # 残りのプレイヤーが全員Allinしたら、下記になる
    if next_position is None:
        big_print('全員Allinしました', 'white')
        return True
    pre_action = action_report[next_position]

    # まだアクションがないなら、ゲームは続く
    if pre_action is None:
        return False
    # most_betと同じならフェーズ終了
    elif pre_action == most_bet:
        # プリフロップ1週目で、BBがcheckできるときは、Falseを返す
        if phase == 'preflop' and next_position == 'BB' and most_bet == 1 and round_num == 1:
            return False
        return True
    else:
        return False

def get_should_position(Fold_list, posi_index):

    """
    次に行われるべきポジションを取り出す
    - 処理:
        - posi_indexから、1つ前のポジションを判定
        - まだ、foldしていない人の次のポジションを取り出す
    """
    next_position = glbvar.postflop_order[posi_index]
    finded_pre_posi = False
    i = 0
    while i < 2:
        for position in glbvar.postflop_order:
            # next_positionを見つけるまでパスし続ける
            if finded_pre_posi is False:
                if position == next_position:
                    finded_pre_posi = True
            # next_positionを見つけたあと、Foldしていない人を返す
            if finded_pre_posi:
                if position not in Fold_list:
                    return position
        i += 1

def make_all_report(trim_straimg_path, position_locations, y_max, game_data):
    """
    画像からall_reportを作成する
    * ここではreportの補正は行わない
    """
    all_report = {}
    posi_index = 0
    round_num = 1
    for data in position_locations:
        position = data['position']
        # 空席でポジションが異なるとき、変換する
        if position in game_data['absent_conver_dict']:
            old_posi = position
            position = game_data['absent_conver_dict'][position]
            big_print(f'stradataでは"{old_posi}"は欠席者としています。ポジションを変換します {old_posi} -> "{position}"', 'white')
        # 行われるべきポジションを取り出して、異なるとき、対応する
        should_position = get_should_position(Fold_list=game_data['Fold_list'], posi_index=posi_index)
        if position != should_position:
            if game_data['phase'] == 'preflop' and round_num == 1 and game_data['absent_list']:
                game_data['absent_conver_dict'] = make_absent_conver_dict(should_position, position, game_data['absent_list'], game_data['absent_conver_dict'])
                all_report = add_absent_data_for_all_report(all_report, game_data['absent_list'])
                position = game_data['absent_conver_dict'][position]
            else:
                big_print(f'次に行われるべきポジションではない人がreportから取り出されました\n position: {position}, should_position: {should_position}\n data: {data}', 'red', '▲')

        # トリムするための座標を用意
        # otherのとき
        if 50 > data['x']:
            x_start = data['x'] + straranges['general']['actions']['posiimg_width'] + straranges['general']['actions']['posi_blank']
            x_end = x_start + straranges['general']['actions']['action_width']
            y_start = data['y'] - straranges['general']['actions']['action_top']
            y_end = data['y'] + straranges['general']['actions']['action_bottom']
            status = {'player': 'other', 'init': False}
        else:
            x_start = data['x'] - straranges['general']['actions']['posi_blank'] - straranges['general']['actions']['action_width']
            x_end = data['x'] - straranges['general']['actions']['posi_blank']
            y_start = data['y'] - straranges['general']['actions']['action_top']
            y_end = data['y'] + straranges['general']['actions']['action_bottom']
            status = {'player': 'my', 'init': False}
        # y_endが画像よりも大きくなったら、補正する
        if y_max < y_end:
            y_end = y_max

        # 最初のSB, BBはinitを調べる
        if game_data['phase'] == 'preflop' and position in ('SB', 'BB') and len(all_report) < 2:
            status['init'] = True

        # トリムした画像を保存するpathを作成
        trim_straimg_action = os.path.join(tmp_save_dir, f'straimg_{position}.jpg')
        # トリム実行
        imghdr.trim_image_without_resize(trim_straimg_path, x_start, x_end, y_start, y_end, name=trim_straimg_action, binary=False)

        # actionをmatchtemplateで調べる
        action_data = get_action_with_template(trim_straimg_action, trim_straimg_path, status, data)
        print(f'{position} -> {action_data}')
        if action_data is None:
            some_error_msg_list.append(f'{position}: アクションが見つかりませんでした')
            ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [trim_straimg_action], error_type=f'cant_get_action_{position}')

        if status['init'] and action_data is None:
            if position == 'SB':
                action_data = {'action': 'init_SB', 'bet_amount': None}
            elif position == 'BB':
                action_data = {'action': 'init_BB', 'bet_amount': None}

        if 'Fold' in action_data['action'] or 'Allin' in action_data['action']:
            game_data['Fold_list'].append(position)

        all_report, game_data = add_all_report_with_action_data(all_report, game_data, action_data, position)

        # 名前を保存してないとき、保存する
        if game_data['got_name'][position] is None:
            # otherのとき
            if 50 > data['x']:
                x_start = data['x'] + straranges['general']['actions']['posiimg_width']
                x_end = x_start + straranges['general']['name']['width']
                y_start = data['y'] - straranges['general']['name']['posi_upper'] - straranges['general']['name']['height']
                y_end = data['y'] - straranges['general']['name']['posi_upper']
            else:
                x_start = data['x'] - straranges['general']['actions']['posi_blank'] - straranges['general']['actions']['posiimg_width']
                x_end = data['x'] - straranges['general']['actions']['posi_blank']
                y_start = data['y'] - straranges['general']['name']['posi_upper'] - straranges['general']['name']['height']
                y_end = data['y'] - straranges['general']['name']['posi_upper']

            # トリムした画像を保存するpathを作成
            trim_straimg_action = os.path.join(tmp_save_dir, f'straimg_name_{position}.jpg')
            # トリム実行(二値化してみる)
            imghdr.trim_image_without_resize(trim_straimg_path, x_start, x_end, y_start, y_end, name=trim_straimg_action, binary=True)
            game_data['got_name'][position] = True

        # posi_index の更新
        posi_index = glbvar.postflop_order.index(should_position) # 現在のポジションを取り出す
        posi_index += 1
        if posi_index >= 6: # 6以上になるときは0に戻す
            posi_index = 0
            round_num += 1

    # ポットを計算する
    game_data = calcurate_pot(all_report, game_data, end_phase=True)

    return all_report, game_data

def add_absent_data_for_all_report(all_report, absent_list):
    """
    欠席者の情報をallreportに追加する
    """
    if absent_list:
        for position in absent_list:
            all_report[f'{len(all_report)}_{position}'] = 'Fold'

    return all_report


def check_situation(strategy_data):
    """
    situationを確認する
    - 処理:
        - flopのallreportがない -> None
        - preflopのalivelistが2人 -> headsup
        - 3人以上 -> multiway
    """
    # プリフロップでwinnerが決まったか、Allinになったとき、下記になる
    if 'flop' not in strategy_data['history'] or strategy_data['history']['flop']['strategy_history'] == {}:
        # ときに何もせず終わる
        return strategy_data
    # preflopの時点のalivelistを作る
    alive_list = check_winner_and_alive_list(strategy_data, no_Allin_position=True, target_phase='preflop')
    if len(alive_list) == 2:
        situation = 'headsup'
    else:
        situation = 'multiway'

    # situationを更新
    strategy_data['general']['situation'] = situation

    return strategy_data

def check_winner_with_getimg(trim_straimg_path, strategy_data, game_data):
    """
    獲得が表示されていたら、BB額とプレイヤーの名前を判定する
    """
    # 初期データの用意
    made_turn = strategy_data['general']['made_turn']
    my_position = next(position for position, player in made_turn.items() if player == 'player_4')
    _, alive_position = check_winner_and_alive_list(strategy_data)
    base_img = cv2.imread(trim_straimg_path, cv2.IMREAD_COLOR)
    threshold = 0.96
    get_amount = {}
    pot = game_data['pot']

    # getをmatchする(my,other)の2つ
    for target, template_link_str in straranges['get']['template'].items():
        # templateを読み込む
        template_img = cv2.imread(template_link_str, cv2.IMREAD_COLOR)

        # テンプレートマッチングを実行
        result = cv2.matchTemplate(base_img, template_img, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        # しきい値を超える領域を取得
        locations = np.where(result >= threshold)

        # 座標とポジションをリストに入れる
        for pt in zip(*locations[::-1]):  # (x, y) 形式に変換
            # まず、get額を求める
            # 画像をトリムする
            x_start = straranges['get']['range']['BB']['x_start']
            x_end = pt[0]
            y_start = pt[1] - straranges['get']['range']['BB']['upper']
            y_end = pt[1] + straranges['get']['range']['BB']['bottom']
            # トリムした画像を保存するpathを作成
            trim_straimg_action_trim = os.path.join(tmp_save_dir, f'straimg_getBB_trim.jpg')

            # トリム実行(二値化なし)
            imghdr.trim_image_without_resize(trim_straimg_path, x_start, x_end, y_start, y_end, name=trim_straimg_action_trim, binary=False)

            #! リサイズ、ノイズ除去、二値化
            output_BB_2 = os.path.join(tmp_save_dir, f'straimg_getBB_template_trim.jpg')
            imghdr.binary_for_small_number_img_gen2(trim_straimg_action_trim, output_BB_2, scale=9, reverse=False)
            #! templateを使って数字を読み取る
            BB_value_from_template = get_number_with_location(output_BB_2, template_link['bet_numbers'], blank=5, error_tag='winner_get')

            # リサイズして二値化する
            imghdr.binary_for_small_number_img_gen2(trim_straimg_action_trim, trim_straimg_action_trim, scale=5)

            # OCRする
            bet_text, confi_score = imghdr.image_to_text(trim_straimg_action_trim, digits=' -c tessedit_char_whitelist=0123456789.')
            BB_value = delete_non_numbers(bet_text, print_text=False)
            max_score = {'txt': BB_value, 'score': confi_score}

            if BB_value == 0 or BB_value > pot or confi_score < 90:
                big_print(f'getBB({BB_value})を正しく読み取れなかったので、二値化して読み取り直します', 'red')

                # トリム実行(二値化あり)
                imghdr.trim_image_without_resize(trim_straimg_path, x_start, x_end, y_start, y_end, name=trim_straimg_action_trim, binary=True)

                # OCRする
                bet_text, confi_score = imghdr.image_to_text(trim_straimg_action_trim, digits=' -c tessedit_char_whitelist=0123456789.')
                BB_value = delete_non_numbers(bet_text, print_text=False)

                if confi_score > max_score['score']:
                    max_score = {'txt': BB_value, 'score': confi_score}

                big_print(f'getBB -> {BB_value}', 'red')

            if BB_value_from_template != BB_value:
                big_print(f'getBB({BB_value})を正しく読み取れませんでした。BB_value_from_template: {BB_value_from_template} が正しいと思います', 'red')
                if check_include_whitelist(ocr_whitelist_csv, {'row': 'pyt_ocr', 'value': BB_value}, {'row': 'template_ocr', 'value': BB_value_from_template}):
                    print('よくあるエラーなので、エラーメッセージを省略します')
                else:
                    some_error_msg_list.append(f'勝者の賞金額が読み取れませんでした。({BB_value}(score: {round(max_score["score"], 2)}), from_template({BB_value_from_template}))とします')
                BB_value = BB_value_from_template

            # 自分のとき
            if target == 'my':
                position = my_position
            # 他の人のとき <- 名前を切り取り、matchさせる
            else:
                # 名前のところだけ画像をトリムする
                x_start = straranges['get']['range']['name']['x_start']
                x_end = x_start + straranges['get']['range']['name']['width']
                y_start = pt[1] - straranges['get']['range']['name']['bottom'] - straranges['get']['range']['name']['height']
                y_end = pt[1] - straranges['get']['range']['name']['bottom']
                # トリムした画像を保存するpathを作成
                trim_straimg_name = os.path.join(tmp_save_dir, f'straimg_getname_trim.jpg')

                # トリム実行(templateが二値化だからこれも二値化する)
                imghdr.trim_image_without_resize(trim_straimg_path, x_start, x_end, y_start, y_end, name=trim_straimg_name, binary=True)
                base_img = imghdr.convert_binary(trim_straimg_name)
                # base_img = cv2.imread(trim_straimg_name, cv2.IMREAD_COLOR)
                max_list = {}
                # どの名前が最も近いか調べる
                for position in alive_position:
                    if position == my_position:
                        continue
                    # templateのリンクを作成
                    trim_straimg_action = os.path.join(tmp_save_dir, f'straimg_name_{position}.jpg')
                    template_img = imghdr.convert_binary(trim_straimg_action)
                    # template_img = cv2.imread(trim_straimg_action, cv2.IMREAD_COLOR)

                    # テンプレートマッチングを実行
                    result = cv2.matchTemplate(base_img, template_img, cv2.TM_CCOEFF_NORMED)
                    # 最大値を取り出す
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    max_list[position] = max_val

                # 最もしきい値が大きいpositionを正とする
                position = max(max_list, key=max_list.get)

            get_amount[position] = BB_value
            # myは1つしかないのでbreak
            if target == 'my':
                break

    # 勝者がいないとき
    if get_amount == {}:
        """
        1, 勝者がいないとき、各プレイヤーは、potを分配する
        2, TODO riverで小さいAllinと大きなRaise, Callがあったとき、どう処理すべきかわからない
        """
        big_print(f'勝者はいないようです -> {alive_position}は、画面上のスタックがinitial_stackと判断します', 'on_light_green')
        for position in alive_position:
            get_amount[position] = None

    print(f'勝者と賞金: {get_amount}')

    return get_amount

def calcurate_initial_stack(strategy_data, game_data, winner, get_amount):
    """
    initial_stackを計算する
    - 処理:
        - 1: Allinした人は、合計bet額が、initial_stackとなる
        - 2: 勝者は、上の画像で見つけたstackから、獲得した分をマイナスしたのが、initial_stack
        - 3: それ以外の人は今まで通りの計算で求められる
        - 4: 小さいAllinの人が勝ったとき、うまく計算できないかもしれない
        - 5: レーキによる獲得額の変動を考慮したinitial_stackの計算に変更(winnerが明確なときのみ行う)
            potの5%(最大3BB)分、獲得額が少なくなっているので、その分、initial_stackを増やす
            get_amountは、initial_stackに対する差額を読み取っているので、そのまま計算すれば、initialが求まる
            上半分で読み取ったstackは、rakeを考慮したstackなので、単純な賞金でinitialを計算しようとするとずれる。
            実際は、rake分なくなっているので、更にrakeを足す
            ちなみに、ゲーム側でrakeを丸めている可能性があるので、少しずれる(0.4を0.5にするとかしているかも)
    - memo:
        - レーキが5%とられるので、獲得から計算したinitial_stackは本来より少しずれる
    """
    print('これからcalcurate_initial_stack()を実行します')
    total_amount = 0
    made_turn = strategy_data['general']['made_turn']
    calcurate_position = [] # ここに入った人は今後計算しない

    # レーキを用意
    pot = game_data['pot']
    rake = 0
    if game_data['phase'] != 'preflop' and pot >= 5:
        rake = min(round(pot * 0.05, 1), 3)

    for position, bet in game_data['total_each_bet'].items():
        # Allinした人なら、total_betがinitial_stackとなる
        Allin_position = True if position in game_data['Allin_position'] else False
        # playerを取り出す
        player = next(player for posi, player in made_turn.items() if posi == position)

        # Noneはパス
        if bet is  None:
            continue

        # initial_stackを足す
        if Allin_position:
            strategy_data['general']['all_players'][player]['initial_stack'] = round(bet, 1)
            calcurate_position.append(position)
        else:
            # 勝者はlast_stack - get_amountでinitialを計算する
            if position in get_amount:
                if get_amount[position] is not None:
                    strategy_data['general']['all_players'][player]['initial_stack'] = round(strategy_data['general']['all_players'][player]['initial_stack'] - get_amount[position], 1)
                calcurate_position.append(position)
            else:
                strategy_data['general']['all_players'][player]['initial_stack'] = round(strategy_data['general']['all_players'][player]['initial_stack'] + bet, 1)

        # totalのbetを集める <- potでもいいと思う
        total_amount = round(total_amount + bet , 1)

    # winnerのinitial_stackを引く
    if winner:
        winner_player = next(player for posi, player in made_turn.items() if posi == winner)
        if winner not in calcurate_position:
            # 通常の処理(Allinをせずに勝った人)
            strategy_data['general']['all_players'][winner_player]['initial_stack'] = round(strategy_data['general']['all_players'][winner_player]['initial_stack'] - total_amount + rake, 1)
        strategy_data['general']['winner'].append(f'{winner}({winner_player})')
    # 獲得が表示されていた人は下記の処理
    else:
        for position, get_bet in get_amount.items():
            winner_player = next(player for posi, player in made_turn.items() if posi == position)
            if position not in calcurate_position: #! <- 上で既にこの処理を行っているので、おこなわれることは無いと思う(250119)
                big_print('行われるはずがない処理が行われます', 'on_red')
                # 通常の処理(Allinをせずに勝った人)
                strategy_data['general']['all_players'][winner_player]['initial_stack'] = round(strategy_data['general']['all_players'][winner_player]['initial_stack'] - get_bet, 1)
            if get_amount[position] is not None:
                strategy_data['general']['winner'].append(f'{position}({winner_player})')
        # 勝者がいないとき、Noneとする
        if strategy_data['general']['winner'] == []:
            strategy_data['general']['winner'] = None

    return strategy_data

def check_winner(all_report):
    """
    250117 checkできるときにFoldした人がいたらおかしくなるから、check_end_game()の方法で調べることにする
    勝者がいるか調べる
    - 処理:
        - 一人だけになったらその人をwinnerとする
        - riverでショーダウンまで行ったり、allinになったりしたら別のプログラムでwinnerを調べる
    """
    alive_list = []
    for posidata, action in all_report.items():
        # ポジションを取り出す
        position = posidata.split('_')[1]
        # Foldで、リストにいる人は削除
        if 'Fold' in action:
            if position in alive_list:
                alive_list.remove(position)
            continue
        # Fold以外の人はリストに追加
        if position not in alive_list:
            alive_list.append(position)

    # 二人以上いたらwinner無し
    if len(alive_list) >= 2:
        return False
    elif alive_list:
        return alive_list[0]
    # ここまでは来ないはず
    big_print(f'alive_listが空です', 'red', '▲')


def check_winner_and_alive_list(strategy_data, *, target_phase=None, no_Allin_position=False, current_phase_list=False, game_data=None):
    """
    alive_listの作成して、winnerを調べる
    - Returns:
        - 1: winnerがいるなら、そのポジション。いないならNone
        - 2: 生き残っているポジションのリスト
        - tmp_alive_list: preflopから確認した、生き残っているはずのプレイヤー。次のプレイヤーが誰かとか調べたいときに使える
        - phase_alive_list: 一番最後のフェーズでアクションした人(Fold以外)をリストにして返す
    - Args:
        - target_phase:
            preflopを入れると、そのフェーズ時点のalive_listを返す
        - no_Allin_position:
            Trueのとき、Allinしたポジションは、alive_listから削除する
        - current_phase_list:
            Trueにすると、phase_alive_listを返す(一番最後のフェーズでアクションした人を返す(winnerを求めるときに使う))
            Falseは、tmp_alive_list を返す
    - 処理:
        - preflopから順に生き残っているポジションのリストを作る
        - 残り1人になったらwinnerを返す
    """

    # 全員が入ったリストを用意
    tmp_alive_list = list(glbvar.preflop_order)

    # 空席者はあらかじめFoldしたことにする
    if game_data and game_data['absent_conver_dict']:
        absent_list = [data['position'] for player, data in strategy_data['general']['all_players']. items() if data['ID'] is None and player != 'player_4']
        for position in absent_list:
            convert_position = game_data['absent_conver_dict'][position]
            tmp_alive_list.remove(convert_position)
    # 各フェーズから順に取り出す
    for phase, data in strategy_data['history'].items():

        all_report = data['strategy_history']
        # all_report にデータが入っていればリセットする
        if all_report:
            phase_alive_list = []

        for posidata, action in all_report.items():
            # positionを取り出す
            position = posidata.split('_')[1]
            # Foldしてる人 or no_Allin_position=Trueかつ、Allinしてる人
            if ('Fold' in action or
                (no_Allin_position and 'Allin' in action)):
                if position in tmp_alive_list:
                    tmp_alive_list.remove(position)
                if position in phase_alive_list:
                    phase_alive_list.remove(position)
            # フェーズごとにalive_listを用意する
            elif position not in phase_alive_list:
                phase_alive_list.append(position)

        # 今すぐにalive_list を返すとき
        if phase == target_phase:
            return tmp_alive_list

    # 条件処理するリストを選ぶ
    if current_phase_list:
        active_list = phase_alive_list
    else:
        active_list = tmp_alive_list

    if len(active_list) >= 2:
        return None, active_list
    elif active_list:
        return active_list[0], active_list
    # ここまでは来ないはず <- 変なハンド履歴だとありえる
    if no_Allin_position is False:
        big_print(f'alive_listが空です', 'red', '▲')
        some_error_msg_list.append(f'alive_listが空です')
    return None, active_list


def add_all_report_with_action_data(all_report, game_data, action_data, position):
    """
    action_dataを受取り、allreportを更新する
    """
    action = action_data['action']
    bet_amount = action_data['bet_amount']
    game_data = calcurate_pot(all_report, game_data)
    if 'init' in action:
        if position == 'SB':
            bet_amount = 0.5
        elif position == 'BB':
            bet_amount = 1
    # report更新
    if bet_amount:
        # bet_amountの割合を計算するとき
        if 'init' not in action:
            # プリフロップはbetの割合を計算しなくていい
            if 'preflop' == game_data['phase']:
                all_report[f'{len(all_report)}_{position}'] = f'{bet_amount}({action})'
            else:
                # Betrateの計算
                rate = calcurate_bet_rate(game_data, bet_amount)
                # 最小Raiseかどうか調べる
                minimum_Raise_status = ''
                if 'Raise' in action:
                    minimum_Raise_status = check_minimum_Raise(all_report, bet_amount)
                all_report[f'{len(all_report)}_{position}'] = f'{bet_amount}({action}({rate}%{minimum_Raise_status}))'
            game_data['original_Raiser'] = position
            game_data['most_bet'] = bet_amount
        # 最初のBBのとき
        else:
            all_report[f'{len(all_report)}_{position}'] = f'{bet_amount}'
        # Allinの人は、Allinリストに追加する
        if 'Allin' in action:
            game_data['Allin_position'].append(position)
    else:
        if action in ('Call'):
            bet_amount = game_data['most_bet']
            all_report[f'{len(all_report)}_{position}'] = f'{bet_amount}({action})'
        else:
            all_report[f'{len(all_report)}_{position}'] = f'{action}'
            # original_Raiserの更新
            if game_data['original_Raiser'] == position:
                game_data['original_Raiser'] = None

    return all_report, game_data

def check_minimum_Raise(all_report, bet_amount=None, *, get_size=False):
    """
    ミニマムレイズだったとき、'(mini)'を返す
    - Args:
        - get_size: Trueにすると、最小Raise額を返す
    """
    # Bet, Raise, AllinのBet額を取り出す
    bet_list = [float(action.split('(')[0]) for action in all_report.values() if 'Bet' in action or 'Raise' in action or 'Allin' in action]

    # 最も大きい2つを取り出す
    largest_two = sorted(bet_list, reverse=True)[:2]

    bet_1 = 0 # 直前のbet
    bet_2 = 0 # それよりも前のbet
    # 1つしかないとき
    if len(largest_two) == 1:
        bet_1 = largest_two[0]
    else:
        bet_1 = largest_two[0]
        bet_2 = largest_two[1]

    # 最小Raise額を計算する
    minimum_Raise_amount = round(bet_1 - bet_2 + bet_1 , 1)

    if abs(minimum_Raise_amount - bet_amount) <= 0.2:
        print(f'ミニマムRaiseです。minimum_Raise_amount: {minimum_Raise_amount}, bet_amount: {bet_amount}')
        return '(mini)'
    return ''



def calcurate_bet_rate(game_data, bet_amount):
    """
    betの割合を計算する
    """
    pot = game_data['pot']
    most_bet = game_data['most_bet']

    # 下記のとき、betとして計算する
    if most_bet == 0:
        rate = round((bet_amount / pot) * 100)
    # Raiseとして計算する
    else:
        rate = round(((bet_amount - most_bet)/(pot + most_bet))*100)

    return rate

def calcurate_total_each_bet(game_data):
    """
    フェーズが終わったときにtotal_each_betの内容を更新する
    - 処理:
        - each_position_betに、前回フェーズの各プレイヤーのtotalbet額が記載されていて、それは、total_each_betに反映されていないので足す
    """
    # コピーしてからforする
    each_position_bet = game_data['each_position_bet'].copy()
    for position, bet in each_position_bet.items():
        # データがない人はパス
        if bet is None:
            continue
        # 更新する
        # 初期値の人は上書きする
        if game_data['total_each_bet'][position] is None:
            game_data['total_each_bet'][position] = bet
        else:
            game_data['total_each_bet'][position] = round(game_data['total_each_bet'][position] + bet, 1)

    return game_data

def calcurate_pot(all_report, game_data, *, end_phase=False):
    """
    各positionのbetサイズをリストにして返す
    """

    each_position_bet = glbvar.made_turn_copy.copy()
    total_bet_amount = 0
    most_bet = 0

    # potを正確に求めるために、下記を確認しながら行う
    Allin_data = {} # Allinしたポジションと、BB額を記録
    alive_list = [] # このフェーズでアクションした人が入る

    # 正確にpotを求めるため、下記の変数を用意する

    for posidata, action in all_report.items():
        position = posidata.split('_')[1]
        # bet額を取り出す
        if 'Fold' in action:
            # Foldした人はそれまでのbetをtotalに足してからNoneにする
            if each_position_bet[position] is not None:
                total_bet_amount += each_position_bet[position]
            # total_each_bet に足す <- init_stackを計算するため。まだ、total_each_betに足す処理をしたことがない人は下記を行う
            if game_data['add_totalbet_for_Fold'][position] is None:
                if game_data['total_each_bet'][position] is None:
                    game_data['total_each_bet'][position] = each_position_bet[position]
                else:
                    if each_position_bet[position] is not None:
                        game_data['total_each_bet'][position] = round(game_data['total_each_bet'][position] + each_position_bet[position], 1)
                    else:
                        game_data['total_each_bet'][position] = round(game_data['total_each_bet'][position], 1)
            game_data['add_totalbet_for_Fold'][position] = True
            amount = None
            # aliveリストの更新
            if position in alive_list:
                alive_list.remove(position)
        elif 'Call' in action or 'Check' in action:
            amount = most_bet
            # aliveリストの更新
            if position not in alive_list:
                alive_list.append(position)
            # Allin Callが存在するなら下記が行われる(小さなAllinの後にRaiseが入って、それに対するCallなら弾く)
            if Allin_data and max(allin_bet for allin_bet in Allin_data.values()) == most_bet:
                Allin_data[position] = most_bet
                big_print(f'Allinに対してCallされました', 'yellow', '▲') #? ハンド履歴の表示で、Allinの後に、Callは存在するのか
        else:
            if '(' in action:
                amount = float(action.split('(')[0])
            else:
                amount = delete_non_numbers(action, print_text=False)
            most_bet = max(most_bet, amount)
            # aliveリストの更新
            if position not in alive_list:
                alive_list.append(position)
            # Allinリストに追加
            if 'Allin' in action:
                Allin_data[position] = amount
        each_position_bet[position] = amount

    # potサイズの更新
    total_bet_amount += sum(_amount_ for _amount_ in each_position_bet.values() if _amount_ is not None)
    if 'preflop' == game_data['phase'] and total_bet_amount <= 1.5:
        pass
    else:
        init_pot = game_data['init_pot']
        game_data['pot'] = round(init_pot + total_bet_amount , 1)
        if len(alive_list) == 1 and game_data['original_Raiser'] == alive_list[0]:
            big_print('Betによってゲームが終了したので、pot額を調整します')
            game_data['pot'] = round(game_data['pot'] - most_bet , 1)

        # 残ってる人が全員Allinしたとき、potを正確に求める
        if end_phase and Allin_data and len(alive_list)-1 <= len(Allin_data) and len(alive_list) >= 2:
            """
            条件:
            1, aliveがいる
            2, 残ってる人 - 1 が、Allin人数以下である <- 3人残ってて、小さいAllinに対してRaiseして、最後の人がFoldしたときにありえる。最後の人がCallしたらここまで来ない
            """
            # 小さいAllinに対してRaiseしたとき、Allin_dataにデータを追加する
            if len(alive_list)-1 == len(Allin_data):
                position = next(position for position in alive_list if position not in Allin_data)
                Allin_data[position] = most_bet

            Allin_bet_list = list(Allin_data.values())
            max_1, max_2 = sorted(Allin_bet_list, reverse=True)[:2]
            if max_1 == max_2:
                pass
            else:
                big_print('Allinだけになったので、pot額を計算し直します', 'white')
                dif_allin = round(max_1 - max_2, 1)
                game_data['pot'] = round(game_data['pot'] - dif_allin , 1)


    # each_position_bet を追加する <- initial_stackを計算するため
    game_data['each_position_bet'] = each_position_bet

    return game_data

def get_action_with_template(trim_straimg_action, trim_straimg_path, status, data):
    """
    trimしたプレイヤーの画像からアクションを読み取る
    - 処理:
        - 1, アクションとmatchさせる
        - 2, bet, Raise, Allinなら、BB額をOCRする <- 必要な範囲のみにトリムしてから行う
    """

    # templateを用意
    if 'other' == status['player']:
        dir_link = template_link['stradata_dir']['other_actions']
    else:
        dir_link = template_link['stradata_dir']['my_actions']

    # baseを読み込む
    base_img = cv2.imread(trim_straimg_action, cv2.IMREAD_COLOR)
    threshold = 0.8

    # アクションを順にｍatchさせる
    for action_img in os.listdir(dir_link):
        # actionを取り出す
        action = os.path.splitext(action_img)[0]
        # matchすべきかどうか判定する
        if (status['init'] and 'init' in action_img or
            status['init'] is False and action in glbvar.action_list):
            # パスを作成
            action_img_path = os.path.join(dir_link, action_img)
        else:
            continue

        # テンプレート画像を読み込み
        template_img = cv2.imread(action_img_path, cv2.IMREAD_COLOR)
        # テンプレートマッチングを実行
        result = cv2.matchTemplate(base_img, template_img, cv2.TM_CCOEFF_NORMED)
        # 最大値を取り出す
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # マッチが閾値以上のとき
        if max_val >= threshold:
            # 下記のとき、bet額も調べるためにトリムする
            BB_value = None
            if action in ('Raise', 'Bet', 'Allin'):
                # トリムした画像を保存するpathを作成
                trim_straimg_action_trim = os.path.join(tmp_save_dir, f'straimg_{action}_trim.jpg')

                # BB額を見るためにトリムする
                if 'other' == status['player']:
                    x_start = data['x'] + straranges['general']['actions']['posiimg_width'] + straranges['general']['actions']['posi_blank']
                    x_end = x_start + straranges['general']['actions']['action_width']
                    y_start = data['y'] + straranges['general']['actions']['BB_top']
                    y_end = data['y'] + straranges['general']['actions']['action_bottom'] - 7 # 少し下部を削ることでOCRの失敗が減ると思う
                else:
                    #* 1) 通常よりも大きめにトリムして、端の画像の位置を調べる
                    x_start = 0
                    x_end = straranges['general']['my_action']['serch_edge_x_end']
                    y_start = data['y'] - straranges['general']['my_action']['serch_edge_y_start']
                    y_end = data['y'] + straranges['general']['my_action']['serch_edge_y_end']

                    # トリム実行
                    imghdr.trim_image_without_resize(trim_straimg_path, x_start, x_end, y_start, y_end, name=trim_straimg_action_trim, binary=False)

                    base_img = cv2.imread(trim_straimg_action_trim, cv2.IMREAD_COLOR)
                    template_img = cv2.imread(straranges['general']['my_action']['edge_link'], cv2.IMREAD_COLOR)
                    # テンプレートマッチングを実行
                    result = cv2.matchTemplate(base_img, template_img, cv2.TM_CCOEFF_NORMED)
                    # 最大値を取り出す
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                    #* 2) 左端の座標が求められたらトリム用の範囲を用意
                    x_start = max_loc[0] + straranges['general']['my_action']['edge_blank']
                    x_end = data['x'] - straranges['general']['actions']['posi_blank']
                    y_start = data['y'] + straranges['general']['actions']['BB_top']
                    y_end = data['y'] + straranges['general']['actions']['action_bottom'] - 7

                # トリム実行
                imghdr.trim_image_without_resize(trim_straimg_path, x_start, x_end, y_start, y_end, name=trim_straimg_action_trim, binary=False)

                # BB額を求める
                BB_value = get_BB_value_with_actionimg(trim_straimg_action_trim, status)

            action_data = {'action': action, 'bet_amount': BB_value}
            return action_data

    big_print(f'アクションが見つかりませんでした -> {trim_straimg_action}', 'red', '▲')

def get_BB_value_with_actionimg(trim_straimg_action_trim, status):
    """
    トリムされたアクションのbet額が記載されてる画像から、BB額を求める
    """

    if status['player'] == 'other':
        template_link_img = template_link['stradata_dir']['other_BB']
    else:
        template_link_img = template_link['stradata_dir']['my_BB']

    #* BBがあるとき左側のみにトリムする
    # トリムした画像を保存するpathを作成
    output_path = os.path.join(tmp_save_dir, f'straimg_BB_trim.jpg')
    suppress_print(imghdr.trim_image_left_of_template)(image_a_path=trim_straimg_action_trim, image_b_path=template_link_img,
                                                output_path=output_path, threshold=0.8)

    # リサイズ、ノイズ除去、二値化
    output_BB_2 = os.path.join(tmp_save_dir, f'straimg_BB_trim_2.jpg')
    imghdr.binary_for_small_number_img_gen2(output_path, output_BB_2, scale=9, reverse=False)

    BB_value_from_template = get_number_with_location(output_BB_2, template_link['bet_numbers'], blank=5, error_tag='action')

    # リサイズ、ノイズ除去、適応二値化
    output_BB_1 = os.path.join(tmp_save_dir, f'straimg_BB_trim_1.jpg')
    imghdr.binary_for_small_number_img(output_path, output_BB_1, scale=9, clean_noise=True)
    bet_text, confi_score = imghdr.image_to_text(output_BB_1, digits=' -c tessedit_char_whitelist=0123456789.')

    max_confi_text = {'txt': bet_text, 'score': confi_score}
    exist_error = False

    if bet_text == '' or confi_score < 90:
        """
        250122 メモ
        ・stackは黒背景に白文字でOCRして精度がいいので、ここも、白黒反転させたら精度あがるかもしれない <- 変わらなさそう..
        ・いくら工夫しても精度が100%にならないなら、最悪、matchtemplateで調べるのも可能 <- 面倒くさいけど作るのもあり
        """

        ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [output_BB_1], error_type=f'BB_OCR_error_1({max_confi_text["txt"]})')

        big_print('Bet額が読み取れなかったので、二値化します', 'on_red')
        some_error_msg_list.append(f'Bet額(bet: {bet_text}, score: {max_confi_text["score"]})が正確に読み取れなかったので、別の方法を試します <- エラーテキストがこのままのとき、score90以上のテキストを取り出せています')
        exist_error = True

        #! 上で行った
        # # リサイズ、ノイズ除去、二値化
        # output_BB_2 = os.path.join(tmp_save_dir, f'straimg_BB_trim_2.jpg')
        # imghdr.binary_for_small_number_img_gen2(output_path, output_BB_2, scale=9, reverse=False)

        bet_text, confi_score = imghdr.image_to_text(output_BB_2, digits=' -c tessedit_char_whitelist=0123456789.')
        if max_confi_text['score'] < confi_score:
            max_confi_text = {'txt': bet_text, 'score': confi_score}
    #* 3) まだデータが空のとき、色々な引数を渡して探す
    if bet_text == '' or confi_score < 90:
        ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [output_BB_2], error_type=f'BB_OCR_error_2({max_confi_text["txt"]})')

        # 全通り試す
        for oem in (3,):
            for psm in (3,6,7,8,9,10,11,13):
                # １文字に適しているとき
                bet_text, confi_score = imghdr.image_to_text(output_BB_2, oem=oem, psm=psm, digits=' -c tessedit_char_whitelist=0123456789.')
                if max_confi_text['score'] < confi_score:
                    max_confi_text = {'txt': bet_text, 'score': confi_score}

    BB_value = delete_non_numbers(max_confi_text['txt'], print_text=False)

    if max_confi_text['score'] < 90:
        some_error_msg_list.append(f'Bet額(bet: {max_confi_text["txt"]}, score: {max_confi_text["score"]})が正しく読み取れませんでした <- これで終わっているとき、from_templateと同じ値です')
        print(f'max_confi_text: {max_confi_text}')
    elif exist_error  and check_include_whitelist(ocr_whitelist_csv, {'row': 'pyt_ocr', 'value': BB_value}):
        # 2.5の読み間違いは良くするので、エラー文を削除する
        del some_error_msg_list[-1]

    if BB_value_from_template != BB_value:
        big_print(f'Bet額が正確に読み取れませんでした。from_template({BB_value_from_template})を正とします')
        if check_include_whitelist(ocr_whitelist_csv, {'row': 'pyt_ocr', 'value': BB_value}, {'row': 'template_ocr', 'value': BB_value_from_template}):
        # if exist_error and BB_value in (27,41) and BB_value_from_template in (2.7, 11):
            # 27の読み間違いは良くするので、エラーは出さない
            pass
        else:
            some_error_msg_list.append(f'Bet額(ocr: {BB_value}, score: {max_confi_text["score"]})が正確に読み取れませんでした。from_template({BB_value_from_template})を正とします')

    return BB_value_from_template

def get_number_with_location(base_number_img, template_dir, *, blank, error_tag=None):
    """
    matchTemplateを使って数字を読み取る
    - Args:
        - blank: 隣の文字と最低いくつ離れていないといけないか
        - error_tag: エラーが起きたとき、どのタイミングでおきたか記録するためのメモ
    """
    # baseを読み込む
    base_img = cv2.imread(base_number_img, cv2.IMREAD_COLOR)

    # 検出された座標を格納するリスト
    num_locations = []
    threshold = 0.91
    num_width_dict = {}
    each_max_val = {}

    # 大きい数字から調べる
    for num in ('9','8','0','6','5','4','3','2','7','1','dot',):
        # 数字によってしきい値を変える
        if 'stack' in error_tag:
            threshold = 0.8
            if num in ('1',):
                threshold = 0.75
            if num in ('dot',):
                threshold = 0.83

        # パスの作成
        num_path = os.path.join(template_dir, f'{num}.jpg')
        # テンプレート画像を読み込み
        template_img = cv2.imread(num_path, cv2.IMREAD_COLOR)
        # テンプレートの大きさを取り出す
        height, width, channels = template_img.shape
        num_width_dict[num] = width

        # テンプレートマッチングを実行
        result = cv2.matchTemplate(base_img, template_img, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        each_max_val[num] = max_val

        # しきい値を超える領域を取得
        locations = np.where(result >= threshold)
        # 座標を (x, y) のリストに変換
        coordinates = list(zip(locations[1], locations[0]))  # x座標とy座標の順番に変更
        # x を基準にソート
        sorted_coordinates = sorted(coordinates, key=lambda coord: coord[0])

        # 座標とポジションをリストに入れる
        for pt in sorted_coordinates:  # (x, y) 形式に変換

            # xが他の座標と50以上離れていないと正としない
            x = pt[0] # 現在のx座標

            match_rate = round(float(result[pt[1], pt[0]]), 3)
            print(f'{num} -> match率: {match_rate:.3f}(x: {x})')

            # 既に見つけたx座標のリスト
            x_dict = {}
            for index, location_data in enumerate(num_locations):
                active_num = location_data['num']
                active_width = num_width_dict[num]
                x_dict[f'{index}_1'] = {'num': location_data['num'], 'x': location_data['x'] + active_width}
                x_dict[f'{index}_2'] = {'num': location_data['num'], 'x': location_data['x']}

            # どの座標よりも5以上離れていればok
            add_point = True
            for _, data in x_dict.items():
                _num_ = data['num']
                _x_ = data['x']
                if abs(x - _x_) <= blank:
                    add_point = False
                    if _num_ == num and abs(x - _x_) > 5:
                        # big_print(f'自分と違い座標のポジションがあったのでパスします\n 近い座標 x: {_x_}, 見つけた座標 x: {pt[0]}, y: {pt[1]}', 'red', '▲')
                        pass
                    break
            # リストに追加する処理
            if add_point:
                num_locations.append({
                    'num': num,
                    'x': pt[0],
                    'y': pt[1],
                })
            else:
                # 近いポジションが現在と異なるならprintする
                if _num_ != num:
                    # big_print(f'現在({num})とは異なるポジション"{_num_}"と座標が近いポジションがあったのでパスします\n 近い座標 y: {_y_}, 見つけた座標 x: {pt[0]}, y: {pt[1]}', 'red', '▲')
                    pass

    # x 座標を基準にソート
    num_locations = sorted(num_locations, key=lambda coord: coord['x'])

    finded_numbers = []
    print(f'-----------\n各数字のmax_val')
    sorted_each_max_val = dict(sorted(each_max_val.items()))
    for num, value in sorted_each_max_val.items():
        if 'stack' in error_tag:
            """
            数字によってしきい値を変えることで、精度を上げてる(250124)
            """
            threshold = 0.8
            if num in ('1',):
                threshold = 0.75
            if num in ('dot',):
                threshold = 0.83
        if value >= threshold:
            big_print(f'{num} -> {round(value, 3):.3f}', 'yellow')
            finded_numbers.append(num)
        else:
            print(f'{num} -> {round(value, 3):.3f}')

    # 見つけた数字をすべて使用しているかチェック
    use_numbers = set([item['num'] for item in num_locations])
    for find_mum in finded_numbers:
        if find_mum not in use_numbers:
            big_print(f'{find_mum} が使用されていません', 'on_red')
            template_ocr_error_msg_list.append([f'tag: {error_tag}, {find_mum} が使用されていません(max_val: {round(sorted_each_max_val[find_mum], 3)})'])

    # numを順に取り出し、'dot'は'.'に変換
    result_str = ''.join([item['num'] if item['num'] != 'dot' else '.' for item in num_locations])

    # 'dot' を含む数をカウント
    dot_count = sum(1 for item in num_locations if 'dot' in item['num'])
    if dot_count >= 2:
        big_print(f'result_str: {result_str} , dotが複数取り出されました', 'on_red')
        # 2つまでdotが連続してるのはエラー出さない
        if '..' in result_str:
            result_str = result_str.replace('..', '.')
        else:
            template_ocr_error_msg_list.append([f'tag: {error_tag}, result_str: {result_str} , dotが複数取り出されました'])

    print(f'templateによるOCR: {result_str}')
    result_num = delete_non_numbers(result_str, print_text=False)

    return result_num

def sort_position_locations(position_locations):
    """
    preflopはアクションの順がおかしくなっていることがあるので、ここで正す
    - 処理:
        - 1: SB~BTNのアクションリストにデータを入れる
        - 2: まとめられたリストをSB~BTNの順で取り出してリストに入れる
    """
    # SB~BTNのリストを作成する
    sort_position_list = {position: [] for position in glbvar.postflop_order}
    for data in position_locations:
        position = data['position']
        sort_position_list[position].append(data)

    # SB~BTNの順で取り出す
    sorted_position_locations = []
    # 取り出すのに残っている数を計算する
    remain_data = sum(len(data) for data in sort_position_list.values())
    while remain_data > 0:
        for position in glbvar.postflop_order:
            # 中にデータがあることを確認
            if len(sort_position_list[position]) > 0:
                data = sort_position_list[position].pop(0)
                sorted_position_locations.append(data)
        # 取り出すのに残っている数を再計算する
        remain_data = sum(len(data) for data in sort_position_list.values())

    return sorted_position_locations

def get_position_locations(trim_straimg_path, strategy_data, game_data):
    """
    各ポジションをmatchさせて、高い位置から順にポジションと座標を並べる
    TODO SBとBBがthreshold=0.85だと見分けつかない。SBのほうが先にあり、BBのとなりなのでなんとか防ぐ処理はできてる。
    TODO ポジションによってthresholdを変えるとかいいかもしれない
    """
    # baseを読み込む
    base_img = cv2.imread(trim_straimg_path, cv2.IMREAD_COLOR)

    # 検出された座標を格納するリスト
    position_locations = []
    threshold = 0.91


    _, alive_list = check_winner_and_alive_list(strategy_data, no_Allin_position=True)

    for position_img in os.listdir(template_link['stradata_dir']['positions']):
        position = os.path.splitext(position_img)[0]

        # 生き残っていないプレイヤーはパスする
        if position not in alive_list:
            continue

        # covertリストに入ってるときは、変換する
        if position in game_data['absent_conver_dict']:
            position_img = position_img.replace(position, game_data['absent_conver_dict'][position])
            position = game_data['absent_conver_dict'][position]

        # パスの作成
        position_path = os.path.join(template_link['stradata_dir']['positions'], position_img)
        # テンプレート画像を読み込み
        template_img = cv2.imread(position_path, cv2.IMREAD_COLOR)

        # テンプレートマッチングを実行
        result = cv2.matchTemplate(base_img, template_img, cv2.TM_CCOEFF_NORMED)

        # しきい値を超える領域を取得
        locations = np.where(result >= threshold)

        # 座標とポジションをリストに入れる
        for pt in zip(*locations[::-1]):  # (x, y) 形式に変換

            match_rate = round(float(result[pt[1], pt[0]]), 3)
            print(f'{position} -> match率: {match_rate}')

            # yが他の座標と50以上離れていないと正としない
            y = pt[1] # 現在のy座標
            y_dict = {index: {'position': location_data['position'], 'y': location_data['y']} for index, location_data in enumerate(position_locations)} # 既に見つけたy座標のリスト
            # どの座標よりも50以上離れていればパスする or 自分の場合は100以上離れていないとパス
            add_point = True
            for _, data in y_dict.items():
                _position_ = data['position']
                _y_ = data['y']
                if _position_ != position:
                    blank = 50 # 自分の座標が被ってるのが心配なときは50以上離れていれば良い
                else:
                    blank = 120 # SBがBBと被ってるのが心配なときは、隣のポジションから120以上離れていれば良い
                if abs(y - _y_) <= blank:
                    add_point = False
                    if _position_ == position and abs(y - _y_) > 50:
                        big_print(f'自分と違い座標のポジションがあったのでパスします\n 近い座標 y: {_y_}, 見つけた座標 x: {pt[0]}, y: {pt[1]}', 'red', '▲')
                    break
            # リストに追加する処理
            if add_point:
                position_locations.append({
                    'position': position,
                    'x': pt[0],
                    'y': pt[1],
                })
            else:
                # 近いポジションが現在と異なるならprintする
                if _position_ != position:
                    big_print(f'現在({position})とは異なるポジション"{_position_}"と座標が近いポジションがあったのでパスします\n 近い座標 y: {_y_}, 見つけた座標 x: {pt[0]}, y: {pt[1]}', 'red', '▲')

    # y 座標を基準にソート
    position_locations = sorted(position_locations, key=lambda coord: coord['y'])

    return position_locations

def trim_phase_img(pic_path, phase, y_end):
    """
    フェーズごとに画像をトリムする
    """
    # トリム座標をまとめる
    x_start = straranges['phase'][phase]['x_start']
    x_end = x_start + straranges['general']['width']
    y_start = straranges['general']['y_start']
    y_end = y_end
    # トリムした画像を保存するpathを作成
    trim_straimg_jpg = os.path.join(tmp_save_dir, f'straimg_phase_{phase}.jpg')

    # トリム実行
    imghdr.trim_image_without_resize(pic_path, x_start, x_end, y_start, y_end, name=trim_straimg_jpg, binary=False)

    return trim_straimg_jpg

def check_strange_intial_stack(strategy_data):
    """
    initial_stackがマイナスになってる人がいたらエラーを出す
    """
    error_list = []

    for player, data in strategy_data['general']['all_players'].items():
        init_stack = data['initial_stack']
        if init_stack is not None and init_stack < 0:
            big_print(f'{player} のinitial_stackがマイナスになっています', 'on_red')
            error_list.append([f'{player} のinitial_stackがマイナスになっています'])
    if error_list:
        strategy_data['general']['error_message'].append({'strange_initial_stack': error_list})

    return strategy_data

def check_duplicate_card(strategy_data):
    """
    被りのカードがないことを確認する
    """
    error_msg = []
    all_cards = []

    # プレイヤーのカードを取り出す
    for player, data in strategy_data['general']['all_players'].items():
        detail = data['detail_hand']
        if detail is None:
            continue

        if len(detail) == 4:
            card1 = detail[:2]
            card2 = detail[2:]
            if card1 in all_cards:
                error_msg.append([f'{player} カードが被っています。card: {card1}, all_cards: {all_cards}'])
            else:
                all_cards.append(card1)
            if card2 in all_cards:
                error_msg.append([f'{player} カードが被っています。card: {card2}, all_cards: {all_cards}'])
            else:
                all_cards.append(card2)
        elif len(detail) == 2:
            if detail in all_cards:
                error_msg.append([f'{player} カードが被っています。card: {detail}, all_cards: {all_cards}'])
            else:
                all_cards.append(detail)
        else:
            error_msg.append([f'{player} カードが条件に合いません。detail_hand: {detail}'])

    # 場のカードを取り出す
    for phase, data in strategy_data['history'].items():
        cards = data['board_cards']
        if cards is None:
            continue
        for card in cards:
            if card in all_cards:
                error_msg.append([f'{phase} カードが被っています。card: {card}, all_cards: {all_cards}'])
            else:
                all_cards.append(card)

    if error_msg:
        strategy_data['general']['error_message'].append({'duplicate_card': error_msg})

    return strategy_data

def check_only_one_hand(strategy_data):
    """
    1つしかハンドを取り出せていない人がいたら、エラーを出力する
    """
    error_msg = []
    for player, data in strategy_data['general']['all_players'].items():
        about = data['about_hand']
        detail = data['detail_hand']
        if about is None and detail:
            error_msg.append([f'{player}: 片方のハンドしか読み込んでいません'])

    if error_msg:
        strategy_data['general']['error_message'].append({'only_one_hand': error_msg})

    return strategy_data

def check_strange_pot_value(pic_path, strategy_data):
    """
    ocrで手に入れたpotと、計算で求めたpotに大きな違い(0.3以上 <- エラーの出力みて調整す)あれば、エラーを追加する
    """
    orc_pot_value = get_pot_value_with_ocr(pic_path)
    error_list = []

    for phase, data in strategy_data['history'].items():
        find_error = False
        if phase == 'preflop':
            continue
        calucurated_pot = data['pot']
        if ((calucurated_pot is None and data['strategy_history'] and orc_pot_value[phase]) or
            calucurated_pot and orc_pot_value[phase] is None):
            """
            1, strategy_historyはデータがあるのに、potが計算できてないとき
            2, 計算ではpotがあるのに、potをocrできなかったとき
            """
            big_print(f'{phase} のpotに問題があります。ocrでpotを読み取れていません', 'on_red')
            error_list.append([f'{phase} のpotに問題があります。ocrでpotを読み取れていません'])

        elif calucurated_pot is None and len(data['strategy_history']) == 0:
            pass
        elif calucurated_pot is None and orc_pot_value[phase] is None:
            pass
        elif abs(calucurated_pot - orc_pot_value[phase]) >= 0.3:
            big_print(f'{phase} のpotに問題があります。ocrと計算で、0.3以上違いがあります', 'on_red')
            error_list.append([f'{phase} のpotに問題があります。ocrと計算で、0.3以上違いがあります。calucurated_pot: {calucurated_pot}, ocr: {orc_pot_value[phase]}'])

    if error_list:
        strategy_data['general']['error_message'].append({'strange_pot': error_list})

    return strategy_data

def get_pot_value_with_ocr(pic_path):
    """
    各フェーズのpot額をocrで手に入れる
    """

    orc_pot_value = {}

    # トリム座標をまとめる
    y_start = straranges['general']['pot_display']['y_start']
    y_end = y_start + straranges['general']['pot_display']['height']

    for phase in glbvar.phase_order:
        if phase == 'preflop':
            continue

        #* 各フェーズのpotごとにトリムする
        x_start = straranges['general']['pot_display'][phase]['x_start']
        x_end = x_start + straranges['general']['pot_display']['width']
        # トリムした画像を保存するpathを作成
        trim_strapot_jpg = os.path.join(tmp_save_dir, f'pot_{phase}.jpg')
        # トリム実行
        imghdr.trim_image_without_resize(pic_path, x_start, x_end, y_start, y_end, name=trim_strapot_jpg, binary=False)

        # リサイズして二値化する
        imghdr.binary_for_small_number_img_gen2(trim_strapot_jpg, trim_strapot_jpg, scale=5)

        # BBがあるか調べて、BBの左側のみにトリムする
        exist_BB = suppress_print(imghdr.trim_image_left_of_template)(image_a_path=trim_strapot_jpg, image_b_path=template_link['pot_BB_icon'],
                                                                            output_path=trim_strapot_jpg, threshold=0.8)

        if exist_BB:
            pot_value = get_number_with_location(trim_strapot_jpg, template_link['pot_numbers'], blank=4, error_tag=f'pot({phase})')
            big_print(f'"{phase}"pot額: {pot_value}BB', 'white')
        else:
            pot_value = None
            print(f'"{phase}"pot額: {pot_value}')

        orc_pot_value[phase] = pot_value


    return orc_pot_value

# ==========================
# 画像上半分の処理
# ==========================

def make_general_data(pic_path):
    """
    画像の上半分から得られるデータをstrategy_dataにまとめる

    Returns:
        - dict: strategy_data 保存用の全ての情報が入ったデータ
            - general:
                各プレイヤーのデータが入る
            - history:
                phaseごとのreportが入る。ボードカードもここに入る

    処理:
        - 1, 各プレイヤースタックを調べる -> 存在するかも調べる
        - 2, 存在するプレイヤーは、名前を保存する
        - 3, btnの位置を調べる
        - 4, made_turnを作成する -> general に追加
        - 5, ハンドを調べる -> general に追加
        - 6, ボードカードを調べる -> history に追加
    """
    # 各プレイヤーのスタックを調べる
    player_stacks, stack_err_msg_list = check_each_stack(pic_path)

    # made_turnを作成する
    made_turn, btn_err_msg = make_made_turn(pic_path, player_stacks)

    # 各プレイヤーの名前から、仮IDを調べるか新規作成する
    player_ID_dict, id_err_msg_list = check_each_player_ID(pic_path, player_stacks)

    # 各プレイヤーのハンドを調べる
    player_hand_dict, player_hand_error_list = get_each_hand(pic_path)

    # ボードカードを調べる
    board_cards, board_card_error_list = get_board_cards(pic_path)

    # エラーをまとめる
    error_list = {'btn_err_msg': btn_err_msg, 'stack_err_msg_list': stack_err_msg_list, 'id_err_msg_list': id_err_msg_list,
                'player_hand_error_list': player_hand_error_list, 'board_card_error_list': board_card_error_list}

    # データをまとめる
    strategy_data = gather_stradata(player_stacks, made_turn, player_ID_dict, player_hand_dict, board_cards, error_list)

    return strategy_data

def gather_stradata(player_stacks, made_turn, player_ID_dict, player_hand_dict, board_cards, error_list):
    """
    画像上半分で集めたデータをstrategy_data にまとめる
    """
    # all_players をまとめる
    all_players = gather_all_players(player_stacks, player_ID_dict, player_hand_dict, made_turn)

    # historysの型を作る
    history = gather_history_with_board_cards(board_cards)

    strategy_data = {
        'general': {
            'winner': [],
            'trust_data': True,
            'error_message': [],
            'table_stakes': glbvar.table_rate,
            'situation': None,
            'made_turn': made_turn,
            'all_players': all_players,
        },
        'history': history,
    }

    # エラーを追加する
    for title, error in error_list.items():
        if error:
            strategy_data['general']['error_message'].append({title: error})

    return strategy_data

def gather_history_with_board_cards(board_cards):
    """
    board_cards を用いてhistory の型を作る
    """

    history = {
        'preflop': {
            'original_Raiser': None,
            'pot': 1.5,
            'board_cards': None,
            'strategy_history': {}
        }
    }

    for phase, cards in board_cards.items():
        history[phase] = {
                'original_Raiser': None,
                'pot': None,
                'board_cards': cards,
                'strategy_history': {}
            }

    return history


def gather_all_players(player_stacks, player_ID_dict, player_hand_dict, made_turn):
    """
    all_players をまとめる
    """
    all_players = {}
    for player, stack in player_stacks.items():
        obj_id = None
        about_hand = None
        detail_hand = None
        position = next(position for position, seat in made_turn.items() if seat == player)
        # スタックがあるとき、ID, handを調べているので取り出す
        if stack is not None:
            if player != 'player_4':
                obj_id = player_ID_dict[player]
            about_hand = player_hand_dict[player]['about_hand']
            detail_hand = player_hand_dict[player]['detail_hand']

        all_players[player] = {
            'position': position,
            'initial_stack': stack,
            'ID': obj_id,
            'about_hand': about_hand,
            'detail_hand': detail_hand,
        }

    return all_players



def get_board_cards(pic_path):
    """
    ボードのカードを調べる
    """
    board_cards = {}
    board_card_error_list = []
    for phase in glbvar.phase_order:
        # プリフロップはパス
        if phase == 'preflop':
            continue
        # フェーズごとにカードを調べる
        cards, card_error_list = get_card_from_board(pic_path, phase)
        # エラーを追加する
        if card_error_list:
            board_card_error_list.append(f'{phase}: {card_error_list}')

        if cards:
            board_cards[phase] = cards
        # カードがなかったら、ループを抜ける
        else:
            break
    return board_cards, board_card_error_list

def get_card_from_board(pic_path, phase):
    """
    phaseを受取り、ボードのカードを調べる
    """
    card_list = []
    error_list = []
    template_link_dict = template_link['board_card']
    width = ranges['board_card']['general']['width']
    height = ranges['board_card']['general']['height']

    # ループで取り出す
    for card_index, range_dict in ranges['board_card']['start_range'][phase].items():

        # トリム座標をまとめる
        x_start = range_dict['x']
        x_end = x_start + width
        y_start = range_dict['y']
        y_end = y_start + height
        # トリムした画像を保存するpathを作成
        tmp_card_jpg = os.path.join(tmp_save_dir, f'tmp_{card_index}.jpg')

        # トリム実行
        imghdr.trim_image_without_resize(pic_path, x_start, x_end, y_start, y_end, name=tmp_card_jpg, binary=False)

        # カードを取り出す
        card, card_err_msg = get_card(template_link_dict, tmp_card_jpg)
        # エラーを追加
        if card_err_msg:
            error_list.append(f'card_index: {card_index} -> {card_err_msg}')
            ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [tmp_card_jpg], error_type=f'card_board({phase})_error_card{card_index}')

        if card:
            card_list.append(card)
        elif card_list:
            big_print(f'{card_index}が取り出せませんでした -> {tmp_card_jpg}', 'red', '▲')
            error_list.append(f'{card_index}が取り出せませんでした -> {tmp_card_jpg}')

    return card_list, error_list



def get_each_hand(pic_path):
    """
    各プレイヤーのハンドを調べる
    1枚だけ開いてるプレイヤーも調べられるようにする
    """
    player_hand_dict = {}
    error_list = []
    for player in glbvar.players:
        about_hand, detail_hand, hand_error_list = get_hand(pic_path, player)
        player_hand_dict[player] = {
            'about_hand': about_hand,
            'detail_hand': detail_hand,
        }

        if hand_error_list:
            error_list.append(hand_error_list)

    return player_hand_dict, error_list

def get_hand(pic_path, player):
    """
    playerのハンドを調べる
    処理:
        - 1, 右側のハンドのみトリムして、markがあるか調べる -> 数字を調べる
        - 2, 右のマークがあれば、左側も調べる
        - 3, 右側のハンドしか見えていないプレイヤーもいる
    """
    hand_error_list = []

    #* 1枚目のみトリムする
    # 座標をまとめる
    # 自分のときと、他人のときで値が異なる
    if player == 'player_4':
        x_start = ranges['personal'][player]['hand']['x'] + ranges['general']['my_hand']['width1']
        x_end = x_start + ranges['general']['my_hand']['width2']
        y_start = ranges['personal'][player]['hand']['y']
        y_end = y_start + ranges['general']['my_hand']['height']
        template_link_dict = template_link['my_hand']
    else:
        x_start = ranges['personal'][player]['hand']['x'] + ranges['general']['other_hand']['width1']
        x_end = x_start + ranges['general']['other_hand']['width2']
        y_start = ranges['personal'][player]['hand']['y']
        y_end = y_start + ranges['general']['other_hand']['height']
        template_link_dict = template_link['other_hand']
    tmp_hand_jpg = os.path.join(tmp_save_dir, f'tmp_card.jpg')
    # トリム実行
    imghdr.trim_image_without_resize(pic_path, x_start, x_end, y_start, y_end, name=tmp_hand_jpg, binary=False)

    card1, hand_err_msg = get_card(template_link_dict, tmp_hand_jpg)
    if hand_err_msg:
        hand_error_list.append(f'{player}: {hand_err_msg}')
        ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [tmp_hand_jpg], error_type=f'card_player({player})_error_card1')

    # カードの存在を確認できたとき(Noneではないとき)
    if card1:
        # 左側のカードをトリムする
        # 自分のときと、他人のときで値が異なる
        x_start = ranges['personal'][player]['hand']['x']
        if player == 'player_4':
            x_end = x_start + ranges['general']['my_hand']['width1']
        else:
            x_end = x_start + ranges['general']['other_hand']['width1']
        # トリム実行
        imghdr.trim_image_without_resize(pic_path, x_start, x_end, y_start, y_end, name=tmp_hand_jpg, binary=False)

        card2, hand_err_msg = get_card(template_link_dict, tmp_hand_jpg)
        if hand_err_msg:
            hand_error_list.append(f'{player}: {hand_err_msg}')
            ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [tmp_hand_jpg], error_type=f'card_player({player})_error_card2')
    else:
        return None, None, hand_error_list

    # card2がないとき
    if card2 is None:
        return None, card1, hand_error_list

    # aboutとdetailをまとめて返す
    about_hand, detail_hand = pkac.change_myhand_to_wizard([card1, card2])
    return about_hand, detail_hand, hand_error_list



def get_card(template_link_dict, tmp_hand_jpg):
    """
    カードをmatchtemplateで調べる
    - args:
        - template_link_dict:
            数字とマークがあるdirのリンクが入った辞書を渡す。これはglobalで定義されているものを使う
        - tmp_hand_jpg:
            マークと数字を調べたい画像を1枚の情報にトリムして、リンクを渡す。
    - 処理:
        - 1, マークを見る -> Noneならカード無し
        - 2, 数字を見る
    """
    hand_err_msg = ''

    #! リサイズする
    resize_hand_jpg = os.path.join(tmp_save_dir, f'tmp_card_resize_not_binary.jpg')
    imghdr.binary_for_small_number_img_gen2(tmp_hand_jpg, resize_hand_jpg, scale=5, binary=False)

    # ベースを読み込む
    base_img = cv2.imread(resize_hand_jpg)

    threshold = 0.95
    mark = None
    #* マークを調べる
    while threshold >= 0.79 and mark is None:
        for mark_jpg in os.listdir(template_link_dict['marks']):
            # 画像以外はパス
            if not mark_jpg.endswith(".jpg"):
                continue

            _mark_ = os.path.splitext(mark_jpg)[0]

            # マークのリンクを作成して読み込む
            mark_link = os.path.join(template_link_dict['marks'], mark_jpg)
            template_img = cv2.imread(mark_link)

            # matchさせる
            result = cv2.matchTemplate(base_img, template_img, cv2.TM_CCOEFF_NORMED)
            # 閾値を超えるマッチ箇所を検索
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            # マッチが閾値以上のとき
            if max_val >= threshold:
                mark = _mark_
                big_print(f'mark: {mark} (threshold: {round(max_val, 2)})', 'white')
                break
        threshold = round(threshold - 0.01, 2)
    if mark is None:
        return None, hand_err_msg

    #* 数字を読み取る

    #! リサイズする
    resize_hand_jpg = os.path.join(tmp_save_dir, f'tmp_card_resize_binary.jpg')
    imghdr.binary_for_small_number_img_gen2(tmp_hand_jpg, resize_hand_jpg, scale=5, binary=True)

    # ベースを２値化して読み込む
    base_img = cv2.imread(resize_hand_jpg)
    threshold = 0.93

    while threshold > 0.6:
        for num_jpg in os.listdir(template_link_dict['numbers']):
            # 画像以外はパス
            if not num_jpg.endswith(".jpg"):
                continue

            _num_ = os.path.splitext(num_jpg)[0]

            # マークのリンクを作成して読み込む
            num_link = os.path.join(template_link_dict['numbers'], num_jpg)
            template_img = cv2.imread(num_link)

            # matchさせる
            result = cv2.matchTemplate(base_img, template_img, cv2.TM_CCOEFF_NORMED)
            # 閾値を超えるマッチ箇所を検索
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            # マッチが閾値以上のとき
            if max_val >= threshold:
                big_print(f'num: {_num_} (threshold: {round(max_val, 2)})', 'white')
                return f'{_num_}{mark}', hand_err_msg
        threshold = round(threshold-0.01, 2)

    big_print(f'数字が読み取れませんでした link -> {tmp_hand_jpg}', 'red', '▲')
    hand_err_msg = '数字が読み取れませんでした'
    return None, hand_err_msg

def check_each_player_ID(pic_path, player_stacks):
    """
    各プレイヤーのIDを調べるか、新規作成する
    処理:
        - 1, 名前の画像を保存する
        - 2, 既存の名前画像と一致するものがあるか調べる
        - 3, 一致するものがなければ、仮IDを新規作成する
    """
    player_ID_dict = {}
    err_msg_list = []
    for player, stack in player_stacks.items():
        # 空席はパス
        if stack is None or player == 'player_4':
            continue
        #* トリムする
        # 座標をまとめる
        x_start = ranges['personal'][player]['name']['x']
        x_end = x_start + ranges['general']['name']['width']
        y_start = ranges['personal'][player]['name']['y']
        y_end = y_start + ranges['general']['name']['height']
        name_jpg_link = os.path.join(tmp_save_dir, f'name_{player}.jpg')
        # トリム実行
        imghdr.trim_image_without_resize(pic_path, x_start, x_end, y_start, y_end, name=name_jpg_link, binary=False)

        # 拡大して二値化する
        imghdr.binary_for_small_number_img(name_jpg_link, name_jpg_link, scale=5)

        # 既存のIDがあるか調べる
        player_ID, err_msg = check_player_ID(name_jpg_link, player)
        player_ID_dict[player] = player_ID

        # エラーを受け取ったとき、追加する
        if err_msg:
            err_msg_list.append(err_msg)

    return player_ID_dict, err_msg_list

def check_player_ID(name_jpg_link, player):
    """
    名前の画像(フルサイズ)のリンクを受取り、小さくトリムした画像を作成する
    その画像と一致する画像が、name_picsにあれば、そのIDを返す。なければ、IDを新規作成する
    処理:
        - 1, 名前画像をトリムする
        - 2, フォルダの中の画像とmatchさせる
        - 3, matchしなければ、IDを新規作成する
    """
    # 画像をトリムする
    x_start = ranges['general']['name']['trim']['blank']
    x_end = x_start + ranges['general']['name']['trim']['width']
    y_start = ranges['general']['name']['trim']['blank']
    y_end = y_start + ranges['general']['name']['trim']['height']
    name_trim_link = os.path.join(tmp_save_dir, f'name_trim_{player}.jpg')
    # トリム実行
    imghdr.trim_image_without_resize(name_jpg_link, x_start, x_end, y_start, y_end, name=name_trim_link)

    # 一致する画像があるか調べる
    template_img = cv2.imread(name_trim_link)
    threshold_max = 0.945 # これ以上一致していれば、確定する
    threshold_mini = 0.92 # これを満たしている中で最も近いのを正とする
    mini_list = {'tmp_id': 0, 'max_val': 0, 'path': None}
    max_match = 0
    second_match = 0
    err_msg = [] # エラーメッセージを入れる

    # 最近見つけたidを先にリストに入れる
    all_id_list = resent_player_id_list.copy()
    # すべてのidをリストに追加する
    all_id_list += os.listdir(player_name_dir)
    # 重複を除く
    all_id_list = list(dict.fromkeys(all_id_list))

    for file_name in all_id_list:
        # 条件に合う画像の名前のみ行う
        if file_name.endswith('.jpg') and file_name.startswith('anlz'):
            # baseのpathを作成
            base_name_path = os.path.join(player_name_dir, file_name)
            # 画像を読み込む
            base_img = cv2.imread(base_name_path)

            # matchさせる
            result = cv2.matchTemplate(base_img, template_img, cv2.TM_CCOEFF_NORMED)
            # 閾値を超えるマッチ箇所を検索
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            if max_match < max_val:
                second_match = max_match
                max_match = max_val
            elif second_match < max_val:
                second_match = max_val

            # マッチが閾値以上のとき
            if max_val >= threshold_max:
                anlz_id, _ = os.path.splitext(file_name)
                if '(' in anlz_id:
                    anlz_id = anlz_id.split('(')[0]
                resent_player_id_list.insert(0, f'{anlz_id}.jpg') # リストに追加する
                big_print(f'IDが見つかりました -> player: {player}, ID: {anlz_id}, max_val: {round(max_val, 3)}, second_match: {round(second_match, 3)}', 'yellow')
                # miniがかなり近いとき
                if mini_list["max_val"] >= threshold_mini and anlz_id not in mini_list["tmp_id"]:
                    # 特定の組み合わせはエラー出力をパスする <- 似た名前の人がいても新規作成してはいけない(既にその名前で登録されてる)
                    if check_include_whitelist(id_whitelist_csv, {'row': 'max_id', 'value': anlz_id}, {'row': 'second_id', 'value': mini_list["tmp_id"]}):
                        pass
                    else:
                        big_print(f'second_match(tmp_id: {mini_list["tmp_id"]})が {threshold_mini} 以上(second_match: {round(mini_list["max_val"], 3)})です', 'on_red')
                        err_msg.append(f'player: {player}, ID: {anlz_id}, match: {round(max_val, 3)} | second_match(tmp_id: {mini_list["tmp_id"]}(match: {round(mini_list["max_val"], 3)}))が {threshold_mini} 以上です')
                        if mini_list['path']:
                            ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [mini_list['path'], name_jpg_link, os.path.join(player_name_dir, f'{anlz_id}.jpg')], error_type=f'name_error_suspect({player})')
                return anlz_id, err_msg
            elif max_val >= threshold_mini and max_val > mini_list['max_val']:
                tmp_anlz_id, _ = os.path.splitext(file_name)
                mini_list = {'tmp_id': tmp_anlz_id, 'max_val': max_val, 'path': base_name_path}
    if mini_list['max_val'] > 0:
        anlz_id = mini_list['tmp_id']
        if '(' in anlz_id:
            anlz_id = anlz_id.split('(')[0]
        resent_player_id_list.insert(0, f'{anlz_id}.jpg') # リストに追加する
        big_print(f'IDが見つかりました({threshold_max}以下) -> player: {player}, ID: {anlz_id}, max_val: {round(mini_list["max_val"], 3)}', 'light_green')
        err_msg.append(f'低いmax_val({threshold_max}以下)でIDが見つかりました -> player: {player}, ID: {anlz_id}, max_val: {round(mini_list["max_val"], 3)}')
        ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [mini_list['path'], name_jpg_link], error_type=f'name_error_suspect({player})')
        #! inputしてsub追加するか確かめる
        judge_id = judge_add_sub_id(f'name_error_suspect({player})', mini_list['path'], name_jpg_link)
        if judge_id:
            return anlz_id, err_msg

    # ここまで来たときは、IDを新規作成する
    max_id = imghdr.get_largest_image_number(player_name_dir, startswith='anlz_')
    if max_id == -1:
        max_id = 0
    anlz_id = f'anlz_{max_id + 1 :06}'

    # 新規作成したIDで、name_picsに画像を移す
    new_name_path = os.path.join(player_name_dir, f'{anlz_id}.jpg')
    shutil.copy(name_jpg_link, new_name_path)

    big_print(f'{player} | match率: {round(max_match, 3)},  IDを新規作成します -> anlz_ID: {anlz_id}\nID_img_path: {new_name_path}', 'white')
    resent_player_id_list.insert(0, f'{anlz_id}.jpg') # リストに追加する
    return anlz_id, err_msg

def judge_add_sub_id(error_type, *args):
    """
    特定の値を超えないIDを見つけたとき、それをsubとしてIDを追加するかどうか判断を委ねるプログラム
    """
    big_print(f'\n==============================================\n   {error_type}', 'yellow')
    for link in args:
        print(link)

    judge = oths.input_y_or_n(f' - 上記の画像は同一人物ですか？ (y, n)\n   y -> subを追加, n -> IDを新規作成', send=True)

    if judge is False:
        big_print('同一人物ではないので、IDを新規作成します', 'on_yellow')
        return False
    # y のとき、subを追加する -> basenameを取り出し、anlzを含む方を使って名前をつけて、そうでない方を、idリストに追加する
    new_name_img = ''
    anlz_id = ''
    for link in args:
        if 'anlz_' in link:
            anlz_id = os.path.basename(link)
            anlz_id = os.path.splitext(anlz_id)[0]
            continue
        new_name_img = link

    # 新しいidをつける
    count = 0
    while True:
        new_name = f'{anlz_id}(sub{count}).jpg'
        new_name_path = os.path.join(player_name_dir, new_name)
        if os.path.exists(new_name_path):
            count += 1
        else:
            break

    # コピーを作成
    shutil.copy(new_name_img, new_name_path)

    # コピーを作成したことがわかるように、エラーフォルダにもデータを入れる
    ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [new_name_path], error_type=error_type)

    big_print(f'新しいID(subを作成しました): {new_name_path}', 'on_yellow')

    return True


def check_include_whitelist(whitelist_link, *args):
    """
    whitelistに入っている組み合わせのとき、Falseを返す
    - Args:
        - *args: csvのヘッダーと値が入ったデータをリストにして渡す [{'row': ***, 'value': ***}, [...]]
    """

    # csvがまだ存在しないとき、Falseを返す
    if not os.path.exists(whitelist_link):
        big_print(f'まだ、csvが存在しないようです', 'on_red')
        return False

    # csvの読み込み
    with open(whitelist_link, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)  # ヘッダーを辞書キーとして扱う
        csv_data = list(reader) # indexを取り出せるようにする

    # 特定のデータが存在するまで、それ以外を削除する
    for arg in args:
        target_row = arg['row']
        target_value = arg['value']
        try:
            target_value = convert_number(target_value)
        except:
            pass

        # 消したいindexを取り出す
        delete_index = [index for index, row in enumerate(csv_data) if row[target_row] != str(target_value)]

        # 削除対象を逆順に削除（インデックスのずれを防ぐ）
        for index in sorted(delete_index, reverse=True):
            csv_data.pop(index)

    # データがあればTrueを返す
    if len(csv_data) > 0:
        return True
    else:
        return False

def make_made_turn(pic_path, player_stacks):
    """
    made_turnを作成する
    処理：
        - 1, btnの位置を調べる
        - 2, 欠席者リスト(player_stacks) を使ってmade_turnを作成する
    """
    # btnの位置を調べる
    btn_player, btn_err_msg = check_btn_player(pic_path)

    # made_turnを作成する
    made_turn = create_made_turn_with_btn_and_absent(player_stacks, btn_player)

    return made_turn, btn_err_msg

def create_made_turn_with_btn_and_absent(player_stacks, btn_player):
    """
    made_turn を作成する
    """
    # 空のデータを用意する
    made_turn = glbvar.made_turn_copy.copy()

    # BTNを確定させる
    made_turn['BTN'] = btn_player

    # 空席をUTGから順に入れていく
    for player, stack in player_stacks.items():
        # 下記のとき、欠席者と判定している
        if stack is None:
            # まだプレイヤーが登録されていないことを確認
            if player not in made_turn.values():
                # UTGから順に取り出し、空の席を取り出す
                absent_position = next(position for position, seat in made_turn.items() if seat is None)
                made_turn[absent_position] = player

    # SB, BBを追加する -> その後、UTGから順にプレイヤーを入れていく
    find_btn = False
    priority_position = ['SB', 'BB']
    print('made_turnを作成します')
    while next((True for seat in made_turn.values() if seat is None), False):
        for player in glbvar.players:
            # btnを見つけた次のプレイヤーからチェックしていく
            if player == btn_player:
                find_btn = True
            # Falseのときは飛ばす
            elif find_btn is False:
                continue
            # btnを見つけた後は下記に進む
            else:
                # まだ追加されていないことを確認
                if player not in made_turn.values():
                    # SB, BBが見つかっていないとき、下記に進む
                    if priority_position:
                        this_position = priority_position.pop(0)
                        made_turn[this_position] = player
                    else:
                        # まだplayerが割り当てられていないポジションを取り出す
                        this_position = next(position for position, seat in made_turn.items() if seat is None)
                        made_turn[this_position] = player

    big_print(f'made_turnを作成できました -> {made_turn}', 'white')
    return made_turn

def check_btn_player(pic_path):
    """
    player_1から順にbtnが存在するか調べる
    """
    # 共通の変数を用意
    template = template_link['icon_btn']
    threshold = 0.8
    original_img_range = {'x_start': 0, 'y_start': 0}
    trim_btn_path = os.path.join(tmp_save_dir, 'trim_btn.jpg')
    err_msg = ''

    for player in glbvar.players:
        # トリムするための座標を用意
        x_start = ranges['personal'][player]['btn']['x']
        x_end = x_start + ranges['general']['btn']['width']
        y_start = ranges['personal'][player]['btn']['y']
        y_end = y_start + ranges['general']['btn']['height']
        # トリムしてmatchさせる
        exist_btn = ctlscr.trim_and_match_with_big_screenshot(x_start, x_end, y_start, y_end, template, threshold,
                        original_img_range=original_img_range, original_img_path=pic_path, name=trim_btn_path, resize=1)
        if exist_btn:
            return player, err_msg

    big_print('DealerButtonが見つかりませんでした', 'red', '▲')
    err_msg = 'DealerButtonが見つかりませんでした'
    return player, err_msg

def check_each_stack(pic_path):
    """
    各プレイヤーのスタックを調べる。ついでに、欠席者も調べる。
    TODO 6スレッドで一度に処理したら早いくなるかも

    Returns:
        - dict: player_stacks
            - player: stack <- 欠席者の場合、Noneが入る
    """
    player_stacks = {}
    stack_err_msg_list = []
    for player in glbvar.players:
        stack, stack_err_msg = check_stack_and_absent(player, pic_path)
        player_stacks[player] = stack
        # 欠席者のとき、msgを追加する
        if stack_err_msg:
            stack_err_msg_list.append([stack_err_msg])

    return player_stacks, stack_err_msg_list

def check_stack_and_absent(player, pic_path):
    """
    playerを受取り、トリムして、BBが存在するか調べる
    BBが存在する場合、BBの左側のみにトリムして、OCRする
    - OCRについて:
        - 1: ノイズ除去と二値化する
        - 2: これで空なら、適応二値化でする
        - 3: これでだめなら、初期の方法を使う
    """

    stack_err_msg = ''

    #* トリムする
    # 座標をまとめる
    x_start = ranges['personal'][player]['stack']['x']
    x_end = x_start + ranges['general']['stack']['width']
    y_start = ranges['personal'][player]['stack']['y']
    y_end = y_start + ranges['general']['stack']['height']
    trim_stack_jpg = os.path.join(tmp_save_dir, f'trim_stack_{player}.jpg')
    # トリム実行
    imghdr.trim_image_without_resize(pic_path, x_start, x_end, y_start, y_end, name=trim_stack_jpg)

    # スタックを二値化して拡大する
    imghdr.binary_for_small_number_img_gen2(trim_stack_jpg, trim_stack_jpg, scale=5)

    #* BBが存在するか調べ、BBがあるとき左側のみにトリムする
    output_path = os.path.join(tmp_save_dir, 'trim_stack_left.jpg')
    exist_BB = imghdr.trim_image_left_of_template(image_a_path=trim_stack_jpg, image_b_path=template_link['icon_BB_binary'],
                                                output_path=output_path, threshold=0.8)

    if exist_BB:

        stack_from_template = get_number_with_location(output_path, template_link['stack_numbers'], blank=5, error_tag=f'stack({player})')

        # OCRする
        stack_text, confi_score = imghdr.image_to_text(output_path, digits=' -c tessedit_char_whitelist=0123456789.')
        max_confi_text = {'txt': stack_text, 'score': confi_score}
        #* 2) データが空のとき、適応二値化で試す
        if stack_text == '' or confi_score < 90:

            # 調整をしていない画像を用意する
            trim_original_stack_jpg = os.path.join(tmp_save_dir, f'trim_original_stack_{player}.jpg')
            imghdr.trim_image_without_resize(pic_path, x_start, x_end, y_start, y_end, name=trim_original_stack_jpg)
            suppress_print(imghdr.trim_image_left_of_template)(image_a_path=trim_original_stack_jpg, image_b_path=template_link['icon_BB_original'],
                                                                output_path=trim_original_stack_jpg, threshold=0.8)

            ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [output_path], error_type=f'stack_OCR_error_{player}_1')

            big_print('スタックが読み取れなかったので、ノイズ除去+グレー化します', 'on_red')
            stack_err_msg = f'{player} スタック額(stack: {stack_text}, score: {max_confi_text["score"]})を正しく読み取れなかったので、別の方法を試します <- エラーテキストがこのままのとき、score90以上の数字を取り出せています'
            # スタックを二値化して拡大する
            imghdr.binary_for_small_number_img(trim_original_stack_jpg, output_path, scale=5)

            stack_text, confi_score = imghdr.image_to_text(output_path, digits=' -c tessedit_char_whitelist=0123456789.')

            if max_confi_text['score'] < confi_score:
                max_confi_text = {'txt': stack_text, 'score': confi_score}

        #* 3) まだデータが空のとき、初期の方法を使う
        if stack_text == '' or confi_score < 90:

            ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [output_path], error_type=f'stack_OCR_error_{player}_2')
            big_print('スタックが読み取れなかったので、調整せずにOCRします', 'on_red')

            imghdr.binary_for_small_number_img(trim_original_stack_jpg, output_path, scale=10, clean_noise=True)
            stack_text, confi_score = imghdr.image_to_text(output_path, digits=' -c tessedit_char_whitelist=0123456789.')

            if max_confi_text['score'] < confi_score:
                max_confi_text = {'txt': stack_text, 'score': confi_score}

        #* 4) 別の方法
        if stack_text == '' or confi_score < 90:

            big_print('スタックが読み取れなかったので、二値化します(2)', 'on_red')
            # スタックを二値化して拡大する
            imghdr.binary_for_small_number_img_gen2(trim_original_stack_jpg, output_path, scale=5, reverse=True)
            stack_text, confi_score = imghdr.image_to_text(output_path, digits=' -c tessedit_char_whitelist=0123456789.')

            if max_confi_text['score'] < confi_score:
                max_confi_text = {'txt': stack_text, 'score': confi_score}

        #* 5) psmの変更
        if stack_text == '' or confi_score < 90:
            for psm in (3,6,7,8,9,10,11,13):
                """
                10: １文字に適しているとき
                8: ラベルに適しているとき
                13: 中央配置に適しているとき
                11: ランダム配置に適しているとき
                """
                stack_text, confi_score = imghdr.image_to_text(output_path, psm=psm, digits=' -c tessedit_char_whitelist=0123456789.')
                if max_confi_text['score'] < confi_score:
                    max_confi_text = {'txt': stack_text, 'score': confi_score}

        if stack_text == '' or confi_score < 90:
            ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [output_path], error_type=f'stack_OCR_error_{player}_3')

        if max_confi_text['score'] < 90:
            stack_err_msg = f'{player} 読み取ったスタック額が怪しいです value: {max_confi_text["txt"]}, max_score: {max_confi_text["score"]} <- これで終わってるとき、template_ocrと同じ値だったようです'
        #     ctldir.copy_data_for_error_directory(original_path_list = [output_path], error_type=f'stack_OCR_error_{player}_1')

        if stack_from_template != delete_non_numbers(max_confi_text['txt'], print_text=False):
            stack_err_msg = f'{player} 読み取ったスタック額が怪しいです value: {max_confi_text["txt"]}, max_score: {max_confi_text["score"]}。 from_template({stack_from_template}) を正とします'
            max_confi_text['txt'] = stack_from_template

        stack = delete_non_numbers(max_confi_text['txt'], print_text=False)
        big_print(f'{player} -> stack:{stack}BB', 'white')
        return stack, stack_err_msg
    big_print(f'"{player}"は欠席者です', 'on_red')
    stack_err_msg = f'{player} は欠席者です'
    ctldir.copy_data_for_error_directory(save_error_directory, original_path_list = [trim_stack_jpg], error_type=f'stack_OCR_error_{player}_absent')
    return None, stack_err_msg

# ==========================
# その他
# ==========================

def collect_and_sort_files_for_stradata(directory):
    # ディレクトリ内のファイルを取得
    files = [
        file for file in os.listdir(directory)
        if file.endswith('.jpg') and file.startswith('history')
    ]
    # ソート：'history_'の後の数字部分で並べ替え
    sorted_files = sorted(
        files,
        key=lambda x: int(x.split('_')[1].split('.')[0])  # 'history_'以降の数字を取得して数値でソート
    )
    return sorted_files

def get_latest_stradir():
    """
    stradataを保存しているディレクトリの中で、最も新しい日付のものから2つ取り出す
    """
    # 対象ディレクトリのパス
    target_dir = stradata_for_save_dir

    # ディレクトリ内のフォルダ名を取得し、日付フォーマットとして処理する
    date_dirs = [
        name for name in os.listdir(target_dir)
        if os.path.isdir(os.path.join(target_dir, name)) and name.isdigit()
    ]

    # 日付順にソート（降順）
    date_dirs_sorted = sorted(date_dirs, reverse=True)

    # 最新の2つを取得
    latest_dirs = date_dirs_sorted[:2]

    return latest_dirs

def add_img_size(pic_path, stranumber, today):
    """
    usedディレクトリに、処理を終えた画像のサイズを記録する
    """

    # 画像を読み込む
    img = cv2.imread(pic_path)
    # 高さと幅を取得
    height, _ = img.shape[:2]

    csv_path = os.path.join(used_pic_dir, today, '_stradata_size.csv')
    fieldnames = ['stranumber', 'height']
    new_data = {'stranumber': stranumber, 'height': height}

    if not os.path.exists(csv_path):
        # csvを作成する
        with open(csv_path, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            # ヘッダーを書き込む
            writer.writeheader()

    # データを追加する
    with open(csv_path, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(new_data)


def check_same_stradata(pic_path, *, how_check='hash', check_input=True):
    """
    TODO 過去1000ハンドまでしか探さないようにする <- それより古い画像は削除して行っていいと思う
    全く同じデータかどうか調べる
    - 処理:
        - 1: 大きさ(高さ)が同じ画像のstranumberを取り出す
        - 2: ハッシュ値が同じかどうかチェックする

    - Args:
        - how_check: [hash, numpy] hashで確かめるか、numpyで確かめるか選べる。
            hashのほうが早いけど、ダウンロードしたタイミングが違うと同じものでも一致しない
            numpyでするとき、しきい値は、0.001が良いと思う。0.0001でも、完全に一致する画像なら引っかかると思うけど、そこまでしなくても誤作動は起きなさそう
        - check_input: Trueにしたらinputで類似画像を確かめる
    """

    # 画像を読み込む
    img = cv2.imread(pic_path)
    # 高さと幅を取得
    height, _ = img.shape[:2]

    if how_check == 'hash':
        base_hash = calculate_file_hash(pic_path)

    dir_names = os.listdir(used_pic_dir)
    # 数値に変換できるものだけを対象にする
    numeric_dirs = [d for d in dir_names if d.isdigit()]
    # 数値として解釈し、大きい順にソート
    sorted_dirs = sorted(numeric_dirs, key=lambda x: int(x), reverse=True)

    # ディレクトリを順に取り出す
    for index, dir_name in enumerate(sorted_dirs):
        # 過去2日までしか確認しない <- 処理速度上がるはず
        if index >= 2:
            break

        csv_path = os.path.join(used_pic_dir, dir_name, '_stradata_size.csv')

        # csvの読み込み
        if not os.path.exists(csv_path):
            continue
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)  # ヘッダーを辞書キーとして扱う
            csv_data = list(reader) # indexを取り出せるようにする

        # 大きさが一致するものを取り出す
        target_stranumbers = [row['stranumber'] for index, row in enumerate(csv_data) if row['height'] == str(height)]

        # 条件に合ったデータをすぐ比較する
        for stranumber in target_stranumbers:
            stra_link = os.path.join(used_pic_dir, dir_name, f'{stranumber}.jpg')

            find_similer = False
            if how_check == 'hash':
                active_hash = calculate_file_hash(stra_link)
                if base_hash == active_hash:
                    find_similer = True
            elif how_check == 'numpy':
                if check_same_img_with_numpy(pic_path, stra_link, threshold=0.0005):
                    find_similer = True

            if find_similer:
                big_print('完全に一致する画像を見つけました', 'on_red')

                if check_input:
                    # inputで合っているか確かめる
                    big_print(f'{pic_path}\n{stra_link}', 'yellow')
                    judge = oths.input_y_or_n(' - この2つの画像は一致していますか？', send=True)

                    # 異なるとき、continueする
                    if judge is False:
                        continue
                return True
    # ここまで来たら全てと一致していない
    return False

def calculate_file_hash(file_path):
    """ファイルのハッシュ値を計算"""
    hasher = hashlib.md5()  # 他に hashlib.sha256() なども使える
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def check_same_img_with_numpy(img1_path, img2_path, threshold=0.001):
    """
    numpyを使って数値的に同じ画像が調べる
    """
    img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)  # グレースケール変換
    img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)

    if img1.shape != img2.shape:
        return False  # サイズが違うなら即不一致

    diff = cv2.absdiff(img1, img2)  # 差分を計算
    diff_ratio = np.sum(diff) / (img1.shape[0] * img1.shape[1] * 255)

    if diff_ratio < threshold:
        big_print(f'とても似ている画像を見つけました diff_ratio: {diff_ratio}', 'on_red')

    return diff_ratio < threshold

def check_exist_stradata_file(latest_dirs, stranumber, pic_path):
    """
    stradataが入ってるディレクトリに、これから調べる画像と同じ名前のものがあるかチェック
    """

    for latest_dir_date in latest_dirs:
        # 探す対象のディレクトリのパスを作成
        target_dir = os.path.join(stradata_for_save_dir, latest_dir_date)
        # stranumber があればTrueになる
        contains_stranumber = any(
        stranumber in file for file in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, file))
        )
        if contains_stranumber:
            return contains_stranumber

    exist_same_img = check_same_stradata(pic_path, how_check='numpy', check_input=True)

    return exist_same_img

def same_name_data_move_to_other_dir(pic_path, stranumber, today):
    """
    既にstradataを作成していると思われる画像を、被っている画像を入れるディレクトリに移す
    """
    # 保存先のディレクトリを用意
    destination_dir_path = os.path.join(duplicates_dir, today)
    if not os.path.exists(destination_dir_path):
        os.makedirs(destination_dir_path)

    # 保存先の画像データのpathを用意
    destination_path = os.path.join(destination_dir_path, f'{stranumber}.jpg')
    # 移動させる
    shutil.move(pic_path, destination_path)

def assign_error_dir(today):
    """
    エラーディレクトリをエラー内容によって振り分ける
    """
    # エラーデータを保存するディレクトリのパスを作成
    parent_dir = os.path.join(error_data_dir, today)
    if not os.path.exists(parent_dir):
        return

    # エラーディレクトリの振り分け先を用意
    dir_error_right_template_ocr = os.path.join(parent_dir, '1_right_template_ocr')
    dir_error_card_number = os.path.join(parent_dir, '2_card_number')
    dir_strange_stack = os.path.join(parent_dir, '3_strange_stack')
    dir_absent_player = os.path.join(parent_dir, '4_absent_player')
    dir_suspect_anlz_id = os.path.join(parent_dir, '5_suspect_anlz_id')
    dir_strange_position_order = os.path.join(parent_dir, '6_strange_position_order')
    dir_modified_position_order = os.path.join(parent_dir, '7_modified_position_order')
    dir_strange_pot = os.path.join(parent_dir, '8_strange_pot')
    dir_template_ocr = os.path.join(parent_dir, '9_template_ocr')
    dir_only_one_hand = os.path.join(parent_dir, '10_only_one_hand')
    dir_duplicate_card = os.path.join(parent_dir, '11_duplicate_card')
    dir_error_history = os.path.join(parent_dir, '12_error_history')

    error_massage_dict = {
        dir_error_history: ['"alive_listが空です"'],
        dir_duplicate_card: ['カードが条件に合いません', 'カードが被っています'],
        dir_template_ocr: ['tag:'],
        dir_strange_pot: ['のpotに問題があります'],
        dir_strange_position_order: ['allreportを修正するときに、エラーがあったようです'],
        dir_modified_position_order: ['次に行われるべきポジションではない人が', 'allreportを修正します', 'フェーズはまだ終わるべきでないのに、終わりました'],
        dir_suspect_anlz_id: ['IDが見つかりました(', '| second_match', '低いmax_val'],
        dir_strange_stack: ['読み取ったスタック額が怪しいです'],
        dir_only_one_hand: ['片方のハンドしか読み込んでいません'],
        dir_error_card_number: ['数字が読み取れませんでした'],
        dir_absent_player: ['欠席者'],
        dir_error_right_template_ocr: ['正とします', '賞金額が読み取れませんでした'],
    }

    for directory in error_massage_dict:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # 探すべきディレクトリのみを用意する
    directory_list = os.listdir(parent_dir)
    directory_list = [name for name in directory_list if 'history' in name] # 特定の名前のものだけに減らす

    # .json ファイルを探索し読み込む
    for directory_name in directory_list:
        find_json = False # jsonが入ってないディレクトリは削除する
        directory_path = os.path.join(parent_dir, directory_name)
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.json'):
                    find_json = True
                    json_path = os.path.join(root, file)
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            #* エラーメッセージを見て、割り振る
                            for directory, err_messge in error_massage_dict.items():

                                judge = judge_delete_error_dir(data['general']['error_message'], negative_target_list = [], positive_target_list=err_messge)
                                if judge:
                                    big_print(f'"{err_messge[0]}" messageを見つけたので、移動させます -> {os.path.join(directory, os.path.basename(root))}', 'yellow')
                                    shutil.move(root, os.path.join(directory, os.path.basename(root)))
                                    break

                    except Exception as e:
                        traceback.print_exc()
                        pass
        if find_json is False:
            shutil.rmtree(directory_path)
            big_print(f"jsonが入ってないので、ディレクトリを削除しました。 ->  {directory_path} ", 'on_red')

    big_print('エラーディレクトリの振り分けが終わりました', 'white')

if __name__ == "__main__":
    main()


