# OntoForge — オントロジーディスカバリーワークショップツール

[English](./README.md) · [한국어](./README.ko.md) · **日本語**

顧客との**対話を通じてオントロジーをリアルタイムに作成・検証**するローカルツールです。合意したオントロジーはそのまま Amazon Neptune へ昇格（promote）して構成を活用し、データモデルを構築して今後のオントロジー構築に再利用できます。

## デモ

![OntoForge デモ](./images/demo.gif)

## 何をするか
1. 対話からエンティティ・関係・プロパティを構造化 → **Kùzu（組み込み型プロパティグラフ）** にリアルタイム反映
2. スキーマ（T-Box）／インスタンス（A-Box）を**リアルタイムグラフとして可視化**（Cytoscape.js）
3. 顧客の質問を **openCypher で検証** — 「この答えは本当にグラフから導かれているんですね」
4. オントロジードキュメント（Markdown、Obsidian 互換）を自動生成
5. **Neptune エクスポート**（openCypher スクリプト + Bulk Loader CSV）
6. **AI-ODLC ワークフロー**: 1-day AI-driven ontology discovery を claims, user stories, events, competency questions, data sources, mappings, validation query seeds, RDF decisions, risks, action items, gates として追跡
7. **RDF/SHACL 引継成果物**: Turtle ontology/instances, JSON-LD, SHACL seed shapes, SPARQL seed queries, RDF mapping notes, Neptune RDF follow-up notes
8. **限定された静的検証**: RDF/SPARQL/SHACL 引継成果物を要求時に1回検証し、自動監視は行わない

詳細な設計・セキュリティ制約・スコープは [`docs/DESIGN.md`](./docs/DESIGN.md) と
[`docs/THREAT_MODEL.md`](./docs/THREAT_MODEL.md)、[`docs/AI_ODLC_WORKFLOW.md`](./docs/AI_ODLC_WORKFLOW.md) を、対話スキルは
[`skills/WORKSHOP_SKILLS.md`](./skills/WORKSHOP_SKILLS.md) を参照してください。

### ワークショップ運用（M2）
- **白紙から開始**: 左上の `⟲ 白紙` ボタン → 新しい顧客対話を最初から積み上げる
- **編集モード**: サイドバーのエンティティ／関係チップをクリックすると削除（関連する関係も連鎖削除）。対話中の「模擬試験を追加したら？」のような変更がリアルタイムに反映される
- **AI-ODLC ブラウザ Cockpit**: Stories, Events, Questions, Model, Data, Review, Actions と条件別 gate failure を確認し、現在 stage の回答入力と claim/finding の confirm・reject・revise・resolve を行う。stage は次へだけ進み、強制進行には監査理由が必要。
- **Terminal Cockpit**: Textual TUI でも同じ server gate を使用し、7つの evidence panel、gate detail、回答・進行・強制進行、review decision、明示的な RDF 静的引継チェックを提供する。
- **敵対的レビュー**: cockpit または `/workflow/review` で ambiguity, contradiction, unsupported causality, event modeling, over-modeling, sensitivity を1回評価する。自動生成項目だけでは review gate は通過せず、high risk の accept には owner 付き action が必要。
- **RDF 引継**: `POST /export/rdf` または report export により、`exports/rdf/` または `exports/report/rdf/` に RDF/SHACL/SPARQL/Neptune RDF follow-up 成果物を生成する。
- **限定された検証ループ**: cockpit ボタンまたは `POST /workflow/validate` により、RDF/SPARQL/SHACL 引継成果物をユーザー操作で1回だけ静的検証する。最新結果1件だけを保持し、自動ポーリングや再試行は行わない。
- **最終 stage の証明**: 最終引継承認には隣接 stage の遷移履歴全体を通って `validation_handoff` に到達する必要がある。最終形の evidence や最終 stage label だけを直接注入しても完了せず、強制的な次 stage 移動には監査理由が必要。
- **ワークショップ引継成果物**: `📄 レポート` ボタン → `exports/report/` に生成
  1. ワークショップサマリー（エンティティ・関係・検証クエリ）
  2. AWS 構築アーキテクチャ提案（Neptune 規模の自動推定 + データフロー + コンプライアンス）
  3. データ準備状況（保有／未保有の分類、準備度 %）
  4. **技術ミーティング引継書** — 確定スキーマ、ロード用エクスポートの案内、データマッピングのアクション、検証ポイント、オープン課題
  - フォーマット: Markdown + HTML + PDF（weasyprint）+ docx（python-docx）
  - 引継バンドル: 同じフォルダに `neptune.cypher` + `bulk/*.csv` + `rdf/*` も併せて生成 → 技術チームにフォルダごと引き渡し

### クエリ実行対象
現在はローカル Kùzu グラフに対して openCypher を実行し、Cytoscape で結果を可視化します。成功したクエリは workflow validation query seed に verification evidence として記録されます。リモート Neptune へのライブクエリはスコープ外で、現時点ではエクスポートと handoff note のみを提供します。

workflow handoff evidence として認めるのは、question と正規化した openCypher の両方が保存済み high-priority competency-query seed に一致し、expected answer shape の各 label に MATCH で束縛された変数を一つの接続された関係 pattern から返し、実行時の query-evidence fingerprint が現在と同じ場合だけです。query fingerprint は RDF static-validation fingerprint と handoff package fingerprint から分離され、ある証拠の freshness が別の証拠を代替しません。ad-hoc、切断された Cartesian MATCH、変更前 model の成功クエリは handoff gate を開きません。

`POST /workflow/validate` は必須 RDF 成果物、JSON-LD 構造、読み取り専用 SPARQL seed 構文、SHACL と T-Box の構造的整合性のみを確認する。SPARQL 実行や正式な SHACL conformance 判定は行わない。結果は `validation_report.json` と `validation_report.md` に記録され、その後に関連入力が変わると再実行せず最新結果を `stale` と表示する。スケジューラ、ポーリング、バックグラウンド処理、自動再試行はない。

検証を実行した場合、最終 package manifest の RDF input fingerprint と検証時の fingerprint も一致する必要があります。そのため package 作成時に base IRI を変更すると、以前の pass はその bundle を承認しません。

## エージェントプラグイン Marketplace

このリポジトリ自体が `ontoforge-workshop` プラグインの marketplace です。
marketplace ファイルを含むブランチを checkout し、リポジトリルートで実行します。

```bash
# Codex と Claude Code をまとめてインストール
./scripts/install-agent-plugins.sh

# 個別にインストール
./scripts/install-codex-plugin.sh
./scripts/install-claude-plugin.sh
```

GitHub に marketplace ファイルが公開された後は、次のように直接インストールできます。

```bash
# Codex
codex plugin marketplace add aws-samples/sample-ontology-discovery-workshop --ref v2
codex plugin add ontoforge-workshop@ontoforge

# Claude Code
claude plugin marketplace add aws-samples/sample-ontology-discovery-workshop@v2 --scope user
claude plugin install ontoforge-workshop@ontoforge --scope user
```

インストール後は新しいセッションを開始し、Codex では `$run-workshop`、Claude Code
では `/ontoforge-workshop:start` を実行します。このプラグインは OntoForge
リポジトリ内で使うワークフローであり、Python アプリケーション自体はインストールしません。

## クイックスタート

### Windows (PowerShell)
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH="src"
uvicorn ontology_workshop.server:app --reload
# ブラウザ: http://localhost:8000
```
> weasyprint は Windows で GTK ランタイムが無いとインストール／実行が難しい場合があります。
> その場合は PDF のみ自動的にスキップされ（残り 3 フォーマットは正常に生成）、HTML レポートを
> ブラウザで「印刷 → PDF として保存」すれば対応できます。ツールがそのように案内します。

### macOS / Linux
```bash
pip install -r requirements.txt

# デモデータのシード + コンソール出力
PYTHONPATH=src python src/seed_demo.py

# ワークショップサーバー（リアルタイム可視化 + スキルパネル）
PYTHONPATH=src uvicorn ontology_workshop.server:app --reload
# ブラウザで http://localhost:8000
```

別の terminal で任意の terminal cockpit を起動できます。

```bash
PYTHONPATH=src python -m ontology_workshop.tui --url http://127.0.0.1:8000
```

認証が必要な場合は `ONTOFORGE_TOKEN` を設定するか `--token` を渡します。TUI は
live update 用 WebSocket 1接続と明示的な Refresh のみを使用し、polling、
自動再接続、review/validation の自動再実行は行いません。

### 永続化と復元
ワークショップデータはデフォルトで `workshop.kuzu` に保存されます。既存ワークショップを続ける場合は、`ONTOFORGE_FRESH=1` を付けずにサーバーを再起動してください。

```bash
PYTHONPATH=src uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
```

通常の再起動では、OntoForge は次のデータを再ロードします。

- グラフスキーマとインスタンスデータ: `workshop.kuzu`
- ワークショップフィードと検証済みクエリ: `exports/session/workshop_snapshot.json`
- Kùzu グラフが空の場合: autosave スナップショットの最新グラフ状態

グラフ、進行ログ、検証クエリ、インポート、リセット、レポートが変更されるたびに `exports/session/workshop_snapshot.json` に自動保存されます。そのため、多くの場合は上記の通常起動コマンドだけでワークショップを復元できます。

`ONTOFORGE_FRESH=1` は起動時にローカル Kùzu DB を削除したい場合のみ使用してください。誤って fresh 起動した場合でも、autosave ファイルが残っていれば `ONTOFORGE_FRESH=1` なしで再起動すると復元できます。

明示的に新しいワークショップを始める場合は、サーバーを通常起動した後に UI の reset ボタンを使うか、次を呼び出してください。

```bash
curl -X POST http://localhost:8000/reset
```

### 対話スキル（M1）
左パネルで顧客の回答を書き取り、スキルを実行すると、エンティティ・関係が自動的に
グラフ・可視化・ドキュメントへ反映されます。抽出経路は 2 通りです:
- `ANTHROPIC_API_KEY` 環境変数があれば **Claude API（Sonnet）** で抽出
- 無ければ**オフラインのルールベース抽出器**にフォールバック（現場デモの安定性のため）

外部 Claude API の利用は、顧客データの取り扱い・法務・セキュリティの承認がある場合のみ有効にします。
承認が無い場合や機微情報が含まれ得る場合は `ANTHROPIC_API_KEY` を設定せず、
オフライン抽出器で進めるか、後続の実装フェーズで Amazon Bedrock の承認済みモデル経路を使用してください。

オフライン抽出器のドメインカバレッジ: 教育 / メディア・エンターテインメント / ゲーム / スポーツ /
製造・ハイテク / テルコ / 自動車 / エンタープライズ（複合企業・系列会社モデルを含む）。
韓国語入力は英語の PascalCase エンティティ名（`학생→Student`、`차량→Vehicle` など）に
標準化されます。ドメインの追加は `src/ontology_workshop/skills.py` の `_ENTITY_HINTS` と
`_mock_relations` に 1 行ずつ追加します。

```bash
export ANTHROPIC_API_KEY=<approved-api-key>   # 任意: API 抽出を使用する場合
```

## アーキテクチャ
正式な構成図は [`docs/architecture.puml`](./docs/architecture.puml) にあり、
セキュリティ設計は [`docs/DESIGN.md`](./docs/DESIGN.md) と
[`docs/THREAT_MODEL.md`](./docs/THREAT_MODEL.md) にまとめられています。

```
対話（Claude + スキル） → オーケストレーター（FastAPI） → Kùzu（単一の信頼できる情報源、openCypher）
                                                      ├─ WebSocket → Cytoscape 可視化
                                                      ├─ Markdown ドキュメント
                                                      └─ Neptune エクスポート
```

## セキュリティ構成
OntoForge は単一オペレーターのローカルワークショップツールです。顧客の機微情報を扱う際は以下の設定を適用してください。

1. ローカルサーバーは `127.0.0.1` にバインドし、共有ネットワークに公開しないでください。ループバック接続（`localhost`、`127.0.0.1`、`::1`）はデフォルトでトークン無しで許可されます。
2. デフォルトのローカル実行はトークン無しで起動します。
   ```bash
   PYTHONPATH=src uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
   # ブラウザ: http://localhost:8000
   ```
3. 共有ネットワークに公開する場合や、localhost でも認証を強制したい場合は、REST/WebSocket アクセストークンを設定します。
   ```bash
   export ONTOFORGE_TOKEN="$(openssl rand -hex 24)"
   export ONTOFORGE_REQUIRE_TOKEN=1  # localhost でもトークンを強制する場合のみ設定
   PYTHONPATH=src uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
   # ブラウザ: http://localhost:8000/?token=$ONTOFORGE_TOKEN
   # curl 使用時: -H "X-OntoForge-Token: $ONTOFORGE_TOKEN"
   ```
4. TLS が必要な環境では uvicorn の SSL オプションを使用します。
   ```bash
   uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000 \
     --ssl-keyfile key.pem --ssl-certfile cert.pem
   ```
5. `workshop.kuzu` と `exports/` は FileVault/BitLocker/LUKS のような暗号化ファイルシステム上に置いてください。エクスポートファイルは `./exports` 配下にのみ生成され、`0600` 権限で保存されます。
6. `ANTHROPIC_API_KEY` は環境変数または承認済みのシークレットマネージャーにのみ保存します。顧客の個人情報・生体情報・規制対象データはマスキングするか、外部 LLM 呼び出しをオフにしてオフライン抽出器で進めてください。
7. Amazon Neptune へのロード前に、[`docs/NEPTUNE_SECURITY.md`](./docs/NEPTUNE_SECURITY.md) の IAM、S3、VPC、KMS、監査ログの基準を適用してください。

データ分類と保存／削除の基準は [`DATA_CLASSIFICATION.md`](./DATA_CLASSIFICATION.md)、セキュリティ報告とスキャン記録は [`SECURITY.md`](./SECURITY.md) に従ってください。

## 主な制約
- 内部モデルは **プロパティグラフ単一**。T-Box/A-Box は UI 上で概念的に分離。
- **OWL 推論はスコープ外** — 必要なら Cypher ルールで模倣し、本格的な推論は別トラック。
- ローカル openCypher → Neptune は**ほぼ**互換（100% ではない）。ロード・チューニングは技術ミーティング段階で。
- ワークショップは顧客のセキュリティ網内でローカル実行。外部通信は任意で設定した Claude API 呼び出しのみで、キーを設定しなければオフライン抽出器で動作します。

## ライセンス
本プロジェクトは Apache-2.0 ライセンスで提供されます。詳細は [`LICENSE`](./LICENSE) を参照してください。
