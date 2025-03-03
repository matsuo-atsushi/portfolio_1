# Strategy_Analyzer_demo-app
## 概要（Introduction）
本プログラムは、ゲームプレイヤーの行動履歴データを統計的・数学的に分析し、最適戦略モデル（GTO：Game Theory Optimal）と比較することで、プレイ傾向のズレを検出する分析ツールです。さらに、そのズレを活用し、対抗戦略（エクスプロイト）の指針を提供します。  
ゲーム理論に基づいた最適な意思決定モデルと実際のプレイを比較することで、戦略の改善点を明確にし、より合理的なプレイを支援します。

## 機能（Features）
- プレイ履歴(画像)の解析（OCR, 画像認識を用いたハンド履歴の読み取り）
- GTO戦略の収集（webスクレイピングによるGTOデータの取得）
- プレイヤーの意思決定分析（GTO戦略と比較し、傾向を可視化）
- 戦略の改善支援（意思決定の傾向を特定し、戦略の最適化を提案）

## 技術スタック（Tech Stack）
- 言語: Python 3.10.4
- ライブラリ: Selenium, pytesseract, OpenCV
- その他: numpy, pyautogui, termcolor

## ライブラリのインストール方法（Installation）
以下のコマンドを実行して、必要なライブラリをインストールしてください。
```bash
pip install -r requirements.txt

## プログラムの実行
```bash
python main.py

## 今後の改良点（Future Plans）
- 分析結果を視覚化するGUIの実装
