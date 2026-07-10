# P0-7 タスク3 着手指示

## 対象

`doc/work_orders/active/codex_p0-7_performance_work_order.md`のタスク3（バッチ配列トレースカーネル）に着手する。

## 前提

- タスク0（計測基盤）・タスク1（Golden Test）・タスク2（aiming残差軽量化、5.0〜5.1倍改善）は完了済み。
- 現状、full aimingは`paraxial`/`off`の約33倍遅い（タスク2後の実測：full ≈2ms/ray、paraxial/off ≈60µs/ray）。
- 本タスクは指示書内で「本丸・最重要」と位置づけられている、per-rayのPythonトレースカーネルをNumPy配列演算へ全面書き換える変更。影響範囲が大きいため、他タスクより慎重に進める。

## 実施内容

指示書のタスク3に定義された内容をそのまま実施する：

- CompiledSystemを構造化配列（surface_type, curvature, conic, asphere_coeffs, semi_diameter, inner_diameter, n_before/after, transform行列, propagation_sign等）に落とす。
- 光線群を`origins[N,3]`/`directions[N,3]`/`wavelength_index[N]`/`status[N]`/`weight[N]`で持つバッチカーネルを実装し、面ループの内側で全光線を一括処理する（球面・平面は閉形式、非球面はNewtonを固定上限＋収束マスクで一括）。
- **既存のper-ray実装（Level 0）は削除せず、`optics_engine/reference/`相当へ移動しリファレンス実装として保持する**（AGENTS.mdの不変規約：Golden Testの基準として必須）。
- **等価性テストを追加する**：Golden Testの2系統（アクロマートダブレット、カセグレン）と、非球面を含む14面ベンチ系について、Level 0とLevel 1のセンサー到達座標を全光線で比較する。許容差は球面のみ系でatol=1e-9mm、非球面を含む系でatol=1e-8mm。
- aimingのバッチ化（全field×波長の主光線をまとめた配列に対してNewton反復を一括実行）。
- 既存の解析関数（spot, RI, PSF等）の呼び出し経路をバッチカーネルに切り替える。
- ベンチ再実行し、before/afterを報告する。目標：14面系・1万本・aiming offのトレースが200ms以内（目標50ms以内）、教育preview（3field×1λ×25rays、paraxial、直呼び）が100ms以内。

## 作業規律の確認

- **タスク3完了後、完了報告を出してこのセッションで停止する。タスク4以降には進まない。**
- Numbaはこのタスクでは使わない（純NumPyで完了条件を満たす。Numbaはタスク7で非球面Newtonに限定適用）。
- 途中で不明点・設計判断が必要な分岐（構造化配列のレイアウト詳細など）が生じた場合、独断で決めず、判断内容とその理由を完了報告に明記すること。

## 完了条件

- 全テスト（既存＋Golden＋等価性）グリーン。
- ベンチ目標（14面系1万本200ms以内、教育preview 100ms以内）の達成状況。
- Level 0実装が削除されず保持されていること。
- 等価性テストの許容差達成状況（atol値と実際の最大誤差）を報告に含める。
