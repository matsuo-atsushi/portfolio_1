"""
複雑な処理がない、シンプルにwizardを操作するコードが記載されている
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

import undetected_chromedriver as uc

from termcolor import colored, cprint
import pyautogui

import time
import random
import sys
import csv
import os
import gzip
import json
import traceback

from strategy_analyzer_app.io_operations.print_processing import big_print, suppress_print
import strategy_analyzer_app.global_vars as glbvar
import strategy_analyzer_app.io_operations.csv_processing as csvproce

def start_uc_driver(*, use_performance_log=False):
    """
    undetected_chromedriverで、driverを用意する
    - use_performance_log:
        performance_log を取得したいとき、Trueにする
    """
    # Performanceログを有効にする設定
    if use_performance_log:
        caps = DesiredCapabilities.CHROME
        caps['goog:loggingPrefs'] = {'performance': 'ALL'}

    # chromeを立ち上げる
    chrome_options = uc.ChromeOptions()

    # 最新の ChromeDriver を自動ダウンロード＆使用
    service = Service(ChromeDriverManager().install())

    if use_performance_log:
        driver = uc.Chrome(service=service, options=chrome_options, desired_capabilities=caps)
    else:
        driver = uc.Chrome(service=service, options=chrome_options)

    # DevTools Protocolを有効にする
    if use_performance_log:
        driver.execute_cdp_cmd('Network.enable', {})

    version = driver.capabilities['browserVersion']
    print(f"現在のChromeのバージョン: {version}")

    return driver

def login_wizard_with_google(driver):
    """
    wizardにログインするための処理。このコードを消してはいけない
    .uc を使って、googleでログインするように変更した
    """
    while True:
        try:
            # 動作確認のためにGoogleを開く
            driver.get("https://app.gtowizard.com/login")

            # 現在のURLが指定文字列を含むまで待機
            start_time = time.time()
            limit_time = 300 # 10sまで待機する
            loading_time = 0
            error_count = 0
            print('wizardが読み込まれるまで待機します(5分間)')
            while loading_time < limit_time:
                try:
                    WebDriverWait(driver, 3).until(
                        lambda d: "https://app.gtowizard.com/solutions" in d.current_url)
                    print("指定のURLを含むページが読み込まれました。")
                    return
                except:
                    # ページ全体のテキストを取得
                    page_text = driver.find_element(By.TAG_NAME, "body").text

                    # 特定のテキストが含まれるか判定
                    if 'エラーが発生しました。もう一度お試しください。' in page_text:
                        if error_count == 0:
                            error_count += 1
                            continue
                        print("エラーが表示されています。")
                        raise
                    end_time = time.time()
                    loading_time = round(end_time - start_time , 1)
                    if loading_time >= limit_time:
                        print('読み込みエラーが発生していると思うので、はじめからやり直します')
                        raise

                    print(f'経過時間 : "{loading_time}s"', end=', ', flush=True)
        except:
            try:
                WebDriverWait(driver, 1).until(
                    lambda d: "https://app.gtowizard.com/solutions" in d.current_url)
                print("指定のURLを含むページが読み込まれました。")
                return
            except:
                big_print('エラーが発生したのではじめからやり直します', 'on_red')

def setting_wizard_situation(driver, *, solution='cash', type='regular', player='6max', spot='all_spots', stack='100', rake='NL50', bet_size='general', open_size='gto', strategy_menu='strategy'):
    """
    data-tst="chrow_cash",
    data-tst="chrow_regular",
    data-tst="chrow_6max",
    data-tst="chrow_all_spots",
    data-tst="chrow_200",
    data-tst="chrow_NL50",
    data-tst="chrow_gto",
    data-tst="chrow_general"
    """

    # 設定が表示されるのを待機
    wait = WebDriverWait(driver, 10)  # 最大10秒待機
    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-tst="gmf_selector_opener"]')))

    # 設定をクリック
    element = driver.find_element(By.CSS_SELECTOR, '[data-tst="gmf_selector_opener"]').click()

    # 設定画面が表示されるのを待機
    wait = WebDriverWait(driver, 10)  # 最大10秒待機
    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-tst="chrow_cash"]')))

    # solutionをクリック
    element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="chrow_{solution}"]').click()
    time.sleep(0.5)

    # typeをクリック
    element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="chrow_{type}"]').click()
    time.sleep(0.1)

    # playerをクリック
    element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="chrow_{player}"]').click()
    time.sleep(0.1)

    # spotをクリック
    element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="chrow_{spot}"]').click()
    time.sleep(0.5)

    # stackをクリック
    element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="chrow_{stack}"]').click()
    time.sleep(0.5)

    # rakeをクリック
    element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="chrow_{rake}"]').click()
    time.sleep(0.5)

    # bet_sizeをクリック
    element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="chrow_{bet_size}"]').click()
    time.sleep(0.5)

    # data-tst="gmf_selector_opener" を持つ要素をすべて取得
    elements = driver.find_elements(By.CSS_SELECTOR, f'[data-tst="chrow_{open_size}"]')
    for element in elements:
        # 各要素をクリック
        try:
            # 要素が表示されるまで待機
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'[data-tst="chrow_{open_size}"]')))

            # 要素をクリック
            ActionChains(driver).move_to_element(element).click().perform()
            time.sleep(0.1)
        except Exception as e:
            print(f"クリック中にエラーが発生しました: {e}")

    # 設定をクリック
    element = driver.find_element(By.CSS_SELECTOR, '[data-tst="gmf_selector_opener"]').click()

    #* 表の表示を変更
    element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="stramenu_opener"]').click()   # data-tst="stramenu_opener"
    time.sleep(0.1)
    element = driver.find_element(By.CSS_SELECTOR, f'[data-tst="strabtn_{strategy_menu}"]').click()   # data-tst="strabtn_strategy", data-tst="strabtn_strategy_ev"

    # loader_spinnerが消えるまで待機する
    #! loader_spinnerの存在が消えるまで待機する <- エラーのとき、これが表示されていることは無いと思う 
    WebDriverWait(driver, 30).until_not(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-tst='loader_spinner']")))

def get_new_logs(driver):
    """
    これまでに取得したログを保存するリストを作成しながら、新しく読み込まれたlogのみを取り出す
    """
    current_logs = driver.get_log("performance")  # 現在のログを取得

    # 差分を取る（すでに取得済みのログを除外）
    new_logs = [log for log in current_logs if log not in glbvar.all_logs]

    # 新しいログを保存リストに追加
    glbvar.all_logs.extend(new_logs)

    return new_logs

def wait_for_vanish_loaderspinner_with_var(driver, limit=30):
    """
    loaderspinnerが消えるのを待つ。そして、その間、特定の変数を監視する。
    - Args:
        - limit: 最大の待機時間
    """
    # loader_spinnerの存在が消えるまで待機する
    # print('loaderspinnerが消えるまで待機します')
    total_time = 0
    while total_time < limit:
        try:
            WebDriverWait(driver, 0.1).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-tst='loader_spinner']")))
            return True
        except:
            total_time += 0.1
            if glbvar.quit_save_log:
                return False

def save_postflop_solution(driver, position, performance_log_path, gto_stack, dont_save=False):
    """
    postflopのsolutionデータをgzで保存する
    - Args:
        - dont_save: Trueのとき、logを保存せずにjsonデータをそのまま返す
    """

    # loader_spinnerの存在が消えるまで待機する
    ok = wait_for_vanish_loaderspinner_with_var(driver, limit=30)
    if ok is False:
        return False

    #* Performanceログを取得して解析 <- 最新のlogだけにする
    logs = get_new_logs(driver)

    # ログは後ろから取り出す処理に変更
    times = 1
    acquired_data = False # 探すべきデータをみつけたときにTrueになる
    # export_data が用意できたら、whileを抜ける
    while times <= len(logs) and acquired_data is False:
        entry = logs[-times]
        log = json.loads(entry['message'])['message']
        if log['method'] == 'Network.responseReceived':
            response_url = log['params']['response']['url']

            if 'solution/?' in response_url:
                request_id = log['params']['requestId']
                try:
                    # レスポンスボディを取得
                    response_body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                    # 'body' を取得
                    body = response_body['body']
                    # JSON 文字列を辞書に変換
                    data = json.loads(body)
                    # "simple_hand_counters" の内容を取り出す <- 後ろから取り出す処理に変更
                    i = 0
                    while i < len(data['players_info']):
                        i += 1
                        player_info = data['players_info'][-i]['player']
                        simple_hand_counters = data['players_info'][-i]['simple_hand_counters']

                        #* 読み取るべきデータかどうか判別する
                        # ポジションが異なるとき、パス
                        if position != player_info['position'] or player_info['is_active'] is False or abs(gto_stack - float(player_info['current_stack'])) > 0.1:
                            print(f'player_info : {player_info}')
                            cprint(f'ポジションが異なるので、次のデータを確認します。(現在:"{position}", log:"{player_info["position"]}")', "red", attrs=["bold"], file=sys.stderr)
                            continue
                        # simple_hand_counters に空のデータが無いか一度だけ確認する
                        else:
                            include_empty_data = False
                            for details in simple_hand_counters.values():
                                if details:
                                    break
                                else:
                                    include_empty_data = True
                                    break
                            # 空のデータだったら、次のデータに行く
                            if include_empty_data:
                                print(f'simple_hand_counters : {simple_hand_counters}')
                                cprint(f'データが空なので、次のデータを確認します', "red", attrs=["bold"], file=sys.stderr)
                                continue

                        cprint(f'performance log の中身を確認しました。問題無いと思います。', "yellow", attrs=["bold"], file=sys.stderr)
                        acquired_data = True

                        # logを保存せずにそのまま返すとき
                        if dont_save:
                            return data

                        #! performance log を保存する
                        # ディレクトリを用意
                        parent_dir = os.path.dirname(performance_log_path)
                        if not os.path.exists(parent_dir):
                            os.makedirs(parent_dir)

                        #* JSONを圧縮して保存
                        #// path_for_save = os.path.join(directory_path, f'{performance_log_name}.json.gz')
                        with gzip.open(performance_log_path, "wt", encoding="utf-8") as file:
                            json.dump(data, file)
                        print(f'gzを保存しました -> {performance_log_path}')
                        return

                        # #* zstdで保存
                        # basename = os.path.splitext(os.path.basename(performance_log_path))[0]
                        # zstd_save_path = os.path.join(parent_dir, f'{basename}.zst')
                        # csvproce.save_zstd(zstd_save_path, data)

                        # zt_data = csvproce.read_data(zstd_save_path, file_type='json-zstd')

                        break
                except Exception as e:
                    traceback.print_exc()
        times += 1
    big_print('gzを保存できなかったようです', 'on_red')

def click_close_button(driver, limit_time=30, args=()):
    """
    まず、loader_spinerの表示がないことを確認して、
    フロップを入力する画面になっていたら、X ボタンをクリックする
    """

    #! loader_spinnerの存在が消えるまで待機する
    try:
        WebDriverWait(driver, limit_time).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-tst='loader_spinner']"))
        )
    except:
        if args:
            pass
        return

    try:
        # CSSセレクタを使って要素をクリック
        close_button = driver.find_element(By.CSS_SELECTOR, '[data-tst="dialog_cards-dialog_close"]')
        close_button.click()
        # 一応、0.01s待機する
        print('wizardの X ボタンをクリックしました')
        time.sleep(0.01)
    except:
        pass
    return

#!!!
def check_204_error(driver):
    """
    相手がGTOにない行動をしてきたとき、自分のターンは、204error(このスポットにはソリューションがありません)がでてないか確認する
    でてたら、別の処理が動いて、相手のアクションをGTOに存在するアクションに変更する
    """
    #! loader_spinnerの存在が消えるまで待機する
    WebDriverWait(driver, 30).until_not(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-tst='loader_spinner']")))

    # 204errorの存在確認
    error_elements = driver.find_elements(By.CSS_SELECTOR, '[data-tst="204"]')
    # 別のエラー確認
    error_loading_solution_elements = driver.find_elements("css selector", "[data-tst='error_loading_solution']")

    # 存在するかの判定
    if len(error_elements) > 0 or len(error_loading_solution_elements) > 0:
        big_print(" 204-Errorが存在します ", 'on_red')
        return True
    else:
        big_print("204-Errorは存在しません", 'white')
        return False

def check_moved_to_wizard(driver, decrease_scale):
    """
    wizardのurlにアクセスできたことを確認するための関数
    ページの倍率も変更する <- 回数で指定
    """
    while True:
        try:
            # 現在のURLを取得
            current_url = driver.current_url
            # URLに指定の文字列が含まれているか確認
            if "https://app.gtowizard.com/" in current_url:
                break
            else:
                raise
        except:
            pass

    # windowを手前にする
    driver.switch_to.window(driver.current_window_handle)
    time.sleep(0.3)

    pyautogui.FAILSAFE = False
    while True:
        try:
            i = 0
            while i < decrease_scale:
                pyautogui.keyDown('command')  # Macの場合
                pyautogui.press('-')
                pyautogui.keyUp('command')
                i += 1
            break
        except:
            big_print('サイトの表示を縮小するときにエラーが発生しました。5秒待機します', 'yellow')
            time.sleep(5)
    pyautogui.FAILSAFE = True

def setup_chrome_driver(q1, small=3):
    #* ブラウザを立ち上げる準備
    driver = start_uc_driver(use_performance_log=True)

    # wizardにログインする
    login_wizard_with_google(driver)

    # wizardの設定をする できるまで繰り返す
    while True:
        try:
            check_moved_to_wizard(driver, decrease_scale=small)
            setting_wizard_situation(driver, stack=100)
            break
        except:
            pass

    return driver
