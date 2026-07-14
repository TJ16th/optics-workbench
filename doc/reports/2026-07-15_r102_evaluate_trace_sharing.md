# R102 evaluate内trace共有 性能回帰修正

## 着手前見積もり

- 規模: 0.8〜1.2人日
- 内訳: trace経路調査 0.2人日、request-local cache実装 0.3人日、直接回帰テスト 0.2人日、性能測定・全回帰・報告 0.3〜0.5人日

## 結論

エンジン実装は完了した。実装コミットは`dd6dcbe12e30ce35e894c9a84dfb45200809ee72`である。

`evaluate_system()`ごとに破棄されるrequest-local trace contextを導入し、`system_hash`、field、wavelength、sampling、aiming、configurationを含むoptionsが完全一致する場合だけ`TraceResult`を共有するようにした。`fast_design_score`では`rms_spot_radius`、`relative_illumination`、`geometric_mtf`、`ray_loss_ratio`が1回の全field traceを共有する。field IDが重複するrelative illuminationは曖昧性があるため従来のfield別traceへフォールバックする。

3系列中央値の中央値は`fast_design_score=7.427 ms`で、修正前`33.686 ms`比`-77.9%`、clean R82基準`19.633 ms`比`-62.2%`となった。`preview full`と`high-count trace`にも修正起因の悪化はなかった。

## 実装内容

- `optics_engine/optimization.py`
  - `_EvaluationTraceContext`を追加した。
  - cache keyを型付きの不変tupleへ変換し、完全に表現できない値を含む場合は共有せず`trace_forward()`へフォールバックする。
  - Jacobianの`_request_local_workspace`と`_candidate_trace_coordinator`はオブジェクト同一性をkeyに含め、candidate間の誤共有を防止した。
  - RMS、geometric MTF、明示的`ray_loss_ratio`、自動追加ray loss operandsを同じcontextへ接続した。
- `optics_engine/psf_mtf.py`
  - 全field traceからfield IDごとのthroughputを抽出する`analyze_relative_illumination_from_trace()`を追加した。
  - 従来のfield別trace経路と結果組み立てを共通化した。
- `tests/test_r102_evaluate_trace_sharing.py`
  - `fast_design_score`の共有対象traceが1回であることを固定した。
  - field、sampling、wavelength、configuration、aimingのいずれかが異なる場合に共有しないことを固定した。
  - cache有無で通常evaluateのdataclass全体がビット同一であることを固定した。
  - Jacobian candidateのoperands、residuals、matrix、columnsがcache有無で完全一致し、摂動列が非ゼロであることを固定した。

## 性能測定

`benchmarks/spec_like_benchmark.py --profile smoke`を各warmup 1回、repeat 5回で実行し、修正前3系列と修正後3系列の各medianから中央値を求めた。

| case | 修正前 (ms) | 修正後 (ms) | 差 |
|---|---:|---:|---:|
| preview full | 6.366 | 5.648 | -11.3% |
| high-count trace | 124.303 | 119.497 | -3.9% |
| fast_design_score | 33.686 | 7.427 | -77.9% |

`fast_design_score`のclean R82基準との差は`7.427 - 19.633 = -12.206 ms`で、R82比`-62.2%`である。R89-1以降も必要な`ray_loss_ratio`算出自体は残しているが、独立再traceを廃止した。残る処理は1回のtrace、各metricのpost-processing、cache key構築であり、重複trace由来の正の残差はない。

コミット後の履歴JSONは`bench_results/20260715_030359_dd6dcbe.json`である。この単独保存runは`preview full=5.887 ms`、`high-count trace=125.019 ms`、`fast_design_score=7.626 ms`だった。並行中R103の未コミットUI差分と指示書が存在するため、JSONの`git_dirty=true`は`git status --short`の内訳を確認済みであり、R102のtrackedエンジン実装は`dd6dcbe`で固定されている。

## 回帰確認

- R102＋関連merit/Jacobian/relative illumination: `47 passed, 1 warning`
- エンジン全体（Golden Test含む）: `194 passed, 1 skipped, 1 warning in 17.90s`
- 通常evaluateのcache有無: `asdict(cached) == asdict(uncached_result)`
- Jacobian: operands、residuals、matrix、columnsがcache有無で完全一致。`TL_focal_length_mm`摂動列は非ゼロ。
- `npm run ui:build:pseudo`: Pass
- `npm run ci`のbuild、`i18n:check`、`i18n:coverage`、`i18n:test`、`svg:export:test`、`chart:test`: Pass
- `npm run ci`: Pass（最終安定状態、UI build＋i18n＋SVG/chart＋Playwright E2E全件）
- R71性能ガード: `4 passed (19.2s)`。P007 Run Charts `4.9s`、P009 Run Charts `11.4s`で各`30s`以内。

検証中は並行R103のUI実装とE2E更新が同じ作業ツリーへ段階的に同期され、一時的にUI CIが失敗した。R103の同期完了後に失敗対象を再試験し、Analysis 3件`3 passed`、Run Charts 4件`4 passed`を確認した上で、最終的に`npm run ci`全体をgreenにした。R102から`apps/workbench-ui`配下は変更していない。

## backlog

`doc/reports/issues_backlog.md`の「evaluate内の同一条件traceをoperand間で再利用する」は実装完了のため削除した。新規backlog項目は追加していない。

## 実環境反映

R102実装コミット直後にエンジンAPIとUI開発サーバーを再起動し、`GET /v1/meta`の`build_info.git_commit=dd6dcbe`と確認対象HEAD`dd6dcbe`の一致を確認した。その後、並行R103が`9c0e02c`としてコミットされHEADが進んだため、再度API/UIを再起動した。最終確認は`build_info.git_commit=9c0e02c`、HEAD`9c0e02c`で一致し、このHEADはR102の`dd6dcbe`を含む。`build_info.git_dirty=true`は指示書、benchmark JSON、報告書によるものである。UIの`http://127.0.0.1:5173`はHTTP `200`を確認した。

## R104履歴修復後の注記

R104で未push履歴をタスク境界ごとに修復したため、上記の旧R103コミット`9c0e02c`は新R103実装コミット`017af59`へ置き換わった。R102エンジン実装コミット`dd6dcbe`と、それ以前の履歴には変更がない。R102完了資料は新コミット`9d32483`へ分離された。
