# OntoForge

[English](./README.md) | [한국어](./README.ko.md) | [日本語](./README.ja.md)

OntoForge は、業務についての会話と既存の資料からグラフモデルを作るローカルのワークショップツールです。参加者は普段使っている AI アシスタントと対話し、ブラウザーでモデルを確認します。

## 進め方

AI は業務シナリオを質問し、回答からエンティティと関係を整理します。既存のスキーマやサンプルデータを参照しながら、参加者が確認した内容をモデルに反映します。

ブラウザーではグラフとワークショップの記録を確認します。ノードの属性を見て関係をたどり、業務上の質問に答えられるかを Cypher で調べます。

## 確認する内容

- T-box: エンティティ型、関係型、属性、識別子の定義
- A-box: 各型のインスタンスとその接続
- Cypher: 業務上の質問を表したクエリと実行結果
- 記録: 決定事項、資料の出典、未解決の質問、モデルの変更

Cypher は、プロパティグラフを検索、作成するための言語です。グラフモデルは型、属性、関係の定義です。この定義とインスタンスデータを分けて管理します。

## 成果物

ワークショップ後には、グラフモデル、決定の根拠、確認に使ったクエリが残ります。モデルは JSON、PNG、SVG で保存できます。Cypher はスキーマ、インスタンスデータ、モデル全体に分けて出力できます。

## 始め方

ローカルのレビュー画面をインストールし、動作を確認します。

```bash
python3 -m venv viz-server/.venv
viz-server/.venv/bin/python -m pip install -r viz-server/requirements.txt
bash scripts/test-viz.sh
bash scripts/serve.sh
```

出力された URL をブラウザーで開きます。通常は `http://127.0.0.1:5173` です。ローカル AI で `/onto-discover` を使い、モデルにしたい業務を説明します。モデルと回答は `ontology-docs/` に保存されます。

サンプルモデルと当日の起動手順は [ローカルワークショップ](./docs/LOCAL_WORKSHOP.md) を参照してください。

既存の API ワークショップと `$run-workshop` プラグインも残しています。サーバーが管理するセッションは、このファイルベースのワークフローとは別です。起動方法は同じ案内文書にあります。

## 関連文書

- [ローカルワークショップ](./docs/LOCAL_WORKSHOP.md)
- [Ontology Discovery ワークフロー](./docs/ONTOLOGY_DISCOVERY.md)
- [モデル形式と Cypher エクスポート](./viz-server/README.md)
- [ワークショップの手順](./docs/AI_ODLC_WORKFLOW.md)
- [アプリケーションの構成](./docs/DESIGN.md)
- [ワークショップスキル](./skills/WORKSHOP_SKILLS.md)
- [セキュリティ](./SECURITY.md)
- [貢献方法](./CONTRIBUTING.md)
