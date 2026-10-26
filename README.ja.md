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

## モデルの評価

ワークショップの後に、最終モデルを評価します。評価は `workshop-model.json` のスキーマ（T-box）を読み取り、データベースへの接続やモデルの変更は行いません。結果はモデルと同じフォルダーの `graph-evaluation-report.html` に保存され、報告書は韓国語で作成されます。

ローカル AI で `/ontoforge-evaluation` を使うか、最終のグラフ評価を依頼します。Claude Code ではモデルのパスを渡せます。例: `/ontoforge-evaluation path/to/workshop-model.json`。ワークショップの外でも、グラフスキーマの評価や比較を依頼すれば同じスキルが動きます。エクスポートと成果物の確認が終わった最後に実行し、モデルを変更したら再実行します。

報告書の内容です。

- 構造の点検: 関係の制約、重複したり一つの名前が複数の意味で使われたりしている関係、同じ事実の二重表現、名前や列挙型の不一致
- 定量指標: 属性の豊富さ、型の階層がある場合の関係の豊富さと継承の豊富さ、ドメイン情報を持たない関係の割合など
- 意味の検討: ラベルの意味、状態や識別子をノードにするか属性にするか、不足している中間分類
- 質問との対応: 回答できなかったゴールデン質問を原因別に分ける方法、質問候補をスキーマで表現できるかの静的な確認
- 改善提案、グラフ DB の検討事項、データや顧客の確認が必要な未解決事項

参考資料は原文を直接開いて確認した論文だけを載せ、確認できなかった項目は未確認と表示します。等級と重大度は評価者の判断です。

構成は次のとおりです。

- 手順、報告書の構成、スタイルは `.claude/skills/graph-evaluation/SKILL.md` にあります。コマンドファイル `.claude/commands/ontoforge-evaluation.md` と Kiro のステアリング `.kiro/steering/ontoforge-evaluation.md` は、このファイルを指す入口です。
- `schema_metrics.py` はスキーマ指標を計算します。ラベル名はモデルごとに異なるため、モデルの汎用ラベルとハブを決めて `--generic`、`--hubs` で渡します。
- `evaluate.py` は任意の静的チェックです。別ファイル `graph-evaluation-static-check.html` を作り、報告書の代わりにはなりません。

```bash
python3 .claude/skills/graph-evaluation/schema_metrics.py path/to/workshop-model.json \
  --generic <汎用ラベル> --hubs <ハブラベル>
```

## 関連文書

- [ローカルワークショップ](./docs/LOCAL_WORKSHOP.md)
- [Ontology Discovery ワークフロー](./docs/ONTOLOGY_DISCOVERY.md)
- [モデル形式と Cypher エクスポート](./viz-server/README.md)
- [ワークショップの手順](./docs/AI_ODLC_WORKFLOW.md)
- [アプリケーションの構成](./docs/DESIGN.md)
- [ワークショップスキル](./skills/WORKSHOP_SKILLS.md)
- [グラフ評価スキル](./.claude/skills/graph-evaluation/SKILL.md)
- [セキュリティ](./SECURITY.md)
- [貢献方法](./CONTRIBUTING.md)
