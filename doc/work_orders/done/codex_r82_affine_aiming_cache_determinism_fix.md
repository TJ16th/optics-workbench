# R82：affine aiming cacheの決定論破壊バグ修正 指示書（Codex向け）

## 背景

R81調査で、P0タスク4で導入したaffine aiming cache（コミット`92008eb`、`optics_engine/tracing.py`の`_AIMING_AFFINE_CACHE`）が、同一requestでも直前に実行した別条件（`samples_per_field`・pupil distribution・target集合・tolerance・refinement条件等）のrequest履歴によって結果が変わる、決定論を破壊するバグを持つことが確定した。

cache keyにはsystem・configuration・field・wavelength・STOP情報しか含まれておらず、先行bundleでfitしたaffine係数が別bundleへ流用される。residualが`max(tolerance_mm*10, stop_outer_mm*2.5e-3)`という粗い閾値以下のrayは、affine予測結果のままexact refinementされない。P011ではこの閾値がexact tolerance（1e-6mm）の約44,000倍粗く、結果として厳密解（exact/Level 0相当）から最大1.41e-2mm（sensor座標）のずれが生じる。P002/P003は無視できるレベルだが、P007・P011・P012では処方の非線形性に応じて明確な差が出ることをR81が実測済みである。

**現状、既存のpytestが全緑なのは、既存テストの実行順序がたまたまP011直接回帰テストの前に9-ray実行を挟みcacheを都合よくwarm状態にしているだけであり、真の決定論・独立実行可能性を担保していない**（P011直接回帰テストは単独実行すると2回とも失敗する）。

本タスクは、このcache機構を「決定論的に厳密解と等価な結果を返す」よう修正する。R81報告書（`doc/reports/2026-07-14_r81_p011_spot_rms_drift_root_cause.md`）に実測値・中間計算値・コード経路の詳細があるので、着手前に必ず参照すること。

## 作業

### 1. 設計方針の決定

1. R81が提示した2つの方向性（①cache keyへ全条件を含め解済みoriginをそのまま再利用する方式／②cacheをinitial guess専用にし、cache hit時も必ず既定toleranceまでexact refinementする方式）を比較検討し、どちらを採用するか、またはそれ以外の設計かを決定する。判断根拠を報告書に明記する。
2. 採用方針は、cache hit・cache miss・cold startのいずれの経路でも、同一requestに対して常に同じ結果（厳密解相当、exact/Level 0との差が既存の許容誤差内）を返すことを満たす必要がある。「速いが不正確」な近道は許容しない。
3. 性能目的（P0タスク4のそもそもの動機）を大きく損なわない設計を優先する。cache自体を無効化する選択肢は、性能への影響を測定した上でのみ検討可（安易な無効化での決着は避ける）。

### 2. 実装

1. 決定した方針に基づき、`_AIMING_AFFINE_CACHE`・`_aiming_cache_key()`・`_fit_affine_aiming()`まわりを修正する。
2. 修正後、以下の条件で同一requestが同じ結果を返すことを確認する。
   - cold（cacheなし）
   - 直前に別サンプル数（例：9 rays）で同じfield/wavelengthを解いた後（warm9相当）
   - 直前に別サンプル数（例：25 rays）で同じfield/wavelengthを解いた後（warm25相当）
3. 上記いずれの経路でも、結果がexact strategy（Level 1 `strategy=exact`）およびLevel 0 per-ray referenceと、既存の許容誤差内で一致することを確認する。

### 3. 検証

1. R81の比較表に倣い、P002・P003・P007・P011・P012の中心81-rayについて、cold / warm9相当 / warm25相当 / exact / Level 0の5列を実測し、修正後は全presetでcache経路とexactの差が許容誤差内（機械精度〜既存tolerance相当）に収まっていることを示す。
2. 決定論を直接固定する回帰テストを新規追加する（同一requestを異なる履歴条件下で複数回実行し、結果がbit-identicalまたは既定許容誤差内で一致することをアサートする）。
3. 既存のP011中心81-ray回帰テスト（`tests/test_preset_api_smoke.py::test_p011_planar_double_gauss_has_six_positive_thickness_elements`）を単独実行しても安定してpassすることを確認する。期待値の更新が必要な場合は、更新後の値がexact/Level 0相当であることの根拠とともに報告書に明記する。
4. 修正前後で性能（P0タスク4が対象としていた計算時間指標）を比較し、著しい性能後退がないことを確認する。後退がある場合は具体的な数値と許容可否の判断根拠を報告する。
5. R80で実測したRun Charts性能（30秒性能ガード）にも影響がないことを確認する。

## 完了条件

- affine aiming cacheが、cache hit・miss・coldいずれの経路でも、同一requestに対しexact/Level 0相当の決定論的な結果を返すことが、複数プリセット・複数履歴条件での実測により示されている。
- 決定論を固定する新規回帰テストが追加され、既存P011回帰テストが単独実行でも安定してpassする。
- 修正前後の性能比較が行われ、著しい後退がないこと（または後退の許容判断根拠）が報告されている。
- R71の30秒性能ガードに影響がないことを確認している。
- 既存テストが（実行順序に依存せず）グリーンであることを確認している。
- 完了報告前にプロセスを再起動し、`build_info.git_commit`がHEADと一致することを断定形で記載する（未来形で締めない）。
- **完了報告の実装根拠には、コミットメッセージだけでなく実際のコミットハッシュ値を必ず併記する。**

## 注意

- 「決定論的になった」という主張は、目視や理論だけでなく必ず複数履歴条件での実測比較・数値で裏付けること。
- P011の`aiming_failed`12件（既存backlog Issue）は本タスクとは別問題（R81で無関係と確認済み）であり、本タスクの対象外。修正しない。
- cacheを単純に無効化するだけの安易な解決は、性能への影響を必ず測定・報告した上でのみ選択肢に含めること。
