# 店舗管理：下部メニュー方式の再導入

2026-10-17、ユーザー希望で店舗管理のみ従来表示へ戻した。未来決算の下部メニューは維持。

## 保留した方式
- 固定の下部メニュー：ホーム／在庫／仕入れ／シフト／その他
- ホームの機能カードを「その他」へ移動
- ライブボードをカテゴリー選択式にして、選択したカテゴリーだけ表示
- 発注状況を折り畳み
- 仕入れ・発注の入口を専用ページに集約（仕入れリストの権限は維持）

再導入の意向あり。今回の復旧では、チェック時の画面更新抑制、引き継ぎチェック、未確認表示、個人ログイン、シフト関連の既存改善と保存データは変更しない。

## 再導入手順

リポジトリのルートで実行：

```sh
git apply --check docs/deferred/store-bottom-navigation.patch
git apply docs/deferred/store-bottom-navigation.patch
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest test_app_navigation test_live_board_groups test_store_ops
```

パッチは core/theme.py、pages/store_dashboard.py、pages/store_live_board.py の3ファイルのみを変更する。共通下部メニューの実装 pages/app_navigation.py は残してあるため再作成不要。

その後、スマホで各メニュー、カテゴリー切替、発注欄、スタッフと管理者の権限を確認し、ユーザーの公開指示に従って公開する。将来コードが変わりパッチ確認に失敗したら強制適用せず、上記仕様に沿って差分を取り込む。

元の導入コミット：9a2e5ae8751ab778e2089257014a1999d375db30
従来の店舗画面の基準：95f67d9
