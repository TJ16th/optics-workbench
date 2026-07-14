# R88：主要API入力検証の強化（R86で発見した黙殺・異常受理パターンの修正） 指示書（Codex向け）

## 背景

R86のスポットチェックで、主要UI向けAPIに複数の「未対応・不正な入力を送ってもエラーにならない」問題が見つかった。最も危険なのは、存在しない材質名を含むsystemの登録がHTTP 200で成功し、後続のtraceで未構造化のHTTP 500クラッシュになる経路である。他にも、未知の`ray_aiming.mode`が黙ってparaxial相当へ落ちながらmetadataには指定した架空mode名が残る、Analysis系が未知のmetric/viewキーを無視する、負のiris半径がdefaultへ静かに戻る、previewの`controls.iris_radius_mm`が丸ごと無視される等が見つかっている。

本タスクはR86で見つかった項目を修正する。R86報告書（`doc/reports/2026-07-14_r86_silent_ignore_spot_check.md`）の一覧表を出発点とすること。

## 作業

### 1. system登録時の材質参照検証（最優先）

1. `POST /v1/systems/register`で、`material_after`等が材質テーブルに存在しない場合、登録時点で構造化4xxエラーを返すようにする（現状はHTTP 200で登録され、後続traceで未構造化のHTTP 500になる）。
2. `semi_diameter_mm`が非正値の場合も、登録時点で構造化4xxエラーを返すようにする。

### 2. 波長の検証

1. `wavelength_nm`が非正値、または材質モデル（Sellmeier式等）の有効域を明らかに外れる極端な値の場合、trace/analysis系のAPIで構造化4xxエラーを返すようにする。有効域の具体的な範囲は、既存の材質モデル実装を確認し、妥当な値（例：既存材質カタログのSellmeier係数が意味を持つ範囲）を根拠とともに決定する。
2. 現状、負の波長がSellmeier式の二乗計算で実質的に正常値として通ってしまう経路を塞ぐ。

### 3. 未知のray_aiming.mode

1. `ray_aiming.mode`に未知の値（既定の`paraxial`/`full`以外）が指定された場合、黙ってparaxial相当の経路へ落とすのではなく、構造化4xxエラーを返すようにする。
2. metadataに実際には使われていないmode名がそのまま記録される問題（`ray_aiming_mode`が入力値をそのまま返す一方、計算は別modeで行われる不整合）も解消する。

### 4. Analysis系の未知metric/view

1. `/v1/analysis/*`系エンドポイントで、未知の`metric`・`view`パラメータが指定された場合、黙って無視するのではなく構造化4xxエラーを返すようにする。既存UIが送るキーには影響しないことを確認する。

### 5. iris半径の検証

1. `configuration.variables.iris_radius_mm`・education previewの`iris_radius_mm`双方で、負値は構造化4xxエラーとする（現状は黙って既定値へ戻る）。
2. systemの物理的な有効径を大幅に超えるiris値について、上限検証を追加するか、意図的に許容する設計とするかを判断し、判断根拠を報告書に明記する（許容する場合も、多数のray missedが発生することをwarning等で明示できると望ましい）。

### 6. preview `controls.iris_radius_mm`

1. 現状、education previewのpayload中`controls.iris_radius_mm`が完全に無視されている（`configuration.variables.iris_radius_mm`は機能するが、`controls`側は未接続）。これが仕様上サポートされるべきパラメータなのか、既に廃止されたレガシーパラメータなのかを確認する。
2. サポートされるべきものであれば、configurationへの変換経路を実装して接続する。レガシーであれば、明示的にdeprecated扱いとし、受け取っても無視される旨をAPI応答（warning等）で示すか、受理自体を拒否するかを判断し根拠を明記する。

## 完了条件

- R86報告書の一覧表にある全項目（system登録の材質・semi-diameter、波長、ray_aiming.mode、Analysis未知metric/view、iris半径、preview controls）について、修正後の挙動をR86と同じ入力で再実行し、構造化エラーまたは正しい挙動に変わったことを実測で確認している。
- 材質名クラッシュ（HTTP 500）が解消され、構造化4xxエラーに変わったことを確認している（最優先項目）。
- 既存UIが正常に送っている入力・設定には影響がないことを確認している（回帰テストを含む）。
- 新規動作を固定する回帰テストを追加し、既存テストとあわせて全てグリーンである。
- 完了報告前にプロセスを再起動し、`build_info.git_commit`がHEADと一致することを断定形で記載する（未来形で締めない）。
- **完了報告の実装根拠には、コミットメッセージだけでなく実際のコミットハッシュ値を必ず併記する。**

## 注意

- R86が「深追いしていない」と明記した範囲（全endpoint・全payload keyのschema総当たり、NaN/Infinity等の境界値総当たり、材料ごとの有効波長域の網羅監査）は本タスクの対象外。R86の一覧表に載った具体項目の修正に集中する。
- 「修正した」「エラーになった」という主張は、目視ではなく必ずR86と同じ入力を再送した実測結果で示すこと。
