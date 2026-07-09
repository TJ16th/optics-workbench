# UI Phase 3 follow-up2: asphere layout visual check

## 対象

`doc/work_orders/active/codex_ui_phase3_followup2.md` の作業1に対応した。

## 選択した方法

方法(a)を選択した。P004の正式追加は `doc/reports/issues_backlog.md` に登録済みだが、近軸値の凍結や仕様9.1節の数値検証まで含むため、この確認タスクには少し大きい。今回は通常プリセットを変更せず、`?fixture=asphere-layout` のときだけ表示される開発・視覚確認用fixtureを追加した。

## 修正内容

- `apps/workbench-ui/src/domain/presets.ts`
  - `visualFixturePresets` を追加。
  - `F_ASPHERE` は球面 `SPH` と `aspherical_even` の `ASP` を同じベース半径で並べ、非球面側に `conic: -1` と `A4` を与えた。
- `apps/workbench-ui/src/ui/App.tsx`
  - 通常時は既存 `presets` のみを表示。
  - `?fixture=asphere-layout` のときだけ `visualFixturePresets` をプリセット一覧に追加。
- `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - fixture上で球面と非球面のSVG pathが異なるsag量を持つことを確認。

## スクリーンショット

- `doc/images/phase3-followup2-asphere-layout-fixture.png`

## 検証

- `npm.cmd run ui:build`
  - 成功。Viteの既存警告のみ。
- `npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts -g "layout view"`
  - 成功。2 passed。

## 残す/戻す判断

fixtureは通常UIには出ない開発確認用入口として残す。正式プリセットではなく、P004追加backlogとは別扱い。
