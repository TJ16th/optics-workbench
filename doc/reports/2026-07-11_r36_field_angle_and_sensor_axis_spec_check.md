# R36 field角度・センサー軸・対角長 仕様確認報告

## 1. 解析条件のfield角度

- 現在のWorkbench UIの`AnalysisField`は`type: 'angular'`のみであり、解析条件パネルは`theta_y_deg` / `theta_z_deg`を直接入力する無限遠field専用である。
- 正本仕様の4.3節・15.1節では、方向は`normalize([1, tan(theta_y), tan(theta_z)])`で定義され、`theta_y`はX軸からY方向、`theta_z`はX軸からZ方向への傾きである。
- 仕様15.2節には有限距離`object_points` / `position_mm`が定義されているが、現実装の`trace_forward`とreference traceはいずれも`angular`以外を`NotImplementedError`とする。したがってUIだけでなく、現カーネルでも有限距離物点は未対応である。
- 誤解防止として、解析条件のField編集欄に「Theta Y / Theta Zは無限遠物点への方向角です。」（ja/en）を追加した。

## 2. プリセットとfield

- `Preset`型と`presets.ts`には推奨fieldセットを持つ項目がない。
- UIは起動時・プリセット切替時とも、固定の`center` / `edge-y` / `edge-z`（0 deg、Y=10 deg、Z=10 deg）へ`analysisFields`をリセットする。前回のfieldは残らない。
- 固定fieldはP005のような狭い系で意図的なoff-axis遮光を生み得るため、設計想定の画角を表すものではない。
- 対応方針は(a)を推奨する。各プリセットに`recommendedFields`を追加し、選択時にそのセットへリセットする。利用者の個別設定を維持するかのUI方針（明示リセットまたは保持）は、その導入タスクで決める。

## 3. センサーY/Z軸

- 正本仕様6.5節はセンサー面をX軸垂直、座標を`sensor_y_mm` / `sensor_z_mm`と定義するが、`width_mm`と`height_mm`のY/Z対応は明記していない。
- カーネルはsensor hitのローカルY/Zを`sensor_y_mm` / `sensor_z_mm`へ記録するだけで、`width_mm` / `height_mm`による範囲判定はしていない。
- Layout Viewは`height_mm / 2`を縦方向（Y表示）半径として使い、`width_mm`は描画に使っていない。出荷プリセットの`36 x 24 mm`は、現表示ではY方向を24 mmとして扱う。
- 統一規約案は`height_mm -> Y軸の全長`、`width_mm -> Z軸の全長`である。これにより36 x 24 mmセンサーはY=24 mm、Z=36 mmとなる。正本仕様への明記と、センサー矩形範囲判定・Layout ViewのZ方向表現は別タスクとして扱う。

## 4. センサー対角長

- `sqrt(width_mm^2 + height_mm^2)`相当の対角長は、現カーネル・Workbench UIともに計算・表示・Layout Viewスケール・画角換算で使用していない。
- 現在のfield角はセンサーサイズ/EFLから逆算せず、ユーザー指定の角度をそのまま使う。対角画角としての評価・表示は未実装である。

## 検証結果

- `npm.cmd run ci`
  - `i18n:check ok (195 keys)`
  - `i18n:coverage ok`
  - `ui:e2e`: `26 passed`
- E2Eの`analysis condition edits mark dirty and rerun preview with updated results`へ、英語の無限遠fieldヒント表示確認を追加した。

## 実行プロセス確認

- 本タスクのコードコミット後にAPIとUIを再起動し、`/v1/meta`の`build_info.git_commit`がコードコミットのHEADと一致することを確認した。
