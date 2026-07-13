# R69 作業1 視覚評価コンポジット仕様追加 完了報告

## 状態

R69作業1は完了した。R69全体は**Partial**であり、作業2〜5は未着手である。

## 変更内容

正本`doc/engine_spec.md`をv2.4へ更新し、次を追加した。

- 6.7節: `eye_reference`の`at_exit_pupil`をコンパイル済み位置へ実反映する規約と、`fixed_offset`の基準を明記した。
- 9.3節: `system_type: afocal`を維持し、`visual_evaluation.mode: instrument_and_retinal`で視覚評価コンポジットを明示するデータモデルを追加した。
- 9.3節: 唯一の`eye_reference`を境界として、前段を`instrument`、後段から末尾`sensor`までを`retinal`とする責務を定義した。
- 9.3節: 主`aperture_stop`は装置側ray aiming基準、`eye_reference`は4 mm眼瞳クリップと接続位置とし、初期版の模型眼内に第2の`aperture_stop`を置かない規約を追加した。
- 24.9節: `instrument`の角度spot/PSF/MTF・射出瞳・アイレリーフ・残存ディオプターと、`retinal`の網膜spot/PSF/MTFを別schema・別単位で返す仕様を追加した。
- 24.9節: 簡約Gullstrand模型眼の処方と、587.56 nm単色、4 mm固定瞳、無調節、平面網膜という初期制限を明記した。
- 24.9節: 境界位置解決、結果分離、模型眼trace、既存afocal回帰が実装されるまで`instrument_and_retinal`をcapabilitiesへ列挙しない条件を追加した。

本仕様は単一面列内の専用境界に限定しており、任意のsystem chainingグラフは導入しない。

## 未実装

- models / validation / compile / tracing / visual analysisの変更
- `position_mode: at_exit_pupil`の実配置処理
- 簡約Gullstrand内部プリセットとgolden test
- API、`/v1/meta`、UI、i18n
- P006/P008の変更前後数値比較

これらはR69作業2〜5の対象であり、本報告時点でDoneとは扱わない。

## 検証根拠

- 仕様コミット: `1f7aed9` (`docs(engine): specify visual eye composite (R69 task 1)`)
- 変更ファイル: `doc/engine_spec.md`
- 静的確認: `git diff --check`成功
- 構造確認: v2.4表題、9.3節、24.9節、両PSF schemaの存在をPowerShellで確認
- コード変更なし。pytest、UI CI、プロセス再起動、`/v1/meta`確認は対象外

R69指示書は作業2〜5が残るため`doc/work_orders/active/`に維持する。
