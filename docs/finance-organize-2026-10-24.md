# 未来決算：画面整理とやること

未公開。公開基点は4157830。月末着地と既存利益計算は変更しない。

- ホームの経営指標から「やること N項目」、入力から未入力・未反映一覧へ。
- 昨日までの売上、公開シフトの出勤予定日の未入力勤務、片方だけの勤務時間、未保存月次費用、将来人件費の未反映、経費税区分を分類。対象日・名前・入力先を表示。
- 同じ種類はまとめて全対象を折り畳む。入力後の再表示で再判定。自動で記録を書き換えない。
- 売上0円の登録済み日・登録休業日、シフトの空欄・休み、仕入れがない日は入力漏れ扱いにしない。
- 設定を歯車に集約。予測条件・臨時休業日を移動。将来予測条件は専用設定画面へ。予測ページの月末詳細は折り畳み、グラフの補足はヘルプへ。
- 入力カードを2列に整理。設定変更の保存は既存データ構造を使用。

変更対象：core/finance_tasks.py、core/theme.py、pages/finance_tasks.py、pages/finance_settings.py、pages/finance_help.py、pages/finance_home.py、pages/future_financials.py、pages/finance_graphs.py、pages/landing_forecast.py、pages/wealth_forecast.py、pages/app_navigation.py、static/mirai-navy.css。テスト：test_finance_tasks.py、test_app_navigation.py。

検証：関連24テスト合格。テスト用データ・8119で360px幅のホーム、入力、やること、設定、予測、将来予測設定、グラフを表示。横はみ出し・JSエラーなし。やることの月次費用リンクが対象月へ遷移することを確認。実データ変更なし。CSSキーfinance-organize-20261024。
