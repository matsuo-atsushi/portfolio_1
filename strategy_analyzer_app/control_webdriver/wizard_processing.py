"""
複雑な処理を含む、wizardを操作するプログラム
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.keys import Keys

from termcolor import colored, cprint
import time
import sys
import pyautogui
import os
import traceback

from strategy_analyzer_app.io_operations.print_processing import big_print
import strategy_analyzer_app.control_webdriver.control_wizard as ctlwiz
from strategy_analyzer_app.text_processing.text_extraction import convert_number, delete_non_numbers


#!!!
def load_action_choices(driver, player_position, action_count, game_phase, start_time=None, get_GTOstack=False):
    """
    wizardでアクションの選択肢を読み込む処理を関数にまとめる
    [返り値]
    action_choices, クリックするときに使うelement

    - Args:
        - get_GTOstack:
            - Trueにするとスタックサイズも返す
    """
    # 数字に変換する
    action_count = int(action_count)

    if get_GTOstack:
        # loader_spinnerの存在が消えるまで待機する
        WebDriverWait(driver, 30).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-tst='loader_spinner']")))

    # フロップ入力画面になっていたら閉じる
    if game_phase != 'preflop':
        ctlwiz.click_close_button(driver, limit_time=0.01, args=(f'player_position:{player_position}', f'action_count:{action_count}', f'game_phase:{game_phase}'))

    #* アクションの選択肢を読み込む
    try_count = 0 # 0, 1, 2 を繰り返し、action_countを+1, -1する
    adjust = 0
    while True:
        roading_done = True
        # 入力したいポジションの選択肢が読み込まれるまで繰り返す
        while True:
            try:
                # クリックしたい要素を見つける(activeのもの)
                parent_element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="hs_{action_count+adjust}_{game_phase}_{player_position}_active"]')
                # ポジションのところにを探して、マウスオーバーする
                child_elements = parent_element.find_elements(By.XPATH, f".//*[contains(text(), '{player_position}')]")
                action = ActionChains(driver)
                action.move_to_element(child_elements[0]).perform()
                # 見つけてすぐだと、全て読み込めていない可能性があるので、0.3s待機してから再読み込みしたものを使用する #* 待機するのはプリフロップ以降のみに変更した
                if game_phase  != 'preflop':
                    time.sleep(0.01)
                parent_element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="hs_{action_count+adjust}_{game_phase}_{player_position}_active"]')
                break
            except:
                try:
                    # activeが見つからなかったら、activeではない要素を探す
                    parent_element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="hs_{action_count+adjust}_{game_phase}_{player_position}"]')
                    # 見つけてすぐだと、全て読み込めていない可能性があるので、0.3s待機してから再読み込みしたものを使用する
                    # ポジションのところにを探して、マウスオーバーする
                    child_elements = parent_element.find_elements(By.XPATH, f".//*[contains(text(), '{player_position}')]")
                    action = ActionChains(driver)
                    action.move_to_element(child_elements[0]).perform()
                    # 見つけてすぐだと、全て読み込めていない可能性があるので、0.3s待機してから再読み込みしたものを使用する #* 待機するのはプリフロップ以降のみに変更した
                    if game_phase  != 'preflop':
                        time.sleep(0.01)
                    parent_element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="hs_{action_count+adjust}_{game_phase}_{player_position}"]')
                    break
                except:
                    # 見つからないとき
                    try:
                        if game_phase != 'preflop':
                            # loader_spinnerが消えて、フロップ入力画面になっていれば閉じる
                            ctlwiz.click_close_button(driver, limit_time=0.05, args=(f'player_position:{player_position}', f'action_count:{action_count}', f'game_phase:{game_phase}'))
                        if start_time is not None:
                            pass
                    except:
                        pass
            #* action_countを±1調整する処理を追加
            if try_count == 0:
                try_count += 1
                adjust = 1
            elif try_count == 1:
                try_count += 1
                adjust = -1
            elif try_count == 2:
                try_count = 0
                adjust = 0

        if adjust != 0:
            big_print('action_countを調整したことで、データが見つかりました', 'white', '▲')

        # 親要素から hspotcrd_action_text の要素を全て取得
        action_text_elements = parent_element.find_elements(By.CLASS_NAME, 'hspotcrd_action_text')
        action_choices = {}
        # 全ての hspotcrd_action_text 要素のテキストを出力
        for idx, element in enumerate(action_text_elements):
            # 十分に読み込めていないのを確認したら、最初からやり直し、再読み込みする
            if element.text == '':
                print('読み込み終えていないと思われるので、再読み込みします')
                if game_phase != 'preflop':
                    # loader_spinnerが消えて、フロップ入力画面になっていれば閉じる
                    ctlwiz.click_close_button(driver, limit_time=0.01, args=(f'player_position:{player_position}', f'action_count:{action_count}', f'game_phase:{game_phase}'))
                roading_done = False
                break
            action_txt = element.text.replace('\n','').replace(' ','')
            action_choices[idx] = action_txt
            if get_GTOstack:
                if (('Allin' in action_txt or 'Raise' in action_txt or 'Bet' in action_txt) and
                    ('%' not in action_txt or '(' in action_txt)):
                    big_print('アクションの表記が異なるので、再読み込みします', 'red')
                    roading_done = False
                    # windowを手前にする
                    driver.switch_to.window(driver.current_window_handle)
                    time.sleep(0.5)
                    pyautogui.press('space')
                    # Spaceキーを入力 これでいける？
                    # parent_element.send_keys(Keys.SPACE)
                    break
        # 無事に読み込みが終わったらループを抜ける
        if roading_done:
            break

    if game_phase != 'preflop':
        # loader_spinnerが消えて、フロップ入力画面になっていれば閉じる
        ctlwiz.click_close_button(driver, limit_time=0.01, args=(f'player_position:{player_position}', f'action_count:{action_count}', f'game_phase:{game_phase}'))

    # stackを求めたいとき
    if get_GTOstack:
        # .hspotcrd_title 内のテキストを取得
        title_element = parent_element.find_element(By.CLASS_NAME, "hspotcrd_title")

        # "BB" の部分を取得（最初の div）
        bb_text = title_element.find_element(By.CSS_SELECTOR, ".d-flex > div:nth-child(1)").text.strip()

        # "82.05" の部分を取得（ml-auto を持つ div）
        amount_text = title_element.find_element(By.CSS_SELECTOR, ".ml-auto").text.strip()

        # 数値変換
        amount = float(amount_text)

        # リスト化
        result = [bb_text, amount]

        # 出力
        # print(result)  # → ['BB', 82.05]

        return action_choices, action_text_elements, start_time, amount

    return action_choices, action_text_elements, start_time

def best_select_player_action(action_choices, player_action, bet_rate, Call_cost, player_position, game_phase, wizard_Raise_list,
                                driver=None, action_text_elements=None, check_between_Bet=False, rough_check=False, dont_click_small_bet=False, analyze_mode=False):
    """
    TODO 引数として足りていないものがあると思うので要テスト
    action_choices の中から、最も適しているアクションを選ぶ
    [返り値]
    selected_Allin, previous_player_small_bet, new_E_player, wizard_Raise_list, selected_action <- csvパスを作成するのに必要

    - Args:
        - dont_click_small_bet:
            - これがTrueのとき、小さいbetをしてきたとき、Checkを選ばなくなる
        - analyze_mode:
            - Trueにすると、小さいRaiseをCallと選ぶことがなくなる
            - Raiseとあるとき、Allinを選ばなくなる <- よほど差があるときしか選ばない(2:8くらいだったらAllinを選ぶ(要検討))
    """

    new_E_player = None # リンプの疑いのあるプレイヤーを入れる変数

    print_player = colored(f' {player_position} ', "white", attrs=["reverse", "blink"])

    # Allinのときは、Allin_Raiseのようになっている。このときは、一旦Raiseとして要素を探して、一番Bet_rateが近いものを選択する
    Allin_flag = False
    if '_' in player_action:
        Allin_flag = True
        player_action = player_action.split('_')[1]
    # Allinをするとき、wizardに入力しないので、下記の処理が行われることは無いと思う
    elif 'Allin' in player_action:
        Allin_flag = True
        if Call_cost == 0:
            player_action = 'Bet'
        else:
            player_action = 'Raise'

    # 入力したいアクションのキーを探す
    action_index = None
    repeat_count = 0
    # wizardに入力するアクションの補正用データ
    action_transform_dict = {'Check':'Call', 'Call':'Check', 'Raise':'Bet', 'Bet':'Raise', 'Allin':'Bet', 'Fold':'Check'}
    action_transform_dict2 = {'Raise':'Allin', 'Bet':'Allin', 'Call':'Fold', 'Check':'Fold'} #? <- 'Check':'Fold' は使う時ある？保険用？
    # Raise, Bet以外の処理
    if player_action in ('Check', 'Call', 'Fold'):
        while True:
            for action_index, wizard_action in action_choices.items():
                # Allinも探し出せるように"in"を使う
                if player_action in wizard_action:
                    # 要素が見つかったらクリック <- csvのときはクリックしない
                    if action_text_elements:
                        # loader_spinnerが消えていて、フロップ入力画面になっていれば閉じる
                        #// if game_phase != 'preflop':
                        #//     ctlwiz.click_close_button(driver, limit_time=0.05, args=(f'action_choices:{action_choices}', f'action_choices:{player_action}', f'bet_rate:{bet_rate}', f'Call_cost:{Call_cost}', f'player_position:{player_position}', f'game_phase:{game_phase}'))
                        while True:
                            try:
                                action_text_elements[action_index].click()
                                break
                            except:
                                big_print('アクションを入力できませんでした。ctlwiz.click_close_button を実行します(1)', 'red')
                                ctlwiz.click_close_button(driver, limit_time=0.05, args=(f'action_choices:{action_choices}', f'action_choices:{player_action}', f'bet_rate:{bet_rate}', f'Call_cost:{Call_cost}', f'player_position:{player_position}', f'game_phase:{game_phase}'))

                    # 補正していたら下記を出力する
                    if repeat_count >= 1:
                        cprint(f'クリックしたアクションを"{player_action}"に補正しました', "yellow", attrs=["bold"], file=sys.stderr)
                        if player_position == new_E_player:
                            cprint(f'{print_player} を"E_player"と扱います', "yellow", attrs=["bold"], file=sys.stderr)
                    return False, False, new_E_player, wizard_Raise_list, wizard_action
            # まだ見つかっていない場合、探しているアクションを補正する
            if repeat_count == 0:
                player_action = action_transform_dict[player_action]
                repeat_count += 1
                cprint(f'アクションが見つからないので、"{player_action}"に補正します(1)', "yellow", attrs=["bold"], file=sys.stderr)
                continue
            # まだ見つかっていない場合、探しているアクションを補正する
            elif repeat_count == 1:
                player_action = action_transform_dict2[player_action]
                # Foldが選ばれるときは、Callをしたときに、Callの選択肢がないとき <- new_E_player に入れて返す
                if player_action == 'Fold':
                    new_E_player = player_position
                repeat_count += 1
                cprint(f'アクションが見つからないので、"{player_action}"に補正します(2)', "yellow", attrs=["bold"], file=sys.stderr)
                continue
            # ここまで処理が進んだときはエラーを出す
            elif repeat_count == 2:
                cprint('クリックすべきアクションが見つかりませんでした', "yellow", attrs=["bold"], file=sys.stderr)
                raise Exception('クリックすべきアクションが見つかりませんでした')
    # Raise, Betの処理 -> 常に、Check, Call, Allinも選択肢に入れて探す
    if player_action in ('Raise', 'Bet'):
        print_rate = colored(f' {bet_rate} ', "red", attrs=["reverse", "blink"])
        print_ctext = colored(f' bet_rate ', "red", attrs=["reverse", "blink"])
        print(f'探している{print_ctext} : {player_action}({print_rate})')

        # Raiseとしか書いてないなら、Raiseと書いてるものを選んで返す
        if rough_check and bet_rate == 0:
            Raise_action = next((value for key, value in action_choices.items() if 'Raise' in value), None)
            # Raiseを含むものがなければ、Allinを探す
            if Raise_action is None:
                Raise_action = next((value for key, value in action_choices.items() if 'Allin' in value), None)
            wizard_Raise_list.append(delete_non_numbers(Raise_action, print_text=False))
            return None, False, None, wizard_Raise_list, Raise_action


        #! wizardの選択肢もRaise割合で探すようにすると実際とズレが大きくなると思ったので、今はコメントアウトした TODO いつか処理を復活させる
        # プリフロップのときは、Raiseの割合を再計算して、それに近いものを選ぶように変更 <- オープンRaiseでもRaiseの割合を計算できるようにした
        # if game_phase == 'preflop':
        #     original_action_choices = action_choices.copy()
        #     action_choices = calculate_preflop_Raise_ratio('wizard', original_action_choices, wizard_Raise_list)
        #     print(f'{print_player} | 修正されたaction_choices:{action_choices}')

        while True:
            # Raise, Betを含むバリューのキーとバリューを別の辞書に取り出す
            selected_actions = {key: value for key, value in action_choices.items() if player_action in value}
            # Raiseが見つからなかったら、Betを探す
            if selected_actions == {}:
                # まだ見つかっていない場合、探しているアクションを補正する
                if repeat_count == 0:
                    player_action = action_transform_dict[player_action]
                    repeat_count += 1
                    continue
                if repeat_count == 1:
                    cprint(f'"Raise""Bet"が見つかりませんでした。"Allin"を探します', "yellow", attrs=["bold"], file=sys.stderr)
                    Allin_flag = True
                    break
            else:
                break
        # Check, Call. Allinも選択肢の中にいれる
        for key, value in action_choices.items():
            if analyze_mode:
                if 'Allin' in value:
                    selected_actions[key] = value
                continue
            if 'Allin' in value or 'Check' in value or 'Call' in value:
                selected_actions[key] = value

        # まだ、空のとき、Allinがあって、CallかFoldしかない状況だと思うので、Callも入れる
        if selected_actions == {}:
            big_print('selected_actions が空なので、Callも選択肢に入れます', 'on_red')
            dont_click_small_bet = False
            # Check, Call. Allinも選択肢の中にいれる
            for key, value in action_choices.items():
                if 'Allin' in value or 'Check' in value or 'Call' in value:
                    selected_actions[key] = value


        # 近いアクションを選ぶ処理を関数でまとめた(250107)
        Allin_minirate = None
        if analyze_mode:
            Allin_minirate = 0.7
        close_rate_list, Call_cost, rate1, rate2 = check_close_action(game_phase, selected_actions, Call_cost, bet_rate, check_between_Bet, dont_click_small_bet, Allin_minirate)

        # region
        # # 順にRaiseのBet割合を出して最もscreenから読み取ったBetの割合に近いものを探す
        # most_close_rate = None
        # most_close_rate2 = None
        # most_close_rate3 = None # AllinよりもCallのほうが近くて調整できなかったときがある
        # for key, wizard_action in selected_actions.items():
        #     # Checkのときは、0として進める
        #     if 'Check' in wizard_action:
        #         wizard_rate = 0
        #     # Callのときは、Callするのに必要な額とする(プリフロップ) <- フロップ以降はCallは Raise0% なので、0で良い
        #     elif 'Call' in wizard_action:
        #         wizard_rate = 0
        #         if game_phase == 'preflop': #! 戻した
        #             wizard_rate = Call_cost #! 戻した
        #     # 通常時の処理
        #     else:
        #         # wizard_rate = wizard_action.split(' ')[1] #! Raiseの大きさとかのみを取り出すために使っていた処理。delete_non_numbers さえ行えば行けるはずなので削除した。これでcsvにも対応できるはず。
        #         # % が含まれている場合もあるので補正する
        #         wizard_rate = delete_non_numbers(wizard_action, print_text=False) #! <- wizard_rate を wizard_action に変更した
        #     # screenから読み取ったBetの割合に最も近いものを探す
        #     if most_close_rate is None:
        #         most_close_rate = wizard_rate
        #     elif abs(most_close_rate - bet_rate) > abs(wizard_rate - bet_rate):
        #         # 2つ探すとき
        #         if check_between_Bet:
        #             most_close_rate2 = most_close_rate
        #         most_close_rate = wizard_rate
        #     # 2,3つ目探すとき
        #     elif check_between_Bet:
        #         if most_close_rate2 is None:
        #             most_close_rate2 = wizard_rate
        #         elif abs(most_close_rate2 - bet_rate) > abs(wizard_rate - bet_rate):
        #             most_close_rate2 = wizard_rate
        #         elif most_close_rate3 is None:
        #             most_close_rate3 = wizard_rate
        #         elif abs(most_close_rate3 - bet_rate) > abs(wizard_rate - bet_rate):
        #             most_close_rate3 = wizard_rate

        # # most_close_rateが少数ならintにしてからstringにする -> 5.0 を 5 にする 2.5 は 2.5 のままにする
        # most_close_rate_str = str(convert_number(most_close_rate))
        # close_rate_list = [most_close_rate_str]
        # # wizardのアクションの中から選べるようにCallをconvertする
        # Call_cost = str(convert_number(Call_cost))

        # # 選ばれた2つの割合を計算する -> 差がありすぎるときはいつも通りに変更する
        # if check_between_Bet:
        #     # 使用する2つを選ぶ
        #     # bet_rate は rate と rate2 の間にあるか <- 0 になるのがあるとき、全く同じことになるからパス
        #     if (most_close_rate2 is not None and
        #         ((bet_rate - most_close_rate > 0 and bet_rate - most_close_rate2 < 0) or
        #         (bet_rate - most_close_rate < 0 and bet_rate - most_close_rate2 > 0))):
        #         most_close_rate_No2 = most_close_rate2
        #     elif (most_close_rate3 is not None and
        #         ((bet_rate - most_close_rate > 0 and bet_rate - most_close_rate3 < 0) or
        #         (bet_rate - most_close_rate < 0 and bet_rate - most_close_rate3 > 0))):
        #         most_close_rate_No2 = most_close_rate3
        #     else:
        #         check_between_Bet = False

        #     if check_between_Bet:
        #         diffirent1 = abs(bet_rate - most_close_rate)
        #         diffirent2 = abs(bet_rate - most_close_rate_No2)
        #         rate1 = round(diffirent2 / (diffirent1+diffirent2) , 3)
        #         rate2 = round(diffirent1 / (diffirent1+diffirent2) , 3)

        #         # 差がありすぎる場合、通常のreturnとする
        #         # if 0.1 > rate2:
        #         #     check_between_Bet = False
        #         # else:
        #         #! ↑の処理は、後で行うことにする。片方がnext_phaseなら差があっても考慮する
        #         # 分岐するとき、リストに追加する
        #         most_close_rate_No2_str = str(convert_number(most_close_rate_No2))
        #         close_rate_list.append(most_close_rate_No2_str)
        #         # # 一つしか選択肢がないかどうかの確認 <- でかいAllinのとき、その下のRaiseは無視する。どっちの選択肢よりも小さいという状況はないはずなので確認は行わない(Callよりも小さいBetをしてることになる)
        #         # else:
        #         #     if (bet_rate - most_close_rate >= 0 and bet_rate - most_close_rate2 >= 0):
        #         #         check_between_Bet = False
        # endregion

        near_actions = []
        # 中間サイズBetされたとき、
        base_selected_Allin = None
        previous_small_bet_list = [] # これを選択すると次のフェーズに進む場合、Trueとなって返される

        # most_close_rateを含む要素を探して、選択する
        for most_close_rate_str in close_rate_list:
            for action_index, wizard_action in selected_actions.items():
                # 初期値の用意
                selected_Allin = False
                previous_player_small_bet = False
                # もし探すべきbet_rateが0かCallと同じとき、CheckかCallを探す
                if '0' == most_close_rate_str or Call_cost == most_close_rate_str:
                    if 'Check' in wizard_action or 'Call' in wizard_action:
                        # 要素が見つかったらクリック <- csvのときはクリックしない
                        if action_text_elements:
                            # loader_spinnerが消えていて、フロップ入力画面になっていれば閉じる
                            #* クリックできるまで処理を繰り返すことにした
                            while True:
                                try:
                                    action_text_elements[action_index].click()
                                    break
                                except:
                                    big_print('アクションを入力できませんでした。ctlwiz.click_close_button を実行します(2)', 'red')
                                    ctlwiz.click_close_button(driver, limit_time=0.05, args=(f'action_choices:{action_choices}', f'action_choices:{player_action}', f'bet_rate:{bet_rate}', f'Call_cost:{Call_cost}', f'player_position:{player_position}', f'game_phase:{game_phase}'))
                        cprint(f'Bet額が小さかったので、"{wizard_action}"に補正しました', "yellow", attrs=["bold"], file=sys.stderr)
                        previous_player_small_bet = True
                        if check_between_Bet is False:
                            return selected_Allin, previous_player_small_bet, new_E_player, wizard_Raise_list, wizard_action
                        else:
                            near_actions.append(wizard_action)
                            break
                # 選択すべきアクションを探す
                elif most_close_rate_str in wizard_action:
                    # 要素が見つかったらクリック <- csvのときはクリックしない
                    if action_text_elements:
                        # loader_spinnerが消えていて、フロップ入力画面になっていれば閉じる
                        #* クリックできるまで処理を繰り返すことにした
                        while True:
                            try:
                                action_text_elements[action_index].click()
                                break
                            except:
                                big_print('アクションを入力できませんでした。ctlwiz.click_close_button を実行します(3)', 'red')
                                ctlwiz.click_close_button(driver, limit_time=0.05, args=(f'action_choices:{action_choices}', f'action_choices:{player_action}', f'bet_rate:{bet_rate}', f'Call_cost:{Call_cost}', f'player_position:{player_position}', f'game_phase:{game_phase}'))
                    if repeat_count >= 1:
                        cprint(f'クリックしたアクションを"{player_action}"に補正しました', "yellow", attrs=["bold"], file=sys.stderr)
                    # Allinを選択した場合、Trueを返す
                    if 'Allin' in wizard_action:
                        # Allinしていないのに、Bet額が大きくて、Allinが選ばれた時
                        if Allin_flag is False:
                            cprint(f'Bet額が大きいので"Allin"に補正しました', "yellow", attrs=["bold"], file=sys.stderr)
                        selected_Allin = True
                    # wizard_Raise_list を更新する <- original_action_choices から、元のRaiseの額を取り出して、BB数のみ入れる
                    if game_phase == 'preflop':
                        action_value = convert_number(delete_non_numbers(action_choices[action_index], print_text=False)) #! <- 本来は original_action_choices を使う
                        # Raise_listの更新は、base(つまり一周目)のみ行う。
                        if len(previous_small_bet_list) == 0:
                            wizard_Raise_list.append(action_value)
                    if check_between_Bet is False:
                        return selected_Allin, previous_player_small_bet, new_E_player, wizard_Raise_list, wizard_action
                    else:
                        near_actions.append(wizard_action)
                        break
            # 一周目のbaseのアクションのみ、状況を入れて返す
            if base_selected_Allin is None:
                base_selected_Allin = selected_Allin
            previous_small_bet_list.append(previous_player_small_bet)

        # ここまで来るときは、中間サイズBetを確認するときのみのはず
        return base_selected_Allin, previous_small_bet_list, new_E_player, wizard_Raise_list, [near_actions,[rate1,rate2]]

def check_close_action(game_phase, selected_actions, Call_cost, bet_rate, check_between_Bet, dont_click_small_bet=False, Allin_minirate=None):
    """
    best_selectの中で、最も近いアクションを探すときのコードを別でまとめた
    - Args:
        - Allin_minirate: 0.7とすれば、差が3:7でAllinが近くないと、Allinを選ばなくなる
    """

    # 順にRaiseのBet割合を出して最もscreenから読み取ったBetの割合に近いものを探す
    most_close_rate = None
    most_close_rate2 = None
    most_close_rate3 = None # AllinよりもCallのほうが近くて調整できなかったときがある
    rate1 = None
    rate2 = None
    Allin_rate = None # Allinのrateが入る
    for key, wizard_action in selected_actions.items():

        # Checkのときは、0として進める
        if 'Check' in wizard_action:
            if dont_click_small_bet: # 最も近いbetの選択肢から、check,Callを外す
                continue
            wizard_rate = 0
        # Callのときは、Callするのに必要な額とする(プリフロップ) <- フロップ以降はCallは Raise0% なので、0で良い
        elif 'Call' in wizard_action:
            if dont_click_small_bet: # 最も近いbetの選択肢から、check,Callを外す
                continue
            wizard_rate = 0
            if game_phase == 'preflop': #! 戻した
                wizard_rate = Call_cost #! 戻した
        # 通常時の処理
        else:
            # wizard_rate = wizard_action.split(' ')[1] #! Raiseの大きさとかのみを取り出すために使っていた処理。delete_non_numbers さえ行えば行けるはずなので削除した。これでcsvにも対応できるはず。
            # % が含まれている場合もあるので補正する
            wizard_rate = delete_non_numbers(wizard_action, print_text=False) #! <- wizard_rate を wizard_action に変更した
            if Allin_minirate and 'Allin' in wizard_action:
                Allin_rate = wizard_rate

        # screenから読み取ったBetの割合に最も近いものを探す
        if most_close_rate is None:
            most_close_rate = wizard_rate
        elif abs(most_close_rate - bet_rate) > abs(wizard_rate - bet_rate):
            # 2つ探すとき
            if check_between_Bet:
                most_close_rate2 = most_close_rate
            most_close_rate = wizard_rate
        # 2,3つ目探すとき
        elif check_between_Bet:
            if most_close_rate2 is None:
                most_close_rate2 = wizard_rate
            elif abs(most_close_rate2 - bet_rate) > abs(wizard_rate - bet_rate):
                most_close_rate2 = wizard_rate
            elif most_close_rate3 is None:
                most_close_rate3 = wizard_rate
            elif abs(most_close_rate3 - bet_rate) > abs(wizard_rate - bet_rate):
                most_close_rate3 = wizard_rate

    # most_close_rateが少数ならintにしてからstringにする -> 5.0 を 5 にする 2.5 は 2.5 のままにする
    most_close_rate_str = str(convert_number(most_close_rate))
    close_rate_list = [most_close_rate_str]
    # wizardのアクションの中から選べるようにCallをconvertする
    Call_cost = str(convert_number(Call_cost))

    # 選ばれた2つの割合を計算する -> 差がありすぎるときはいつも通りに変更する
    if check_between_Bet:
        # 使用する2つを選ぶ
        # bet_rate は rate と rate2 の間にあるか <- 0 になるのがあるとき、全く同じことになるからパス
        if (most_close_rate2 is not None and
            ((bet_rate - most_close_rate > 0 and bet_rate - most_close_rate2 < 0) or
            (bet_rate - most_close_rate < 0 and bet_rate - most_close_rate2 > 0))):
            most_close_rate_No2 = most_close_rate2
        elif (most_close_rate3 is not None and
            ((bet_rate - most_close_rate > 0 and bet_rate - most_close_rate3 < 0) or
            (bet_rate - most_close_rate < 0 and bet_rate - most_close_rate3 > 0))):
            most_close_rate_No2 = most_close_rate3
        else:
            check_between_Bet = False

        if check_between_Bet:
            diffirent1 = abs(bet_rate - most_close_rate)
            diffirent2 = abs(bet_rate - most_close_rate_No2)
            rate1 = round(diffirent2 / (diffirent1+diffirent2) , 3)
            rate2 = round(diffirent1 / (diffirent1+diffirent2) , 3)

            # 差がありすぎる場合、通常のreturnとする
            # if 0.1 > rate2:
            #     check_between_Bet = False
            # else:
            #! ↑の処理は、後で行うことにする。片方がnext_phaseなら差があっても考慮する
            # 分岐するとき、リストに追加する
            most_close_rate_No2_str = str(convert_number(most_close_rate_No2))
            close_rate_list.append(most_close_rate_No2_str)
            # # 一つしか選択肢がないかどうかの確認 <- でかいAllinのとき、その下のRaiseは無視する。どっちの選択肢よりも小さいという状況はないはずなので確認は行わない(Callよりも小さいBetをしてることになる)
            # else:
            #     if (bet_rate - most_close_rate >= 0 and bet_rate - most_close_rate2 >= 0):
            #         check_between_Bet = False

            # Allinがリストに入ってるとき、条件に合わなければデータを減らす
            if Allin_rate and str(convert_number(Allin_rate)) in close_rate_list:
                # 最も近いのがAllinのとき
                if str(convert_number(Allin_rate)) == close_rate_list[0]:
                    # 指定よりもAllinの比率が低いとき
                    if rate1 <= Allin_minirate:
                        rate1 = None
                        rate2 = None
                        del close_rate_list[0]
                        big_print(f'Allinが指定の比率{Allin_minirate}よりも小さかったのでbestselectから削除しました', 'on_red')

    return close_rate_list, Call_cost, rate1, rate2

def select_flopcards(driver, cards, game_phase):
    """
    フロップの入力をする。
    見つからなかったら、ボード選択が表示されているか確認する。<- これもなかったら、フロップ入力ボタンをクリックする機能を追加した
    """
    # 処理を追加
    WebDriverWait(driver, 30).until_not(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-tst='loader_spinner']"))
    )

    # 待ち時間を追加
    if game_phase != 'flop':
        time.sleep(0.1)

    continue_select = True

    while continue_select:
        for card in cards:
            find_selectboardbtn = 0
            while True:
                try:
                    flopcard = WebDriverWait(driver, 0.1).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-tst="cards_dialog_available_{card}"]'))
                            )
                    break
                except:
                    try:
                        element = WebDriverWait(driver, 0.1).until(
                            EC.element_to_be_clickable((By.ID, 'selectboardbtn'))
                        )
                        # 一回目の'selectboardbtn'を見つけたときは、クリックせずにパスする <- 0.3s待機するし、多分大丈夫
                        if find_selectboardbtn == 0:
                            find_selectboardbtn += 1
                            time.sleep(0.3)
                            continue
                        # ２回目'selectboardbtn'を見つけたらクリックする
                        element.click()
                    except:
                        try:
                            #* フロップ入力ボタンを探す
                            # XPathを使用して、data-tst 属性に "hs_flop_" を含む要素を探す
                            xpath_expression = f'//*[@data-tst[contains(., "hs_{game_phase}_")]]'

                            # 要素が見つかるまで最大0.1秒待ち、要素をクリック
                            element = WebDriverWait(driver, 0.1).until(
                                EC.element_to_be_clickable((By.XPATH, xpath_expression))
                            )

                            # 要素をクリック
                            element.click()
                        except:
                            find_selectboardbtn = 0

            # 要素をクリック
            flopcard.click()
            clicked_card = colored(f' {card} ', "white", attrs=["reverse", "blink"])
            print(f'{clicked_card}', end=' ', flush=True)

        # 入力が終わったことを確認する
        """
        okと判断する条件は下記のどちらか
        ・loader_spinner がでている
        ・ボード選択が表示されていない
        """
        try:
            # loader_spinnerが表示されているか -> されてたらok
            loader = driver.find_element(By.CSS_SELECTOR, "div[data-tst='loader_spinner']")
            # 表示されているか確認
            if loader.is_displayed():
                continue_select = False
        except:
            try:
                # ボード選択の表示の確認 -> 表示されてたら繰り返す
                element = WebDriverWait(driver, 0.1).until(
                    EC.element_to_be_clickable((By.ID, 'selectboardbtn'))
                )
                element.click()
            except:
                continue_select = False

    return

