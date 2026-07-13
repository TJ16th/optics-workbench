# R68 アフォーカル系と模型眼の接続設計調査 完了報告

## 結論

現行の光線追跡カーネルは`eye_reference`通過後も後続面を追跡するため、模型眼の屈折面と網膜`sensor`を同じ`surfaces`へ並べること自体は可能である。しかし、現行モデルは`focal`なら末尾`sensor`、`afocal`なら末尾`eye_reference`を要求し、射出瞳、アイレリーフ、主絞り、結果単位もシステム全体で1組として扱う。したがって、単純な面列延長だけでは既存afocal評価との責務分離を保証できない。

推奨案は、一般的なsystem chainingグラフを導入せず、単一面列に「装置側afocal区間 → `eye_reference`中間境界 → 模型眼区間 → 網膜`sensor`」を明示する視覚評価コンポジットを追加する中規模拡張である。装置側角度評価と模型眼側網膜評価を同一traceから別名前空間で返す。

本タスクではエンジン・UI・プリセットを実装していない。

## 現行モデルの棚卸し

### 正本仕様

- `doc/engine_spec.md` 6.7節は`eye_reference`をafocal系の終端とし、射出瞳位置で眼瞳クリップと角度分布を評価する。
- 9.2節は`focal`の終端を`sensor`、`afocal`の終端を`eye_reference`とし、像高mmと射出角度deg、lp/mmとcycles/degreeを分離する。
- 24.2〜24.6節は、object angular fieldから`eye_reference`までを追跡し、角度spot/PSF/MTF、残存ディオプター、射出瞳、アイレリーフ、アイボックスを評価する。

### 実装上の境界

- `optics_engine/models.py:131-134`の`EyeReference`は瞳径、`at_exit_pupil|fixed_offset`、offsetを持つ。`OpticalSystem.system_type`は同ファイル192行で`focal|afocal`の二択である。
- `optics_engine/validation.py:31-47`はfocal末尾に`sensor`、afocal末尾に`eye_reference`を要求する。中間`eye_reference`自体は禁止していない。
- `optics_engine/system.py:48-91`は単一の平坦な面列を累積X位置へコンパイルし、主絞りindexとsensor indexを各1個だけ保持する。コンポーネント境界、port、媒質handoff、複数系の座標変換はない。
- `optics_engine/tracing.py:359-458`は面列を順に追跡する。`eye_reference`では瞳径による遮光と射出角度記録を行うがbreakしないため、後続の`refractive`面と`sensor`へ物理的には到達できる。
- `optics_engine/visual.py:109-126`のアイレリーフは最初の`eye_reference`と全系で最後のpowered surfaceの差を取る。模型眼面を後置すると最後のpowered surfaceが眼内面になり、装置のアイレリーフを壊す。
- `optics_engine/visual.py:129-170`と184行以降のafocal/角度MTFは`eye_reference`で記録した角度を使う。この記録自体は中間境界化しても利用できる。
- `position_mode: at_exit_pupil`はモデルと仕様に存在するが、`compile_system`は`thickness_after_mm`の累積位置しか作らない。リポジトリ内検索でも自動配置処理は確認できず、現行実装は仕様記述を満たしていない。

### 単純延長の可否

`system_type: focal`として、装置面、`eye_reference`、模型眼面、網膜`sensor`を並べればvalidationとtraceは通せる見込みである。ただし次の問題があるため、製品仕様としては採用しない。

- `afocal`としての終端・単位契約を失い、image-plane policy等がfocal系として適用される。
- 主`aperture_stop`は全系で1つであり、装置のaiming基準と眼瞳を区別する明示的な契約がない。
- アイレリーフ、角倍率、近軸量が模型眼面を含む全系計算に混入しうる。
- `at_exit_pupil`が自動配置されないため、接続位置を手作業の厚みで代用することになる。

よって「光線を通すだけ」なら可能だが、「既存afocal指標を保った模型眼評価」としては中間境界の仕様拡張が必要である。

## 標準模型眼

初期候補には、調節休止状態の**簡約Gullstrand模型眼**を選ぶ。既存の球面屈折、定数屈折率、平面sensorに最も直接対応し、設計検証用の基準処方として扱いやすい。

| 面 | 半径 R (mm) | 後方厚み (mm) | 後方屈折率 | 現行表現 |
|---|---:|---:|---:|---|
| 角膜前面 | +7.70 | 0.50 | 1.376 | spherical `refractive` |
| 角膜後面 | +6.80 | 3.10 | 1.336 | spherical `refractive` |
| 水晶体前面 | +10.0 | 3.60 | 1.4085 | spherical `refractive` |
| 水晶体後面 | -6.00 | 17.187 | 1.336 | spherical `refractive` |
| 網膜 | -17.2 | 0 | - | 現行は平面`sensor`で近似 |

数値はWiley-VCHの視覚光学資料に掲載されたrelaxed simplified Gullstrand eye（主に587 nm）による。[Handbook of Optical Systems sample, Table 36-8](https://application.wiley-vch.de/books/sample/3527403809_c01.pdf)

材料は`CORNEA(n=1.376)`、`AQUEOUS_VITREOUS(n=1.336)`、`LENS_EQ(n=1.4085)`という`constant`材料で表現できる。装置から角膜まではAIRとする。

現行枠組みで不足する点は次の通り。

- 非屈折面の`sensor`は平面交差として扱われるため、`R=-17.2 mm`の曲面網膜を表現できない。初期版は軸上位置の平面網膜に限定し、曲面評価面は後続拡張とする。
- 定数屈折率処方は587 nm単色の基準である。眼の縦色収差を評価するには波長別屈折率または分散モデルの根拠データが必要である。
- 調節、GRIN水晶体、個人差、偏心・傾斜は表現しない。現行のaspherical_evenは表面非球面には使えるが、GRIN媒質の代替にはならない。
- `eye_reference`の瞳位置と模型眼の虹彩位置の対応、および装置の射出瞳との位置合わせを接続仕様として固定する必要がある。

## 実現案と規模

### 案1: focal系への直接追加

変更規模は小。ただしこれは既存カーネルを利用する実験用プロトタイプに限る。

長所は、面交差・屈折・sensor spotの新規カーネルが不要で、最短で網膜位置の光線分布を確認できること。短所は、afocal終端契約を失い、装置側の射出瞳・アイレリーフ・角度MTFと模型眼側評価が混線すること、`at_exit_pupil`を実装しないまま位置を手入力することにある。

### 案2: 中間境界を持つ視覚評価コンポジット

変更規模は中であり、推奨案とする。

単一面列と既存traceを維持しつつ、データモデルへ視覚評価モードまたは`retinal_evaluation`ブロックを追加する。コンパイル時に`eye_reference`を装置・模型眼間の境界として保持し、末尾に網膜`sensor`を許可する。

長所は、既存の決定論的trace、面型、cache hashを再利用しながら、装置側角度評価と網膜側位置評価を明確に分離できること。一般グラフより仕様・API・UIへの影響を限定できる。短所は、validation、paraxial/visual analysis、API schema、capabilities、UI評価モード、テストを横断して変更する必要があること。

### 将来案: 一般system chaining

変更規模は大。各systemに入出力port、座標変換、媒質連続性、個別hash/cache、aiming境界、結果合成を導入し、任意の装置を連結する。

再利用性は高いが、模型眼1件のためには過剰であり、チルトした接続、複数コンポーネント、独立最適化等の要求が具体化するまで採用しない。

## 推奨仕様の骨子

1. 装置側はafocal責務を維持し、`eye_reference`を終端ではなく明示的な評価境界として扱えるモードを追加する。
2. 境界後に模型眼の`refractive`面と網膜`sensor`を許可し、traceは既存の単一面列を継続する。
3. `instrument`結果に射出瞳、アイレリーフ、角度spot/PSF/MTF、残存ディオプターを置き、境界より後のpowered surfaceを計算対象から除外する。
4. `retinal`結果に網膜spot/PSF/MTFを置き、長さ・空間周波数単位を使用する。
5. 主`aperture_stop`は装置のray aiming基準、`eye_reference`は眼瞳クリップと接続位置として扱う。初期版は模型眼内に第2の`aperture_stop`を作らない。
6. `position_mode: at_exit_pupil`を実際のコンパイル位置へ反映し、`fixed_offset`とともに直接テストする。
7. 初期capabilityは簡約Gullstrand、単色587.56 nm、固定4 mm瞳、無調節、平面網膜に限定する。

## 次段階の実装タスク案

- 正本仕様へ視覚評価コンポジット、終端・境界規約、結果schema、単位、初期制限を追加する。
- models/validation/compileへ境界index、末尾網膜sensor、`at_exit_pupil`実配置を追加する。
- afocal分析を境界までに限定し、網膜spot/PSF/MTFを境界後のsensorから生成する。
- 簡約Gullstrand眼の内部presetと、単色・平面網膜のgolden testを追加する。
- API/meta/capabilitiesとUIの評価モード・結果表示・i18nを追加する。
- 既存afocal系の射出瞳、アイレリーフ、角度MTFが不変である回帰テストを追加する。

## Backlog更新

`doc/reports/issues_backlog.md`のR34登録Issueを本調査の推奨方針、処方、受け入れ条件で更新した。新規Issueは追加していない。

## 検証根拠

- 正本参照: `doc/engine_spec.md` 6.7節、9.2節、24.2〜24.6節
- 実装参照: `optics_engine/models.py`、`optics_engine/validation.py`、`optics_engine/system.py`、`optics_engine/tracing.py`、`optics_engine/visual.py`
- 数値出典: [Handbook of Optical Systems sample, Table 36-8](https://application.wiley-vch.de/books/sample/3527403809_c01.pdf)
- 実施内容: コード検索と静的設計レビュー。コード変更がないためpytest/UI CI/プロセス再起動は対象外。
- 完了コミット: 本報告、R34 backlog更新、指示書のactive→done移動を含むR68コミット
