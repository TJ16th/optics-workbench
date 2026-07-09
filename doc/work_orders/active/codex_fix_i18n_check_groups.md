# i18n:check失敗の修正（P3-1由来の未使用キー） 指示書（Codex向け）

## 背景

`2026-07-10_verify_fix_and_build_info.md`の検証で、`npm run i18n:check`が失敗していることが判明した。原因は今回の作業（build_info）ではなく、Phase 3 P3-1（群定義の表示・編集UI）で追加された以下のi18nキーが未使用と判定されているため：

- `surfaceTable:surfaceTable.groups.issue_error`
- `surfaceTable:surfaceTable.groups.issue_warning`
- `surfaceTable:surfaceTable.groups.duplicate_id`
- `surfaceTable:surfaceTable.groups.unknown_surface`
- `surfaceTable:surfaceTable.groups.invalid_range`
- `surfaceTable:surfaceTable.groups.overlap`

これはP3-1完了報告時点で`npm run ui:build`と`i18n:coverage`は確認されていたが、`i18n:check`（未使用キー検出）が見落とされていたことを示す。P3-1完了報告の時点でも既にこの状態だった可能性が高い。

## 作業

1. 上記6キーについて、実際にコード側から参照されているか確認する（i18next-parserの検出漏れなのか、本当に未参照なのか）。
   - 動的なキー生成（例：`t(`surfaceTable.groups.${errorType}`)`のような文字列結合）をしている場合、静的解析ツールが検出できないことがある。その場合はi18next-parserの設定（`i18next-parser.config.cjs`）に該当パターンの除外/許可リストを追加する。
   - 本当に未参照であれば、P3-1のgroup validation警告表示ロジックが、これらのキーを使うつもりで実装されていない（実装漏れ）可能性がある。その場合はコード側を確認し、意図された警告表示（duplicate group ID、unknown surface reference、invalid range、overlapping range）が実際にUIへ出ているか確認する。
2. 原因に応じて修正する：動的キー参照なら設定除外、実装漏れならコード側の呼び出しを追加する。
3. `npm run i18n:check`をグリーンにする。
4. `npm run ci`全体を再実行し、他の既存確認（i18n:coverage、i18n:test、ui:build）も含めて通ることを確認する。

## 完了条件

- `npm run i18n:check`がグリーン。
- `npm run ci`全体がグリーン。
- 原因（動的キー参照か実装漏れか）が報告に明記されている。実装漏れだった場合、P3-1のgroup validation警告が実際にUIへ表示されることをスクリーンショットまたはE2Eで確認する。
