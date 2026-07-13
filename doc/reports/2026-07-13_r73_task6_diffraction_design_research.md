# R73 作業6 diffraction included切替 設計調査

## 状態

**Done（設計調査のみ。回折PSF/MTFは未実装）**

- 調査対象: `doc/engine_spec.md` 22章、`optics_engine/psf_mtf.py`、`optics_engine/tracing.py`、`optics_engine/api/main.py`、`optics_engine/metadata.py`
- backlog: 既存の「回折PSF・波面収差・FFT瞳関数を追加する `[issue: #8]`」を重複登録せず、本調査結果で具体化した
- capability: `capabilities.diffraction_psf=false`を維持
- 変更規模: **大**

## 現行実装との境界

現行の`analyze_geometric_psf`はセンサー到達点を2Dヒストグラム化し、`analyze_geometric_mtf`は到達点分布の複素指数平均からMTFを求める。`analyze_white_psf` / `analyze_white_mtf`も幾何光線を波長ウェイトに応じて結合する方式であり、波面位相と回折限界は扱わない。

回折PSFには少なくとも次の追加情報が必要だが、現行`TraceResult.paths`には交点、入射方向、statusしかなく、区間光路長、区間屈折率、OPL、正規化瞳座標は存在しない。

1. 各光線の光路長`OPL = Σ(n_i · ds_i)`
2. chief rayまたは基準光線に対する参照球面と`OPD`
3. 規則格子上の瞳振幅`A(u,v)`と位相`2π OPD/λ`
4. FFT後の像面サンプリング間隔とエネルギー正規化
5. 波長ごとに異なるPSFスケールを揃える共通物理格子

したがって、回折対応は`psf_mtf.py`への関数追加だけでは完結せず、traceカーネルからAPI/artifactまで横断する。

## 実現方針

### 案A: 光線OPL・参照球面・直接FFT（推奨）

決定論的な瞳格子から実光線を追跡し、各区間の`n · ds`を積算する。像点を中心とする参照球面との差からOPDを求め、circle/annulus、ケラレを含む振幅とともに複素瞳関数を構築する。

```text
P(u,v) = A(u,v) exp(i 2π OPD(u,v) / λ)
PSF = normalize(|FFT(P)|²)
OTF = FFT(PSF) / FFT(PSF)[0,0]
MTF = |OTF|
```

長所:

- 球面・非球面、色収差、annulus、ケラレを同じ実光線モデルから扱える。
- 局所的な高次収差や瞳欠損をZernike次数で切り落とさない。
- 仕様22.2節の瞳関数FFTへ直接対応する。

短所:

- OPL蓄積、参照球面、瞳座標、格子化をtrace結果へ追加する必要がある。
- full ray aiming後の不規則な瞳写像を規則格子へ再標本化する規約が必要になる。
- FFT格子、zero padding、像面スケール、aliasingの検証範囲が広い。

### 案B: 光線OPDのZernike fitting後にFFT

疎な実光線からOPDを求め、円形瞳上のZernike係数へfitした後、規則格子へ波面を再構成してFFTする。

長所:

- 波面を少数係数で保存でき、収差診断や低次数の教育表示と結び付けやすい。
- 疎な瞳サンプルを平滑な規則格子へ変換しやすい。

短所:

- 高次・局所収差がfit次数に依存し、瞳端や強い非球面で誤差が増える。
- annulusにはannular Zernike等の別基底が必要で、ケラレやspiderの不連続振幅を表せない。
- fitting誤差と物理収差を区別する追加診断が必要になる。

案Bは診断・高速近似として有用だが、初期実装の正本にはせず、案AのOPD格子を正本として段階的に追加する。

## 推奨する段階導入

1. 単色・軸上・円形瞳に限定し、traceへ区間OPLと瞳座標を追加する。
2. chief ray基準の参照球面OPD、規則瞳格子、FFT PSF、OTF/MTFを実装する。
3. 理想円形瞳、既知defocus、piston不変性で数値規約を固定する。
4. field、annulus、ケラレ、非球面へ拡張する。
5. 波長ごとのPSFを共通の像面物理格子へ再標本化してwhite PSFを合成し、そのPSFからwhite MTFを求める。
6. artifact、APIの`mode: geometric | diffraction`、UI切替を追加し、最後に`capabilities.diffraction_psf=true`へ変更する。

## 変更規模

| 領域 | 規模 | 主な変更 |
|---|---|---|
| trace・結果モデル | 大 | 区間屈折率、幾何長、OPL、瞳座標、参照光線 |
| 波面・FFT解析 | 大 | OPD、振幅mask、格子化、FFT、物理スケール、正規化 |
| field・annulus・white | 中〜大 | vignetting、遮蔽、波長別格子、共通像面格子合成 |
| API・artifact・metadata | 中 | mode、構造化エラー、配列artifact、capability |
| テスト・benchmark | 大 | 解析解、収束性、決定論、複数field/波長、性能履歴 |

総合見積りは**大**。理由は、PSFの式自体よりも、位相の基準、瞳から像面への物理スケール、遮蔽、白色合成を一貫したデータ契約として固定する作業が支配的だからである。

## 性能・メモリ見積り

FFT部分はfield数`F`、波長数`W`、一辺`N`の格子に対して概ね`O(F · W · N² log N)`となる。`complex128`格子1枚は256²で1 MiB、512²で4 MiB、1024²で16 MiBである。位相、複素瞳、FFT結果、PSF等を同時保持すると数倍になるため、field・波長を逐次処理し、必要なartifactだけを保持する方針が妥当である。

初期既定値は256または512格子とし、Airy第1暗環を十分に解像するzero paddingと瞳サンプリング収束条件をテストで決める。grid sizeとpaddingはcache keyへ含める。

## 検証計画

- 理想円形瞳: Airy第1暗環`r = 1.22 λ N`、cutoff`f_c = 1 / (λ N)`、円形瞳の解析MTFとの一致。
- 位相基準: piston追加でPSF/MTF不変、既知defocusで対称な広がりを再現。
- 遮蔽: annulusの中央遮蔽率変更に対して中央ピーク・ring分布が決定論的に変化。
- sampling: pupil gridとzero paddingを増やしたときのencircled energy・MTF収束。
- white: 各波長PSFを共通`mm`格子で重み付き合成してからMTF化し、重み正規化と像位置ずれを確認。
- API: `diffraction_included`、mode、artifact、非有限値、sampling不足を構造化レスポンスで固定。
- 性能: 仕様相当の複数field/波長を`bench_results/`へ追記し、前回比を報告。

## 結論

推奨方針は**案Aの光線OPL・参照球面・直接FFT**である。Zernike fittingは後段の診断・近似として追加する。今回、回折計算コードおよびcapabilityは変更していない。

## R73全体完了監査

| 作業 | 状態 | 根拠 |
|---|---|---|
| 1. 縦収差異常の調査・修正 | Done | 実装`1afa3a99cd59a3918bcef40315f5fcda6416b8cc`、報告`3facfdf`、`tests/test_engine_v2_1.py`、P002/P003スクリーンショット |
| 2. 4専用View仕様 | Done | 仕様`49b3b4b017666584123ede0fe2054ab5c3ac5a91`、報告`d44ad26`、`doc/ui_spec.md` 17.7〜17.10 |
| 3. white / monochromatic MTF | Done | 実装`f943c59143eada507b0539af417fb1cce11351f1`、報告`58a9f76`、`analysis-conditions.spec.ts`のwhite MTF E2E、保存済みスクリーンショット |
| 4. `aiming_failed`可視化 | Done | 実装`e32a9e9c2ab793d881b2499385dd312a8af42419`、報告`b0771dd`、`analysis-conditions.spec.ts`のP007 E2E、保存済みスクリーンショット |
| 5. 収差merit operand | Done | 実装`434748c7121ebbeaee3ef7e38c4dd702c5f279df`、報告`77f92ae`、`tests/test_phase7_optimization_evaluate.py` |
| 6. diffraction included設計調査 | Done（実装対象外） | 本報告、`doc/engine_spec.md` 22章、既存backlog `[issue: #8]`の具体化、`capabilities.diffraction_psf=false`維持 |

## 最終検証

- `python -m pytest -q` -> `107 passed, 1 skipped, 1 warning in 18.60s`
- `npm run ci` -> build、`i18n:check`、`i18n:coverage`、`i18n:test`、SVG/chart検証、Playwright `38 passed (48.9s)`
- 検証時HEAD: `77f92ae3968352fae20efe1ae86735a0a8115571`
- 最後の実質コードコミット: `434748c7121ebbeaee3ef7e38c4dd702c5f279df`
- `GET /v1/meta`の`build_info.git_commit`: `434748c`（最後の実質コードコミットと一致）
- `GET /v1/meta`の`capabilities.diffraction_psf`: `false`
- UI `http://127.0.0.1:5173/`: HTTP `200`
- `build_info.git_dirty`: `true`。内訳は本報告・backlog更新と、人間配置の未追跡作業指示書であり、機能コード差分ではない。

R73指示書は本報告と同じコミットで`doc/work_orders/done/`へ移動する。
