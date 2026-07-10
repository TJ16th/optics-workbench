# R24c 正本ファイル差分確認 完了報告

## 対象

- `doc/work_orders/active/codex_r24c_verify_canonical_files_diff (1).md`
- 比較範囲: `origin/master..HEAD`
- 確認コマンド:
  - `git diff origin/master..HEAD --stat -- AGENTS.md doc/engine_spec.md doc/ui_spec.md`
  - `git diff origin/master..HEAD -- AGENTS.md`
  - `git diff origin/master..HEAD -- doc/engine_spec.md`
  - `git diff origin/master..HEAD -- doc/ui_spec.md`

## 差分行数

```text
 AGENTS.md          | 19 +++++++++++++++++++
 doc/engine_spec.md |  8 ++++++--
 doc/ui_spec.md     | 10 ++++++++++
 3 files changed, 35 insertions(+), 2 deletions(-)
```

## ファイル別の変更概要

### AGENTS.md

差分あり。追加内容は運用ルールの補強で、仕様本文の変更ではない。

- `doc/work_orders/` 直下に `active/`・`done/`・`README.md` 以外を置かないルールを追加。
- コード変更を伴わない確認・運用作業でも、明示依頼タスクは `doc/reports/` に完了報告を残すルールを追加。
- `/v1/meta` の `build_info.git_commit` / `build_info.git_dirty` の確認・解釈ルールを追加。
- 複数エンドポイントに同種レスポンス項目がある場合の横断確認・直接テスト固定ルールを追加。
- ローカルAPI/UIプロセス再起動と、機能・UI変更後の `build_info.git_commit` 一致確認ルールを追加。
- Work Order File Namingルールを追加。
- Completion Report Move Ruleを追加。

### doc/engine_spec.md

差分あり。仕様の意味を変えるというより、既存項目の評価位置・用語説明を明確化している。

- エッジ厚評価位置を「両面の共通有効径位置」から `min(semiD_a, semiD_b)` の位置と明記。
- `longitudinal aberration` の説明を補正し、単色では球面収差/縦方向焦点ずれ、複数波長重ね描きでは軸上色収差も含むことを明記。
- 単色版と複数波長版を同じAPI/表示名で扱うが、凡例と波長条件で意味を区別する旨を追記。

### doc/ui_spec.md

差分あり。Optical Layout Viewの描画規約を追記している。

- 改訂履歴に `17.2 Optical Layout Viewの描画規約` 追記を追加。
- 光線LODとして、全光線ではなくfield/wavelength/pupil sampleの代表光線を抽出表示する方針を追加。
- 総光線数と表示光線数をmetadataまたはDOM属性で保持する検証方針を追加。
- 光線stroke、波長色、表示上限の方針を追加。
- `semi_diameter_mm` は製造外径ではなく有効径境界として描く、と明記。
- 隣接面の有効半径差、ガラス領域塗り分け、接合面表示、負エッジ厚警告表示のMVP方針を追加。

## 判断

3ファイルすべてに差分がある。内容は、AGENTS.mdの運用規約追加と、engine/UI仕様のLayout View・エッジ厚・縦収差説明の明確化である。

R24bのpush承認判断に必要な正本ファイル差分は上記のとおり確認済み。実際の `git push origin master` はまだ実行していない。
