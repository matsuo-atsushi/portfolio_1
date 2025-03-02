"""
各プレイヤーのgtoのsolutionを用意する
"""

import os
import traceback
import time
from pathlib import Path
import pandas as pd

from strategy_analyzer_app.io_operations.print_processing import big_print, suppress_print
from strategy_analyzer_app.text_processing.text_extraction import convert_number, delete_non_numbers
from strategy_analyzer_app.poker_logic.action_report_control import fix_action
import strategy_analyzer_app.global_vars as glbvar
import strategy_analyzer_app.io_operations.csv_processing as csvproce
import strategy_analyzer_app.poker_logic.modify_allreport_logic as allrepo
import strategy_analyzer_app.poker_logic.poker_utils as pkutil
import strategy_analyzer_app.control_webdriver.wizard_processing as wizproce
import strategy_analyzer_app.control_webdriver.control_wizard as ctlwiz

# error_logリスト
multiway_log = 'postflop: multiway' # multiwayであるとき
cant_Call_log = 'preflop: cant_choice_Call_player' # Eがいるとき追加される
exists_postflop_solution_log_with_hand = 'postflop: exists_solution_with_hand' # postflopのsolutionがあり、ハンドがわかっているとき
exists_postflop_solution_log_No_hand = 'postflop: exists_solution_No_hand'
no_actions_log = 'preflop: no_actions' # 一度もアクションをしていないとき、jsonを保存する意味がないので、listにlogだけ追加して、jsonは保存しない
preflop_no_solution_log = 'preflop: no_solution_error' # E がたくさんいたりしたら、preflopのsolutionが取り出せなくなる
postflop_no_solution_log_1 = 'postflop: no_solution_error(solu_err)'
postflop_no_solution_log_2 = 'postflop: no_solution_error(no_Call)'
complete_log = 'complete'
cant_trust_street_log = 'cant_trust_street' # 信用できないゲームのとき、このlogを入れて、二度と解析しないようにする <- no_handで、potサイズが大きくズレてるときこれが入る

# global変数を宣言
check_postflop_solution = True # (False, trust_only, no_hand)これをFalseにすると、wizardを使って、postflopのsolutionの確認するのをパスする。そして、パスしたことをエラーlogに追加する
complete_anlyzID_list = [] # 調べたanlzIDを入れる
target_count = 90 # (10, 100) postflop時の解析する目標数を入れる。100を入れたら、100あるものから調べていく
target_style = None # 信頼できるデータしか集めないとき、without_zerorange を入れる
driver = None # 初期値

def main():

    global check_postflop_solution, complete_anlyzID_list, target_count, target_style

    # 小さい数字から並べたidリストを用意
    id_list = make_id_list()

    # 信頼できるデータを先に集める
    for check_postflop_solution in (False, 'no_hand'):
        """
        False -> preflopのみ解析する
        no_hand -> ハンドがあるものも、ないものも解析する
        """
        for target_style in ('without_zerorange',):
            complete_anlyzID_list = []
            for anlz_id in id_list:
                # まだ調べてないか確認する
                if anlz_id in complete_anlyzID_list:
                    continue

                big_print(f'\n======== "{anlz_id}" の確認を行います ========', 'light_green')
                make_data_for_analyze(anlz_id)

def make_data_for_analyze(anlz_id):
    """
    1, 読み込むデータを用意する
    2, 既にデータが作られているstrategyはパスする
    3, 変換を行う
    """
    global check_postflop_solution, complete_anlyzID_list, target_count, target_style

    # データを作るstradataのリストを用意する
    target_unique_id, matching_anlz_ids, progress_list = get_stradata_list(anlz_id)

    # 処理済みidリストに入れる
    complete_anlyzID_list += matching_anlz_ids

    # stranumberを順に読み込む
    for stranumber in progress_list['target']:

        big_print(f'\n======== {anlz_id}:  これから、"{stranumber}" の確認を行います ========', 'white')

        try:
            # 処理する
            convert_stradata(stranumber)
        except Exception as e:
            traceback.print_exc()

def convert_stradata(stranumber):
    """
    stradataを読み込んで変換を行う
    """
    # データのパスを探す
    stradata_path = serch_stradata_path(stranumber)
    # 読み込む。データがなかったらエラー出る
    print(f'   path -> {stradata_path}')
    if stradata_path is None:
        """
        250204
        ここに到達するのは、何らかの間違いでjsonを削除してしまったときにくる気がする
        """
        big_print(f'stranumber: {stranumber} のjsonデータが存在しません', 'red', '▲')
        # if stranumber in ('17374548786342',):
        #     return
        # input('input: ...')
        return
    stradata = csvproce.read_data(stradata_path, file_type='json')

    # プレイヤーのデータを作成する
    player_anlyz_data = make_player_list(stradata, stranumber)

    # 各フェーズごとに分析用のデータを作成する
    player_anlyz_data = create_analyze_data_with_report(stradata, player_anlyz_data)

    # 保存する
    save_player_anlyz_data(stradata, player_anlyz_data, stranumber)

def save_player_anlyz_data(stradata, player_anlyz_data, stranumber):
    """
    player_anlyz_dataを保存して、解析済みリストに追加する
    """

    all_players = stradata['general']['all_players']

    for position, data in player_anlyz_data.items():
        # anlz_id を取り出す
        anlz_id = next(data['ID'] for data in all_players.values() if data['position'] == position)
        if anlz_id is None or 'error_msg' not in data['general']:
            continue

        big_print(f'anlz_id: {anlz_id}({position}) のデータを追加します')

        #* listに保存するための error_log を用意する <- やっぱり、error_logはすべて残す(後から何か変えるかもしれない)
        error_log_list = data['general']['error_msg'].copy()
        # multiway, cant_Call_log は削除する
        # if multiway_log in error_log_list:
        #     error_log_list.remove(multiway_log)
        # if cant_Call_log in error_log_list:
        #     error_log_list.remove(cant_Call_log)
        # logがあるとき、1つのテキストにする
        if error_log_list:
            error_log = ', '.join(error_log_list)
        # logがなければ空にする
        else:
            error_log = ''

        #* jsonを追加する
        should_save_json = check_save_json(data)
        if should_save_json:
            json_path = os.path.join(glbvar.player_private_dir, anlz_id, 'convert_stradata', f'{stranumber}.json')
            csvproce.make_json_data(json_path, data, alert=False)
        else:
            if error_log:
                error_log += f', {no_actions_log}'
            else:
                error_log = no_actions_log

        # 保存先のcsvpathを用意 <- ここまで来たとき、既にcsvのディレクトリもcsvも用意されてる
        convert_list_csv = os.path.join(glbvar.player_private_dir, anlz_id, 'convert_list.csv')
        fieldnames=['stranumber', 'error_log']

        #* postflopの解析をしたとき
        global check_postflop_solution
        if check_postflop_solution:
            # エラーlogがなければcompleteにする
            if error_log == '':
                error_log = complete_log
            # csv読み込む
            rows = csvproce.read_data(convert_list_csv, file_type='csv')
            # csvを書き換える
            for row in rows:
                if row["stranumber"] == stranumber:  # 数値ではなく文字列として比較
                    row["error_log"] = error_log
            # csvを上書き保存する
            csvproce.save_new_data(convert_list_csv, rows, fieldnames, file_type='csv', alert=False)

        else:
            #* convert_listに追加する
            csvproce.add_value_to_csv(convert_list_csv, fieldnames=fieldnames, new_data={'stranumber': stranumber, 'error_log': error_log})

def check_save_json(data):
    """
    jsonを保存すべきかどうか調べる
    """
    if 'preflop' in data:
        return True
    big_print('actionのデータが1つもないので、データの保存をパスします', 'cyan')

# =====================================
# 各フェーズごとに分析用のデータを作成する
# =====================================

def create_analyze_data_with_report(stradata, player_anlyz_data):
    """
    各フェーズごとに分析用のデータを作成する
    - 処理:
        - 1: フェーズごとのallreportを取り出す
        - 2: allreportを順に取り出す
        - 3: pot, situation, gtoを用意して追加する
    """

    global driver, target_style, check_postflop_solution

    game_data = {
        'phase': None,
        'pot': 0, # potを計算する
        'pre_pot': 0, # 1つ前フェーズの終了時のpotを保存する
        'current_effective_stack_ratio': 0, # 有効スタックの残高を確認して pot/stack を計算する
        'wizard_count': 0, # wizardを操作するときのカウント <- preflopはその都度countする。postflopで使われ始める
        'situation': {'all_Fold': {'count': 0}}, # 初期値
        'original_Raiser': None,
        'alive_positions': list(player_anlyz_data.keys()), # 生き残っているposition
        'Allin_positions': {}, # Allinしたポジションと、そのphaseを記録する。そのphase中は、stack_sizeの判定に使用する
        'continue': True, # action is None だったとき終了する
        'most_bet': 0,
        'action_report': glbvar.made_turn_copy.copy(), # potを計算するために、そのphaseのreportを作成する
        'total_bet': glbvar.made_turn_copy.copy(),
        'error_log': [],
        'driver': driver,
        'this_phase_cards': [],
        'postflop_path': None, # postflopのsolutionが存在するとき、pathが入る。存在しないとき、Falseになる
        'exist_data': None, # postflopのオフラインsolutionpathが存在する可能性があるとき、True
        'action_choices': None,
        'wiz_elements': None,
        'postflop_position_list': {},
        'pre_actions': glbvar.made_turn_copy.copy(), # 1つ前に行われたアクションが入っている
        'current_actions': glbvar.made_turn_copy.copy(), # このターンに行われたアクションが入っている
        'zero_range_positions': [], #postflopのsolitionがないpositionを入れる。ここがlen=2になるとき、かつ、without_zerorangeのとき、raiseして処理を抜ける
        'my_position': get_my_position(stradata), # my_positionを取り出す。これは不要なデータなので信頼できないデータに入れる
    }

    #* フェーズごとに取り出す
    for phase, data in stradata['history'].items():

        # reportがないphaseがあれば終了
        allreport = data['strategy_history']
        if len(allreport) == 0 or game_data['continue'] is False:
            break

        # 初期化する
        game_data['phase'] = phase
        game_data['action_report'] = glbvar.made_turn_copy.copy() # potを計算するために、そのphaseのreportを作成する
        game_data['current_actions'] = glbvar.made_turn_copy.copy()
        game_data['most_bet'] = 0
        game_data['Allin_positions'][game_data['phase']] = [] # リストを新規作成
        phase_active_positions = [] # このフェーズでアクションしたポジションを入れる #? 何のために用意した？
        current_allreport = {} # gtoを取り出すためのallreportを作成する

        # カードを追加する
        game_data['this_phase_cards'] = data['board_cards']
        # pathがあるなら、pathにもcardを追加する
        if game_data['postflop_path'] and game_data['this_phase_cards']:
            _, str_cards = pkutil.cards_sort(game_data['this_phase_cards'])
            game_data['postflop_path'] = os.path.join(game_data['postflop_path'], str_cards)
            # カードを入力する必要があれば入力する
            if game_data['action_choices']:
                wizproce.select_flopcards(game_data['driver'], game_data['this_phase_cards'], game_data['phase'])

        # preflopではないとき、IP, OOP, MP を確認する
        if phase != 'preflop':
            game_data['postflop_position_list'] = check_postflop_position(allreport)

        #* allreportを取り出す
        big_print(f'{game_data["phase"]} の確認を開始します', 'white')
        for posidata, action in allreport.items():
            big_print(f'   - {posidata}: {action}', 'white')
            # actionがないとき終了する
            if action is None:
                big_print('actionがNoneだったので解析を終了します', 'on_red')
                game_data['continue'] = False
                big_print('デバッグ: action is None がいます', 'on_red')
                # input('inputで止めてます....')
                break

            # 信頼できるデータしか集めないとき
            if check_postflop_solution and len(game_data['zero_range_positions']) == 2:
                big_print('データに信頼できるものがないので処理を強制的に終了します', 'on_red')
                # ハンドがあるものだったとき、logを追加して保存する
                if check_postflop_solution == 'trust_only':
                    big_print(f'logに "{exists_postflop_solution_log_with_hand}" を追加します', 'on_red')
                    game_data['error_log'].append(exists_postflop_solution_log_with_hand)
                    game_data['continue'] = False
                    break
                elif check_postflop_solution == 'no_hand':
                    big_print(f'logに "{cant_trust_street_log}" を追加します', 'on_red')
                    game_data['error_log'].append(cant_trust_street_log)
                    game_data['continue'] = False
                    break
                else:
                    # 強制終了
                    raise

            # positionを取り出す
            position = posidata.split('_')[1]

            # preflopのSB, BB はパスする
            if game_data['phase'] == 'preflop' and action in ('0.5', '1'):
                game_data['action_report'][position] = delete_non_numbers(action, print_text=False)
                game_data['most_bet'] = delete_non_numbers(action, print_text=False)
                continue

            # potを計算する
            game_data['pot'] = calucurate_pot(game_data['pre_pot'], game_data['action_report'])

            # 特定の条件のとき、いくつかの処理をパスするので、条件を確認
            go_procces = True
            if (position not in player_anlyz_data or
                'player_4' in player_anlyz_data[position]['general']['position'] or
                'done' in player_anlyz_data[position]['general']['position']):
                go_procces = False

            # allreportを更新する #! solutionを取り出す前に行うことにした。自分が分岐するとき、次のアクションが何かわかるようにした。今まで通りcurrent_report使う処理は、一番最後まできたら終了するようにした
            current_allreport[posidata] = action

            # Allinしてると認定されている人なら飛ばす(250216追加。current_allreport にもいれないつもりだったけど、入れてから飛ばすことにした)
            if next((True for tmp_list in game_data['Allin_positions'].values() if position in tmp_list), False):
                big_print(f'既にwizardか、ストリート上、Allinしている人が取り出されたので飛ばします posidata: {posidata}', 'on_red')
                continue

            # gto solutionを取り出す。postflopは必ず行う
            if go_procces or game_data['phase'] != 'preflop':
                # effective_stackの現在の残高を更新する
                game_data['current_effective_stack_ratio'] = select_use_StackSize(game_data, position, player_anlyz_data, target_effective_stack=True, effe_ratio=True)
                # gto solutionを取り出す
                solution_data, gto_select_action = get_gto_solution(current_allreport, game_data, position, player_anlyz_data, action)

                # Betが大きすぎて、Allinと認められたプレイヤーは下記を行う
                if 'Allin' in str(gto_select_action) and position in game_data['alive_positions']:
                    game_data['alive_positions'].remove(position)
                    game_data['Allin_positions'][game_data['phase']].append(position)
                    # input('input: Allinが入りました')

                # situationを判定する。postflopでは各プレイヤーごとに変わる
                game_data['situation'] = judge_situation(game_data, game_data['action_report'], current_allreport, position)

            # カウント追加(postflopのみ)
            if game_data['phase'] != 'preflop':
                game_data['wizard_count'] += 1

            # report更新
            game_data['action_report'][position] = update_action_report(game_data['action_report'][position], action, game_data, position, player_anlyz_data)
            # current_actions更新
            game_data['current_actions'][position] = update_current_actions(game_data['current_actions'][position], action)

            # AllinかFoldのとき、リストから削除する
            if ('Fold' in action or 'Allin' in action) and position in game_data['alive_positions']:
                game_data['alive_positions'].remove(position)
                if 'Allin' in action:
                    big_print('デバッグ: Allinがいます', 'on_red')
                    # input('inputで止めてます....')
                    game_data['Allin_positions'][game_data['phase']].append(position)
            # most_bet, original_Raiserを更新する
            if 'Raise' in action or 'Bet' in action or 'Allin' in action:
                if game_data['most_bet'] < delete_non_numbers(action, print_text=False):
                    game_data['most_bet'] = delete_non_numbers(action, print_text=False)
                    game_data['original_Raiser'] = position
            # RaiserがcheckしたらNoneにする
            elif 'Check' in action and game_data['original_Raiser'] == position:
                game_data['original_Raiser'] = None

            # anlyzdataを追加する
            # player_anlyz_data にpositionが登録されてない人。自分はパス
            if go_procces is False:
                continue
            # まだ、phaseのdictがないなら用意する
            if game_data['phase'] not in  player_anlyz_data[position]:
                if game_data['phase'] == 'preflop':
                    player_anlyz_data[position][game_data['phase']] = {
                    'general': {},
                    'solutions': []
                    }
                else:
                    player_anlyz_data[position][game_data['phase']] = {
                        'general': {'board': game_data['this_phase_cards'], 'position': game_data['postflop_position_list'][position]},
                        'solutions': []
                    }

            # データをまとめて追加する
            data_for_add = organize_anlyz_data(game_data, solution_data, action, gto_select_action)
            player_anlyz_data[position][game_data['phase']]['solutions'].append(data_for_add)

        # total_betを更新する
        game_data = update_total_bet(game_data)

        # pre potを更新
        # potを計算する
        game_data['pre_pot'] = calucurate_pot(game_data['pre_pot'], game_data['action_report'])

        # actionsを入れ替える
        game_data['pre_actions'] = game_data['current_actions']

        # preflopが終わるとき、pathを用意する -> そのpathがnext_phaseでなければsolutionを手に入れることはできない
        if game_data['phase'] == 'preflop':
            exists_flop_history = check_exists_flop_history(stradata['history'])
            # 先に、multiwayかどうか調べる
            multiway = True if stradata['general']['situation'] == 'multiway' else False
            if multiway and len(game_data['alive_positions']) <= 2:
                big_print('multiway の状況となっているのに、残っているポジションが2人以下のようです。multiway = False にします', 'red', '▲')
                input('input: ')
                multiway = False
            # limpもパスする
            limp_situation = True if cant_Call_log in game_data['error_log'] else False
            # stradataのsituationの判定するタイミングが間違えていて、flopで終わるspotはすべてNoneになってしまっているので、別の場所(create_path_for_postflop())でもmultiwayかどうか判定する
            if exists_flop_history is False or multiway or limp_situation:
                game_data['exist_data'] = False
                game_data['postflop_path'] = False
                if multiway:
                    game_data['error_log'].append(multiway_log)
            else:
                # multiwayではないとき、pathを作成する。ここでも、multiwayでないかチェックする
                game_data = create_path_for_postflop(game_data, allreport, player_anlyz_data)
        elif game_data['phase'] not in ('preflop', 'river'):
            # original_Raiserをチェックする
            game_data['original_Raiser'] = check_original_Raiser(game_data['pre_actions'], game_data['original_Raiser'])

    # 各プレイヤーのdataにエラーlogを追加する
    for log in game_data['error_log']:
        for position in player_anlyz_data:
            if 'error_msg' in player_anlyz_data[position]['general']:
                player_anlyz_data[position]['general']['error_msg'].append(log)

    return player_anlyz_data

# =====================================
# gto_solutionを取り出す(action, EV, [EQ, EQR])
# =====================================

def get_gto_solution(current_allreport, game_data, position, player_anlyz_data, action):
    """
    reportからpathを作成して、solutionを読み込む
    """

    # preflopのとき
    if game_data['phase'] == 'preflop':

        # 既にAllinして確認するものがないとき、下記を行うだけ
        if position not in game_data['alive_positions']:
            solution_data, gto_select_action = make_no_solution_data(player_anlyz_data, game_data, position, action)
            return solution_data, gto_select_action

        # stack_sizeを決める
        use_StackSize = select_use_StackSize(game_data, position, player_anlyz_data)

        # pathを用意する
        solution_dir_list = allrepo.create_path_for_get_solution(current_allreport, use_StackSize, game_data)

        # solutionがないストリートのときの処理
        if solution_dir_list is None:
            # エラーログがなければ追加する
            if preflop_no_solution_log not in game_data['error_log']:
                game_data['error_log'].append(preflop_no_solution_log)
            solution_data, gto_select_action = make_no_solution_data(player_anlyz_data, game_data, position, action)
            return solution_data, gto_select_action

        gto_select_action = select_action_in_gto(use_StackSize, solution_dir_list, action, position, game_data)

        # solutionを取り出す。データをまとめる
        solution_data = read_gto_solution_and_gather_data(player_anlyz_data, position, solution_dir_list, game_data, action, gto_select_action)

        return solution_data, gto_select_action

    # postflopのとき
    """
    1, オフラインデータがあるかチェック
    2, ないなら、wizardを読み込む -> gzを保存
    3, gz を読み込んで処理
    4, solutionが存在しないストリートのときの処理
    """
    # solutionが存在しないとき
    if game_data['exist_data'] is False and game_data['postflop_path'] is False:
        solution_data, gto_select_action = make_no_solution_data(player_anlyz_data, game_data, position, action)
        return solution_data, gto_select_action

    # gzのpathを作成
    solution_gz_path = os.path.join(game_data['postflop_path'], f'{game_data["wizard_count"]}_{position}_solutions.json.gz')
    # 存在する可能性があるとき
    if game_data['exist_data']:
        # gzが存在しないとき
        if not os.path.exists(solution_gz_path):
            # driverが立ち上がっていなければ起動すうる
            if game_data['driver'] is None:
                big_print('driverを立ち上げます', 'yellow')

                global driver
                driver = ctlwiz.setup_chrome_driver(None, small=5)
                game_data['driver'] = driver

            game_data['exist_data'] = False # Falseにして、今後wizardの処理を行わせる
            glbvar.all_logs = [] # 読み込み済みのlogをリセットする
            # wizardにURLでジャンプする
            pkutil.input_nextphase_URL(game_data['driver'], game_data['postflop_path'], None, mode='postflop')

    # データがなく、pathが存在するとき、wizardを操作してgzや、フォルダを作る
    if game_data['exist_data'] is False and game_data['postflop_path']:
        # elementを取り出す
        action_choices, wiz_elements, _, gto_stack = wizproce.load_action_choices(game_data['driver'], position, game_data["wizard_count"], game_data["phase"], get_GTOstack=True)
        # 別のところからでもクリックできるようにする
        game_data['action_choices'] = action_choices
        game_data['wiz_elements'] = wiz_elements

        # solutionエラーが出てないか確認する
        exists_error = ctlwiz.check_204_error(game_data['driver'])
        # エラーが出てるとき -> logが存在しない
        if exists_error:
            """
            1, エラーディレクトリを作成する
            2, gtoに近いアクションを選ぶ
            3, 次のpathを作成する(gtoアクションの名前で作成)
            4, solutionがないときのデータを用意
            5, 相手が行ったアクションで近いものをwizardでクリックする
            """
            # zerorangeリストに入れる
            if position not in game_data['zero_range_positions']:
                game_data['zero_range_positions'].append(position)

            big_print('solution_errorが出ています', 'on_red')
            # gtoに近いものを選ぶ
            gto_select_action = select_postflop_action_in_gto(action, position, game_data, action_choices)
            # solutionerrorであることをディレクトリで示す
            error_dir = os.path.join(game_data['postflop_path'], '_solution_error')
            if not os.path.exists(error_dir):
                os.makedirs(error_dir)
            # 次のpathを作成する
            game_data['postflop_path'] = os.path.join(game_data['postflop_path'], gto_select_action)
            # solutionがないときのsolutiondataを作成する
            solution_data, _ = make_no_solution_data(player_anlyz_data, game_data, position, action)
            # クリックする
            click_wiazrd(gto_select_action, game_data)
            return solution_data, gto_select_action

        # gzの保存
        ctlwiz.save_postflop_solution(game_data['driver'], position, solution_gz_path, gto_stack)

        # folder, general.jsonを作成する
        make_solution_dirs(solution_gz_path, action_choices, game_data["wizard_count"])

    # gtoに近いものを選ぶ
    gto_select_action = select_postflop_action_in_gto(action, position, game_data)

    # gzを読み込んで必要なデータを用意する
    solution_data = read_postflop_gto_with_gz(player_anlyz_data, position, solution_gz_path, game_data, action, gto_select_action)

    # zerorangeの確認
    zerorange_solution = check_zerorange_solution(solution_data)
    # zerorangeリストに入れる
    if zerorange_solution or position == game_data['my_position']:
        if position not in game_data['zero_range_positions']:
            game_data['zero_range_positions'].append(position)
    # もし信頼できるデータとなったとき、リストから削除する
    elif not zerorange_solution and position in game_data['zero_range_positions']:
        game_data['zero_range_positions'].remove(position)

    # wizardをクリックする(必要があれば)
    if game_data['action_choices']:
        click_wiazrd(gto_select_action, game_data)

    # postflop_path を更新する
    game_data['postflop_path'] = udpate_postflop_path(game_data['postflop_path'], gto_select_action)

    return solution_data, gto_select_action

def check_zerorange_solution(solution_data):
    """
    solutiondataをみて、solutionがない状況かどうか判定する
    また、potの差が大きすぎたら、信頼できないデータとする
    """
    global check_postflop_solution, target_style

    if check_postflop_solution == 'trust_only' and target_style == 'without_zerorange':
        # 条件に合わないものは返す
        if 'solution' not in solution_data:
            return True
        # solutionを取り出す
        action_values = next((solution['detail'] for solution in solution_data['solution'] if 'detail' in solution), False)
        if not action_values:
            return True

        # totalが0は返す
        total_rate = sum(value for value in action_values.values())
        if total_rate == 0:
            big_print(f'信頼できないデータです ハンドレンジがありません', 'on_red')
            return True

    # potとgtoの差が大きすぎるものはパスする
    real_pot = delete_non_numbers(solution_data['pot'].split('(')[0], print_text=False)
    gto_pot = delete_non_numbers(solution_data['pot'].split('gto')[1], print_text=False)
    diff_pot_rate = round(((1 - min(gto_pot, real_pot) / max(gto_pot, real_pot))*100), 1)
    if glbvar.trust_diff_pot_rate < diff_pot_rate:
        big_print(f'信頼できないデータです diff_pot_rate: {diff_pot_rate}%', 'on_red')
        return True

    big_print(f'信頼できるデータです diff_pot_rate: {diff_pot_rate}%', 'on_yellow')

def make_no_solution_data(player_anlyz_data, game_data, position, action):
    """
    solutionがないときに入れるデータを作成する
    """
    # potサイズの計算をする
    real_pot = game_data['pot']
    current_stack = calucurate_current_stack(player_anlyz_data[position]['general']['initial_stack'], game_data['action_report'][position], game_data['total_bet'][position])
    pot_per_stack = round(real_pot/current_stack*100)
    solution_data = {
        'pot': f'{real_pot}(pot/stack:{pot_per_stack}%({game_data["current_effective_stack_ratio"]}%))',
        'action': f'{action}',
    }
    return solution_data, None

def udpate_postflop_path(postflop_path, gto_select_action):
    """
    postflop_path を更新する
    """
    # ディレクトリを集める -> ディレクトリは、アクション選択肢
    dir_actions = os.listdir(postflop_path)

    if '(' in gto_select_action:
        gto_select_action = gto_select_action.split('(')[0]

    # 最も近いアクションを含むdirを探す
    next_dir = next(dir_name for dir_name in dir_actions if gto_select_action in dir_name)

    next_postflop_path = os.path.join(postflop_path, next_dir)

    return next_postflop_path

def read_postflop_gto_with_gz(player_anlyz_data, position, solution_gz_path, game_data, active_action, gto_select_action):
    """
    gtoのデータを取り出す
    """
    # general.jsonを取り出す
    parent_path = os.path.dirname(solution_gz_path)
    gereral_path = os.path.join(parent_path, f'{game_data["wizard_count"]}_general.json')
    general_data = csvproce.read_data_with_make_data(gereral_path, file_type='json')

    # potについて計算する
    real_pot = game_data['pot']
    gto_pot = general_data['pot_size']
    current_stack = calucurate_current_stack(player_anlyz_data[position]['general']['initial_stack'], game_data['action_report'][position], game_data['total_bet'][position])
    pot_per_stack = round(real_pot/current_stack*100) # potが大きいと%が大きくなる。potが大きくなるとアクションに傾向が出る人をあぶり出す

    # rangeのアクションを取り出す
    range_action_values = {action: rate for action, rate in general_data['range_action'].items() if action != 'Hand'}

    # ハンドがわかっていないとき
    if 'about_hand' not in player_anlyz_data[position]['general'] or player_anlyz_data[position]['general']['about_hand'] is None:
        # rangeのsolutionのみ入れる
        solution_data = {
            'pot': f'{real_pot}(pot/stack:{pot_per_stack}%({game_data["current_effective_stack_ratio"]}%), gto:{gto_pot})',
            'solution': range_action_values,
            'action': f'{active_action}(near_gto:{gto_select_action})',
        }

        return solution_data

    # ハンドがわかっているとき
    # gzを読み込む
    gz_data = csvproce.read_data_with_make_data(solution_gz_path, file_type='gzip')

    # detail_handのデータをlogから取り出す処理をまとめた
    detail_action_values, hand_EVs, EQ, EQR = get_detail_info_from_log(gz_data, gto_pot, player_anlyz_data[position]['general']['detail_hand'])

    # データをまとめる
    solution_data = {
        'pot': f'{real_pot}(pot/stack:{pot_per_stack}%({game_data["current_effective_stack_ratio"]}%), gto:{gto_pot})',
        'solution': [
            {'range': range_action_values},
            {'detail': detail_action_values}
            ],
        'action': f'{active_action}(near_gto:{gto_select_action})',
        'EV': hand_EVs,
        'EQ': EQ,
        'EQR': EQR,
    }

    return solution_data

def get_detail_info_from_log(log_data, gto_pot, detail_hand):
    """
    logデータからdetail_handのsolutionデータなどを取り出す
    """
    # detail_handのインデックスを取り出す
    hand_index = glbvar.all_hand_order.index(detail_hand)#(player_anlyz_data[position]['general']['detail_hand'])

    #* ハンドのsolutionを用意する
    #1 ) action_valuesとEVs
    detail_action_values = {}
    hand_EVs = {}
    for i, solution_data in enumerate(log_data['solutions']):
        action = solution_data['action']['display_name'].capitalize()
        rate = solution_data['action']['betsize_by_pot']
        strategy_ratio = solution_data['strategy'][hand_index]
        ev_ratio = solution_data['evs'][hand_index]

        # action_nameを用意
        if rate is None:
            action_name = action
        else:
            action_name = f'{action}{round(float(rate)*100)}%'
        # データを追加する
        detail_action_values[action_name] = round(strategy_ratio*100, 1)
        hand_EVs[action_name] = round(ev_ratio, 2)

    # EVにpercentを追加する
    hand_EVs = calucurate_EV_percent(detail_action_values, hand_EVs, gto_pot)

    # 2) EQ, EQR を用意する
    for player_info in log_data['players_info']:
        # アクティブプレイヤーを取り出す
        if player_info['player']['is_active']:
            EQ = round(player_info['hand_eqs'][hand_index] * 100 , 1)
            EQR = round(player_info['hand_eqrs'][hand_index] * 100 , 1)

    return detail_action_values, hand_EVs, EQ, EQR

def make_solution_dirs(solution_gz_path, action_choices, wizard_count):
    """
    gzの中身を見てその他のアクションディレクトリや、general.jsonを作成する
    - Args:
        - action_choices: フォルダを作るときに、名前に違いがないか一応チェックする
    """
    # gzを読み込む
    gz_data = None
    while gz_data is None:
        gz_data = csvproce.read_data_with_make_data(solution_gz_path, file_type='gzip')
        if gz_data is None:
            time.sleep(0.5)

    # ディレクトリpathを用意
    parent_dir = os.path.dirname(solution_gz_path)

    #* generalを作成する ->  pot, range_actionを取り出す
    # データを取り出す
    range_action_data = {}
    for i, solution_data in enumerate(gz_data['solutions']):
        action = solution_data['action']['display_name'].capitalize()
        # action_group = data['action']['advanced_group'].capitalize()
        rate = solution_data['action']['betsize_by_pot']
        code = solution_data['action']['code']
        action_ratio = solution_data['total_frequency']
        range_action_data[i] = {
            'action': action,
            # 'action_group': action_group,
            'rate': rate,
            'code': code,
            'action_ratio': action_ratio,
        }

    #* 保存用のデータを作成しながら、フォルダも作る
    range_action = {'Hand': 'range'}
    for data in range_action_data.values():
        action = data['action']
        # action_group = data['action_group']
        rate = data['rate']
        code = data['code']
        action_ratio = data['action_ratio']

        # データを整理
        if rate is None:
            action_name = action
            dir_name = f'{action_name}({code})'
        else:
            action_name = f'{action}{round(float(rate)*100)}%' # ({action_group})
            dir_name = f'{action_name}({code})'

        # alertを用意
        if action_name not in action_choices.values():
            big_print(f'choicesに存在しないaction_nameです。 action_name: {action_name}, action_choices: {action_choices}', 'red', '▲')

        # データを追加
        range_action[action_name] = round(action_ratio*100, 1)
        # ディレクトリを作成
        dir_path = os.path.join(parent_dir, dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    # potを取り出す
    pot = gz_data['game']['current_street']['end_pot']
    pot = round(float(pot), 1)

    general_data = {
        'pot_size': pot,
        'range_action': range_action,
    }

    # general.jsonを作成
    general_path = os.path.join(parent_dir, f'{wizard_count}_general.json')
    csvproce.make_json_data(general_path, general_data, alert=False)

def click_wiazrd(gto_select_action, game_data):
    """
    wizardで今回のアクションをクリックする
    """
    for i, action in game_data['action_choices'].items():
        if gto_select_action in action:
            game_data['wiz_elements'][i].click()
            return

def select_postflop_action_in_gto(action, position, game_data, action_choices_data=None):
    """
    postflopの最も近いアクションを取り出す
    - 処理:
        - 1, general.jsonからaction_choicesを作成する
        - 2, もっとも近いアクションを判定する

    :params action_choices_data: 既にデータを持っているなら渡せば、general_dataから探さなくてよくなる
    """
    # データを取り出さないといけないとき
    if action_choices_data is None:
        # general.jsonを取り出す
        gereral_path = os.path.join(game_data['postflop_path'], f'{game_data["wizard_count"]}_general.json')
        general_data = csvproce.read_data_with_make_data(gereral_path, file_type='json')

        # action_choicesを作成する
        action_choices = {}
        for index, action_choice in enumerate(general_data['range_action']):
            if action_choice == 'Hand':
                continue
            #! 一旦、Bet_smallとかも入れたデータで処理する。エラー出るなら考える。Bet_smallとかあるほうが、situationをつくるのが楽になる気がする(250130)
            # if '(' in action:
            #     action = action.split('(')[0]
            action_choices[index] = action_choice
    else:
        action_choices = action_choices_data

    # アクションを分解する
    player_action, bet_rate = pkutil.convert_for_input_action(action)

    *_, selected_action = suppress_print(wizproce.best_select_player_action)(action_choices, player_action, bet_rate, 0, position, game_data['phase'], [],
                                driver=None, action_text_elements=None, check_between_Bet=True, dont_click_small_bet=True, rough_check=True, analyze_mode=True)

    if len(selected_action) == 2:
        against_list = selected_action[0].copy()
        selected_action = against_list[0]

    return selected_action

def select_action_in_gto(use_StackSize, solution_dir_list, action, position, game_data):
    """
    gtoの中で最も近いアクションを選ぶ
    """
    # 分岐するときは、Noneをいれる
    if len(solution_dir_list) == 2:
        # 分岐したなら、error_log入れる
        if cant_Call_log not in game_data['error_log']:
            game_data['error_log'].append(cant_Call_log)
            big_print('デバッグ:リンプ(E)がいます', 'on_red')
            # input('inputで止めてます....')
        return None
    # アクションの選択肢を取り出す
    all_path_data = glbvar.all_path_dict[use_StackSize]
    if solution_dir_list[0] in all_path_data:
        action_choices_list = all_path_data[solution_dir_list[0]]
    else:
        big_print('アクションの選択肢がありません。既にAllinしているプレイヤーだと思います', 'red', '▲')
        return None
    action_choices = action_choices_list[1]

    player_action, bet_rate = pkutil.convert_for_input_action(action)

    *_, selected_action = suppress_print(wizproce.best_select_player_action)(action_choices, player_action, bet_rate, 0, position, game_data['phase'], [],
                                driver=None, action_text_elements=None, check_between_Bet=True, dont_click_small_bet=True, rough_check=True, analyze_mode=True)

    if len(selected_action) == 2:
        against_list = selected_action[0].copy()
        selected_action = against_list[0]

    return selected_action

def select_use_StackSize(game_data, position, player_anlyz_data, target_effective_stack=False, effe_ratio=False, effe_posi=False, effe_init=False):
    """
    使用するスタックサイズを選ぶ
    - 処理:
        - 現在のプレイヤーよりもinitial_stackが多い人がいる -> 現在のプレイヤーのスタックサイズに近いgtoを使う
        - 現在のプレイヤーが最も多い -> 自分よりも1つ少ない人をgtoスタックとして探す
    - Args:
        - target_effective_stack:
            Trueのとき、有効スタックの現時点の。pot/stack を返す
        - effe_ratio:
            Trueのとき、有効スタックの割合を返す
        - effe_posi:
            Trueのとき、有効スタックのプレイヤーのpositionを返す
        - effe_init:
            Trueのとき、有効スタックのinitial_Stackを返す
    """

    # 各プレイヤーのinit_stack, 現在のプレイヤーのinit_stackを取り出す
    active_position_stack = None
    each_init_stack = []
    # そのphaseでAllinしたpositionも判定にいれる
    for active_position in glbvar.preflop_order:
        if active_position in game_data['alive_positions'] or active_position in game_data['Allin_positions'][game_data['phase']]:
            each_init_stack.append(player_anlyz_data[active_position]['general']['initial_stack'])
            if position == active_position:
                active_position_stack = player_anlyz_data[active_position]['general']['initial_stack']

    #* 1) 現在のプレイヤーのスタックサイズが何番目に大きいか
    # リストを降順にソートし、順位を取得
    sorted_each_init_stack = sorted(each_init_stack, reverse=True)  # 降順にソート
    rank = sorted_each_init_stack.index(active_position_stack) + 1  # 1から始まる順位にする

    effective_stack = None
    if rank == 1:
        # 2番目に大きいスタックを使う
        effective_stack = sorted_each_init_stack[1]
    else:
        # 現在のプレイヤーのスタックサイズを使う
        effective_stack = active_position_stack

    if target_effective_stack:
        effective_position = next(position for position, data in player_anlyz_data.items() if data['general']['initial_stack'] == effective_stack)
        if effe_posi:
            return effective_position
        effective_stack_init = player_anlyz_data[effective_position]['general']['initial_stack']
        if effe_init:
            return effective_stack_init
        current_effective_stack = calucurate_current_stack(effective_stack_init, game_data['action_report'][effective_position], game_data['total_bet'][effective_position])
        # if effe_current:
        #     return current_effective_stack
        if current_effective_stack == 0:
            return '-'
        current_effective_stack_ratio = round(game_data['pot']/current_effective_stack*100)
        if effe_ratio:
            return current_effective_stack_ratio

    #* 2) gtoのスタックサイズリストで近いものを選ぶ
    sorted_gto_StackSize_list = sorted(glbvar.analyze_StackSize_list, key=lambda x: abs(x - effective_stack))

    big_print(f'使用するStackSize:"{sorted_gto_StackSize_list[0]}" -> sorted_gto_StackSize_list:{sorted_gto_StackSize_list}', 'on_white')

    return sorted_gto_StackSize_list[0]


def read_gto_solution_and_gather_data(player_anlyz_data, position, solution_dir_list, game_data, action, gto_select_action):
    """
    preflop専用
    ===========
    パスを受取り、solutionを取り出す。
    - 処理:
        - hand:
            - Noneの場合、pot, 全体のアクション比率を取り出す
            - ハンドが明確のとき、pot, solution, EV(%も計算)を返す
        - pathが存在するか:
            - この確認を追加した。もし、pathが1つも存在しなかったら、solutionがからになって、エラーになる。でも、そんな状況こない気がする
    """
    # 作ったデータはここに入れる
    solution_data_list = []

    about_hand = player_anlyz_data[position]['general']['about_hand']

    gto_pot_list = {}
    against_data = {0: 'Fold', 1: 'Raise'}

    # potについて計算する
    real_pot = game_data['pot']
    current_stack = calucurate_current_stack(player_anlyz_data[position]['general']['initial_stack'], game_data['action_report'][position], game_data['total_bet'][position])
    pot_per_stack = round(real_pot/current_stack*100) # potが大きいと%が大きくなる。potが大きくなるとアクションに傾向が出る人をあぶり出す

    # pathを順に取り出す
    for index, solution_dir in enumerate(solution_dir_list):
        solution_data = {}
        # generalのパスを作成 -> 読み込む
        wizard_count = get_wizard_count(solution_dir)
        general_json = os.path.join(solution_dir, f'{wizard_count}_general.json')
        # jsonが存在するか確認する
        if not os.path.exists(general_json):
            general_json = check_exists_limp_situation(game_data, position, general_json)
            if general_json is None:
                big_print('pathがないようなので、飛ばします', 'cyan')
                continue
            against_data[index] = 'limper' # againstを書き換える
            solution_dir = os.path.dirname(general_json) # dirを修正する
        # 現在のpositionと異なるpathのとき、passする
        if check_active_position_solution(position, solution_dir) is False:
            # input('input: solutionのpositionが異なります....')
            continue

        solution = csvproce.read_data(general_json, file_type='json')
        range_solution = {action: rate for action, rate in solution['range_action'].items() if action != 'Hand'}

        # gtoでのpotを取り出す
        gto_pot = solution['pot_size']
        gto_pot_list[index] = {'gto_pot': gto_pot,}

        # 共通のpotを取り出す
        solution_data['pot'] = f'{real_pot}(pot/stack:{pot_per_stack}%({game_data["current_effective_stack_ratio"]}%), gto:{gto_pot})'
        # handがわかってないとき
        if about_hand is None:
            # rangeデータを取り出して返す
            solution_data['solution'] = range_solution
            solution_data['action'] = f'{action},(gto_near:{gto_select_action})'
            solution_data_list.append(solution_data)
            continue

        # ハンドがわかってるとき -> EVも取り出す
        action_values = pkutil.get_action_values_from_csv(solution_dir, about_hand, target='action_values')
        EV_data = pkutil.get_action_values_from_csv(solution_dir, about_hand, target='EV')
        EV_data = calucurate_EV_percent(action_values, EV_data, gto_pot)

        # gtoに無い行動を取った後、判定できなくなるからレンジのsolutionも入れる
        solution_data['solution'] = {'range': range_solution, 'about': action_values}
        solution_data['action'] = f'{action}(near_gto:{gto_select_action})'
        solution_data['EV'] = EV_data

        solution_data_list.append(solution_data)

    # 分岐しなかったとき
    if len(solution_data_list) == 1:
        # 1つしか参考にできるpahtがなかったら、それから、gto_actionを取り出す -> 2番目のpathが正だと思う
        if gto_select_action is None:
            # gtoの中で最も近いアクションを取り出す -> dataに追加する
            use_StackSize = get_use_stacksize_from_path(solution_dir_list[-1])
            gto_select_action = select_action_in_gto(use_StackSize, [solution_dir_list[-1]], action, position, game_data)
            solution_data_list[0]['action'] = f'{action},(gto_near:{gto_select_action})'
        return solution_data_list[0]
    # 1つもsolutionがなかったとき
    elif len(solution_data_list) == 0:
        big_print('solutionが1つもありませんでした。代わりのデータを入れます', 'red', '▲')
        # input('inputで止めてます....')

        solution_data = {
            'pot': f'{real_pot}(pot/stack:{pot_per_stack}%({game_data["current_effective_stack_ratio"]}%))',
            'action': f'{action}',
        }

        return solution_data

    # 分岐したとき、構成を変える
    solution_data_1 = solution_data_list[0]
    solution_data_2 = solution_data_list[1]
    new_solution_data = {
        'pot': {'real': solution_data_1['pot'],
                'gto_againt_Fold': gto_pot_list[0]['gto_pot'],
                'gto_againt_Raise': gto_pot_list[1]['gto_pot'],},
        'solution': [
            {'against': against_data[0], 'solution': solution_data_1['solution']},
            {'against': against_data[1], 'solution': solution_data_2['solution']},
        ],
        'action': solution_data_1['action'],
    }

    # EVがないときは、ここで返す
    if about_hand is None:
        return new_solution_data

    # EVがあるなら追加してから返す
    new_solution_data['EV'] = [
            {'against': against_data[0], 'EV': solution_data_1['EV']},
            {'against': against_data[1], 'EV': solution_data_2['EV']},
        ]

    return new_solution_data

def get_use_stacksize_from_path(create_path):
    """
    pathからstack_sizeを取り出す
    """
    # 各階層ごとに分割
    path = Path(create_path)
    path_parts = path.parts

    # スタックサイズと、それよりも後ろのデータを取り出す
    stack_dir_name = next(dir_name for dir_name in path_parts if 'BB' in dir_name)
    stack_size = convert_number(delete_non_numbers(stack_dir_name, print_text=False))

    return stack_size

def check_active_position_solution(position, dir_path):
    """
    作られたpathの中のcsvのファイル名に現在のpositionが含まれているか確認する
    基本的に問題ないはずだけど、リンプの2週目は、自分がFoldした後のsolutionを取り出してしまうので、それを防ぐ
    """

    csv_name = csvproce.get_csv_file_name(dir_path)
    if position in str(csv_name):
        return True

    big_print(f'異なるpositionのsolution path のようです -> file: {csv_name}', 'on_red')
    return False

def check_exists_limp_situation(game_data, position, json_path):
    """
    general.jsonのpathがないとき、それは、E がいるとき。
    もし、BBでCheckできる状況なら、SBがリンプしたとしてpathを用意する
    """
    # BBがCheckできる状況か
    if position == 'BB' and game_data['most_bet'] == 1:
        big_print('SBがリンプしたときのpathを用意します', 'yellow')
        # pathを用意する
        path = Path(json_path)
        path_list = path.parts

        # stackを探す
        stack_data = next(data for data in path_list if 'BB' in data)
        stack_dir_index = path_list.index(stack_data)
        # URLの作成に必要なデータのみ取り出す
        street_list = path_list[:stack_dir_index+1]

        dir_path = os.path.join(*street_list)

        # pathを作成する
        new_json_path = os.path.join(dir_path, 'Fold', 'Fold', 'Fold', 'Fold', 'Call', '5_general.json')

        if os.path.exists(new_json_path):
            return new_json_path
        else:
            big_print(f'作成したpathが存在しないようです -> {new_json_path}', 'red', '▲')

def get_wizard_count(path):
    """
    solutionのdirpathを受取り、wizard_countを数える
    - 処理:
        - 現在のプレイヤーのカウントを求めるなら、-1は不要
        - URLを作るときは -1 がいる(?)
    """
    # action_listを作成する
    action_law_data = path.split('BB')[1]
    action_list = action_law_data.split('/')[1:]
    wiz_action_count = len(action_list)

    return wiz_action_count

def calucurate_current_stack(init_stack, current_bet, total_bet):
    """
    現在の残りスタックを計算する
    - Args:
        - current_bet: このphaseでbetした合計(まだbetしてないならNone)
        - total_bet: 1つ前のphaseまでにbetした合計(preflopならNone)
    """
    # total_bet_amount を求める
    if total_bet is None:
        total_bet_amount = delete_non_numbers(current_bet, print_text=False)
    elif current_bet is None:
        total_bet_amount = delete_non_numbers(total_bet, print_text=False)
    else:
        total_bet_amount = round(current_bet + total_bet , 1)

    current_stack = round(init_stack - total_bet_amount, 1)

    return current_stack

def calucurate_EV_percent(action_values, EV_data, pot):
    """
    EVの％を計算してデータに追加して返す
    ハンドの全体のEVも計算する(各アクションの選択肢の比率を反映する)
    - 計算式:
        EV / pot * 100 <- %にする
    """
    total_ev = 0
    total_ev_per = 0
    new_EV_data = {'total': None} # totalを先頭に入れる
    for action, ev in EV_data.items():
        # EVの％を追加する
        percent = round(ev/pot*100, 1)
        new_EV_data[action] = f'{ev}({percent}%)'

        # totalを計算する
        action_ratio = action_values[action]

        total_ev += action_ratio/100 * ev
        total_ev_per += action_ratio/100 * percent

    # totalを追加する
    new_EV_data['total'] = f'{round(total_ev, 2)}({round(total_ev_per, 1)}%)'

    return new_EV_data

def get_my_position(stradata):
    """
    stradataからmy_positionを取り出す
    """
    my_position = next(data['position'] for player, data in stradata['general']['all_players'].items() if player == 'player_4')
    return my_position

# =====================================
# その他
# =====================================

def check_exists_flop_history(historys):
    """
    flop以降にhistoryが存在するか確認する
    """
    # flopがあり、そのデータが空ではない
    if 'flop' in historys:
        if len(historys['flop']['strategy_history']) >= 1:
            return True
    return False

def check_original_Raiser(pre_actions, original_Raiser):
    """
    もし、このphaseでAllinした人がoriginal_Raiserになってるとき、Noneにする
    Allinした人は次のphaseからアクションしないことになるので、考慮しない
    """
    if original_Raiser and 'Allin' in str(pre_actions[original_Raiser]):
        # input('inputで止めてます....(5)')
        return None
    else:
        return original_Raiser

def check_postflop_position(allreport):
    """
    IP, OOP, MP の辞書を作成する
    """
    position_list = []
    for posidata in allreport:
        position = posidata.split('_')[1]
        if position not in position_list:
            position_list.append(position)
        # 一周したら終了
        else:
            break

    position_data = {}
    for index in (0, -1):
        if index == 0:
            position_data[position_list[index]] = 'OOP'
        else:
            position_data[position_list[index]] = 'IP'

    # IPでもOOPでもないポジションはMPとする
    MP_positions = [position for position in position_list if position not in position_data]
    # position_list に追加する
    for position in MP_positions:
        position_data[position] = 'MP'

    return position_data

def create_path_for_postflop(game_data, allreport, player_anlyz_data):
    """
    postflopのオフラインデータを取り出すためのpathを作成する
    このpathを使って、URLの作成も行う
    """
    # 生き残っているpositionを適当に1つ選んで、エフェクティブスタックを求める
    use_StackSize = select_use_StackSize(game_data, game_data['alive_positions'][0], player_anlyz_data)

    solution_dir_list = allrepo.create_path_for_get_solution(allreport, use_StackSize, game_data, branch_data={'position': None, 'style': 'dont_branch'}, check_end=True)
    postflop_path = solution_dir_list[0]

    if 'postflop_error' == pkutil.check_EndPhase_with_csv_folder(postflop_path, action=None, detail='postflop_error'):
        big_print('このストリートはpostflop solutionがないようです', 'on_red')
        game_data['error_log'].append(postflop_no_solution_log_1)
        # input('inputで止めてます....(6)')
        game_data['postflop_path'] = False
        game_data['exist_data'] = False
        return game_data
    end_phase = pkutil.check_EndPhase_with_csv_folder(postflop_path, action=None, detail=True)
    if 'next_phase' != end_phase:
        big_print('next_phaseではありません', 'red')
        if 'multiway' == end_phase:
            big_print('multiwayのようなので、変更します', 'yellow')
            game_data['error_log'].append(multiway_log)
            game_data['exist_data'] = False
            game_data['postflop_path'] = False
            return game_data
        else:
            big_print('恐らく、最後のCallがgtoに存在しないので、pathが作成できませんでした。postflopのsolutionは無しで進めます。', 'on_red')
            game_data['error_log'].append(postflop_no_solution_log_2)
            game_data['exist_data'] = False
            game_data['postflop_path'] = False

    # next_phaseのディレクトリがあるか調べる
    postflop_path += '(next_phase)'
    if not os.path.join(postflop_path):
        big_print('next_phaseディレクトリがありません', 'red', '▲')
        # input('inputで止めてます....(7)')
        raise ValueError('next_phaseディレクトリがありません')

    # postflopの確認をすることになっているかどうかにより処理を変える
    global check_postflop_solution
    if check_postflop_solution:
        game_data['wizard_count'] = count_postflop_path(postflop_path)
        game_data['postflop_path'] = postflop_path
        game_data['exist_data'] = True
    else:
        game_data['exist_data'] = False
        game_data['postflop_path'] = False
        # ハンドがわかっている人がいるかどうか調べる
        known_others_hand = check_known_others_hand(player_anlyz_data)
        # ハンドがわかっている人が一人でもいるとき
        if known_others_hand:
            game_data['error_log'].append(exists_postflop_solution_log_with_hand)
        # 誰のハンドもわかってないとき
        else:
            game_data['error_log'].append(exists_postflop_solution_log_No_hand)

    return game_data

def check_known_others_hand(player_anlyz_data):
    """
    ハンドがわかっている人がいるかどうか調べる
    """
    # 各プレイヤーを取り出す。about_hand のキーがあり、about_handがNoneでない人が一人でもいればTrue
    known_others_hand = next((True for data in player_anlyz_data.values() if 'about_hand' in data['general'] and data['general']['about_hand']), False)

    return known_others_hand

def count_postflop_path(postflop_path):
    """
    postflopに進むpathから、countを求める
    """
    # 各階層ごとに分割
    path = Path(postflop_path)
    path_parts = path.parts

    # スタックサイズと、それよりも後ろのデータを取り出す
    stack_dir_name = next(dir_name for dir_name in path_parts if 'BB' in dir_name)
    stack_dir_index = path_parts.index(stack_dir_name)
    # URLの作成に必要なデータのみ取り出す
    street_list = path_parts[stack_dir_index + 1:]

    count = len(street_list)

    return count

def update_total_bet(game_data):
    """
    action_reportの内容を、total_betに反映する
    """
    for position, total_bet in game_data['total_bet'].items():
        action_bet = game_data['action_report'][position]
        # action_bet がNoneのとき(そのphaseなにもしてないとき)パス
        if action_bet is None:
            continue
        # total_betがNoneのとき、上書きする
        elif total_bet is None:
            game_data['total_bet'][position] = action_bet
        # それ以外、足して更新
        else:
            game_data['total_bet'][position] = round(total_bet + action_bet, 1)

    return game_data

def update_current_actions(pre_action, action):
    """
    current_actions を更新する
    - 優先順位:
        Allin, Raise, Bet, Call, Check
    """
    # まだ何もアクションしてない, preがCheck, Allin, Raiseなら上書きする
    if (pre_action is None or
        'Allin' in action or
        'Raise' in action or
        'Check' in pre_action or
        'Call' in pre_action):
        return action

    # 前にRaiseしていて、今回はRaiseではない
    if (('Raise' in pre_action and 'Raise' not in action) or
        ('Bet' in pre_action and 'Bet' not in action) or
        ('Fold' in action)):
        return pre_action

    raise ValueError('update_current_actions() で想定していないことが起きました')

def update_action_report(current_report, action, game_data, position, player_anlyz_data):
    """
    action_reportを更新する
    - 処理:
        - 現状がNoneなら上書きする
        - それ以外ならdelete_non_numberして足す
        - preflopは、deletenonnumberすればいいけど、postflopはbetの%があるから、splitしないといけない
        - Allin は、有効スタック分だけ、Allinしたとする
    """
    # Foldした人は更新しない
    if 'Fold' in action or 'Check' in action:
        return current_report

    if game_data['phase'] == 'preflop':
        # Allinしたプレイヤーは、有効スタック分、Allinしたとする。
        if 'Allin' in action:
            effective_stack = select_use_StackSize(game_data, position, player_anlyz_data, target_effective_stack=True, effe_init=True)
            return effective_stack
        return delete_non_numbers(action, print_text=False)

    # Allinしたプレイヤーは、有効スタック分の残高すべてを、Allinしたとする。
    if 'Allin' in action:
        # 有効スタックの判定に使うpositionを取り出す
        effective_stack_posi = select_use_StackSize(game_data, position, player_anlyz_data, target_effective_stack=True, effe_posi=True)
        # このphaseが始まるときのスタックを取り出す
        current_phase_stack = calucurate_current_stack(player_anlyz_data[effective_stack_posi]['general']['initial_stack'], None, game_data['total_bet'][effective_stack_posi])
        return current_phase_stack

    # postflopはfix_actionをかます <- preflopで同じようにしても問題ない気がする
    return delete_non_numbers(fix_action(action), print_text=False)

def organize_anlyz_data(game_data, solution_data, action, gto_select_action):
    """
    anlyzに追加する用のデータを用意する
    """
    # プリフロップのとき
    data_for_add = {}

    # postflopのとき、カードを追加する
    if game_data['phase'] != 'preflop':
        # data_for_add['board'] = game_data['this_phase_cards']
        pass

    for key, data in solution_data.items():
        data_for_add[key] = data

    data_for_add['situation'] = game_data['situation']

    return data_for_add

def judge_situation(game_data, action_report, current_allreport, position):
    """
    situationを判定する
    - list:
        - memo: action_reportにはbetした額が入るだけなので、Foldは入らない。数値かNoneのみ
        - preflop:
            - all_Fold: Foldした人数
            - only_limper: リンプしたポジション
            - Raiser: Raiseの数と、ポジション
        - postflop:
            - position: 各プレイヤーによってsituationが変わるので引数が必要
    """

    # プリフロップのとき
    if game_data['phase'] == 'preflop':
        #* Foldしかいないとき
        # 1つ前がall_Foldでないときは判定しなくていい
        if 'all_Fold' in game_data['situation']:
            only_Fold = next((False for position, action in action_report.items()
                            if action is not None and position not in ('BB', 'SB') or
                            ((position == 'BB' and action != 1) or
                            (position == 'SB' and action != 0.5))), True)
            if only_Fold:
                Fold_count = sum(1 for posidata, action in current_allreport.items() if 'Fold' in action and posidata != list(current_allreport)[-1])
                return {'all_Fold': {'count': Fold_count}}

        #* リンプしかいないとき <- SBのリンプしたいないときはgtoあるけど、150BBだとない。ここのgtoとの比較が信頼できるデータかどうかは、別で判断するべき
        if 'only_limper' in game_data['situation'] or 'all_Fold' in game_data['situation']:
            # actionがNoneではなく、0.5と1以外があるときはFalse
            only_limper = next((False for action in action_report.values() if action is not None and action not in (0.5,1)), True)
            if only_limper:
                limper_positions = [position for position, action in action_report.items() if action == 1 and position != 'BB']
                return {'only_limper': {'positions': limper_positions}}

        #* Raiseがいるとき
        # ここまで来たらRaiser確定でいいと思う
        Raiser_count = 0
        Raiser_positions = []
        most_bet = 1 # Callを弾くために必要
        for posidata, action in current_allreport.items():
            # 最後は判定しない
            if posidata == list(current_allreport)[-1]:
                break
            # Foldも数字にして(->0)処理する。most_betより大きくないとカウントされないからこれでいいと思う
            action = delete_non_numbers(action, print_text=False)
            if most_bet < action:
                most_bet = action
                position = posidata.split('_')[1]
                if position not in Raiser_positions:
                    Raiser_positions.append(position)
                Raiser_count += 1
        return {'Raiser': {'count': Raiser_count, 'positions': Raiser_positions}}

    # プリフロップ以外のとき
    """
    - situationに入れるデータ
        1, original_Raiser
        2, 今自分がしたこと
        3, 1つ前のphaseで自分がしたこと
        4, 今相手がしてきたこと
        5, 1つ前に相手がしてきたこと
    """
    #* 相手がしてきたことを取り出す
    others_action_current = judge_others_action_for_situation(game_data['original_Raiser'], position, game_data['current_actions'])
    others_action_pre_phase = judge_others_action_for_situation(game_data['original_Raiser'], position, game_data['pre_actions'])

    situation_data = {
        'original_Raiser': game_data['original_Raiser'],
        'this_player_before': game_data['current_actions'][position],
        'this_player_pre_phase': game_data['pre_actions'][position],
        'others_action_current': others_action_current,
        'others_action_pre_phase': others_action_pre_phase,
    }

    return situation_data

def judge_others_action_for_situation(original_Raiser, position, actions_data):
    """
    postflopのsituationで相手のアクションを決める
    current, pre phaseどちらでも使える
    """
    """
    自分以外がしたアクションを、優先度順で取り出す
    Allin, Raise, Bet. Call, Check
    """
    enemy_action_current = None
    for active_postition, action in actions_data.items():
        if active_postition == position:
            continue
        # 初期値入れる。Foldは除く
        if enemy_action_current is None and 'Fold' not in str(action):
            enemy_action_current = action
        #! どのアクションのときも、数値が大きいものを優先する(Check, Foldは0になる。Callは、Callの額が取り出される。Betとかも額が取り出される)
        else:
            # 数値が ene_ac_curent よりも大きとき、入れ替える。CallとRaiseが同じ額になっていまうので、同じ額のとき、Raiseとかを優先する
            if ((delete_non_numbers(fix_action(enemy_action_current), print_text=False) < delete_non_numbers(fix_action(action), print_text=False)) or
                (delete_non_numbers(fix_action(enemy_action_current), print_text=False) == delete_non_numbers(fix_action(action), print_text=False) and
                ('Allin' in str(action) or 'Raise' in str(action) or 'Bet' in str(action)))):
                enemy_action_current = action
    return enemy_action_current

def calucurate_pot(pre_pot, action_report):
    """
    potサイズを計算する
    """
    # そのフェーズのトータルのbet額を取り出す
    total_bet = sum(delete_non_numbers(action, print_text=False) for action in action_report.values())

    total_pot = round(pre_pot + total_bet, 1)

    return total_pot

# =====================================
# 各プレイヤーのデータを入れる箱を用意する
# =====================================

def make_player_list(stradata, stranumber):
    """
    分析をするプレイヤーのデータを作成する
    """
    player_anlyz_data = {}

    all_players = stradata['general']['all_players']

    # 欠席者のカウントをする
    absent_count = sum(1 for player, data in all_players.items() if player != 'player_4' and data['ID'] is None)

    # 各プレイヤーのidをまとめたデータを作成する <- 特定のプレイヤーに対して戦略を変えている可能性がある
    each_player_id = gather_each_player_id(all_players)

    # 各プレイヤーのデータを取り出す
    for player, data in all_players.items():
        # 自分や、欠席者はパスする
        if player == 'player_4' or data['ID'] is None:
            if player == 'player_4':
                player_anlyz_data[data['position']] = {
                    'general': {
                        'position': f'{data["position"]}(player_4)',
                        'initial_stack': data['initial_stack'],
                        }
                    }
            continue
        # 各プレイヤーは、まだ変換されていないデータであることを確認する
        anlz_id = data['ID']
        # csvを読み込む。csvがなければ新規作成して、空のデータが返ってくる
        convert_list = get_converted_stradata(anlz_id)
        # 変換リストにデータがあればパス
        global check_postflop_solution
        if stranumber in convert_list and check_postflop_solution is False:
            player_anlyz_data[data['position']] = {
                    'general': {
                        'position': f'{data["position"]}(done)',
                        'initial_stack': data['initial_stack'],
                        }
                    }
            continue
        # リストに追加する
        player_anlyz_data[data['position']] = {
            'general': {
                'stranumber': stranumber,
                'error_msg': [],
                'position': data['position'],
                'initial_stack': data['initial_stack'],
                'about_hand': data['about_hand'],
                'detail_hand': data['detail_hand'],
                'absent_count': absent_count,
                'table_stakes': stradata['general']['table_stakes'],
                'each_player_id': each_player_id,
                }
        }

    return player_anlyz_data

def gather_each_player_id(all_players):
    """
    各positionのidを取り出す
    - 自分: 'me'
    - 欠席者: 'absent' <- Noneはabsentになる
    """
    each_player_id = {}
    for player, data in all_players.items():
        position = data['position']
        obj_id = data['ID']

        if player == 'player_4':
            obj_id = 'me'
        elif obj_id is None:
            obj_id = 'absent'

        each_player_id[position] = obj_id

    return each_player_id

def serch_stradata_path(stranumber):
    """
    stranumberから、dataのパスを用意する
    """
    # stradataが保存されているディレクトリを順に取り出す
    for dir_name in os.listdir(glbvar.stradata_for_save_dir):
        # dirのパスを作成して、その中を探す
        dir_path = os.path.join(glbvar.stradata_for_save_dir, dir_name)
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                # 条件に一致するデータを見つけたら、pathを作成して返す
                if stranumber in file and file.endswith('.json'):
                    data_path = os.path.join(root, file)
                    return data_path

# =====================================
# 読み込むデータのリストを作成
# =====================================

def get_converted_stradata(anlz_id, *, get_all=False):
    """
    既に変換しているstradataのリストを取り出す
    - Args:
        - get_all: Trueにするとcsvデータ全てを取り出す
    """
    convert_list_csv = os.path.join(glbvar.player_private_dir, anlz_id, 'convert_list.csv')

    # csvを読み込む。csvがなければ新規作成して、空のデータが返ってくる
    reader = csvproce.read_data_with_make_data(convert_list_csv, file_type='csv', fieldnames=['stranumber', 'error_log'])

    if get_all:
        data = [row for row in reader]
        return data

    converted_list = [row['stranumber'] for row in reader]

    return converted_list

def get_stradata_list(anlz_id):
    """
    csvを読み込んでこのidの人が参加しているstradataのリストを用意する
    変換済みのlistも読み込んで、変換済みのstradataは削除する
    """
    #* postflopのgtoを読み込むとき
    global check_postflop_solution, target_count
    if check_postflop_solution:
        # 進捗具合を整理する
        progress_list = {'complete': [], 'target': []}

        # unique_idと同じanlz_idを取り出す
        target_unique_id, matching_anlz_ids = get_same_uniqueID(anlz_id)

        # 目標が０になったときuniqueがNoneでも解析できるようにする
        if target_count == 0 and target_unique_id is None:
            matching_anlz_ids.append(anlz_id)

        # anlz_IDを取り出す
        for target_anlzID in matching_anlz_ids:
            # 空のanlz_IDを取り出したときパスする
            if target_anlzID is None:
                continue

            # 変換済みのリストを読み込む
            converted_list = get_converted_stradata(target_anlzID, get_all=True)

            #* ハンドが見えてるものしか処理しないとき
            if check_postflop_solution == 'trust_only':
                # ハンドがあるものだけを選ぶ(logが1つしかないものが信頼できる)
                progress_list['complete'] += [data['stranumber'] for data in converted_list if data['error_log'] == 'complete']
                progress_list['target'] += [data['stranumber'] for data in converted_list if data['error_log'] == exists_postflop_solution_log_with_hand]
            #* ハンドが見えてないpostflopを解析するとき
            elif check_postflop_solution == 'no_hand':
                # ハンドがないものだけを選ぶ(logが1つしかないものが信頼できる)
                progress_list['complete'] += [data['stranumber'] for data in converted_list if data['error_log'] == 'complete']
                progress_list['target'] += [data['stranumber'] for data in converted_list if data['error_log'] in (exists_postflop_solution_log_No_hand, exists_postflop_solution_log_with_hand)] # cant_trust_street_log

        big_print(f'unique_id: {target_unique_id}, complete数: {len(progress_list["complete"])}, 総数: {len(progress_list["complete"]) + len(progress_list["target"])}', 'yellow')
        return target_unique_id, matching_anlz_ids, progress_list

    #* 全てをオフラインで処理するとき

    csv_path = os.path.join(glbvar.player_private_dir, anlz_id, 'history_stranumber.csv')
    # csvを読み込む
    reader = csvproce.read_data(csv_path, file_type='csv')

    # 一覧を読み込む
    stranumber_list = [row['stranumber'] for row in reader]

    # 変換済みのリストを読み込む
    converted_list = get_converted_stradata(anlz_id)
    # 一覧から、変換済みのものをは弾く
    stranumber_list_deleted = [stranumber for stranumber in stranumber_list if stranumber not in converted_list]
    progress_list = {'complete': [], 'target': stranumber_list_deleted}

    return None, [],  progress_list

def get_same_uniqueID(anlz_id):
    """
    anlz_idを受取り、同じuniqueIDのanlz_idのものをリストで返す
    """
    # CSVを読み込む
    csv_path = glbvar.id_mapping_csv_link
    df = pd.read_csv(csv_path, dtype=str)

    #* unique_idを取り出す
    # `anlz_id` に対応する `unique_id` を取得
    unique_id_data = df.loc[df["anlz_id"] == anlz_id, "unique_id"]
    # 結果をリスト化
    unique_id_list = unique_id_data.tolist()
    if len(unique_id_list) == 0:
        unique_id = None
    else:
        unique_id = unique_id_list[0]
    # nan だったとき、Noneに入れ替える
    unique_id = None if pd.isna(unique_id) else unique_id

    if unique_id is None:
        matching_anlz_ids = []
    else:
        #* unique_id と一致するanlz_idを取り出す
        # name_id == "name_000004" の unique_id を取得
        target_unique_id = df.loc[df["anlz_id"] == anlz_id, "unique_id"].values
        # unique_id が一致する name_id を取得
        matching_anlz_ids = df[df["unique_id"].isin(target_unique_id)]["anlz_id"].tolist()
        # NaNはNoneに変換する
        matching_anlz_ids = [x if pd.notna(x) else None for x in matching_anlz_ids]

    return unique_id, matching_anlz_ids

# =====================================
# その他のプログラム
# =====================================

def make_id_list():
    """
    確認するidのリストを用意する
    """

    id_list = [dir_name for dir_name in os.listdir(glbvar.player_private_dir) if 'anlz_' in dir_name and '(' not in dir_name]
    sorted_id_list = sorted(id_list, key=lambda x: int(x.split('_')[1]))

    return sorted_id_list

if __name__ == "__main__":
    main()