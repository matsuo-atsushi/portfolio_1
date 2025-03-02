

import pytesseract
from PIL import Image
import cv2
import os

from strategy_analyzer_app.io_operations.print_processing import big_print

def trim_image_save(base_img_link, x_start, x_end, y_start, y_end, name='trimmed_original_img.jpg', resize=2):
    """
    TODO
    240618_メモ
    デバック用にスクショをトリミングしてるけど、saveせずにそのままテキスト抽出できる
    いずれ、動作を早くするために、saveは消していいと思う。
    250104
    スクショをトリムするときに、座標を2倍している理由は、保存するときに画像を2倍にリサイズしてから保存してるから。
    多分、2倍にしないと、macでスクショした画像とスクショが、テンプレートマッチできなかったからだと思う。
    """
    base_img = cv2.imread(base_img_link)

    trimmed_img = base_img[int(y_start)*resize : int(y_end)*resize, int(x_start)*resize: int(x_end)*resize] # img[top : bottom, left : right]
    cv2.imwrite(name, trimmed_img)
    return trimmed_img

def trim_image_without_resize(base_img_link, x_start, x_end, y_start, y_end, name='trimmed_original_img.jpg', *, binary=False):
    """
    リサイズ無しでトリムする。
    スクショをトリムするなら、リサイズが必要だけど、それ以外の画像ならリサイズは不要
    """
    base_img = cv2.imread(base_img_link)

    trimmed_img = base_img[y_start : y_end, x_start: x_end] # img[top : bottom, left : right]

    # 画像を2値化するとき
    if binary:
        temp_img_gray = cv2.cvtColor(trimmed_img, cv2.COLOR_BGR2GRAY)
        ret, trimmed_img = cv2.threshold(temp_img_gray, 0, 255, cv2.THRESH_OTSU)

    cv2.imwrite(name, trimmed_img)
    return trimmed_img

def trim_image_left_of_template(image_a_path, image_b_path, output_path, threshold=0.8):
    """
    画像をmatchtemplateして、存在するとき、左側のみトリムする
    """
    # 画像を読み込む
    image_a = cv2.imread(image_a_path)
    image_b = cv2.imread(image_b_path)

    if image_a is None or image_b is None:
        raise FileNotFoundError("画像Aまたは画像Bが見つかりません")

    # テンプレートマッチングを実行
    result = cv2.matchTemplate(image_a, image_b, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    print(f'BB match率: {round(max_val, 3):.3f}', end=', ')

    if max_val >= threshold:
        # 画像Bの左上隅の位置を取得
        top_left = max_loc

        # トリミング範囲を計算（画像Bの左側）
        x_end = top_left[0]  # 画像Bの左上隅のX座標
        trimmed_image = image_a[:, :x_end]

        # トリミング結果を保存
        cv2.imwrite(output_path, trimmed_image)
        return True
    big_print('画像がマッチしませんでした')
    return False

def image_to_text(image_path, *, oem=3, psm=6, digits,):
    # 画像を読み込む
    img = Image.open(image_path)

    try:
        text = pytesseract.image_to_string(img, lang='eng' , config=f'--oem {oem} --psm {psm}{digits}')
        ocr_data = pytesseract.image_to_data(img, lang='eng' , config=f'--oem {oem} --psm {psm}{digits}', output_type=pytesseract.Output.DATAFRAME)
    except:
        return '', 0

    # テキストと信頼スコアを取得
    text_with_scores = ocr_data[['text', 'conf']].dropna()  # 欠損値を削除
    text_with_scores = text_with_scores[text_with_scores['conf'] > 0]  # 無効な信頼スコア（-1）を除外

    # 結果を表示
    # print("認識されたテキストと信頼スコア:")

    try:
        # テキストだけを結合
        recognized_text = text_with_scores['text'].iloc[0]
        # print(recognized_text)  # 出力: 67.5

        # # 平均信頼スコアを計算
        average_confidence = text_with_scores['conf'].mean()
        # print(f"\n平均信頼スコア: {average_confidence}")

        max_confidence = text_with_scores['conf'].max()

        if max_confidence < 90:
            big_print(f'スコアが低いです max_confidence: {max_confidence}', 'red')
            print("認識されたテキストと信頼スコア:")
            print(text_with_scores)
            print(f'平均スコア: {average_confidence}')
            print(f'\n{ocr_data}')

        return recognized_text, max_confidence
    except:
        print(text_with_scores)
        return text, 0

def match_base_data(template_img_link, base_img = 'screenshot_temp.jpg', type = 'UNCHANGED'):
    """
    画像検索できるデータに変換する
    """
    if type == 'UNCHANGED':
        screen_conversion_img = cv2.imread(base_img, cv2.IMREAD_UNCHANGED)
        template_conversion_img = cv2.imread(template_img_link, cv2.IMREAD_UNCHANGED)
    elif type == 'IMREAD_GRAYSCALE':
        screen_conversion_img = cv2.imread(base_img, cv2.IMREAD_GRAYSCALE)
        template_conversion_img = cv2.imread(template_img_link, cv2.IMREAD_GRAYSCALE)
    return screen_conversion_img, template_conversion_img

def match_template_data(screen_conversion_img, template_conversion_img, type = ''):
    """
    matchさせる
    """
    if type == '':
        match_result = cv2.matchTemplate(screen_conversion_img, template_conversion_img, cv2.TM_CCOEFF_NORMED)
    # シンプルな画像のときは、TM_CCORR_NORMEDを使うことにする
    elif type == 'white_blank':
        match_result = cv2.matchTemplate(screen_conversion_img, template_conversion_img, cv2.TM_CCORR_NORMED)

    return match_result

def get_max_val_from_matchresult(match_result):
    min_val, max_val, min_loc, mac_loc = cv2.minMaxLoc(match_result)
    return max_val

def get_match_result(template_img_link, base_img = 'screenshot_temp.jpg'):
    """
    【メソッドまとめた】
    template_img_linkと、スクショからマッチさせる
    """
    screen_conversion_img, template_conversion_img = match_base_data(template_img_link, base_img = base_img)
    match_result = match_template_data(screen_conversion_img, template_conversion_img)
    return match_result

def convert_binary(img_link):
    """
    画像のリンクを受け取り、2値化したデータを返す
    そのデータはmatchに使える
    OCRにも使えるかもしれない
    """
    # 画像Aとテンプレート画像tを読み込む
    imread_img = cv2.imread(img_link, cv2.IMREAD_COLOR)

    # グレースケール変換
    imread_img = cv2.cvtColor(imread_img, cv2.COLOR_BGR2GRAY)

    # 2値化 (閾値127を使用して白黒に)
    _, img_binary = cv2.threshold(imread_img, 0, 255, cv2.THRESH_OTSU)

    return img_binary

def binary_for_small_number_img(image_path, output_path, *, scale=1, clean_noise=False, binary=False, reverse=False):
    """
    うまくOCRできない小さな画像をノイズ除去したり、リサイズしたり、二値化する
    - Args:
        - scale: もし、縦の大きさを2倍にしたいなら、√2 をscaleに渡す
    """
    # 画像の読み込み
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    # リサイズ処理（拡大）
    height, width = image.shape
    resized_image = cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_CUBIC)

    if binary is False and clean_noise is False:
        cv2.imwrite(output_path, resized_image)
        return

    # ノイズ除去（ぼかし）
    blurred = cv2.GaussianBlur(resized_image, (11, 11), 0)
    if clean_noise and binary is False:
        cv2.imwrite(output_path, blurred)
        return


    # 適応的二値化
    binary_image = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # 白黒反転
    if reverse:
        binary_image = cv2.bitwise_not(binary_image)

    # 保存する場合
    cv2.imwrite(output_path, binary_image)
    #// print(f"Binarized image saved to {output_path}")

def binary_for_small_number_img_gen2(image_path, output_path, *, scale=1, binary=True, reverse=False):
    """
    - Args:
        - scale: リサイズの倍率。高さを2倍したいなら√2を渡す
        - binary: 二値化したくないときは、Falseを渡す
        - reverse: Trueにすると、二値化した画像の白黒反転する
    """
    # 画像の読み込み
    image = cv2.imread(image_path)

    # 1. リサイズ
    width = int(image.shape[1] * scale)
    height = int(image.shape[0] * scale)
    resized_image = cv2.resize(image, (width, height), interpolation=cv2.INTER_CUBIC)

    # 2. グレースケール化
    if binary:
        gray_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2GRAY)
    else:
        gray_image = resized_image

    # 3. ノイズ除去
    if width >= 350: # 大きい画像は、11を使ってみる
        value = 11
    else:
        value = 5
    denoised_image = cv2.GaussianBlur(gray_image, (value, value), 0)

    # 4. 二値化
    if binary:
        _, binary_image = cv2.threshold(denoised_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if reverse:
            # 白黒反転（ビット反転）
            binary_image = cv2.bitwise_not(binary_image)
    else:
        binary_image = denoised_image


    # 保存する場合
    cv2.imwrite(output_path, binary_image)

def get_largest_image_number(directory_path, *, startswith):
    """
    指定されたディレクトリ内の画像ファイル名 'anlz_000004' の形式で
    最も大きい番号を取り出す。
    """
    max_number = -1
    for filename in os.listdir(directory_path):
        if filename.startswith(startswith):
            number_jpg = filename.split("_")[-1] # anlz_以降を取り出す
            if '(' in number_jpg:
                continue
            number = os.path.splitext(number_jpg)[0] # .jpgを除く
            max_number = max(max_number, int(number))
    return max_number

