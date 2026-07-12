# R62作業1 P007ドキュメント整合 中間報告

## 状態

R62全体は`Partial`である。本報告では作業1「P007のドキュメント整合」のみ完了し、作業2「実レンズ構成のアフォーカル系プリセット」と作業3「非球面正式プリセット」は未着手である。

## 変更内容

- `apps/workbench-ui/src/domain/presets.ts`の現行P007定義を正本として確認した。
- `doc/ui_spec.md` 9.1節の内蔵プリセット数を、現時点の実数`7`へ更新した。
- 9.4節へP007の目的、6面の面テーブル、推奨field、期待値を追加した。
- `doc/engine_spec.md`にはUIプリセット一覧が存在しないため変更しなかった。
- 既存プリセットのコード・数値は変更していない。

## 数値確認

P007の現行実装を直接ロードし、近軸解析と実光線追跡を行った。

| 項目 | 結果 |
|---|---:|
| EFL | `519.6281203750518 mm` |
| BFL | `452.04242770474303 mm` |
| F number | `19.682883347539843` |
| 実光線条件 | 3 field × 3 wavelength × 9 samples |
| status | `alive: 81` |
| sensor Y範囲 | `-6.102512836842609〜7.108107733359594 mm` |

P007の名称・summaryにある「50mm / fast」と現行近軸値には差があるが、R62のスコープ外である既存プリセット数値変更は行わず、仕様には実測値を記載した。

## 根拠

- 実装根拠: `3dd94b86ed6b8d415e28b32a54b0961857e868c2`（短縮形: `3dd94b8`、`docs: document P007 preset coverage (R62 task 1)`）
- 検証対象: `apps/workbench-ui/src/domain/presets.ts`のP007
- 検証方法: `analyze_paraxial()`、`trace_forward()`による直接確認

ドキュメントのみの変更であり、pytest、UI CI、API/UI再起動は対象外である。R62指示書は作業2・3が残っているため`doc/work_orders/active/`に維持する。
