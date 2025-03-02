
from termcolor import colored, cprint
import os
import sys
import csv
import time
import json


import strategy_analyzer_app.poker_logic.action_report_control as actrepo
from strategy_analyzer_app.poker_logic.action_report_control import fix_action
from strategy_analyzer_app.text_processing.text_extraction import convert_number, delete_non_numbers, BB_delete_non_numbers
from strategy_analyzer_app.io_operations.print_processing import big_print, suppress_print
import strategy_analyzer_app.poker_logic.poker_utils as pkutil
import strategy_analyzer_app.control_webdriver.control_wizard as ctlwiz
import strategy_analyzer_app.control_webdriver.wizard_processing as wizproce
import strategy_analyzer_app.poker_logic.poker_action_processing as pkac
import strategy_analyzer_app.global_vars as glbvar

#!!!
def create_path_for_get_solution(allreport, use_StackSize, game_data, branch_data=None, check_end=False):
    """
    allreportからpathを作成する
    anlyz用のpathを作るので、通常時とは処理が少し違う
    TODO anlzのall_pathを作成する, postflopはdriverとか、elementとか引数で渡す <- postflopはこの処理は使わない

    - 処理:
        - Eの扱いについて:
            - foldすることがわかってるとき、Foldで進める
        - postflopに進むとき:
            - 分岐しない(Eが残るか、Foldするかは既に明らかになっている) <- そもそも、Eがいたらgtoの信頼ないけど、とりあえず、gto取り出す
    - Args:
        - branch_data:
            - 初期値はNoneこのとき、Eを見つけた途端、分岐する
            - positionの指示がある: そのポジションがCallするまでまで分岐しない <- 結局分岐しないこともある。それまでにでてきたEは、foldしてないなら、Raiseとして進める
            - position is None: Foldしてない人は、Raiseとして進める
            - #//style: dont_branch のとき、分岐しない。なんなら、EがでてきたらRaiseとして進める <- 使ってない
        - check_end:
            - Trueにすると、allreportをすべて読み込む。postflopに続くpathを作成するときにTrueにする
    """
    # allpathを読み込む
    # もし空のデータだったら読み込む
    if len(glbvar.all_path_dict) == 0:
        all_path_dict = {}
        for stack_size in glbvar.analyze_StackSize_list:
            json_path = os.path.join(glbvar.offline_wizard_for_analyze_dir, f'{stack_size}BB', 'all_path.json')
            with open(json_path, 'r', encoding='utf-8') as file:
                loaded_data = json.load(file)
                all_path_dict[stack_size] = loaded_data
        glbvar.all_path_dict = all_path_dict
    all_path_data = glbvar.all_path_dict[use_StackSize]

    # 一人目は original_directory を使う
    initial_directory_path = os.path.join(glbvar.offline_wizard_for_analyze_dir, f'{use_StackSize}BB')

    directory_path_list = [initial_directory_path]
    fold_positions = []

    # UTGがリンプのとき、returnする
    if len(allreport) == 0:
        return directory_path_list

    # Fold, Allinした人は削除する。もし、取り出されたら、小さいAllinした人だと思うので、Foldしたとして処理を進める
    alive_positions = list(glbvar.preflop_order)
    alive_positions_list = [alive_positions]
    finish_path = {0: False, 1: False} # pathの確認を行わないとき、Trueにする
    E_player_list = []
    E_player = None
    most_bet = 0 # その時点のmost_betを記録する

    for position_data, action_data in allreport.items():
        # 一番最後は、現在のプレイヤーのアクションなので、終了する
        if check_end is False and position_data == list(allreport)[-1]:
            break

        print(f'(- {position_data}: {action_data})')

        # preflopのSB,BBはパスする
        if game_data['phase'] == 'preflop' and action_data in ('0.5', '1'):
            continue

        brach_path = False
        #// i = 0
        for i, dir_path in enumerate(directory_path_list):

            # ポジションを取り出す
            position = position_data.split('_')[1]
            # E でFoldしたとして確定させているポジションは、飛ばす
            if position in fold_positions:
                continue

            # positionがEとして処理されてるとき
            if position in E_player_list:
                """
                1, Eだった人がここで、Foldするなら、1週目からFoldとして進める。そうでないなら、Raiseで進める <- Foldすることになってるかどうかは、事前にわかっているから、多分なにもしなくてもそうなってる
                2, 他にEがいるならそのプレイヤーの分岐から行う
                    このとき、path_listを作り変えることになる <- Eのアクションが固定されることで分岐しない可能性がある
                """
                # 順番で次がEの人を取り出す
                current_index = E_player_list.index(position)
                next_index = (current_index + 1) % len(E_player_list)
                if next_index == 0:
                    if branch_data and branch_data['style'] == 'dont_branch':
                        return directory_path_list
                    #* すべてのEの分岐を試したことになる。分岐する必要がないとして、最初からpathの作成を行う。そして、ここで、returnする <- 多分うまくいかない
                    # input('=========   input: すべてのEの分岐を試したので、これから分岐させずにpathを作成します   =========\n')
                    directory_path_list = create_path_for_get_solution(allreport, use_StackSize, game_data, branch_data={'position': None, 'style': 'dont_branch'})
                    return directory_path_list
                # 別のEを分岐させたとして進める
                next_E_position = E_player_list[next_index]
                # input('=========   input: 別のEを分岐させたとして進めます   =========\n')
                # directory_path_list が作り変えられる
                directory_path_list = create_path_for_get_solution(allreport, use_StackSize, game_data, branch_data={'position': next_E_position, 'style': None})
                return directory_path_list

            # 現在のポジションのpathが取り出されるまで繰り返す
            while True:

                if dir_path not in all_path_data:
                    big_print('pathがないので、このpathの確認は中止します', 'on_red')
                    finish_path[i] = True
                    break

                action_choices_list = all_path_data[dir_path]
                action_choices = action_choices_list[1]

                # csv に記載されているポジションを取り出す
                csv_name = action_choices_list[0]
                if position not in csv_name:
                    """
                    positionが異なるとき、小さなAllinをRiaseとみなしたとき。allreportではAllinした人のアクションは次取り出されないので、Foldしたとして進める
                    """
                    csv_position = os.path.splitext(csv_name)[0].split('_')[1] # csvのファイル名から、positionを取り出す
                    # 既にFoldしてる人であれば、Foldを追加して次に進める
                    if csv_position not in alive_positions_list[i]:
                        dir_path = os.path.join(dir_path, 'Fold')
                        big_print(f'既にアクションを終えているポジション({csv_position})が取り出されたので、Foldしたとして、pathの作成を進めます', 'yellow')
                        continue
                    big_print(f'取り出したデータとポジションが一致しません。solutionがないと判定します', 'red', '▲')
                    return None
                    #// raise ValueError(f'取り出したデータとポジションが一致しません\ncsv_name:{csv_name}\nplayer_position:{position}\naction_choices:{action_choices}\nactive_directory_path:{dir_path}\nall_report:{allreport}')
                break

            if finish_path[i]:
                continue

            # actiondataを変換する
            player_action, bet_rate = pkutil.convert_for_input_action(action_data)
            # Fold, Allinした人はaliveから削除する
            if ('Fold' in action_data or 'Allin' in action_data) and position in alive_positions_list[i]:
                alive_positions_list[i].remove(position)

            # most_betを記録する
            consider_Fold = False
            if 'Raise' in player_action:
                if most_bet <= bet_rate:
                    most_bet = bet_rate
                else:
                    # most_betよりも小さいアクションは、Foldと見なす
                    big_print(f'{position_data}: Betがmost_betよりも小さいので、Foldとみなします', 'on_red')
                    consider_Fold = True
                    selected_action = 'Fold'
                    found_E_player = False
                    selected_Allin = False

            if consider_Fold is False:
                # 最適なアクションを選択する処理を関数にした
                (selected_Allin, judged_small_bet,
                found_E_player, tmp2_wizard_Raise_list,
                selected_action) = suppress_print(wizproce.best_select_player_action)(action_choices, player_action, bet_rate, 0, position, game_data['phase'], [],
                                            driver=None, action_text_elements=None, check_between_Bet=True, dont_click_small_bet=True, rough_check=True, analyze_mode=True)

            # 選択肢にないのにCallをしたとき
            dont_consider_limper = False # Trueにしたら、E_player_list に入れない
            if found_E_player:
                # E が誰もいないときかつ、allreport上、まだ、生きてるとき、分岐する
                if E_player is None:
                    # 次のEのアクションを調べる
                    next_E_action = check_E_next_action(position_data, allreport)
                    # 通常時の処理 or branchする指定があるとき
                    if ((branch_data is None or
                        position in str(branch_data['position'])) and
                        next_E_action is None):
                        E_player = position
                        brach_path = True
                    # E を分岐させないとき、Raiseとして進める
                    else:
                        # 次がFoldとわかっているとき、分岐せず、Foldを選ぶ
                        dont_consider_limper = True
                        if next_E_action is False:
                            pass
                        # 次がFoldいが以外とわかっているなら、分岐せず、Raiseを選ぶ
                        elif next_E_action is True:
                            *_, selected_action = wizproce.best_select_player_action(action_choices, 'Raise', 0, 0, position, game_data['phase'], [], rough_check=True)
                # foldすることが明確になってるEはこれ以降取り出されても飛ばせるようにリストに入れる
                elif position not in game_data['alive_positions']:
                    fold_positions.append(position)

                if position not in E_player_list and dont_consider_limper is False:
                    E_player_list.append(position)

            if selected_Allin and position in alive_positions_list[i]:
                alive_positions_list[i].remove(position)

            # 分岐が行われないとき -> いつも通りの処理を行うために変数を用意する
            if len(selected_action) == 2:
                against_list = selected_action[0].copy()
                selected_action = against_list[0]

            # パスの更新
            directory_path_list[i] = os.path.join(dir_path, selected_action)

            # 分岐するとき -> 今のアクションをRaiseにして分岐させる
            if brach_path:
                *_, selected_action = wizproce.best_select_player_action(action_choices, 'Raise', 0, 0, position, game_data['phase'], [], rough_check=True)
                # リストに追加してbreakしてforを抜ける
                directory_path_list.append(os.path.join(dir_path, selected_action))
                alive_positions_list.append(alive_positions_list[i].copy())
                break

    return directory_path_list

def check_E_next_action(position_data, allreport):
    """
    E がでてきたとき、E の次のアクションを調べる。
    - 次のアクションがない -> 分岐する
    - 次のアクションがFold -> Foldで進める
    - 次のアクションがFold以外 -> Raiseで進める

    - Returns:
        - False: 分岐なし。Foldにする
        - True: 分岐なし。Raiseにする
        - None: まだ、次のアクションがでてないので、分岐する
    """
    # 次のアクションを探す
    go_check = False
    for posidata, action in allreport.items():
        # E と判定されたときのposidataまで進める
        if go_check is False:
            if posidata == position_data:
                go_check = True
        else:
            position = position_data.split('_')[1]
            if position in posidata:
                if 'Fold' in action:
                    return False
                else:
                    # if game_data['most_bet'] > delete_non_numbers(action, print_text=False):
                    #     return 'consider_Raise_next_Fold'
                    # return 'consider_Raise'
                    return True
    return None

