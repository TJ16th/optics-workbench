# R103：UI Phase 3（同一画面workspace） 指示書（Codex向け）

## 背景

R99案AのPhase 1（R100：preset browser・右context・theme）、Phase 2（R101：navigation shell・state分離）が完了した。本タスクはR99ロードマップのPhase 3「同一画面workspace」を実装する。R99 3.4節の設計（Surface/Group＋live mini-layout、Layoutのlegend/result strip compact化、Snapshot強制遷移廃止）に従う。

**Analysis chart picker・2〜4 panel workspace・Through-focus MTF統合はR99定義どおりPhase 4であり、本タスクのスコープ外**（前回R101指示書で「Phase3以降」と粗く括った範囲のうち、chart pickerは次タスクへ分離する）。

## 作業

1. **ヘッダー右上「System」ドロップダウンの正体確認**：R101完了スクリーンショットで、ヘッダー右上（engine ok/api 2.5.0バッジの左）に「System」と表示されたドロップダウンが確認された。これが旧ContentSwitcherの残骸（左ナビと重複する画面切替）なのか、意図した別機能なのかを確認する。残骸なら除去する。意図した機能なら、何のUIかを報告書で説明する（対応不要）。
2. **Surface/Group編集のlive mini-layout（R99 3.4節1項）**：Systemビューのsurface/group tableの右または下にmini optical layoutを常設する。
   - table行の選択で、mini-layout上の対応面をhighlightする。
   - 編集結果はdebounced previewで反映する（debounce間隔は既存のスライダー系実装に合わせる）。
   - エンジンへの数値・request payloadは変更しない。既存のpreview APIの呼び出しのみで実現する。
3. **Layoutビューのcompact化（R99 3.4節2項）**：main optical layoutを第一viewportへ固定し、spot/trace summaryは右端または下端のcompact result stripへ移す。現在の大面積常設legendをやめ、折りたたみlegendまたはcanvas内popoverへ変更する。R30の固定凡例の情報量（線種・波長色・要素・マーカーの6カテゴリ網羅）は維持したまま、常時占有面積だけを削減すること。
4. **Snapshot保存後のCompare自動遷移廃止（R99 3.4節5項・論点6）**：R99推奨どおり廃止を採用する。保存後はtoast＋「Compareで開く」明示actionへ変更し、連続条件調整を中断しないようにする。
5. **テスト**：
   - live mini-layoutの行選択highlight・debounced previewのE2E。
   - legend折りたたみ/popoverの開閉と、開閉が中央Layout寸法を変えないことのE2E（R101のパネル開閉寸法安定テストと同じパターン）。
   - Snapshot保存でCompareへ遷移しないこと・toast actionからCompareへ到達できることのE2E。
   - 既存回帰：R100（preset検索・theme切替）、R101（navigation shell・breakpoint別既定状態・drawer）、`npm run ci`全通過、`npm run ui:build:pseudo`成功。

## 完了条件

- 上記1〜4が実装され、5のテストが全て通過している。
- 1920×1080でSystemビューの「編集→mini-layoutで即確認」が1画面・スクロールなしで成立している（R99の目標①②）。
- 現行の数値結果・request payload・snapshotデータ構造・既存i18n識別子を変更していない（新規キーの追加は可、ja/en両方へ追加しi18n:check通過）。
- 実ブラウザ確認のスクリーンショット（Systemビューlive split・Layout compact化・snapshot toastの3点以上）を`doc/reports/screenshots/`へ保存。
- build_info一致確認（プロセス再起動・`/v1/meta`照合）。

## 注意

- **本タスクはUI側のみ。エンジン・API側（`apps/workbench-ui`外のPython側）は変更しないこと**。R102（evaluate trace共有最適化）がエンジン領域で並行進行中のため、コンフリクトを避ける。
- Phase 4項目（chart picker、panel workspace、Through-focus MTF統合、chart selection/panel layoutのstate保存）、Phase 5項目（1120px以下responsive・アクセシビリティ仕上げ）には着手しない。
- mini-layoutは既存のOptical Layout描画コンポーネントの再利用を基本とし、描画ロジックの二重実装（R33で問題化した「表示専用ロジックが実データと結びつかない」パターン）を作らないこと。
- 報告書は`doc/reports/2026-07-15_r103_ui_phase3_same_screen_workspace.md`（日付は完了日）へ。着手前に規模見積もり（人日換算）を報告書冒頭へ記載すること。
