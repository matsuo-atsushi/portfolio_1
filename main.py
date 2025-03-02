import strategy_analyzer_app.get_stradata.get_strategy_data_from_pic as getstra
import strategy_analyzer_app.get_stradata.convert_data_for_analyze_stradata as convstra
import strategy_analyzer_app.get_stradata.make_statistics_stradata as statidata

if __name__ == '__main__':
    # ハンド履歴(画像)からゲーム内容を読み込む
    getstra.main()

    # 各プレイヤーのgtoのsolutionを用意する
    convstra.main()

    # gtoとどれだけアクションが乖離しているか統計データをとり、エクスプロイト方針を立てる
    statidata.main()