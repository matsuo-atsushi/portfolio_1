

def fix_action(action):
    """
    action_reportの内容をbet数やAllinなど、今までのものに変換するための処理
    [返り値]
    数字はfloatで返す
    FoldはFoldのまま
    """
    # bet数に変換する
    index = str(action).find('(')
    if index != -1:
        find_bet = float(action[:index])
    else:
        find_bet = action  # '('がない場合は元の文字列を返す

    return find_bet


