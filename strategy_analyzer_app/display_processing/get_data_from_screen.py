
import sys
from termcolor import colored, cprint
import time
import os
import json
import cv2
import shutil
import csv
from datetime import datetime

import pandas as pd

import strategy_analyzer_app.image_processing.image_handling as imghdr
import strategy_analyzer_app.global_vars as glbvar


def trim_screenshot_from_big(x_start, x_end, y_start, y_end, original_img_range=None, original_img_path='screenshot_temp.jpg', name='trimmed_original_img.jpg', resize=2):
    """
    gen2の全体スクショの指定の範囲をトリミングして保存する
    TODO 保存せず、トリムしたデータをそのままマッチングに持っていく方法はないか調べる
    """

    # 全体スクショの始まりを取り出す
    if original_img_range is None:
        pass
    # 辞書の指定があるとき
    else:
        scr_x_start = original_img_range['x_start']
        scr_y_start = original_img_range['y_start']


    # 切り取りたいスクショの範囲を計算して求める
    tri_left = x_start - scr_x_start
    tri_right = x_end - scr_x_start
    tri_top = y_start - scr_y_start
    tri_bottom = y_end - scr_y_start

    # トリミングして終了
    imghdr.trim_image_save(original_img_path, tri_left, tri_right, tri_top, tri_bottom, name=name, resize=resize)

def trim_and_match_with_big_screenshot(x_start, x_end, y_start, y_end, template_link, threshold, original_img_range=None,
                                        original_img_path='screenshot_temp.jpg', name='trimmed_original_img.jpg', *, resize=2) -> bool:
    """
    指定の範囲を切り取り、指定のテンプレートとマッチさせ、しきい値以上ならTrueを返す
    """
    # トリミングする -> 'trimmed_original_img.jpg'
    trim_screenshot_from_big(x_start, x_end, y_start, y_end, original_img_range, original_img_path, name, resize)

    result = match_template_and_check_maxval(template_link, threshold, base_img=name)
    return result

def match_template_and_check_maxval(template_link, threshold, base_img='trimmed_original_img.jpg') -> bool:
    """
    テンプレートimgと指定された画像をマッチさせて、しきい値以上かどうか調べる
    """
    # トリミングしたスクショとテンプレートをマッチさせる
    match_result = imghdr.get_match_result(template_link, base_img)
    max_val = imghdr.get_max_val_from_matchresult(match_result)

    # しきい値を超えているか確認する
    if max_val >= threshold:
        return True
    else:
        return False

