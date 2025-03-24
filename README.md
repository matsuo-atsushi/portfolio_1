# Strategy_Analyzer_demo_app
## 概要（Introduction）
本プログラムは、ゲームプレイヤーの行動履歴データの統計を取り、最適戦略（GTO：Game Theory Optimal）と比較することで、プレイ傾向の偏りを検出する分析ツールです。さらに、その偏りを活用し、対抗戦略（エクスプロイト）の指針を作成します。  
最適戦略モデルと実際のプレイを比較することで、戦略の改善点を明確にし、より合理的なプレイを補助します。

## 機能（Features）
- プレイ履歴(画像)の解析（OCR, 画像認識を用いたハンド履歴の読み取り）
- GTO戦略の収集（webスクレイピングによるGTOデータの取得）
- プレイヤーの意思決定分析（GTO戦略と比較し、傾向を可視化）
- 戦略の改善支援（意思決定の傾向を特定し、戦略の最適化を提案）

## 技術スタック（Tech Stack）
- 言語: Python 3.10.4
- ライブラリ: Selenium, pytesseract, OpenCV, Pandas
- その他: numpy, pyautogui, termcolor

## ライブラリのインストール方法（Installation）
以下のコマンドを実行して、必要なライブラリをインストールしてください。
```bash
pip install -r requirements.txt
```

## プログラムの実行（How to Run）
```bash
python main.py
```

## 紹介動画（Introduction Video）

<p align="center">
  <a href="https://www.youtube.com/watch?v=HYnHYDGULV8&ab_channel=matsuoatsushi" target="_blank" rel="noopener noreferrer">
    <img src="https://github.com/user-attachments/assets/b3a58cae-cbff-4eab-b943-010ac0629ce7" alt="説明動画">
  </a>
</p>

## 今後の改良点（Future Plans）
- 分析結果を視覚化するGUIの実装
- GTOデータをローカルで計算する処理の実装
