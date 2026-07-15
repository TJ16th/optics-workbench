# R116 P011 full aiming収束失敗の根本修正

## 状態

**Done**。実装根拠はコミット`1f4ac20d825d2683e2b5be1991aa1cdd567d9489`（`fix(engine): aim layout rays at effective pupil edge (R116)`）である。

## 原因

P004/P011の高速Double Gaussでは、Layout View用のmarginal baseline rayが要求するSTOP外縁点の一部が、STOPより上流のレンズ有効径・球面形状を通過できなかった。Newton反復回数を20から40/80へ増やしても失敗位置は変わらず、反復の初期値や上限不足ではなく、要求点の幾何的な到達不能が原因だった。

通常のfull aiming光線束にも同じ物理的vignettingがあり、P004は`219 alive / 6 aiming_failed`、P011は`213 alive / 12 aiming_failed`である。この通常bundleはspot等の数値評価に使われるため、今回の表示修正では変更していない。

## 修正内容

- Layout Viewのbaseline ray生成だけに`_layout_aim_origins()`を追加した。
- chief rayは従来どおりSTOP中心を狙う。
- solid stopのmarginal rayが外縁へexact aimできない場合、STOP中心から要求外縁へ向かう半径scaleを24回の二分探索で縮め、通過可能な最大の実効瞳端を決定論的に求める。
- annulusは既存の中心遮蔽・外縁表示規約を維持し、フォールバック対象外とした。
- baseline metadataへ`aiming_target_scale`と`aiming_target_adjusted`を追加し、縮退を観測可能にした。
- 正の半径で一度も収束しない場合は成功扱いにせず、従来どおり`aiming_failed`を維持する。

## 結果

全recommended field、3波長、chief/marginal各3本の27本を確認した。

| Preset | 修正前baseline失敗 | 修正後baseline失敗 | 調整本数 | `aiming_target_scale`範囲 |
|---|---:|---:|---:|---:|
| P004 | 11 | 0 | 11 | 0.8995708823 - 0.9999952316 |
| P011 | 12 | 0 | 12 | 0.8830567002 - 0.9939795732 |

同一入力を連続実行したbaseline metadata・pathは完全一致した。既存の通常bundle期待値、P004 center RMS `0.48432273992330394 mm`、P011 center RMS `0.4653881107408963 mm`は変更していない。

## 検証

- 新規直接回帰: `tests/test_preset_api_smoke.py::test_fast_double_gauss_layout_baseline_uses_deterministic_effective_pupil_edges`
- focused P004/P011: `4 passed`
- engine全体: `196 passed, 1 skipped, 1 warning in 23.23s`
- R102決定論テスト＋Golden Test: `18 passed in 2.20s`
- `git diff --check`: 問題なし

機能コミット後にAPIとUIを再起動した。`GET /v1/meta`の`build_info.git_commit=1f4ac20`と確認対象HEAD`1f4ac20`は一致し、UI `http://127.0.0.1:5173/`はHTTP `200`だった。`build_info.git_dirty=true`は未追跡の作業指示書と本報告書によるものである。

## 規模見積もり

原因切り分け、修正、決定論・Golden回帰までを含めて約0.7人日相当。trace kernel本体の挙動変更は不要で、Layout View用baseline生成に閉じた修正となった。
