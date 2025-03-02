"""
import poker_bot.poker_logic.poker_utils as pkutil
"""

from termcolor import colored, cprint
import os
import sys
import csv
import time
from datetime import datetime
import subprocess
import threading
import queue
import json
from pathlib import Path
import re

from strategy_analyzer_app.io_operations.print_processing import big_print
from strategy_analyzer_app.text_processing.text_extraction import convert_number, delete_non_numbers
import strategy_analyzer_app.global_vars as glbvar

# ====================================
# URLの作成
# ====================================

def input_nextphase_URL(driver, create_path, use_StackSize, mode='no_card'):
    """
    create_pathを使ってフロップ入力画面まで進む
    - Args:
        - mode:
            - 'no_card': cardとかわかってないときに使う
            - 'postflop': postflopの情報が出ているときに使う
    """
    # action_listを作成する
    if mode == 'no_card':
        action_law_data = create_path.split('BB')[1]
        action_list = action_law_data.split('/')[1:]
        wiz_action_count = len(action_list)-1

        nextphase_URL = make_nextphase_URL(action_list, use_StackSize, phase='preflop')

        # 変数を入れる
        # もし、log保存が実行中なら止めるための変数をTrueにする
        repeat = 0
        while glbvar.running_save_log: # 終了するまでここで待機する
            if glbvar.quit_save_log is False:
                glbvar.quit_save_log = True
                print('log保存処理が強制終了されるまで少し待機します')  # 少し待てば、log保存の処理はストップするはず
            time.sleep(0.01)
            repeat += 1
            if repeat > 200: # 2s待てば強制的に抜ける
                break
        glbvar.quit_save_log = False # 戻す
        glbvar.proceed_postflop = True # これはlog保存が実行される直前にFalseになっているので競合することはないと思う
        glbvar.pre_postflop_path = create_path

        # nextphaseにジャンプする
        big_print(f'ポストフロップのURL -> {nextphase_URL}\npath -> {create_path}', 'white')
        driver.get(nextphase_URL)

        return wiz_action_count

    # ポストフロップのとき
    """
    1, pathから use_StackSize を求める
    2, phaseがいくつかによってどこまで作るか変える
    """
    # 各階層ごとに分割
    path = Path(create_path)
    path_parts = path.parts

    # スタックサイズと、それよりも後ろのデータを取り出す
    stack_dir_name = next(dir_name for dir_name in path_parts if 'BB' in dir_name)
    stack_dir_index = path_parts.index(stack_dir_name)
    # URLの作成に必要なデータのみ取り出す
    street_list = path_parts[stack_dir_index + 1:]

    # 各フェーズのアクションと、カードを取り出す
    actions = []
    cards = []
    street_actions = [] # カードを見つけるたび、新規作成する
    for index, action_dir in enumerate(street_list):
        # カードのディレクトリを探す
        if len(action_dir) in (6, 2):
            # 文字量がカードと同じで、カードの表記と同じとき、確定する
            if action_dir[0] in glbvar.rank_order and action_dir[1] in glbvar.suit_order:
                cards.append(action_dir)
                actions.append(street_actions)
                street_actions = []
                continue
        # それ以外のとき
        street_actions.append(action_dir)
        # 一番最後は追加する
        if index+1 == len(street_list):
            actions.append(street_actions)

    # URLを作成する
    board = ''.join(cards)
    actions_URL = {
        'preflop_actions': None,
        'flop_actions': None,
        'turn_actions': None,
        'river_actions': None,
    }

    # URLに入力するデータを用意
    count = 0
    for index, action_list in enumerate(actions):
        # preflopのとき
        if index == 0:
            preflop_actions = make_url_street(action_list, phase='preflop')
            actions_URL['preflop_actions'] = preflop_actions
            count += len(action_list)
            continue

        # それ以外のとき
        postflop_actions = make_url_street(action_list, phase='postflop')
        # indexから、phaseを選択
        select_phase = list(actions_URL)[index]
        # データを追加
        actions_URL[select_phase] = postflop_actions
        count += len(action_list)

    # URLを作成する
    nextphase_URL = make_nextphase_URL(actions_URL, use_StackSize=convert_number(delete_non_numbers(stack_dir_name, print_text=False)), count=count, board=board, phase='postflop')

    # nextphaseにジャンプする
    big_print(f'ポストフロップのURL -> {nextphase_URL}\n\npath -> {create_path}', 'white')
    driver.get(nextphase_URL)

def cards_sort(cards):
    """
    フロップのカードの順を並び替える
    - Args:
        - cards: ex..['Ks', 'Ad', 'Kh']
    """
    # 数字の優先順位
    rank_order = glbvar.rank_order
    # マークの優先順位
    suit_order = glbvar.suit_order

    # ソート関数
    def card_sort_key(card):
        rank, suit = card[0], card[1]
        return (rank_order.index(rank), suit_order.index(suit))

    # ソート実行
    sorted_cards = sorted(cards, key=card_sort_key)
    str_cards = ''.join(sorted_cards)

    return sorted_cards, str_cards

def make_nextphase_URL(action_list, use_StackSize, board=None, count=0, phase='preflop'):
    """
    TODO フロップがわかっているとき、フロップの入力もURLで行う <- 自分のCallで進まないときはフロップの入力も行う + 相手のアクションが先のとき、checkをしたとしてURLを作る
    フロップ入力画面まで進むURLを作成する
    https://app.gtowizard.com/solutions?solution_type=gwiz&gametype=Cash6m50zGeneral&depth=100&
    history_spot=10&soltab=strategy&gmfs_solution_tab=ai_sols&gmff_depth=100&
    gmff_type=general&gmff_rake=NL50&gmff_opening_size=gto&gmff__3bet_size=gto&gmfft_sort_key=0&gmfft_sort_order=desc&gmff_favorite=false&
    preflop_actions=R2-F-C

    https://app.gtowizard.com/solutions?solution_type=gwiz&soltab=strategy&gmfs_solution_tab=ai_sols&gametype=Cash6m50zGeneral&depth=20&
    gmfft_sort_key=0&gmfft_sort_order=desc&stratab=strategy_ev&gmff_depth=20&
    gmff_type=general&gmff_rake=NL50&gmff_opening_size=gto&gmff__3bet_size=gto&history_spot=6&
    preflop_actions=F-F-F-F-C-X&dialogs=cards-dialog

    https://app.gtowizard.com/solutions?tmpId=1735608071874&solution_type=gwiz&soltab=strategy&gmfs_solution_tab=ai_sols&gametype=Cash6m50zGeneral&depth=100&
    gmfft_sort_key=0&gmfft_sort_order=desc&preflop_actions=F-F-F-F-C-X
    &history_spot=6&gmff_depth=100&gmff_favorite=false&gmff_rake=NL50

    stratab=strategy_ev

    * postflop
    https://app.gtowizard.com/solutions?solution_type=gwiz&soltab=strategy&gmfs_solution_tab=ai_sols&
    gametype=Cash6m50zGeneral&depth=100&gmfft_sort_key=0&gmfft_sort_order=desc
    &preflop_actions=F-F-F-R2.5-F-C
    &history_spot=12
    &board=AdKs4h2d
    &flop_actions=X-R1.8-R6.35-R15.45-C
    &turn_actions=X

    https://app.gtowizard.com/solutions?solution_type=gwiz&soltab=strategy&gmfs_solution_tab=ai_sols
    &gametype=Cash6m50zGeneral&depth=75&gmfft_sort_key=0&gmfft_sort_order=desc&stratab=strategy
    &gmff_depth=75&gmff_type=general&gmff_rake=NL50&gmff_opening_size=gto&gmff__3bet_size=gto
    &history_spot=8
    &preflop_actions=F-R2-F-F-C-R10-C-F
    &gmff_favorite=false&dialogs=

    https://app.gtowizard.com/solutions?solution_type=gwiz&soltab=strategy&gmfs_solution_tab=ai_sols
    &gametype=Cash6m50zGeneral&depth=75&gmfft_sort_key=0&gmfft_sort_order=desc&stratab=strategy
    &gmff_depth=75&gmff_type=general&gmff_rake=NL50&gmff_opening_size=gto&gmff__3bet_size=gto
    &history_spot=8
    &preflop_actions=F-R2-F-F-C-R10-C-F
    &dialogs=&board=Jd6hAh

    """
    # URLに入力するアクションを作成する
    # preflop_actions = ''
    # for action_data in action_list:
    #     URL_action = convert_action_for_URL(action_data)
    #     if preflop_actions == '':
    #         preflop_actions = f'{URL_action}'
    #     else:
    #         preflop_actions = preflop_actions + f'-{URL_action}'

    # preflopのとき
    if phase == 'preflop':
        preflop_actions = make_url_street(action_list, phase='preflop')

        action_count = len(action_list)

        nextphase_URL = (
                        f'https://app.gtowizard.com/solutions?solution_type=gwiz&soltab=strategy&gmfs_solution_tab=ai_sols&gametype=Cash6m50zGeneral&depth={use_StackSize}&'
                        f'gmfft_sort_key=0&gmfft_sort_order=desc&stratab=strategy&gmff_depth={use_StackSize}&'
                        f'gmff_type=general&gmff_rake=NL50&gmff_opening_size=gto&gmff__3bet_size=gto&history_spot={action_count}&'
                        f'preflop_actions={preflop_actions}&dialogs=cards-dialog')
        # 改行を無くす
        # nextphase_URL = nextphase_URL.replace('\n','')

        return nextphase_URL

    #* postflopのとき
    # nextphase_URL = (
    #                 f'https://app.gtowizard.com/solutions?solution_type=gwiz&soltab=strategy&gmfs_solution_tab=ai_sols&'
    #                 f'gametype=Cash6m50zGeneral&depth={use_StackSize}&gmfft_sort_key=0&gmfft_sort_order=desc'
    #                 )

    # nextphase_URL = (
    #                     f'https://app.gtowizard.com/solutions?solution_type=gwiz&soltab=strategy&gmfs_solution_tab=ai_sols&gametype=Cash6m50zGeneral&depth={use_StackSize}&'
    #                     f'gmfft_sort_key=0&gmfft_sort_order=desc&stratab=strategy&gmff_depth={use_StackSize}&'
    #                     f'gmff_type=general&gmff_rake=NL50&gmff_opening_size=gto&gmff__3bet_size=gto&history_spot={count}&'
    #                     )

    nextphase_URL = (
                        # f'https://app.gtowizard.com/solutions?solution_type=gwiz&soltab=strategy&gmfs_solution_tab=ai_sols&gametype=Cash6m50zGeneral&depth={use_StackSize}&'
                        # f'gmfft_sort_key=0&gmfft_sort_order=desc&stratab=strategy&gmff_depth={use_StackSize}&'
                        # f'gmff_type=general&gmff_rake=NL50&gmff_opening_size=gto&gmff__3bet_size=gto&history_spot={count}&'

                        f'https://app.gtowizard.com/solutions?solution_type=gwiz&soltab=strategy&gmfs_solution_tab=ai_sols'
                        f'&gametype=Cash6m50zGeneral&depth={use_StackSize}&gmfft_sort_key=0&gmfft_sort_order=desc&stratab=strategy'
                        f'&gmff_depth={use_StackSize}&gmff_type=general&gmff_rake=NL50&gmff_opening_size=gto&gmff__3bet_size=gto'
                        f'&history_spot={count}'
                        # f'&preflop_actions=F-R2-F-F-C-R10-C-F'

                        f'https://app.gtowizard.com/solutions?solution_type=gwiz&soltab=strategy&gmfs_solution_tab=ai_sols'
                        f'&gametype=Cash6m50zGeneral&depth={use_StackSize}&gmfft_sort_key=0&gmfft_sort_order=desc&stratab=strategy'
                        f'&gmff_depth={use_StackSize}&gmff_type=general&gmff_rake=NL50&gmff_opening_size=gto&gmff__3bet_size=gto'
                        f'&history_spot={count}'
                        # f'&preflop_actions=F-R2-F-F-C-R10-C-F'
                        # f'&dialogs=&board=Jd6hAh'

                        )

    # URLを作成する
    for phase_name, actions in action_list.items():
        if actions is None:
            break
        if 'preflop' in phase_name:
            nextphase_URL += (
                f'&{phase_name}={actions}'
                f'&dialogs=&board={board}'
            )
        else:
            nextphase_URL += (
                f'&{phase_name}={actions}'
            )

    return nextphase_URL

def make_url_street(action_list, phase):
    """
    urlに入力するstreetを作成する
    """
    # preflopのとき
    if phase == 'preflop':
        preflop_actions = ''
        for action_data in action_list:
            URL_action = convert_action_for_URL(action_data)
            if preflop_actions == '':
                preflop_actions = f'{URL_action}'
            else:
                preflop_actions = preflop_actions + f'-{URL_action}'
        return preflop_actions

    # postflopのとき
    postflop_actions = ''
    for action_data in action_list:
        # ()の中身を取り出す
        URL_action = action_data.split('(')[1].split(')')[0]
        if postflop_actions == '':
            postflop_actions = f'{URL_action}'
        else:
            postflop_actions = postflop_actions + f'-{URL_action}'
    return postflop_actions

def convert_action_for_URL(action_data):
    """
    URLで入力するための簡易アクションデータを作成する
    Allinがあるとき、ここまで進まないはずなので、処理を作らない
    """
    # まず、wizardで入力する形式に変換する
    player_action, bet_rate = convert_for_input_action(action_data)

    # アクションを選ぶ
    if 'Fold' in player_action:
        URL_action = 'F'
    elif 'Call' in player_action:
        URL_action = 'C'
    elif 'Check' in player_action:
        URL_action = 'X'
    elif 'Raise' in player_action:
        URL_action = f'R{convert_number(bet_rate)}'

    return URL_action

def convert_for_input_action(action_data):
    """
    all_reportのaction_dataを、wizardに入力するときに使う形式に変換する
    """
    bet_rate = None
    # アクションを選ぶ
    if 'Fold' in action_data:
        player_action = 'Fold'
    elif 'Call' in action_data:
        player_action = 'Call'
    elif 'Check' in action_data:
        player_action = 'Check'
    elif 'Raise' in action_data or 'Allin' in action_data or 'Bet' in action_data:
        if 'Bet' in action_data:
            player_action = 'Bet'
        else:
            player_action = 'Raise'
        # 実際のRaise額を取り出す
        if '%' in action_data:
            action_rate = next(rate for rate in action_data.split('(') if '%' in rate)
            bet_rate = delete_non_numbers(action_rate, print_text=False)
        elif '(' in action_data:
            bet_rate = float(action_data.split('(')[0])
        else:
            bet_rate = delete_non_numbers(action_data, print_text=False)
    return player_action, bet_rate

# ====================================
# その他
# ====================================

#!!!
def get_action_values_from_csv(directory_path, about_hand, *, target='action_values'):
    """
    csvが存在するパスを受け取り、ハンドのvaluesを返す
    Fold100%のときも、ちゃんと他の選択肢も入れたデータをheaderから作る

    target = 'EV' とすることでEVを取り出せるようにした(250106)
        Fold100%のときはうまく取り出せないけど、そのときは、EVを取り出さないと思うから、とりあえずそのままにする。
    """

    # CSVファイルの読み込み
    action_values = {}
    correct_position = False

    while correct_position is False:
        # CSVファイルを読み込む <- os.walkを使うことでcsvのファイル名がわからないときにも読み込みできる
        for root, _, files in os.walk(directory_path):
            for file in files:
                # CSVファイルのみを対象とする
                if file.endswith(".csv"):
                    # リンプがいるときは、探すべきディレクトリのポジションが変わるので、修正する #! empデータは使用しなくなったので、下記が行われることはないはず。(250106)
                    if 'emp' in file:
                        print(f'探しているディレクトリを間違えているようです "{file}"')
                        fixed_position = file.split('(')[0].split('_')[1]
                        current_position = directory_path.split('wizard_offline')[1].split('/')[2] #TODO <- プログラムのデータの環境が変われば、これも動作しなくなる可能性がある
                        directory_path = directory_path.replace(current_position, fixed_position)
                        break

                    #* EVを取り出すかaction_valuesを取り出すか選択する
                    if target == 'action_values':
                        if 'EVs' in file:
                            continue
                    elif target == 'EV':
                        if 'EVs' not in file:
                            continue

                    csv_path = os.path.join(root, file)
                    print(f"{target} を取り出すファイル(1) : {csv_path}")
                    correct_position = True

                    with open(csv_path, mode="r", encoding="utf-8") as csvfile:
                        # csv を取り出す
                        reader = csv.DictReader(csvfile)
                        # ヘッダーを取得 <- Fold100%だったときに使う
                        header = reader.fieldnames
                        # Handの項目に 'AKo' があるか確認
                        for row in reader:
                            hand = row.get('Hand')
                            if hand == about_hand:
                                # about_hand が見つかったら、その行を辞書に格納
                                action_values = {key: float(row[key]) for key in row if key != 'Hand'}
                                break
            break

    # 空のとき
    if action_values == {}:
        for action in header:
            if 'Hand' not in action:
                if 'Fold' in str(action):
                    action_values[action] = 100
                else:
                    action_values[action] = 0

    return action_values

def check_EndPhase_with_csv_folder(directory_path, action, detail=False):
    """
    現在のディレクトリにあるフォルダを取り出す。
    これから選ぼうとしているアクションが、end_phase となるものなら、Trueを返す
    """
    end_this_phase = False

    # action が入ってないときは、一番最後に選ばれたアクションのfolderを調べる <- 既に作られたpathから、multiwayかどうか調べるときに使う
    if action is None:
        splited_path = directory_path.split('/')
        action = splited_path[-1]
        directory_path = '/'.join(splited_path[:-1]) # 最後のアクションを省いたpathにする

    for root, dirs, files in os.walk(directory_path):
        next_folder_name = next(folder for folder in dirs if action in folder)
        if '(' in next_folder_name:
            print(f'このターンでフェーズが終了するようです\nアクション : {next_folder_name} | path : {directory_path}')
            end_this_phase = True
        # postflop_errorを調べたいとき
        if detail == 'postflop_error':
            if 'solution_error' in next_folder_name:
                big_print(f'ポストフロップエラーが出るようです path : {directory_path}', 'on_red')
                return 'postflop_error'
        # フェーズが終わるかどうか調べたいとき
        elif detail:
            if 'next_phase' in next_folder_name:
                return 'next_phase'
            elif 'multiway' in next_folder_name:
                return 'multiway'
        return end_this_phase

# ======================================
# エクスプロイトの方針をまとめる
# ======================================

#!!!
def procces_assemble_exploit_plan(phase_bias_data, allphase_statistics_dict):
    """
    エクスプロイトの方針をまとめる
    """
    exploit_enemy_stra_feature = {}

    for phase, bias_data in phase_bias_data.items():

        # 取り出したデータからエクスプロイトの方針をまとめる
        exploit_plan = assemble_exploit_plan(bias_data)

        # 競合する調整があれば修正する
        exploit_plan = adjust_exploit_plan_for_conflict(exploit_plan)

        # 相手の傾向と、エクスプロイト計画を1つにする
        enemy_stra_feature = {
            'bias': bias_data,
            'exploit': exploit_plan,
        }

        exploit_enemy_stra_feature[phase] = enemy_stra_feature

    # 統計データを追加する
    exploit_enemy_stra_feature['statistics_data'] = allphase_statistics_dict

    return exploit_enemy_stra_feature

def adjust_exploit_plan_for_conflict(exploit_plan):
    """
    エクスプロイト方針で競合する内容があるとき、gtoに置き換える
    - 処理:
        - 同じタイプの中で、agre と passi に 同じものが入ってるとき競合していると判定する
    """
    # 下記を用いてjudgeする。もし調整することになっていれば、Trueが入れられる。それがagreとpassiの両方にあるとき競合している
    judge_template = {
        'Fold': None,
        'Call': None,
        'Bet': None,
        'Raise': None,
    }

    # 削除するアクションはリストに入れる
    delete_actions = []

    # 競合しているアクションを調べる
    for type_key, data in exploit_plan.items():
        judge_data = judge_template.copy()
        # agreとpassiを調べる
        for index, (style, actions) in enumerate(data.items()):
            # 調整するアクションがあればTrueを入れる
            for target_action in judge_data:
                exists_action = next((True for adjust_action in actions if target_action in adjust_action), False)
                # もし、gtoのアクションがあれば他のアクションを削除する
                if next((True for action in actions if 'gto' == action), False):
                    for action in actions:
                        if 'gto' == action:
                            continue
                        add_data = {'type_key': type_key, 'action': action}
                        if add_data not in delete_actions:
                            big_print(f'gtoがあるので、他の調整するアクションは削除します。type_key: {type_key}, action: {target_action}', 'on_red')
                            delete_actions.append({'type_key': type_key, 'action': action})
                # 一周目はあるかどうかの確認を行う
                elif index == 0:
                    judge_data[target_action] = exists_action
                # ２周目は競合しているかの確認を行う
                else:
                    # Trueかつ、1つ前と同じとき競合している
                    if exists_action and judge_data[target_action] == exists_action:
                        big_print(f'調整するアクションが競合しています。type_key: {type_key}, action: {target_action}', 'on_red')
                        # どちらのデータも削除するリストに入れる
                        delete_actions.append({'type_key': type_key, 'action': target_action})

    # 競合しているアクションを削除するためのキーをまとめる
    delete_keys = []
    for data in delete_actions:
        type_key = data['type_key']
        target_action = data['action']

        for style, actions in exploit_plan[type_key].items():
            # 削除するキーがあればリストに追加する
            for action in actions:
                if target_action in action:
                    delete_keys.append({'type_key': type_key, 'style': style, 'action': action})

    # 削除する
    for data in delete_keys:
        type_key = data['type_key']
        style = data['style']
        target_action = data['action']
        exploit_plan[type_key][style].remove(target_action)

    # 重複を削除する
    remove_duplicates_exploit_plan = {}
    for hand_type, category in exploit_plan.items():
        remove_duplicates_exploit_plan[hand_type] = {}
        for key in category:
            remove_duplicates_exploit_plan[hand_type][key] = list(set(category[key]))  # 重複削除


    return remove_duplicates_exploit_plan

def assemble_exploit_plan(bias_data):
    """
    #TODO ここの内容は統計取るところでやったほうがいいと思う
    jsonから、エクスプロイトの方針をまとめる
    - Returns:
        - agre: 頻度を増やすアクションが入る
        - passi: 頻度を減らすアクション
        - IP, OOP: このポジションのときに調整するアクション
        - against: 相手がこのアクションしてきたときの調整するアクション
        - gto: 特に調整がなければgto通りでいくけど、他に調整内容があったとしても、gto通りでいきたいときこれを入れる。最も優先度が高い
    """
    # 箱を用意する
    plan = {
        'weak': {'agre': [], 'passi': []},
        'weak_IP': {'agre': [], 'passi': []},
        'weak_OOP': {'agre': [], 'passi': []},
        'value': {'agre': [], 'passi': []},
        'value_IP': {'agre': [], 'passi': []},
        'value_against_Raise': {'agre': [], 'passi': []},
        'strong': {'agre': [], 'passi': []},
        'catcher': {'agre': [], 'passi': []},
    }
    # 方針を入れる
    for bias_key, value in bias_data.items():
        # Callし過ぎの相手
        if bias_key == 'too_Call' and value:
            plan['weak']['passi'] += ['Bet', 'Raise']
            plan['value']['agre'] += ['Bet(small)']
        # Foldし過ぎの相手
        if bias_key == 'too_Fold' and value:
            plan['weak']['agre'] += ['Bet']
            plan['value']['passi'] += ['Bet']
            plan['strong']['agre'] += ['Bet']
        # ブラフ関係
        if bias_key == 'bluff':
            # ブラフが少ない人
            if value:
                plan['catcher']['agre'] += ['Call']
                plan['value']['agre'] += ['Bet']
                plan['weak']['agre'] += ['Raise(mini)']
            # ブラフが多い人
            elif value is False:
                plan['catcher']['passi'] += ['Call']
                plan['value']['agre'] += ['Bet(small)']
                plan['value_against_Raise']['agre'] += ['Fold']
                plan['strong']['agre'] += ['gto']
                plan['weak']['agre'] += ['Bet']
        # 罠好き関係
        if bias_key == 'strong_hand':
            # 強いハンドでCheckし過ぎる人
            if value is False:
                plan['weak']['passi'] += ['Bet']
                plan['value']['passi'] += ['Bet']
                plan['value']['agre'] += ['Raise'] # <- valueBetは減らして、Betが来たときRaise頻度増やす
                plan['weak_IP']['passi'] += ['Bet']
                plan['weak_OOP']['agre'] += ['Bet']
            # 強いハンドでBetし過ぎる人
            elif value:
                plan['catcher']['passi'] += ['Call']
                plan['value_OOP']['agre'] += ['Bet']
                plan['weak_OOP']['agre'] += ['Bet']
                # 全てRaiseは減らす
                for plan_key in plan:
                    plan[plan_key]['passi'] += ['Raise']
    return plan




