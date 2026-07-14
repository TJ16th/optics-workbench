# R93：ヤコビアンバッチ J4（candidate軸trace kernel）＋J5（運用固め） 指示書（Codex向け）

## 背景

R91でJ2（correctness-first Jacobian API）・J3（request-local warm refinement）を実装したが、実測ベンチマークでR83の`1.25×cold`目標を満たしたのは14条件中1件のみで、P007・P012では一部条件でJ3がJ2/coldより遅くなることが判明した。Codexの分析では、J3はcandidate軸のtrace自体を候補間で共有しておらず、aiming（収束計算）の初期値だけを高速化しているため、根本的な高速化効果が限定的とのことだった。

R84の段階導入案では、この根本原因に対処する策としてJ4（candidate軸trace kernel、`_trace_raw_candidates()`の新設）を提案していた。人間は「J4は繊細な領域（trace kernel）への投資でありリスクが大きい、現時点で本当に必要か不明」という懸念を持っていたが、検討の結果、着手することを決定した。

**このタスクは、このプロジェクトで最も慎重な検証が必要な変更の一つである。** `_trace_raw()`・aiming周りは、過去にR81で重大な決定論バグが見つかった領域であり、既存のGolden Test・Level 0参照実装との等価性が長年かけて確立されてきた資産である。焦らず、各作業ごとに完了報告してから次へ進むこと。

## 作業

### 作業1：candidate軸trace kernelの実装

1. R84の設計案に沿って、`origin: [candidate, ray, 3]`、`direction: [candidate, ray, 3]`、`wavelength: [candidate, ray]`、`status: [candidate, ray]`、`surface data: [candidate, surface, ...]`という形状で、複数candidateの光線を1つの配列にまとめてtraceする`_trace_raw_candidates()`を新設する。
2. **batch適格条件**：各candidateが同じsurface topology・surface ID順・material ID順を持つことを前提とする。異なるトポロジー（摂動によって面の有効性やmaterial参照が変わる等）を持つcandidateは、既存のJ2/J3独立評価経路へ自動fallbackする。
3. **alive maskの扱い**：candidate間で生存ray数が異なるため、まずはdense mask方式（candidate×ray全体を保持し、無効エントリはmaskで扱う）を採用する。compact配列化によるさらなる最適化は本タスクの対象外とする。
4. **chunk分割**：メモリ上限を超える場合、candidate順の固定chunkへ分割する。chunk sizeは性能のみに影響し、数値結果を変えないこと。各candidate内のray reductionは常に元ray index順で行う。
5. 現行`_trace_raw()`・Level 0参照実装を変更・置き換えない。既存関数は温存し、新関数を追加する形にする。
6. `_trace_raw_candidates()`が返す結果が、同じcandidate群を現行`_trace_raw()`で1つずつ独立に計算した結果、およびLevel 0参照実装と、Golden等価性テストで一致することを確認する（既存のGolden Test方式・許容誤差の考え方を踏襲する）。

### 作業2：J3との統合とベンチマーク

1. J3のJacobian評価経路（`evaluate_jacobian`相当）が、batch適格な場合に`_trace_raw_candidates()`を使うよう切り替える。不適格な場合は既存のJ2/J3独立経路へfallbackすることを維持する。
2. R83・R91と同一条件（P002/P007/P012/P011、簡易merit条件、5/10/20変数）で、J4適用後のベンチマークを実施する。**測定は複数回（最低10回）行い、run間のばらつきが大きかったR91の教訓を踏まえ、中央値だけでなく分布（最小・最大・標準偏差程度）も報告する。**
3. R83の`1.25×cold`という保守的仮定と比較し、達成できたかを明確に判定する。達成できなかった場合、原因をprofilingで特定し、報告書に記載する（この時点で追加実装はしない）。

### 作業3：J5 運用固め

1. `/v1/meta.capabilities`のjacobian関連項目を、実際に動作する機能（candidate batch対応の有無等）と一致するよう更新する。
2. artifact concurrency・TTLがJ4のchunk分割・並行呼び出しでも安全であることを確認する（R91で追加したlock/atomic writeが引き続き機能することを含む）。
3. `doc/engine_spec.md` 25.7節へ、J4実装状況（candidate軸batch対応、適格条件、fallback条件）を追記する。
4. full pytest・spec-like benchmark・既存UI E2Eが全てグリーンであることを確認する。

## 完了条件（全作業共通）

- 各作業について、既存のGolden Test・Level 0参照実装との等価性が実測で確認されている。
- R82の決定論（同一request signatureでbit-identical）、R91で確立したJ2/J3の精度budget・境界ケーステスト・収束次数テストに悪影響がないことを確認している。
- 性能測定は複数回実施し、ばらつきを含めて報告している。単一run・単一条件での「達成」主張は行わない。
- 新規動作を固定する回帰テストが追加されている。
- 完了報告前にプロセスを再起動し、`build_info.git_commit`がHEADと一致することを断定形で記載する（未来形で締めない）。
- **各作業の完了報告の実装根拠には、コミットメッセージだけでなく実際のコミットハッシュ値を必ず併記する。**

## 注意

- 作業1〜3は1つずつ完了報告すること。作業1が完了したら報告し、次へ進む前に一度区切ること。
- 作業2のベンチマークで`1.25×cold`目標未達だった場合、無理に追加実装で目標達成を狙わず、正直に未達と報告すること（R91と同じ姿勢を維持する）。目標未達自体は失敗ではなく、判断材料として価値がある。
- batch適格条件・fallback条件は、性能のためにこっそり緩めない。同一トポロジーという条件を満たさないcandidateは必ず既存の安全な独立経路を通すこと。
- 「等価性を確認した」という主張は、目視ではなく必ずGolden Test・実測数値で裏付けること。
