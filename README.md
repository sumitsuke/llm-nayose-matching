# LLMの二段階セルフレビューは日本語名寄せを直せるか（事前登録つき実測）

**問い**: LLMに一度出させた「同一人物か」の判定を*叩き台*として再提示すると、叩き台を渡さない独立再実行と比べて名寄せ精度は上がるのか・下がるのか・変わらないのか。

日本人サッカー選手の **日本語名（漢字/カナ）⇔ ローマ字名** の同一人物判定を題材に、正解ラベルつきで測定する。

## 設計（要点）
- **条件**: A=初回判定 / B=独立再実行（Aと同一プロンプト・別コンテキスト）/ C=二段階レビュー（A の出力を叩き台として再監査）。

## 走らせ方（標準ライブラリだけ・約 0.5 秒）

```bash
python3 src/analyze.py        # data/phase1/run_results.json → data/phase1/analysis_summary.json（コミット済みと 1 バイトも違わない）
git diff --exit-code data/phase1/analysis_summary.json
```

**第三者が検証できる範囲**: 公開している判定結果（`run_results.json`）と正解ラベルに対する**集計**（A/B/C の正解数・破壊件数・CI）は上の 2 行で再生成できます。**正解ラベルそのものの正しさ**（生年月日で機械照合した工程）は、元データを非公開にしているため第三者は確認できません。CI（`.github/workflows/verify.yml`）は push のたびに再生成→一致を確かめます。
- **被験モデル**: `gpt-5.4-mini`（reasoning_effort=low・版とパラメータは事前登録に pin）。
- **ペア**: 160件（確認120＝真マッチ60/非マッチ60 ＋ 難例40）。非マッチは**同姓・同世代**で構成し「別の年代だから」の近道を除去。真マッチは翻字揺れ・語順・混成名など。
- **表層形**: 日本語側=Wikidata（CC0）、ローマ字側=Transfermarkt由来データ。**モデル入力から生年月日・各種ID・URLは除外**（ID照合でなく名寄せを測るため）。
- **正解**: 同一エンティティによる構築＋**独立属性の生年月日で機械検証**（別途）。

## 事前登録
主要評価項目・CI法・予測（文献からは C≈B を予想／両方向とも情報量あり）は [`PREREGISTRATION.md`](PREREGISTRATION.md) に、**A/B/C 走行の前に**コミットしてある（このコミット履歴がタイムスタンプ）。走行後に結果・分析コード・図を追加する。

## 公開・非公開
- 公開: 事前登録・ペアの氏名/クラブ（`data/phase1/pairs.json`）・実際のプロンプト（`data/phase1/prompts.json`）。
- **非公開**: 生年月日を含む検証データ・生の元データ（未成年への配慮＋元データの再配布回避のため）。集計・結果は公開する。

## 規律
一次情報での裏取り・null 許容（効かなければ効かないと報告）・全分析の開示・小標本ゆえ点推定でなく信頼区間を主。著者は AI 成果物の検証を業務にしており、本実測はその検証規律の実演を兼ねる。

## 設計・検証の記録（Sumitsuke Lab）

このリポジトリの背景・検証環境・判定・最終検証日・失敗例は、Sumitsuke Lab の本家記事にまとめています。

- LLM に「もう一度見直して」は効くのか——正解つき 160 件で天井に当たった記録 → https://sumitsuke.jp/lab/llm-self-review-ceiling/
- 受託（生成 AI コード・外注コードの点検と修理・テキスト完結） → https://sumitsuke.jp/works/repair/

## 連絡先

AIで作ったアプリ・外注コードの検証、名寄せなどのデータ整合のご相談を承っています。
- AIコードの検証・監査・修正 → https://coconala.com/services/4282365
- プロフィール → https://coconala.com/users/6153961 ／ https://getaxiom.dev

## License

Code: MIT (see `LICENSE`). Data, tables and figures: CC BY 4.0 (see `DATA_LICENSE`) — please credit **Sumitsuke Lab** (https://sumitsuke.jp/lab/).
