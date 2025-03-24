"""
gtoとどれだけアクションが乖離しているか統計データをとり、エクスプロイト方針を立てる
"""

import os
import copy

from strategy_analyzer_app.io_operations.print_processing import big_print
from strategy_analyzer_app.text_processing.text_extraction import  delete_non_numbers
import strategy_analyzer_app.global_vars as glbvar
import strategy_analyzer_app.io_operations.csv_processing as csvproce
import strategy_analyzer_app.poker_logic.poker_utils as pkutil
import strategy_analyzer_app.get_stradata.convert_data_for_analyze_stradata as cnvstra

checked_anlyz_id = [] # 分析済みのidを入れる

def main():
    """
    1, anlz_1から順に取り出す
    2, 集計を取って、統計取る
    """
    # 統計を取る順を作成する
    id_list = make_id_list()

    for obj_id in id_list:
        # 既に調べたidはパスする
        if obj_id in checked_anlyz_id:
            continue

        big_print(f'============== {obj_id} の確認を行います ==============', 'white')
        statistics_stradata(obj_id)

# =============================
# 統計を取る
# =============================

# 集計データを入れるリストを用意
template_statistics_data = {
    'Fold': [],
    'Call': [],
    'Check': [],
    'Bet': [],
    'Raise': [],
    'Allin': [],
}

def statistics_stradata(obj_id):
    """
    idを受取り、そのidの統計を取る
    - 処理:
        - 1: 集計データを入れるリストを用意する
        - 2: 順に集計する
        - 3: 統計を計算する
    """
    global checked_anlyz_id

    statistics_data = {
        'index': 0,
        'hand': {'gto': copy.deepcopy(template_statistics_data), 'action': copy.deepcopy(template_statistics_data)},
        'no_hand': {'gto': copy.deepcopy(template_statistics_data), 'action': copy.deepcopy(template_statistics_data)},
        'weak': {'gto': copy.deepcopy(template_statistics_data), 'action': copy.deepcopy(template_statistics_data)}, # 弱いハンドだけのデータを入れる(postflop以降)
        'strong': {'gto': copy.deepcopy(template_statistics_data), 'action': copy.deepcopy(template_statistics_data)}, # 強いハンドのデータだけ入れる(postflop以降)
        }

    # anlz_idから、同一のuniqueIDであるanlz_idを取り出す
    target_unique_id, matching_anlz_ids = cnvstra.get_same_uniqueID(obj_id)

    if target_unique_id is None:
        checked_anlyz_id.append(obj_id)
        return
    else:
        big_print(f'unique_id: {target_unique_id} の分析を行います', 'yellow', '=')
        checked_anlyz_id += matching_anlz_ids

    # 同一のanlz_id を取り出す
    for active_obj_id in matching_anlz_ids:
        # Noneが入ってたらパス
        if active_obj_id is None:
            continue
        # 順に convert_stradata を取り出す
        conv_data_dir = os.path.join(glbvar.player_private_dir, active_obj_id, 'convert_stradata')
        # pathが存在しないものはパス
        if not os.path.exists(conv_data_dir):
            continue
        for conv_data_name in os.listdir(conv_data_dir):
            big_print(f'   - {conv_data_name} のデータを集めます', 'white')
            # convert_stradata を読み込む
            conv_data_path = os.path.join(conv_data_dir, conv_data_name)
            conv_data = csvproce.read_data(conv_data_path, file_type='json')

            # データから集計用のデータを取り出す
            statistics_data = gather_statistics_data(statistics_data, conv_data)

    # 統計を取る
    allphase_statistics_dict = procces_statistics(statistics_data)

    # 相手の特徴を判別する
    phase_enemy_stra_feature = judge_strategy_feature(allphase_statistics_dict)

    # 相手の特徴から、具体的にどこを調整するかまとめる
    exploit_enemy_stra_feature = pkutil.procces_assemble_exploit_plan(phase_enemy_stra_feature, allphase_statistics_dict)

    # 相手の特徴を保存する
    json_path = os.path.join(glbvar.unique_id_dir, target_unique_id, 'strategy_bias.json')
    csvproce.make_json_data(json_path, exploit_enemy_stra_feature, alert=False)

    return

# =============================
# 相手の特徴を判別する
# =============================

def judge_strategy_feature(allphase_statistics_dict):
    """
    相手の特徴を判定する
    - 1, Callし過ぎ、Foldし過ぎ
    - 2, ブラフ多すぎ、少なすぎ
    - 3, 強いハンドでCheckし過ぎ、Betし過ぎ

    - 処理:
        - Callし過ぎ:
            hand, no_hand で判定。
            gtoよりもCallが多く、gtoよりもFoldが少ないとき
        - Foldし過ぎ:
            no_hand(Foldしてるので、ハンドが見えない)
            gtoのFoldしない確率よりも、Foldしない確率が少ない(逆説的にFoldする確率が多い) <- 補数で判定することにした
        - ブラフ:
            weak, no_hand
            - ブラフ過多の場合
                Fold, Call, Checkが普通かgtoよりも少なく、
                Bet, Raiseが多いとブラフ過多 <- Bet頻度が多いということは、必然的に弱いハンドでもBetしていることになる
            - ブラフ少ない場合
                Bet, Raiseがgtoよりも少ないとき。かつ、Callが少ないかgtoと同じ
                これはつまり、Fold, Checkの頻度がgtoよりも多いということになる (Callが多く、Foldが少ないなら、それはブラフが少ないというよりもCallが多いとなるので、Callが普通以下の条件はいると思う)
        - 強いハンド:
            storng
            - 強いハンドでBetしなさすぎる
                Checkが多すぎる(一旦、Callは考えない)
            - 強いハンドでBetしすぎる
                Bet頻度が多い(一旦、Raiseは考えない)
    """
    # phaseごとにまとめる
    phase_enemy_stra_feature = {}

    # phaseごとに特徴を取り出す
    for active_phase, statistics_dict in allphase_statistics_dict.items():

        enemy_stra_feature = {}

        #* 1) Callし過ぎ
        # 使用するデータを取り出す
        # 1: ハンドあり
        use_statistics_data = statistics_dict['hand_trust']
        enemy_stra_feature['too_Call'] = check_bias_strategy_gen2(use_statistics_data, hand_exists=True, target='too_Call')
        # 2: ハンドなし(まだ判定できてないとき)
        if enemy_stra_feature['too_Call'] is None:
            use_statistics_data = statistics_dict['no_hand_trust']
            enemy_stra_feature['too_Call'] = check_bias_strategy_gen2(use_statistics_data, hand_exists=False, target='too_Call')

        #* 2) Foldし過ぎ
        use_statistics_data = statistics_dict['no_hand_trust']
        enemy_stra_feature['too_Fold'] = check_bias_strategy_gen2(use_statistics_data, hand_exists=False, target='too_Fold')

        #* 3) ブラフ多すぎ、少なすぎ
        # 信頼できるブラフハンドだけを集めたデータを入れる
        # 1: 弱いハンドの統計
        use_statistics_data = statistics_dict['weak']
        enemy_stra_feature['bluff'] = check_bias_strategy_gen2(use_statistics_data, hand_exists=True, target='bluff')
        # 2: ハンドが見えてるとき
        if enemy_stra_feature['bluff'] is None:
            use_statistics_data = statistics_dict['hand_trust']
            enemy_stra_feature['bluff'] = check_bias_strategy_gen2(use_statistics_data, hand_exists=True, target='bluff')
        # 3: ハンド無し(まだ判定できてないとき)
        if enemy_stra_feature['bluff'] is None:
            use_statistics_data = statistics_dict['no_hand_trust']
            enemy_stra_feature['bluff'] = check_bias_strategy_gen2(use_statistics_data, hand_exists=False, target='bluff')

        #* 4) 強いハンドでCheckし過ぎ、Betし過ぎ
        # 信頼できる強いハンドだけを集めたデータを入れる
        use_statistics_data = statistics_dict['strong']
        enemy_stra_feature['strong_hand'] = check_bias_strategy_gen2(use_statistics_data, hand_exists=True, target='strong_hand')

        phase_enemy_stra_feature[active_phase] = enemy_stra_feature

    return phase_enemy_stra_feature

def check_bias_strategy(use_statistics_data, mini_total, *, target):
    """
    判別に使用するデータを受取り、判別のtarget内容によって判定を変える
    - Args:
        - target:
            [too_Call, too_Fold, bluff, strong_hand] 特徴を判別したい内容を入れる
    - 処理:
        - 一旦、total=1000で、100%以上差があれば傾向があるとする
        いずれ、50%の傾向でも、少し調整をするとかしていいと思う
        - 強いハンドのとき、Betが多すぎることしか確認していない。(RaiseやAllinが多すぎるかどうかは確認していない)
    - Returns:
        - 計算上その傾向があればTrueを返す
        いずれ、どれくらいその傾向が強いかを数値で返して、どれくらい調整するか判別できるようにする
    """
    # 判定に使用するアクションを選ぶ
    if target == 'too_Call':
        target_actions = ['Call', 'Fold']
        # mini_total = 30
    elif target == 'too_Fold':
        target_actions = ['Fold']
        # mini_total = 30
    elif target == 'bluff':
        target_actions = ['Fold', 'Call', 'Check', 'Raise', 'Bet', 'Allin']
        # mini_total = 10
    elif target == 'strong_hand':
        target_actions = ['Check', 'Bet'] # Raise削除した。一旦、Allinも削除した(Allinが多すぎたらかなりぶれてしまう)
        # mini_total = 10

    judge_data = {} # 各アクションがgtoよりも大きいとき、Trueが入れられる。少ないとき(ブラフが多い少ない)、Falseが入る。傾向がないとき、Noneが入る
    for action in target_actions:
        total = use_statistics_data[action]['total_count']
        diff_txt = use_statistics_data[action]['diff_rate']
        # 50回以下のデータは判定をパスする
        if total < mini_total:
            judge_data[action] = None
            continue
        # gtoとの乖離の比率を取り出す
        diff = delete_non_numbers(diff_txt.split('ratio:')[1], print_text=False)

        # 1000回以上で、100%以上 または、 100回以上で、150%以上なら、True
        if target in ('too_Call', 'too_Fold'):
            if (total >= 1000 and diff >= 100) or (total >= mini_total and diff >= 150):
                judge_data[action] = True
                continue
        else:
            if (total >= 500 and diff >= 100) or (total >= mini_total and diff >= 150):
                judge_data[action] = True
                continue
            elif target == 'bluff' and ((total >= 500 and diff <= -50) or (total >= mini_total and diff <= -60)):
                judge_data[action] = False
                continue

        # totalに応じてしきい値を変える
        if target in ('too_Call', 'too_Fold'):
            threshold = -0.0556 * total + 155.56 # x=100 で、y=150, x=1000で、y=100 となるしきい値の式
        else:
            threshold = -0.1111*total + 155.56 # x=50 で、y=150, x=500で、y=100 となるしきい値の式
            threshold_passive = 0.0222*total - 61.11 # x=50のとき、y=-60で、x=500のとき、y=-50

        # しきい値以上なら、True
        if threshold <= diff:
            judge_data[action] = True
        # 少ないときはFalse
        elif target == 'bluff' and threshold_passive >= diff:
            judge_data[action] = False
        # しきい値以下はFalse
        else:
            judge_data[action] = None

    bias_data = {} # 相手の傾向を入れる
    #* Callが多すぎる、または、Foldが多すぎるかの判定のとき
    if target in ('too_Call', 'too_Fold'):
        return judge_data[target_actions[0]]
    #* 弱いハンドのとき、ブラフが多いかどうか判定する
    elif target == 'bluff':
        #1) Betが多すぎるかどうかの確認
        if judge_data['Bet']:
            bias_data['too_Bet'] = True
        elif judge_data['Bet'] is False:
            bias_data['too_Bet'] = False
        #2) Raiseが多すぎるかどうかの判定
        if judge_data['Raise']:
            bias_data['too_Raise'] = True
            if judge_data['Bet']:
                big_print('弱いハンドのときに、Betが多すぎるし、Raiseも多すぎるようです', 'cyan')
        elif judge_data['Raise'] is False:
            bias_data['too_Raise'] = False
        #3) Allinが多すぎるかどうかの判定(一応)
        if judge_data['Allin']:
            bias_data['too_Allin'] = True
        elif judge_data['Allin'] is False:
            bias_data['too_Allin'] = False

        return bias_data

    #* 強いハンドのときCheckが多すぎるのか、Betが多すぎるのか判定する
    elif target == 'strong_hand':
        #1) Checkが多すぎるかどうかの確認(Checkが多すぎるという確認だけで良い)
        if judge_data['Check']: # and next((False for action, judge in judge_data.items() if 'Check' != action and judge), True)
            bias_data['too_Check'] = True
        #2) Betが多すぎるかどうかの判定
        if judge_data['Bet']:
            bias_data['too_Bet'] = True
            if judge_data['Check']:
                big_print('強いハンドのときに、Betが多すぎるし、Checkも多すぎるようです\nそんなことある？', 'cyan', '▲')

        return bias_data

def check_bias_strategy_gen2(use_statistics_data, hand_exists, *, target):
    """
    判別に使用するデータを受取り、判別のtarget内容によって判定を変える
    もともとのプログラムは分かりづらかったので修正した
    - Args:
        - target:
            [too_Call, too_Fold, bluff, strong_hand] 特徴を判別したい内容を入れる
        - hand_exists:
            True, False. Trueにしたら母数が少なくても傾向があるかを判定する
    - 処理:
        - 一旦、total=1000で、100%以上差があれば傾向があるとする
        いずれ、50%の傾向でも、少し調整をするとかしていいと思う
        - 強いハンドのとき、Betが多すぎることしか確認していない。(RaiseやAllinが多すぎるかどうかは確認していない)
    - Returns:
        - 計算上その傾向が多すぎればTrueを返す。傾向がなければNone、少なすぎる場合は、False
        いずれ、どれくらいその傾向が強いかを数値で返して、どれくらい調整するか判別できるようにする
    """

    #* 判定に使用するアクションを選ぶ
    if target == 'too_Call':
        target_actions = ['Call', 'Fold']
    elif target == 'too_Fold':
        target_actions = ['Fold']
    elif target == 'bluff':
        target_actions = ['Fold', 'Call', 'Check', 'Raise', 'Bet'] # Allin削除した
    elif target == 'strong_hand':
        target_actions = ['Check', 'Bet'] # Raise削除した。一旦、Allinも削除した(Allinが多すぎたらかなりぶれてしまう)

    # 母数の指定
    mini_total = 10
    if hand_exists:
        mini_total = 5

    #* 各アクションがgtoよりも大きいとき、Trueが入れられる。少ないとき(ブラフが多い少ない)、Falseが入る。傾向がないとき、Noneが入る
    judge_data = {}
    for action in target_actions:
        total = use_statistics_data[action]['total_count']
        diff_txt = use_statistics_data[action]['diff_rate']
        # 特定回以下のデータは判定をパスする
        if total < mini_total:
            judge_data[action] = None
            continue
        # gtoとの乖離の比率(%)を取り出す
        split_diff_txt = diff_txt.split('ratio:')[1]
        diff_ratio = delete_non_numbers(split_diff_txt, print_text=False)
        if '-' in split_diff_txt:
            diff_ratio *= -1

        # gtoとの乖離の差を取り出す
        split_diff_value = diff_txt.split('(')[0]
        diff_value = delete_non_numbers(split_diff_value, print_text=False)
        if '-' in split_diff_value:
            diff_value *= -1

        """
        500ハンド超えてるなら、100%の差があれば傾向がある
        または、mini_total を超えていて、150%の差があれば傾向がある
        250226
        スコアの合計で傾向があるか判定する処理に変更
        """
        # 乖離度合いのスコアを計算
        diff_score = 0
        # 比が150, 65, 30 以上ならスコアを足す
        if abs(diff_ratio) == 999:
            diff_score += 1
        elif abs(diff_ratio) >= 150:
            diff_score += 3
        elif abs(diff_ratio) >= 65:
            diff_score += 2
        elif abs(diff_ratio) >= 30:
            diff_score += 1
        # 差が15,10,5以上ならスコアを足す
        if abs(diff_value) >= 15:
            diff_score += 3
        elif abs(diff_value) >= 10:
            diff_score += 2
        elif abs(diff_value) >= 5:
            diff_score += 1

        # scoreが4以上でgtoより乖離していると判定する
        # 乖離無し
        if diff_score < 4:
            judge_data[action] = None
        # 乖離ありのとき正か負を判定
        elif diff_ratio > 0:
            judge_data[action] = True
        else:
            judge_data[action] = False

    #* 傾向があるか判定する
    bias_data = {} # 相手の傾向を入れる
    if target == 'too_Call':
        # Callが多く、Foldが少ないとき
        if judge_data['Call'] and judge_data['Fold'] is False:
            return True
        else:
            return None

    elif target == 'too_Fold':
        if judge_data['Fold']:
            return True
        else:
            return None

    elif target == 'bluff':
        # 1) ブラフ過多の確認
        # Fold, Call, Check に多すぎる傾向はない
        if not judge_data['Fold'] and not judge_data['Call'] and not judge_data['Check']:
            # Bet に多すぎる傾向がある。 Raiseはどちらでもいい
            if judge_data['Bet']:

                if judge_data['Raise']:
                    big_print('Raiseも多すぎるようです', 'on_red')
                elif judge_data['Raise'] is False:
                    big_print('Raiseは少なすぎるようです', 'on_red')
                return True
        # 2) ブラフが少なすぎるかどうかの確認
        # Fold, Check に少なすぎる傾向はなく、Callに多すぎる傾向はない
        if judge_data['Fold'] in (True, None) and judge_data['Call'] in (False, None) and judge_data['Check'] in (True, None):
            # Betが少なすぎたらその傾向がある。Raiseはどちらでもいい
            if judge_data['Bet'] is False:
                if judge_data['Raise']:
                    big_print('Raiseは多すぎるようです', 'on_red')
                elif judge_data['Raise'] is False:
                    big_print('Raiseも少なすぎるようです', 'on_red')
                return False
        return None

    elif target == 'strong_hand':
        # Checkが多すぎる
        if judge_data['Check']:
            return False
        elif judge_data['Bet']:
            return True
        else:
            return None

# =============================
# 統計を計算する
# =============================

def procces_statistics(statistics_data):
    """
    集められたデータから、統計を取る
    - 統計:
        - 1: ハンドあり、gtoとの乖離少なめ
        - 2: ハンドなし、gtoとの乖離少なめ
        - 3: 信頼できる弱いハンドのみ
        - 4: 信頼できる強いハンドのみ
    """

    # 各フェーズごとにわけでデータを入れる
    allphase_statistics_dict = {}

    # 各フェーズごとにデータを取り出す
    phase_list = ['total']
    phase_list += list(glbvar.phase_order)
    for phase in phase_list:

        #* ハンドあり、なし、を順に統計とる
        all_statistics_dict = {}
        for hand_key in ('hand', 'no_hand'):
            statistics_data_trust, _ = statistics_data_with_params(statistics_data, hand_key, separe=0.9, target_phase=phase)
            # データを追加する
            all_statistics_dict[f'{hand_key}_trust'] = statistics_data_trust

        #* 弱いハンドのみの統計を計算する
        statistics_data_weak, _ = statistics_data_with_params(statistics_data, 'weak', separe=0.9, target_phase=phase)
        all_statistics_dict['weak'] = statistics_data_weak

        #* 強いハンドのみの統計を計算する
        statistics_data_strong, _ = statistics_data_with_params(statistics_data, 'strong', separe=0.9, target_phase=phase)
        all_statistics_dict['strong'] = statistics_data_strong

        allphase_statistics_dict[phase] = all_statistics_dict

    return allphase_statistics_dict

def merge_statistics_data(statistics_data):
    """
    handとno_handで別れてるデータを1つにする
    """
    # 新規で入れるデータを用意。統計を取るデータを利用するために、total key を用意
    merged_data = {'total': {'gto': copy.deepcopy(template_statistics_data), 'action': copy.deepcopy(template_statistics_data)}}

    # hand, no_hand を別で取り出す
    for key, pare_data in statistics_data.items():
        if 'index' == key:
            continue
        # gto, action を別で取り出す
        for type, data in pare_data.items():
            # action別で取り出す
            for action, aggregated_data in data.items():
                # リストを追加する
                merged_data['total'][type][action] += aggregated_data

    return merged_data

def statistics_data_with_params(statistics_data, hand_key, *, separe, target_phase):
    """
    集計されたデータのgtoからの乖離を求める
    - Args:
        - hand_key: hand, no_hand, weak, strong. 'hand'ならハンドあり、'no_hand'ならハンド無しを計算する
        - separe: この数字以上にgtoとrealのpotの差があれば信頼できないデータ側に入れる
            None にすれば、potサイズの乖離を考慮せずすべて一緒に計算する
        - target_phase: 'total'なら、全てのphaseを対象にする。なにかtargetを入れれば、そのphaseデータのみを集める
    - 処理:
        - 信頼できるデータかどうか:
            gtoと実際のpotサイズの差がsepare未満 または、 差の比率が25%以下
    """
    # 統計を取るためのデータを整理するリストを用意
    all_statistics = {
        'trust': {
            'rate': {action: [] for action in glbvar.action_list}, # 各アクションの空リストを作成する
            'sum': {action: 0 for action in glbvar.action_list}, # 各アクションの空データを作成する
        },
        'not': {
            'rate': {action: [] for action in glbvar.action_list}, # 各アクションの空リストを作成する
            'sum': {action: 0 for action in glbvar.action_list}, # 各アクションの空データを作成する
        },
    }

    # 統計を取るために集計する
    # gto と action 別で取り出す
    for type, statistics_dict_data in statistics_data[hand_key].items():
        # アクション別で取り出す
        for action, data_list in statistics_dict_data.items():
            # データを順に取り出す
            for data in data_list:
                # phaseの判定をする
                active_phase = data['phase']
                # ほしいphaseと異なるデータはパスする
                if target_phase != 'total' and target_phase != active_phase:
                    continue
                # weak, strongはpreflopのデータは不要
                if hand_key in ('weak', 'strong') and active_phase == 'preflop':
                    continue

                # 信頼できるデータかどうか判別する
                # 信頼できないとき
                if separe is None or separe >= abs(data['diff_gto']['diff']) or glbvar.trust_diff_pot_rate >= abs(data['diff_gto']['rate']):
                    trust_key = 'trust'
                else:
                    trust_key = 'not'

                if type == 'gto':
                    # rateを追加する
                    all_statistics[trust_key]['rate'][action].append(data['rate'])
                elif type == 'action':
                    # 見つかったアクションを足す
                    all_statistics[trust_key]['sum'][action] += 1

    # 各アクションのgtoとの乖離を計算する
    result_dict = {}
    for trust_key, active_statistics in all_statistics.items():
        # 乖離を計算する
        result_statistics_data = calucurate_deviation_statistics_data(active_statistics)
        result_dict[trust_key] = result_statistics_data

    return result_dict['trust'], result_dict['not']

def calucurate_deviation_statistics_data(active_statistics):
    """
    統計を取るために集計されたデータから、gtoとのアクションの乖離を計算する
    ・各アクションのgtoと実際の乖離を計算する
    """
    # 分子、分母を入れる辞書を用意
    each_action_data = {action: {'diff_rate': None, 'total_count': 0, 'gto_rate': 0, 'action_rate': 0} for action in glbvar.action_list}

    # 各アクションのgto頻度を計算する
    for action, aggregate_data in active_statistics['rate'].items():
        gto_sum = sum(rate for rate in aggregate_data)
        total_count = len(aggregate_data)

        # gto頻度の平均を計算
        if total_count > 0:
            gto_ave_rate = round(gto_sum/total_count, 3)
        else:
            gto_ave_rate = 0

        # データを入れる
        each_action_data[action]['total_count'] = total_count
        each_action_data[action]['gto_rate'] = gto_ave_rate

    # 各アクションのgto頻度の乖離を計算する
    for action, action_sum in active_statistics['sum'].items():
        # 補数で計算するとき、下記をTrueにする
        reversed_rate = False
        # choiceが一度でもあった場合、計算する
        if each_action_data[action]['total_count'] > 0:
            # アクションの平均頻度を計算する
            action_ave_rate = round(action_sum/each_action_data[action]['total_count'], 3)

            # どちらも50%を超えているとき、補数で計算する
            if action_ave_rate >= 0.5 and each_action_data[action]['gto_rate'] >= 0.5:
                reversed_rate = True
                action_ave_rate = round(1 - action_ave_rate, 3)

                each_action_data[action]['gto_rate'] = round(1 - each_action_data[action]['gto_rate'], 3)

            # gto頻度との乖離を計算する
            if each_action_data[action]['gto_rate'] == 0 and reversed_rate is False:
                diff_rate = None
            else:
                diff_rate = culcurate_diffrate_between_real_to_gto(action_ave_rate, each_action_data[action]['gto_rate'])
                # Foldのとき逆にする
                if diff_rate and reversed_rate:
                    diff_rate *= -1

            # 2) 差
            diff_value = round((action_ave_rate - each_action_data[action]['gto_rate']) * 100 , 1)
            # Foldのとき逆にする
            if reversed_rate:
                diff_value *= -1
        else:
            action_ave_rate = 0
            diff_rate = None
            diff_value = 0

        # データを追加する
        # マイナスかプラスかわかるようにする
        symbol = ''
        if diff_value > 0:
            symbol = '+'
        elif diff_value == 0:
            symbol = '±'
        # 補数で比較したとき、テキストを追加する
        reversed_symbol = ''
        if reversed_rate:
            reversed_symbol = '(reversed_rate)'

        each_action_data[action]['diff_rate'] = f'diff:{symbol}{diff_value}%(ratio:{symbol}{diff_rate}%){reversed_symbol}' # +10%(120%)
        each_action_data[action]['action_rate'] = action_ave_rate

    return each_action_data

def culcurate_diffrate_between_real_to_gto(real_ave_rate, gto_ave_rate):
    """
    gtoとrealの頻度の比を計算する
    - 処理:
        - 小さい方を大きい方で割る。それを逆数にすれば、2倍差があるとき、100%の差があると今まで通り出せる
        - それが、realの方が小さいならマイナス。realが多いなら、プラスにして返す
    """
    # 小さい方が0のとき、999を返す
    if min(real_ave_rate, gto_ave_rate) == 0:
        diff_rate = 999

    else:
        # 大きい方を小さい方で割り、% にして、100をマイナスする -> 2倍の差があるとき、+100がでてくる
        diff_rate = round(max(real_ave_rate, gto_ave_rate) / min(real_ave_rate, gto_ave_rate) * 100 - 100 , 1)

    # realの方が小さかった時、マイナスにする(->マイナスは少なすぎるを表す)
    if real_ave_rate < gto_ave_rate:
        diff_rate *= -1

    return diff_rate

# =============================
# dataから集計する
# =============================

def gather_statistics_data(statistics_data, conv_data):
    """
    convert_stradata から集計する
    1, ハンドありか無しか判断
    2, 順に集計する
    """
    # ハンドありか無しか判定
    exist_hand = False
    if conv_data['general']['about_hand']:
        exist_hand = True

    # 統計データを取らないとき、Trueにする
    dont_continue_get_data = False

    # 集計を取る
    for phase in glbvar.phase_order:
        # phaseがなければ抜ける
        if phase not in conv_data:
            break

        # そのphaseの data list を取り出す
        data_list = conv_data[phase]['solutions']
        for data in data_list:
            # solutionがないものはパスする
            if 'solution' not in data:
                continue
            # preflopでsolutionがリストのものはパスする <- このとき、リンプインがいるので参考にならない
            if phase == 'preflop' and isinstance(data['solution'], list):
                continue
            # 統計データを取らない指示があるときループを抜ける
            if dont_continue_get_data:
                break

            # インデックスを更新する(これによって0から始まらなくなるけど特に問題ない)
            statistics_data['index'] += 1

            # 1) actionを取り出す
            active_action = data['action']
            # summaryに変換する
            summary_action = convert_action_summary(active_action)

            # potを取り出す
            pot_data = data['pot']
            # gtoとrealのpotの差額を求める
            diff_pot_from_gto = calucurate_diff_pot(pot_data)

            # 2) solutionを取り出す
            #* ハンドが無いとき
            if exist_hand is False:
                active_solution = data['solution']
                summary_solution = convert_solution_for_summary(active_solution)
                # action_choices にCallがないとき、状況によってはパスする
                if check_no_Call_situation(summary_action, summary_solution, data):
                    continue
                statistics_data = add_statistics_data(statistics_data, 'no_hand', summary_solution, summary_action, diff_pot_from_gto, phase)
                continue

            #* ハンドがあるとき
            # 1) rangeのsolutionを集計する
            if phase == 'preflop':
                active_solution = data['solution']['range']
            else:
                active_solution = next(solution_data['range'] for solution_data in data['solution'] if 'range' in solution_data)
            summary_solution = convert_solution_for_summary(active_solution)
            # action_choices にCallがないとき、状況によってはパスする
            if check_no_Call_situation(summary_action, summary_solution, data):
                continue
            statistics_data = add_statistics_data(statistics_data, 'no_hand', summary_solution, summary_action, diff_pot_from_gto, phase)

            # 2) aboutのsolutionを集計する
            if phase == 'preflop':
                active_solution = data['solution']['about']
            else:
                active_solution = next(solution_data['detail'] for solution_data in data['solution'] if 'detail' in solution_data)

            # ゼロレンジsolutionのとき飛ばす
            if 0 == sum(ratio for ratio in active_solution.values()):
                continue

            summary_solution = convert_solution_for_summary(active_solution)
            statistics_data = add_statistics_data(statistics_data, 'hand', summary_solution, summary_action, diff_pot_from_gto, phase)

            # 以降の処理はpreflopでは行わない
            if phase == 'preflop':
                continue
            # 弱いハンドなら弱いハンドリストにいれる
            if check_hand_type(data, type='weak'):
                statistics_data = add_statistics_data(statistics_data, 'weak', summary_solution, summary_action, diff_pot_from_gto, phase)
            # 強いハンドならstrong_handリストに入れる
            elif check_hand_type(data, type='strong'):
                statistics_data = add_statistics_data(statistics_data, 'strong', summary_solution, summary_action, diff_pot_from_gto, phase)

    return statistics_data

def check_hand_type(data, *, type):
    """
    solutionを受取り、EVやEQをみて、ハンドのタイプを判別する
    - Args:
        - type: [weak, strong] ブラフか強いハンドか判別する
    - 処理: <- もしかしたら、
        - weak: EQが40以下のハンドを入れる(弱いハンドのときのアクションを取り出せば傾向をつかめると思う)
        - strong: EQ が 70 以上(一旦70にした) <- 80に変更(相当強いハンドのみに絞る)
        - EQのしきい値はphaseやpositionによって変えてもいいかもしれない
    """
    eq = data['EQ']

    # 弱いハンドかどうか
    if type == 'weak':
        if eq  <= glbvar.weak_EQ:
            return True
        return False

    # 強いハンドかどうか
    if type == 'strong':
        if eq  >= glbvar.strong_EQ:
            return True
        return False

def check_get_next_action(solution):
    """
    about_hand のsolutionがFold100%のとき、これ以降のアクションは取り出さない。
    これ以降はすべてFold100%になり、統計データに偏りが強くなりすぎる。
    rangeがFold100%のとき、そもそもそんな状況はほぼない。そして、gtoもなくなると思う。
    """
    # 選択肢にFoldがない場合、考えなくて良い
    if 'Fold' not in solution:
        return False

    # Fold100%のとき、これ以降のアクションは調べない
    if solution['Fold'] == 100:
        big_print('gto上、Fold100%の状況なので、これ以降のactionは統計にいれません', 'on_red')
        return True

    # 上記でなければ問題なし
    return False

def check_no_Call_situation(action, solution, data):
    """
    action choices にCallがないとき、状況によってはパスする
    """
    # action が Callじゃないなら判定しなくていい
    if 'Call' != action:
        return False

    # solutionにCallがあるなら問題なし
    if 'Call' in solution:
        return False

    # all_Foldの状況のリンプインは統計データに入れる
    if 'all_Fold' in data['situation']:
        return False

    # そうでない場合は、パスする
    big_print('リンプが入った後のリンプインは統計データに入れません', 'on_red')
    return True

def add_statistics_data(statistics_data, target_key, summary_solution, summary_action, diff_pot_from_gto, phase):
    """
    solutionを集計に入れる
    - Args:
        - dont_update_index: Trueのとき、indexを更新しない
    - 処理:
        solutionにないアクションはrate0%で追加することにした。(gtoにないアクションを選択され続けると頻度が1を超える。それでも問題ないと思うけど、こうすることにした)
    """
    # indexを取り出し、次のためにあらかじめ足す
    index = statistics_data['index']

    for choice, rate in summary_solution.items():
        # 追加するデータを用意する
        add_data_solu = {
            'index': index,
            'rate': round(rate/100, 3), # 少数にする
            'diff_gto': diff_pot_from_gto,
            'phase': phase,
        }
        # データを追加する
        statistics_data[target_key]['gto'][choice].append(add_data_solu)

    # solutionにないアクションをrate0%で追加する
    for choice in glbvar.action_list:
        if choice not in summary_solution:
            # 追加するデータを用意する
            add_data_solu = {
                'index': index,
                'rate': 0,
                'diff_gto': diff_pot_from_gto,
                'phase': phase,
            }
            # データを追加する
            statistics_data[target_key]['gto'][choice].append(add_data_solu)

    # アクションを追加する
    add_data_action = {
        'index': index,
        'diff_gto': diff_pot_from_gto,
        'phase': phase,
    }
    statistics_data[target_key]['action'][summary_action].append(add_data_action)

    return statistics_data

def calucurate_diff_pot(pot_data):
    """
    real と gto のpot額の差を求める
    - Returns:
        - diff_value: 差額と割合を計算して返す
    """
    diff_value = {
        'diff': 0,
        'rate': 0,
    }

    gto_pot = delete_non_numbers(pot_data.split('gto')[-1], print_text=False)
    real_pot = delete_non_numbers(pot_data.split('(')[0], print_text=False)

    # 差額を計算する
    diff_value['diff'] = round((gto_pot - real_pot), 1) # 一旦、abs無しにする

    # 割合を計算する(大きい方を基準に計算する)
    diff_value['rate'] = round(((1 - min(gto_pot, real_pot) / max(gto_pot, real_pot))*100), 1)

    return diff_value

def convert_solution_for_summary(active_solution):
    """
    solutionを集計用に変換する
    - 処理:
        - Raiseが複数あるとき、Raiseにまとめる
        - Allin は Allinとする
    """
    converted_solution = {}
    for choice in active_solution:
        # 一致するアクションを探す
        for summary in ('Fold', 'Call', 'Check', 'Raise', 'Bet', 'Allin'):
            if summary in choice:
                # Raiseのときは既にある可能性があるので、処理が他に必要
                if summary in ('Bet','Raise'):
                    # 既にkeyがあるとき、足してbreakする
                    if summary in converted_solution:
                        converted_solution[summary] = round(converted_solution[summary] + active_solution[choice], 1)
                        break
                # 上記以外は、新規追加する
                converted_solution[summary] = active_solution[choice]
                break

    return converted_solution

def convert_action_summary(active_action):
    """
    actionを統計と取るための形に変換する
    """
    if 'near_gto' in active_action:
        active_action = active_action.split('near_gto')[0]

    # リストの中に一致するものがあればそれをsummaryとする
    for summary in ('Fold', 'Call', 'Check', 'Raise', 'Bet', 'Allin'):
        if summary in active_action:
            return summary

# =============================
# 統計を取る準備
# =============================

def make_id_list():
    """
    確認するidのリストを用意する
    """

    id_list = []
    for dir_name in os.listdir(glbvar.player_private_dir):
        if 'anlz_' not in dir_name:
            continue
        if '(' in dir_name:
            dir_name = dir_name.split('(')[0]
        id_list.append(dir_name)

    sorted_id_list = sorted(id_list, key=lambda x: int(x.split('_')[1]))

    return sorted_id_list

if __name__ == "__main__":
    main()