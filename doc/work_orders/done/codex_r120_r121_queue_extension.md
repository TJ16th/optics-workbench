# R120/R121：連続作業キュー拡張 指示書（Codex向け・無人時間帯用）

## 背景

R105/R106調査報告（`2026-07-15_r105_r106_system_table_and_position_ui.md`）の推奨案を人間が承認した：**R105は案B（全幅表＋surface inspector）、R106は案B（system Position Manager）を採用**。本指示書は既存の連続作業キュー（`codex_r116_r119_autonomous_work_queue.md`）の**末尾への追加**であり、R119完了後にR120→R121の順で直列実行すること。キュー全体の運用ルール（直列・タスク別コミット・amend禁止・push禁止・バッチ実行モード・判断要時は提案待ちスキップ）をそのまま適用する。

**完了報告の記載ルール（今回から明示要求）**：機能の完了主張には「どの対象範囲に対して実装したか」の列挙を必須とする（例：編集可能にした列の一覧、対応した面kindの一覧）。R103報告で「surface編集」が実態（annulus半径のみ）より広く読める記載だった反省による。

---

## R120：System諸元表の全幅化とsurface inspector（R105案B）

R105調査の実測（mini-layout非表示なら1920pxで8/8列表示可）に基づく実装。

1. **Table / Split表示切替**を導入し、**Tableビュー（全幅諸元表）を既定**とする。mini-layout（R103）はSplitビューまたは明示切替で表示。切替状態はlocalStorageへ永続化（R101の慣行）。
2. **surface inspector**：行選択で下段またはdrawerのinspectorを開き、選択surfaceの諸元を編集可能にする。
   - 編集対象（MVP）：Radius、非球面係数（conic/A4等、kindが対応する場合）、Thickness After、Material、Semi-Diameter。
   - Materialは既存のmaterial index（エンジンの材質カタログ）からのselect方式とし、自由文字列入力にしない（R88の材質参照検証の教訓：不正参照を入力段階で防ぐ）。
   - 反映は既存annulus編集と同じ流れ（system dirty化→70ms debounce preview→必要時validate/register）。dirty状態を視覚的に明示する。
   - **ID/KindはMVPでは編集不可**（参照整合性への影響が大きいAdvanced扱い）。読み取り専用である旨をinspector上に表示する。
   - 不正入力は黙殺せず構造化エラーを表示する（R85/R86の教訓）。
3. 既存のannulus STOP編集・Group Panel編集は挙動を変えない。
4. **E2E**：P009で1920px時に8列すべて完全表示（横スクロールなし）／inspector経由でRadius・Thickness・Material・Semi-Diameterを変更しpreviewへ反映／不正値で構造化エラー表示／Table・Split切替の永続化。
5. スクリーンショット：全幅Tableビュー、inspector展開、Splitビューの3点以上。
6. 報告書に**編集可能列×面kindの対応一覧表**を必ず記載すること。
- 報告書：`doc/reports/2026-07-15_r120_system_table_full_width_and_inspector.md`

## R121：Position Manager（R106案B）

R106調査の推奨フロー1〜6に従う。`system.zoom_positions`を正本とし、**MVPはエンジン変更不要**の範囲で実装する。

1. **System画面にPosition Manager**を追加：position ID・nominal focal length・group別X/Y/Zシフトの一覧表示と編集（追加・複製・更新・削除・並び替え）。編集はsystem dirty→validate/register の既存フローへ接続。
2. **PreviewのGroup Motion**：position選択をIDが見えるSelect/stepperへ改善（既存sliderは維持）。
3. **「現在値をpositionとして保存」**：現在のgroup X/Y/Zシフトを新規ID入力または既存position更新でsystemへ書き戻す。保存済みpositionと一時offsetを視覚的に区別し、一時値がある場合は`modified`表示＋「更新」「別名保存」「破棄」を提供する。
4. **Snapshotへ`configuration`（選択position IDと一時offset）を保存**し、Compare・export・importで復元する。snapshotデータ構造の**追加**は可（既存フィールドの変更・削除は不可、後方互換を維持し、旧snapshotの読み込みが壊れないことをテストで固定）。
5. **tilt/roll/irisはnamed position化不可**であることをUI上に明示する（現行`zoom_positions` schemaの表現範囲外のため。将来の案C検討事項として報告書に記録）。
6. エンジン変更が必要と判明した項目（label/kind/trajectory metadata等）は実装せず、提案として報告書へ記載する。
7. **E2E**：P013でのposition切替・現在値保存→registerフロー・snapshot保存/復元でのconfiguration再現・P003（OIS group持ち）でのY/Zシフト保存。
8. スクリーンショット：Position Manager一覧、保存ダイアログ、snapshot復元の3点以上。
9. 報告書に**保存可能な状態要素／不可の要素の一覧**を必ず記載すること。
- 報告書：`doc/reports/2026-07-15_r121_position_manager.md`

---

## 共通の完了条件

- `npm run ci`全通過、`npm run ui:build:pseudo`成功、i18nはja/en両方。
- **UI側のみ。エンジン・API側の変更は不可**（R121で必要と判明した場合は提案として報告）。
- 数値結果・request payloadは不変（R121のsnapshot構造は後方互換の追加のみ可）。
- build_info一致確認、スクリーンショット保存。
- 各報告書冒頭に着手前見積もり。
