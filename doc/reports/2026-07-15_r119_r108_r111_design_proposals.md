# R119 R108/R111設計提案

## 着手前見積もり

- 種別: 設計調査のみ（実装・仕様変更なし）
- 規模: 小〜中
- 想定時間: 1〜2時間
- 主な確認対象: `doc/engine_spec.md` 21.5節・22章・26.3節・26.6節、R73作業6、R89作業4、現行の像面solve・PSF・UI実装

## 結論

- **R108**: 「整合プレビュー → 固定する量を選択 → 明示適用」の1ボタン導線を推奨する。既定はfield angleを維持し、近軸像距離solveの結果をsensor直前gapへ適用する。センサー寸法と画角は同時に自動変更しない。
- **R111**: 幾何PSFの契約を先に固定し、その後にOPL計測と回折PSFを段階導入する案を推奨する。回折へ直行するとtrace結果モデルからartifact/UIまで同時変更になり、検証境界が広すぎる。

本報告は提案のみであり、コード、API、正本仕様、capabilitiesは変更していない。

## R108 画角・像高・bf・像面のワンボタン整合

### 現状

エンジンには次の2系統が既にある。

1. `image_plane_policy`: 物理sensorを動かさず、解析用評価面を`paraxial_image`、`best_focus_rms`、`best_focus_mtf`等へ解決する。`apply_to: report_only`なら解だけを返す。
2. `POST /v1/solve/paraxial-image-distance`: sensor直前の最終空気間隔を、基準configuration・主波長の近軸像位置とsensorが一致する値へ解決する。R89-4（機能コミット`c6e447c`）で実装済み。

UIには評価面solve、解いたoffsetの表示、sensor直前gapへの書き戻しがある。一方、angular field、センサー寸法、像高の関係を同じ操作で検査・調整する導線はない。無限遠focal系の近軸関係は、field方向ごとに概ね`h = EFL * tan(theta)`であるが、実光線像高や歪曲を含む像高とは区別が必要である。

### 不一致の定義

整合コマンドは少なくとも次を別々に表示する。

| 項目 | 比較 | 表示する差 |
|---|---|---|
| focus | 現在sensor Xとsolve後像面X | `delta_sensor_x_mm` |
| field fit | 最大fieldの近軸像高とsensor半幅/半高 | `coverage_ratio_y/z`、余白または超過量mm |
| real image | chief ray実像高と近軸像高 | 歪曲を含む差mm/% |

閾値案はfocusを`max(0.001 mm, solve tolerance)`、field fitをsensor寸法の`0.1%`とする。ただし閾値はUIだけで断定せず、応答値と使用した基準を常に表示する。

### UX案A: 即時自動整合

ボタン押下で近軸像距離solveを実行し、最終gapとfield angleをsensorへ収まる値に同時変更する。

- 長所: 操作数が最少。
- 短所: 処方と評価条件を同時に変え、比較結果の意味が不明瞭になる。sensorの縦横比やY/Z field、歪曲をどう扱ったかも見えにくい。
- 規模: 中。
- 評価: 非推奨。

### UX案B: 整合プレビュー付き適用（推奨）

Analysisの`Image plane policy`パネルに`Align`コマンドを置く。実行時はまず変更せず、以下のプレビューを右コンテキストパネルまたはモーダルに表示する。

1. 現在値、solve値、差分、solve statusを表示する。
2. field fitについて、`Preserve field angles`（既定）または`Fit fields to sensor`を選択する。
3. `Preserve field angles`では最終gapだけを更新し、sensor寸法とfieldは維持する。はみ出しは警告として残す。
4. `Fit fields to sensor`ではsensor寸法を維持し、Y/Zの最大angular fieldを近軸逆算する。中心・中間fieldは、絶対角ではなく最大fieldに対する既存比率を保つ。
5. 適用後はsystem dirtyとし、再validate / register後に解析を再実行する。適用前後の数値結果を混在させず、旧結果にはstale表示を付ける。

- 長所: 変更対象と評価条件の意味が明示され、既存のstateless責務分界を守れる。
- 短所: 1回の確認操作が増える。
- 規模: 中。既存solveと`applySensorOffset`を再利用できる。
- 推奨理由: 光学処方の変更と画角条件の変更を分離でき、意図しない「結果改善」を避けられる。

### UX案C: 常時リンクモード

sensor寸法、field angle、像面を拘束式で常時同期するtoggleを設ける。

- 長所: ズームや焦点距離変更時に追従できる。
- 短所: どの値が独立変数か分かりにくく、編集ループやsnapshot再現性の設計が必要。variable binding registryとも競合する。
- 規模: 大。
- 評価: 将来のPosition/Configuration管理と統合して検討する。

### 推奨するAPI境界

- 初期実装は既存`/v1/solve/paraxial-image-distance`と`/v1/analysis/paraxial`をUIが順に呼び、プレビューを構成する。新endpointは不要。
- `best_focus_rms`等を処方へ書き戻す場合は、既存`/v1/solve/best-focus`の`report_only`結果を使い、近軸solveと同じ操作に暗黙統合しない。
- apply時に送る変更は、選択されたauthorityに応じて「最終gap」または「field set」に限定する。
- afocal系、solve失敗、負gap、非空気の最終区間、sensor不在は適用不可とし、エンジンの構造化issueをそのまま表示する。

### 数値結果の扱い

- gap変更後のspot/MTF/歪曲等は別処方の結果なので、既存結果を即時staleにする。
- field変更後はfield IDを保っても角度が変わるため、旧結果との自動系列結合をしない。
- プレビュー内の像高は`paraxial`と`chief ray`を別行で示し、歪曲を含む実像高を「理想像高」として扱わない。
- snapshotには適用後のsystem/fieldを通常どおり保存し、solveプレビュー自体は永続状態にしない。

## R111 解析PSF

### 現状

`analyze_geometric_psf`は到達光線のsensor座標を重心基準で2Dヒストグラム化する。現行trace結果だけから算出でき、`psf_representation: geometric_ray_hit_point_cloud`、`diffraction_included: false`を返す。幾何MTFは同じ到達点分布の複素指数平均、white PSF/MTFは波長別の幾何光線を重み付き合成する。

回折PSFに必要な区間屈折率、幾何長、OPL、OPD、規則瞳座標、参照球面は現行`TraceResult`にない。`capabilities.diffraction_psf=false`は実態と一致している。

### 案A: 幾何PSFを先に製品契約として固定（推奨）

既存実装を土台に、表示とAPIの意味を先に固定し、その後に回折を独立modeとして追加する。

| 段階 | 内容 | 規模 | 依存 |
|---|---|---:|---|
| A1 | geometric mode、正規化、重心、pixel/grid範囲、ray loss、単位、artifact metadataを固定 | 小〜中 | 現行trace |
| A2 | pupil座標と区間OPLをtraceへ追加。ただし既存結果を変えない | 大 | Golden、決定論、性能test |
| A3 | 単色・軸上・circle瞳のOPD/FFT PSF | 大 | A2、FFT格子規約 |
| A4 | field、annulus、ケラレ、非球面 | 中〜大 | A3、aiming/pupil mask |
| A5 | 共通mm格子のwhite PSF/MTFとUI mode切替 | 中〜大 | A4、artifact/API |

- 長所: 各段階のoracleが明確で、現行幾何解析を価値として早く提供できる。回折追加後も比較基準になる。
- 短所: 一時期、PSFという名称で幾何のみを提供するため、UIに`Geometric`と明示する必要がある。
- 総合規模: 大だが段階分割可能。

### 案B: 回折PSFへ直行

traceのOPL拡張、参照球面、瞳格子、FFT、artifact、API mode、UIを一括実装する。

- 長所: 最終目標へ最短の機能列に見える。
- 短所: 位相基準、物理スケール、遮蔽、白色合成、既存trace回帰を同時検証する必要がある。失敗時に誤差源を分離しにくい。
- 規模: 特大。複数タスク・複数コミットへの分割が必須。
- 評価: 非推奨。

### Through-focus MTFとの整合

R92のThrough-focus MTFは現在`diffraction_included: false`の幾何MTFであり、仮想評価面への最終光線投影を使う。

- A1ではPSF/MTF/Through-focusの全応答に`mode: geometric`相当と`diffraction_included: false`を一貫表示する。
- 回折modeではdefocusごとに単に光線到達点を投影するのではなく、評価面に対応した参照球面またはdefocus位相項を瞳関数へ加える。
- Through-focusのdefocus軸、M/S方向、周波数`lp/mm`は既存契約を維持し、同じ点列で`geometric`と`diffraction`を比較可能にする。
- 回折の焦点深度をrange既定値の参考に使っても、幾何曲線へ回折を混入させない。
- white Through-focusは各波長PSFを共通物理格子へ合成してからMTF化する。波長別MTFの単純平均にはしない。

### 推奨する検証ゲート

1. 幾何PSF: 同一traceからbit同一、energy正規化、平行移動時の重心不変形状、ray loss metadata。
2. OPL: Level 0との区間長一致、piston不変、入力順非依存、既存Golden結果不変。
3. 単色回折: Airy第1暗環`1.22 * wavelength * F-number`、cutoff周波数、解析MTFとの一致。
4. defocus: `+/-`等量defocusの対称性とThrough-focus最大位置。
5. annulus/field/white: 遮蔽率によるring変化、ケラレmask、共通mm格子でのenergy保存。
6. capability: 上記対象範囲が実動作してからのみ`diffraction_psf=true`へ変更する。

## 判断事項

実装着手前に人間が決める項目は次の2点である。

1. R108は推奨案Bを採用するか。採用時、初回の`Fit fields to sensor`はY/Z個別対応まで含めるか、単一field方向に限定するか。
2. R111は推奨案AでA1から始めるか。A2以降はtrace契約変更を伴うため、別タスクとして改めて発注する。

## 根拠

- 正本仕様: `doc/engine_spec.md` 21.5節、21.6節、22章、26.3節、26.6節
- 近軸像距離solve: `doc/reports/2026-07-14_r89-4_paraxial_image_distance_solve.md`、機能コミット`c6e447c`、当時の全エンジン結果`157 passed, 1 skipped, 1 warning`
- 回折設計調査: `doc/reports/2026-07-13_r73_task6_diffraction_design_research.md`
- 現行実装: `optics_engine/image_plane.py`、`optics_engine/psf_mtf.py`、`optics_engine/api/main.py`、`apps/workbench-ui/src/ui/App.tsx`

本タスクではコードを変更していないため、エンジン/UIの再起動およびテスト再実行は対象外とした。
