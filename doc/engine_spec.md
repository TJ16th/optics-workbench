# 光学シミュレーションエンジン 要求仕様・技術仕様書（v2.3）

## 改訂履歴

### v2.3における主な改訂点（小改訂）

クライアント（Workbench UI v0.3）の日英対応を成立させるための小改訂。エンジン自体は多言語化しない。

1. **エラー・警告コード規約を新設**（26.10節）。全エラー・警告は機械可読コード＋構造化パラメータ＋英語フォールバック文（message_en）で返す。表示文言の組み立て・翻訳はクライアント責務とし、エンジンはロケールを持たない。既存のエラー例（10.3節等）もこの形式に統一する。
2. **`GET /v1/meta` に列挙情報を追加**（26.9節）。metric名・エラーコード・警告コード・光線ステータス・変数キーパターンの全列挙を返し、クライアントが用語集・エラーカタログのカバレッジをCIで機械検証できるようにした。

### v2.2における主な改訂点

外部最適化（特にDLS / Levenberg-Marquardt系）を実用的に成立させるため、最適化インターフェースを全面改訂した。最適化アルゴリズム自体を外部に置く境界線（25.1節）は変更していない。

1. **評価APIをオペランドベクトル形式へ改訂**（25.3節）。target / toleranceによる正規化を定義し、オペランドごとの残差ベクトルを返却する。従来のmerit（正規化値の重み付き和。normalizedの定義が未規定だった）は廃止し、meritは残差二乗和＋ペナルティの導出値とした。DLS系最適化が要求する残差ベクトルとヤコビアンを返せる構造になった。
2. **光線破綻の連続ペナルティと決定論保証を新設**（25.5節）。TIR・ケラレ・aiming失敗を光線ロス率に比例した連続ペナルティ（疑似オペランド）として扱い、ハードなinfeasibleと区別する。同一リクエストに対するmerit再現性の規約を定義した。
3. **最適化変数のキー体系を定義し、曲率空間を推奨**（25.6節）。radius空間は平面（R=±∞）をまたぐ際に特異となるため、最適化には curvature（c=0で平面を滑らかに通過）を推奨する。conic・非球面係数・群位置の変数化キーを追加した。
4. **ヤコビアンバッチモードを新設**（25.7節）。1リクエストで全変数の有限差分ヤコビアンを計算し、摂動候補間でCompiledSystem・瞳サンプリング・aiming warm startを共有する。将来の自動微分（25.8節）への差し替え時もAPI形状を変えない。
5. **edge_thicknessオペランド（10.3節・25.2節）、近軸像距離solve（26.3節・26.6節）、gaussian_quadrature瞳サンプリング（15.3節）を追加**。エッジ厚制約の正式化、最終空気間隔の等式制約の自動解決、少数光線での高精度RMS評価により、最適化ループの制約表現と単価を改善する。

### v2.1における主な改訂点

UI仕様（Optics Workbench v0.1）のレビューで発覚した、エンジン側に責務を持つべき未定義事項を修正した。

1. **評価面とimage_plane_policyを新設**（21.5節）。像面依存の解析APIが評価面ポリシー（fixed_sensor / paraxial_image / best_focus_rms / best_focus_mtf / best_focus_merit / custom_offset / sweep）をパラメータとして受け取る仕様とし、`/v1/solve/best-focus` をrms / MTF / merit基準およびsweep（focus curve）へ拡張した。apply_toの責務分界を定義し、系定義への書き戻し（sensor_surface）はエンジンではなくクライアント側の操作とした（エンジンのstateless原則を維持）。
2. **artifactの取得エンドポイントと生存期間を定義**（26.9節）。`GET /v1/artifacts/{category}/{id}` を追加し、artifactは揮発性（TTL・プロセス再起動で消滅）であること、永続化はクライアント責務であることを明記した。
3. **6.3節のカセグレン例の数値を修正**。旧例（R2=-500, d=700, 像面800）は近軸検算の結果、実像を結ばず（|f2|=250 < f1-d=300 で副鏡通過後に発散）、副鏡径も軸上光束（半径30mm）に対し不足（semiD 25）していた。検証済みの数値（R2=-1050, d=650, 像距離1050, semiD 40）に差し替えた。
4. **`GET /v1/health` と `GET /v1/meta` を追加**（26.10節）。バージョン一式・capabilitiesを返すメタ情報エンドポイントを定義し、クライアントのversion mismatch検出を可能にした。

### v2における主な改訂点

レビュー結果に基づき、以下を改訂した。

1. **瞳モデルとRay Aimingの章を新設**（第16章）。絞り面基準のray aimingを必須仕様とし、瞳サンプリングの基準面・放射量論的な均一性の定義を明確化した。
2. **近軸計算の章を新設**(第14章）。EFL・F値・BFL・瞳位置などの導出評価値の基盤として近軸トレースを一級市民の仕様とした。偏芯系における近軸量の定義規約を追加した。
3. **ミラー後の伝播規約を明文化**（6.3節・17.4節）。thickness符号規約を定め、初期版の対象を同軸反射系までに限定。折り返し斜鏡系は将来拡張とした。反射望遠鏡の中央遮蔽用に円環（annulus）絞り形状を追加した。
4. **アフォーカル評価モードを新設**（9.2節・24.2節）。双眼鏡・望遠鏡（接眼込み）向けに、評価面＝射出瞳・評価量＝角度とするデータモデルとトレースパイプラインを明示した。
5. **field角度の合成規約を明文化**（4.3節）。tanベースの方向ベクトル合成を採用した。
6. **M/S像面の算出にCoddington方程式を併用**（21.2節）。同軸系はCoddington、偏芯系はRMS探索とし、相互検証に使う。
7. **歪曲の基準焦点距離を定義固定**（21.3節）。基準同軸状態・主波長の近軸EFLを用いる。
8. **周辺光量の定義を放射量論ベースに統一**（21.4節）。物体空間の立体角均一サンプリングによりcos^4則が自然に導出される定式化とした。
9. **高速化方針を全面改訂**（第27章）。性能目標はNumPyベクトル化（Level 1）で達成可能との見立てを明記し、真のボトルネック（validation・パース・システムコンパイル）への対策としてCompiledSystemキャッシュを一級市民化。JAXの位置づけを「自動微分による勾配提供」に変更し、Rust/C++の優先度を下げた。キャッシュの部分無効化粒度を仕様化した。
10. **バリデーション規約を追加**（10.3節）。ズーム群移動による空気間隔の負値・群干渉のチェックを追加した。
11. **双眼鏡のposeにチルトを追加**（24.7節）。コリメーション誤差の模擬を可能にした。
12. **Golden Test を検証項目に追加**（30.5節）。既知設計・既存OSSとの突き合わせによる符号規約バグの早期検出を仕様化した。

---

## 0. 文書の目的

本書は、写真レンズ・双眼鏡・望遠鏡を対象とした光学シミュレーションエンジンの仕様を定義する。

本エンジンは、軸対称のレンズ面・ミラー面・絞り・センサー・理想薄レンズを組み合わせ、3次元光線追跡、収差解析、PSF/MTF評価、周辺光量評価、双眼鏡・望遠鏡向けの視覚系評価を行う。

主な目的は以下である。

1. 光学初学者・写真愛好家向けの教育用シミュレーション
2. 簡易的なレンズ設計・構成検討
3. 外部最適化エンジンから呼び出せる評価エンジン
4. 写真レンズ・双眼鏡・望遠鏡の違いを同一の光線追跡基盤で扱うこと

---

## 1. ソフトウェアの目的

### 1.1 教育用途

本ソフトの第一目的は、光学に詳しくないユーザーが、レンズの基本原理を直感的に理解できるようにすることである。

想定する学習内容は以下。

* 凸レンズ・凹レンズで光線がどう曲がるか
* 焦点距離が変わると画角がどう変わるか
* 絞りを絞ると光線束がどう変わるか
* フォーカス群を動かすと結像位置がどう変わるか
* 非球面が球面収差をどう補正するか
* ガラス材料によって色収差がどう変わるか
* 周辺画角でコマ収差・非点収差・像面湾曲がどう出るか
* 手ブレ補正群をシフトすると光線束がどう変化するか
* レンズ群をチルトすると像面がどう傾くか
* 双眼鏡では射出瞳・アイレリーフ・アイボックスがなぜ重要か
* 望遠鏡では口径・倍率・接眼レンズが見え方にどう効くか

教育用途では、数値精度よりも「変化が見えること」「操作に対してすぐ反応すること」を重視する。

### 1.2 簡易設計・試作用途

本ソフトの第二目的は、ユーザーが簡易的にレンズ構成を作り、性能を評価できるようにすることである。

想定する作業は以下。

* 単レンズ・複数枚レンズの構成検討
* 凸凹レンズの組み合わせによる焦点距離・収差変化の確認
* ズーム群・フォーカス群の移動による性能変化の確認
* 絞り位置の変更による収差・周辺光量の変化確認
* 簡易的な最適化ループによる曲率・間隔・硝材の探索
* 撮像面上のスポット、PSF、MTF、歪曲、周辺光量の比較
* 双眼鏡・望遠鏡の倍率、射出瞳、アイレリーフ、視野の評価

ただし、初期版では商用光学設計ソフトと同等の厳密な最適化・公差解析・製造性評価までは対象外とする。

### 1.3 API評価エンジン用途

本エンジンは、GUIから直接使うだけでなく、外部アプリケーションや最適化エンジンからAPI経由で呼び出せる構成とする。

```
GUI / 教育UI / 最適化プログラム
        ↓
    HTTP API
        ↓
光学シミュレーションエンジン
        ↓
光線経路・収差・PSF・MTF・評価値
```

自動最適化そのものは本エンジン外で実行してよい。
本エンジンは、設計候補に対する評価値を安定して返す役割を持つ。

---

## 2. ターゲットユーザー

### 2.1 主なユーザー

| ユーザー | 主な目的 |
|---|---|
| 写真愛好家 | レンズの仕組みを視覚的に理解する |
| 光学初学者 | 収差・絞り・焦点距離・画角を学ぶ |
| 教育コンテンツ制作者 | 光線図や収差図を教材として生成する |
| 個人開発者 | 簡易レンズ設計・可視化ツールを作る |
| 研究・試作用途のエンジニア | レンズ構成案を簡易評価する |
| 双眼鏡・望遠鏡愛好家 | 倍率・射出瞳・視野・見え味を理解する |
| 最適化アルゴリズム開発者 | 外部最適化から評価APIを呼び出す |

### 2.2 想定スキルレベル

本ソフトは、以下の2層のユーザーを想定する。

**初学者・教育向けユーザー**

* 数式を知らなくても操作できる
* 光線の動きが視覚的にわかる
* 絞り、焦点距離、収差、周辺光量を感覚的に理解できる

**設計・検討向けユーザー**

* レンズ面、曲率半径、硝材、間隔、有効径を編集できる
* 収差図、PSF、MTF、周辺光量を確認できる
* 外部最適化から評価値を利用できる

---

## 3. 対象光学系

### 3.1 初期対象

初期版で対象とする光学系は以下。

* 写真レンズ
    * 通常の中心射影系レンズ
    * 単焦点レンズ
    * ズームレンズ
    * フォーカス群を持つレンズ
    * 手ブレ補正群を持つレンズ
* 双眼鏡
* 望遠鏡
* レンズ＋ミラーを含む**同軸反射系**（カセグレン式・マクストフ式など、全要素の光軸が共通X軸上にある系）
* 理想薄レンズを含む簡易光学系
* シフト・チルトを含む偏芯光学系

**【v2改訂】反射系の範囲限定**

初期版で対応するミラー系は、光軸が折れ曲がらない同軸反射系までとする。ニュートン式の斜鏡のように光軸を90°折り返す系は、座標変換・可視化・群定義の複雑さが大きく増すため、将来拡張とする（17.4節参照）。

### 3.2 将来拡張対象

以下は将来拡張とする。

* 対角画角180°超の魚眼レンズ
* 光軸を折り返す斜鏡・プリズムを含む系（ニュートン式望遠鏡、ポロプリズム双眼鏡の完全モデル等）
* 自由曲面
* 回折光学素子
* 薄膜コーティング
* ゴースト・フレア
* 偏光
* 散乱
* 公差解析
* 熱変形
* 複屈折
* センサーのマイクロレンズ詳細モデル
* 実写画像への適用レンダリング

180°超魚眼については初期版の必須対象から外すが、field定義は角度ベースとしておき、将来拡張しやすい構造にする。

なお、ポロプリズム・ダハプリズムを含む双眼鏡は、初期版ではプリズムを「等価空気長を持つ平行平板ガラス」として直進展開したモデルで扱う。像の反転・正立化は幾何学的な折り返しとしては追跡せず、展開系として評価する。

---

## 4. 基本座標系

### 4.1 グローバル座標

本エンジンでは、光軸をX軸とする。

```
物体側                              像面側
 -X  ------------------------------> +X
          光の進行方向
```

* 光軸方向：X軸
* 水平方向：Y軸
* 垂直方向：Z軸
* 単位：mm
* 基本的な光の進行方向：+X

従来の光学資料では光軸をZ軸に取ることが多いが、本エンジンでは画面上で左から右へ光が進む直感性を優先し、+X方向を光の進行方向とする。

**【v2追記】外部ツールとの座標変換**

Zemax・CODE V・rayoptics等の既存ツールは光軸をZ軸に取る。外部フォーマットとの相互変換（インポート・エクスポート・Golden Test）では、以下の写像を標準とする。

```
外部(Z軸光軸) → 本エンジン(X軸光軸)
  Z → X（光軸）
  X → Y（水平）
  Y → Z（垂直）
```

この写像は右手系を保存する。ローダー・エクスポーター・検証コードはこの規約に従う。

### 4.2 ローカル面座標

各光学面はローカル座標系を持つ。

```
local x : 面頂点から光軸方向
local y : 面内水平
local z : 面内垂直
```

軸対称面では、ローカル座標内で以下の半径を使う。

```
r = sqrt(y^2 + z^2)
```

面形状はローカル座標内では軸対称として扱う。
ただし、面または群の配置はグローバル座標上でシフト・チルトできる。

重要な設計原則は以下である。

```
面形状は軸対称
配置は3次元
光線追跡は常に3次元
解析では上下左右対称を仮定しない
```

### 4.3 field角度の方向ベクトル合成規約【v2新設】

fieldを角度 (theta_y_deg, theta_z_deg) で指定する場合、無限遠物点からの光線方向ベクトルは以下の**tanベース合成**で定義する。

```
direction ∝ normalize([ 1, tan(theta_y), tan(theta_z) ])
```

ここで theta_y はX軸からY方向への傾き、theta_z はX軸からZ方向への傾きである。

この規約を採用する理由は以下。

* 中心射影（ピンホール）モデルにおいて、理想像高 h = f・tan(theta) と整合する
* センサー上の矩形グリッドと物体側の角度グリッドが線形対応する
* 歪曲評価（21.3節）の定義と一貫する

回転合成（Y軸回転→Z軸回転の順次適用）はtanベースと広角で差が生じるため、採用しない。ただし将来の魚眼対応時には、投影モデルごとに合成規約を切り替えられる構造とする。

field定義には合成済み方向ベクトルの直接指定も許可する。

```yaml
fields:
  - id: custom_dir
    type: direction
    direction: [0.94, 0.0, 0.342]
```

---

## 5. 曲率半径・平面の扱い

### 5.1 曲率半径の符号

曲率半径 radius_mm は以下の規約で定義する。

| 値 | 意味 |
|---|---|
| R > 0 | 曲率中心が面頂点より +X 側にある |
| R < 0 | 曲率中心が面頂点より -X 側にある |
| R = 0 | 平面として扱う |

### 5.2 平面の扱い

本仕様では、入力データ上は radius_mm = 0 を平面として扱う。

```
radius_mm = 0 の場合、その面は平面
```

内部計算では曲率 c を以下で定義する。

```
if radius_mm == 0:
    curvature = 0
else:
    curvature = 1 / radius_mm
```

外部データから inf, Infinity, ∞ が読み込まれた場合は、ローダー側で radius_mm = 0 に正規化する。

なお、この規約は一般的な光学ソフト（平面 = 曲率半径∞）と異なる非標準規約であることを認識した上で採用する。JSON/YAMLで無限大の扱いが処理系依存になることを避けるための実装上の判断であり、外部との境界では必ずローダー・エクスポーターで正規化する。

---

## 6. 光学要素

### 6.1 対応する要素

初期版で扱う光学要素は以下。

| kind | 内容 |
|---|---|
| refractive | 屈折面 |
| mirror | 反射面 |
| aperture_stop | 可動絞り |
| mechanical_aperture | 固定絞り・メカ枠 |
| thin_lens | 理想薄レンズ |
| sensor | 撮像面 |
| eye_reference | 射出瞳・眼基準面（アフォーカル評価用）【v2新設】 |
| dummy | 群境界・座標参照面 |

### 6.2 屈折面

屈折面では、面交点、面法線、入射側屈折率、出射側屈折率からSnellの法則に基づいて出射方向を計算する。

### 6.3 ミラー面と伝播規約【v2改訂】

ミラー面では反射のみを行う。

反射方向 R は、入射方向 I、面法線 N から以下で求める。

```
R = I - 2 dot(I, N) N
```

**伝播方向と厚みの符号規約**

ミラーで反射した後、光はX軸負方向へ進む。シーケンシャル追跡における規約を以下に定める。

1. 各光線セグメントは伝播方向符号 propagation_sign ∈ {+1, -1} を持つ。初期値は +1。
2. ミラー面を通過するたびに propagation_sign を反転する。
3. thickness_after_mm は「次面頂点までの光路に沿った距離」であり、**ミラー反射後の区間では負値で記述する**（Zemax等の慣例に合わせる）。

例：カセグレン式望遠鏡【v2.1修正：近軸検証済みの数値に差し替え】

```yaml
surfaces:
  - id: M1            # 主鏡（凹, f1 = 1000）
    kind: mirror
    radius_mm: -2000.0
    thickness_after_mm: -650.0     # 反射後、-X方向へ650mm
    semi_diameter_mm: 100.0
  - id: M2            # 副鏡（凸, |f2| = 525）
    kind: mirror
    radius_mm: -1050.0
    thickness_after_mm: 1050.0     # 再反射後、+X方向へ1050mm
    semi_diameter_mm: 40.0
  - id: IMG
    kind: sensor
```

近軸検算（口径半径100mmのマージナル光線）：

```
y=100, u=0
M1後: u = -100/1000 = -0.1
M2位置(650mm): y = 100 - 0.1*650 = 35   → M2半径40mm内、ケラレなし
M2後: u = -0.1 + 35/525 = -0.0333
結像: 35/0.0333 = 1050mm後（M1頂点の+X側400mm）
EFL = 100/0.0333 = 3000mm, F/15
```

副鏡が実像を結ぶには |f2| > f1 - d が必要である（本例：525 > 350）。この条件を満たさない構成（例：|f2|=250, d=700 → f1-d=300）では副鏡通過後に光束が発散し実像を結ばないため、validateは主鏡・副鏡の近軸検算による結像可否チェックを警告として実装してよい。

4. 屈折率の符号反転規約（反射後 n < 0）は**採用しない**。屈折率は常に正とし、伝播方向は propagation_sign で管理する。近軸計算（第14章）でも同じ規約を使う。
5. validateエンドポイントは、thickness符号とミラー枚数の整合（奇数回反射後は負、偶数回反射後は正）を検査し、不整合をエラーとする。

**初期版の制約**

初期版では、ミラー面のローカル光軸はグローバルX軸と同軸であることを前提とする（同軸反射系）。ミラーへのチルト適用は微小量（公差・偏芯シミュレーション用途）に限り許可し、光軸を90°折り返す用途には対応しない。

### 6.4 絞り

絞りは光線の通過可否のみを判定する。

* 固定絞り
* 可動絞り
* メカ枠
* 視野絞り
* 有効径制限

を同じ枠組みで扱う。

対応する開口形状は以下。【v2改訂：annulus追加】

| shape | 内容 | 主用途 |
|---|---|---|
| circle | 円形開口 | 通常の絞り |
| annulus | 円環開口（中央遮蔽） | 反射望遠鏡の副鏡遮蔽 |
| polygon | 正多角形開口 | 絞り羽根形状（将来拡張） |

annulus定義例：

```yaml
- id: OBSCURATION
  kind: mechanical_aperture
  aperture:
    shape: annulus
    outer_semi_diameter_mm: 100.0
    inner_semi_diameter_mm: 30.0    # この半径以下は遮光
```

### 6.5 センサー

センサーはX軸に垂直な平面として定義する。
センサー面上の座標は sensor_y_mm, sensor_z_mm で扱う。

```yaml
- id: IMG
  kind: sensor
  sensor:
    width_mm: 36.0
    height_mm: 24.0
    pixel_pitch_um: 4.0
    normal: [-1.0, 0.0, 0.0]
```

### 6.6 理想薄レンズ

理想薄レンズは、厚みを持たず、焦点距離に基づいて光線方向を変える特別要素である。

用途は以下。

* 教育用の概念説明
* レンズ群の簡略化
* 単純な望遠鏡・双眼鏡モデル
* 実レンズ追跡のテスト
* 高速な概略検討

定義例：

```yaml
- id: TL1
  kind: thin_lens
  focal_length_mm: 100.0
  semi_diameter_mm: 25.0
  thickness_after_mm: 120.0
```

薄レンズでは、光線が薄レンズ面と交差した点を通り、焦点距離に対応した方向へ変換される。
物理的な屈折率境界を持たない特別要素として扱う。

### 6.7 眼基準面（eye_reference）【v2新設】

アフォーカル系（双眼鏡・接眼込み望遠鏡）の評価では、センサーの代わりに眼基準面を終端要素として置く。

```yaml
- id: EYE
  kind: eye_reference
  eye:
    pupil_diameter_mm: 4.0          # 仮想眼瞳径
    position_mode: at_exit_pupil    # at_exit_pupil | fixed_offset
    offset_from_last_surface_mm: null
```

* position_mode: at_exit_pupil の場合、エンジンが計算した射出瞳位置に自動配置される
* 評価量は「眼基準面を通過する光線の角度分布」となる（24.2節参照）
* アイボックス評価では、この面をY/Z/X方向へ仮想的に動かして通過率を評価する

---

## 7. 面形状

### 7.1 球面

球面は radius_mm により定義する。

```yaml
surface_type: spherical
radius_mm: 50.0
```

radius_mm = 0 の場合は平面。

### 7.2 偶数次非球面

非球面の sag は、ローカルX方向変位として定義する。

```
x(r) =
  c r^2 / { 1 + sqrt(1 - (1 + k)c^2 r^2) }
  + A4 r^4
  + A6 r^6
  + A8 r^8
  + ...
```

ここで、

```
c = 1 / R
k = conic constant
r = sqrt(y^2 + z^2)
```

データ例：

```yaml
- id: S3
  kind: refractive
  surface_type: aspherical_even
  radius_mm: 32.5
  conic: -1.2
  asphere_coefficients:
    A4: 1.2e-6
    A6: -3.4e-10
    A8: 5.0e-14
  thickness_after_mm: 3.0
  material_after: N-BK7
  semi_diameter_mm: 15.0
```

---

## 8. 材料定義

### 8.1 材料モデル

材料は以下の形式を許可する。

| type | 内容 |
|---|---|
| constant | 波長に依存しない屈折率 |
| nd_vd | nd / Vd から近似分散を生成 |
| sellmeier | Sellmeier係数から屈折率を計算 |
| catalog | カタログ硝材IDを参照 |
| custom_table | 波長-屈折率テーブル補間 |

### 8.2 Sellmeier式

Sellmeier式は以下とする。

```
n(λ)^2 - 1 =
B1 λ^2 / (λ^2 - C1)
+ B2 λ^2 / (λ^2 - C2)
+ B3 λ^2 / (λ^2 - C3)
```

λはµm単位とする。

### 8.3 波長定義

標準波長は以下を用意する。

```yaml
wavelength_presets:
  F: 486.13
  e: 546.07
  d: 587.56
  C: 656.27
```

---

## 9. 光学系データモデル

### 9.1 全体構造

```yaml
optical_system:
  name: sample_lens
  units: mm
  optical_axis: +X
  system_type: focal          # focal | afocal 【v2新設】
  wavelengths_nm:
    primary: 587.56
    samples: [486.13, 546.07, 587.56, 656.27]
  materials:
    - id: AIR
      type: constant
      n: 1.0
    - id: N-BK7
      type: sellmeier
      B: [1.03961212, 0.231792344, 1.01046945]
      C: [0.006000699, 0.0200179144, 103.560653]
  surfaces:
    - id: S1
      kind: refractive
      surface_type: spherical
      radius_mm: 50.0
      thickness_after_mm: 5.0
      material_after: N-BK7
      semi_diameter_mm: 20.0
    - id: S2
      kind: refractive
      surface_type: spherical
      radius_mm: -50.0
      thickness_after_mm: 15.0
      material_after: AIR
      semi_diameter_mm: 20.0
    - id: STOP
      kind: aperture_stop
      thickness_after_mm: 10.0
      aperture:
        shape: circle
        semi_diameter_mm: 8.0
    - id: IMG
      kind: sensor
      thickness_after_mm: 0.0
      sensor:
        width_mm: 36.0
        height_mm: 24.0
        pixel_pitch_um: 4.0
```

**絞り面の指定**

kind: aperture_stop を持つ面は系内にちょうど1つ存在しなければならない（開口絞り）。mechanical_aperture は複数置いてよい。開口絞り面は、ray aiming（第16章）と近軸瞳計算（第14章）の基準面となる。

### 9.2 アフォーカル系のデータモデル【v2新設】

双眼鏡・接眼込み望遠鏡は system_type: afocal とし、終端要素を sensor ではなく eye_reference とする。

```yaml
optical_system:
  name: sample_binocular_channel
  system_type: afocal
  surfaces:
    - {}   # 対物レンズ群
    - {}   # プリズム展開平行平板
    - {}   # 視野絞り
    - {}   # 接眼レンズ群
    - id: EYE
      kind: eye_reference
      eye:
        pupil_diameter_mm: 4.0
        position_mode: at_exit_pupil
```

focal系とafocal系の違いは以下の通り。

| 項目 | focal | afocal |
|---|---|---|
| 終端要素 | sensor | eye_reference |
| 像の記録量 | 面上座標 (y, z) mm | 射出角度 (theta_y, theta_z) deg |
| spot/PSFの単位 | µm | arcmin または mrad |
| MTFの単位 | lp/mm | cycles/degree |
| 歪曲の基準 | h = f・tan(theta) | 角倍率の線形性 |
| 合焦評価 | 像面X位置 | 射出光束の平行度（ディオプター） |

afocal系では、1つの物点から出た光線束が eye_reference 通過後にどれだけ平行に揃っているかを合焦品質として評価する。残存する発散/収束はディオプター単位で報告する。

```json
{
  "field_id": "center",
  "residual_divergence_diopter": -0.12
}
```

---

## 10. 群・ブロック定義

### 10.1 群の目的

ズーム群、フォーカス群、手ブレ補正群、チルト群などを扱うため、複数の面を群としてまとめる。

```yaml
groups:
  - id: G1
    name: front_group
    from_surface: S1
    to_surface: S4
  - id: FOCUS_G
    name: focus_group
    from_surface: S8
    to_surface: S10
  - id: OIS_G
    name: image_stabilization_group
    from_surface: S12
    to_surface: S13
```

from_surface から to_surface までを含む。

### 10.2 ズーム・フォーカス位置

ズーム位置やフォーカス位置に応じて、群のX方向位置を変えられる。

```yaml
zoom_positions:
  - id: wide
    focal_length_nominal_mm: 24.0
    group_positions:
      G1:
        shift_x_mm: 0.0
      G2:
        shift_x_mm: 12.0
  - id: tele
    focal_length_nominal_mm: 70.0
    group_positions:
      G1:
        shift_x_mm: 6.0
      G2:
        shift_x_mm: 3.0
```

### 10.3 群移動のバリデーション【v2新設】

群のX方向移動により物理的に不可能な構成が生じ得るため、validateおよび各解析エンドポイントは構成適用後に以下を検査する。

| 検査 | 内容 | 違反時 |
|---|---|---|
| 空気間隔の負値 | 群移動適用後の全空気間隔 ≥ 最小値（既定 0.0 mm） | エラー |
| 群の交差 | 隣接群の面頂点X座標の順序逆転 | エラー |
| 有効径の干渉 | 面頂点間隔がsag量を下回る場合の面同士の接触 | 警告 |
| エッジ厚【v2.2追加】 | 隣接面間の周縁厚（頂点間隔にsag差を加味し、両面の有効半径の小さい方 `min(semiD_a, semiD_b)` の位置で評価）が最小値を下回る | 警告。評価値 edge_thickness としても出力（25.2節）し、最適化では連続制約として扱える |
| 最小空気間隔制約 | ユーザー指定の min_air_gap_mm を下回る | 警告（最適化ではペナルティ化可能） |

最適化バッチ評価では、違反候補に対してトレースを実行せず、constraint_penalty を含むエラー応答を即時返却する（27章の高速化とも整合）。

```json
{
  "status": "infeasible",
  "violations": [
    {
      "type": "negative_air_gap",
      "between": ["S4", "S5"],
      "gap_mm": -0.35
    }
  ]
}
```

---

## 11. シフト・チルト

### 11.1 シフト

シフトは、指定した面範囲または群を光軸に垂直な方向へ平行移動する操作である。

光軸がX軸なので、シフト量はY/Z方向で指定する。

```yaml
decenters:
  - id: OIS_SHIFT_1
    from_surface: S12
    to_surface: S13
    shift_y_mm: 0.12
    shift_z_mm: -0.04
```

群IDで指定してもよい。

```yaml
decenters:
  - id: OIS_SHIFT_1
    group: OIS_G
    shift_y_mm: 0.12
    shift_z_mm: -0.04
```

### 11.2 チルト

チルトは、指定した面範囲または群を、指定した回転中心まわりに傾ける操作である。

```yaml
tilts:
  - id: TILT_G1
    from_surface: S5
    to_surface: S7
    tilt_y_deg: 1.5
    tilt_z_deg: 0.0
    roll_x_deg: 0.0
    rotation_center:
      reference: from_surface_vertex
      offset_x_mm: 2.0
      offset_y_mm: 0.0
      offset_z_mm: 0.0
```

回転中心は、対象範囲の最も若い面、つまり from_surface の面頂点を基準とし、そこからのオフセットで指定する。

### 11.3 チルト軸

| パラメータ | 意味 |
|---|---|
| tilt_y_deg | Y軸まわりの回転。X-Z平面内で傾く |
| tilt_z_deg | Z軸まわりの回転。X-Y平面内で傾く |
| roll_x_deg | X軸まわりの回転 |

通常のレンズ群チルトでは、tilt_y_deg または tilt_z_deg を使う。

### 11.4 非対称系の扱い

シフト・チルトが存在する光学系では、上下左右対称を仮定しない。

したがって、収差解析・周辺光量解析・PSF/MTF評価では、必ずプラス側・マイナス側のfieldを評価できるようにする。

```yaml
field_grid:
  theta_y_deg: [-20, -10, 0, 10, 20]
  theta_z_deg: [-15, -7.5, 0, 7.5, 15]
```

偏芯系ではray aimingが必須となる（第16章）。また、近軸量は基準同軸状態で定義する（14.4節）。

---

## 12. 光線モデル

### 12.1 Ray構造

光線は3次元ベクトルとして扱う。

```json
{
  "id": "ray_000001",
  "origin": [0.0, 0.0, 0.0],
  "direction": [1.0, 0.0, 0.0],
  "wavelength_nm": 587.56,
  "weight": 1.0,
  "status": "alive",
  "propagation_sign": 1
}
```

direction は常に正規化する。propagation_sign はミラー系の伝播方向管理に使う（6.3節）。

### 12.2 光線ステータス

```
alive
hit_sensor
hit_eye_reference
blocked_by_aperture
missed_surface
total_internal_reflection
reflected
refracted
numerical_error
aiming_failed
```

【v2追記】hit_eye_reference はアフォーカル系の正常終端、aiming_failed はray aiming（第16章）が収束しなかった光線を示す。

全反射時の挙動はオプションで選べる。

```
tir_behavior: terminate
```

または、

```
tir_behavior: reflect
```

初期の通常レンズ解析では terminate を既定とする。

---

## 13. 屈折・反射計算

### 13.1 Snellの法則

屈折はSnellの法則に基づく。

```
n1 sin(theta1) = n2 sin(theta2)
```

### 13.2 ベクトル形式の屈折

入射方向を I、面法線を N、入射側屈折率を n1、出射側屈折率を n2 とする。

```
eta = n1 / n2
cos_i = -dot(N, I)
sin2_t = eta^2 * (1 - cos_i^2)
```

sin2_t > 1 の場合は全反射。

屈折方向 T は以下。

```
T = eta * I + (eta * cos_i - sqrt(1 - sin2_t)) * N
```

ここで N は、入射光線に対して逆向き、つまり dot(N, I) <= 0 となるように向きを揃える。

### 13.3 反射

反射方向は以下。

```
R = I - 2 dot(I, N) N
```

---

## 14. 近軸計算【v2新設】

### 14.1 目的

EFL、F値、BFL、瞳位置・瞳径、倍率、理想像高といった導出評価値の多くは近軸量に依存する。また、ray aiming（第16章）の初期値、ベストフォーカス探索の初期値、教育UIでの焦点距離表示にも近軸量を使う。本章で近軸トレースを一級市民の仕様として定義する。

### 14.2 近軸トレース

y-nu法（高さy・換算傾角nu）による近軸光線追跡を実装する。

```
屈折:   n' u' = n u - y * c * (n' - n)
転送:   y' = y + t * u'
```

* 球面・非球面は頂点曲率 c（非球面はベース曲率）で扱う
* 薄レンズは u' = u - y / f で扱う
* ミラーは反射として扱い、伝播方向は propagation_sign で管理する（屈折率の符号反転は行わない。6.3節と同一規約）
* 平面（c = 0）は屈折のみ

2本の基準近軸光線を追跡する。

| 光線 | 定義 | 用途 |
|---|---|---|
| 近軸周辺光線（marginal） | 軸上物点から絞り縁を通る | EFL、BFL、F値、瞳径 |
| 近軸主光線（chief） | 最大field角から絞り中心を通る | 瞳位置、理想像高、倍率色収差基準 |

### 14.3 出力する近軸量

| 評価値 | 内容 |
|---|---|
| effective_focal_length_mm | 実効焦点距離（EFL） |
| back_focal_length_mm | 最終面から近軸像面までの距離 |
| front_focal_length_mm | 前側焦点距離 |
| f_number | 無限遠F値 = EFL / 入射瞳径 |
| working_f_number | 有限距離実効F値 |
| entrance_pupil_position_mm | 第1面基準の入射瞳位置 |
| entrance_pupil_diameter_mm | 入射瞳径 |
| exit_pupil_position_mm | 最終面基準の射出瞳位置 |
| exit_pupil_diameter_mm | 射出瞳径 |
| paraxial_image_position_mm | 近軸像面位置 |
| paraxial_magnification | 近軸横倍率（有限距離時） |
| angular_magnification | 角倍率（afocal系） |
| principal_plane_positions_mm | 前側・後側主点位置 |

afocal系では、近軸周辺光線の入出射高さ比から角倍率を求め、EFL・F値の代わりに角倍率・射出瞳径を主要仕様とする。

### 14.4 偏芯系における近軸量の定義規約

シフト・チルトを含む系では厳密な意味での近軸量が定義できない。本エンジンでは以下の規約を採用する。

```
近軸量は、すべての decenters / tilts をゼロにした
「基準同軸状態」に対して定義・計算する。
```

* 歪曲の基準焦点距離（21.3節）、理想像高、F値表示はすべて基準同軸状態の近軸量を使う
* zoom_positions による群X移動は基準同軸状態に含める（ズーム位置ごとに近軸量は変わる）
* API応答には "paraxial_reference": "coaxial_baseline" を明記する

### 14.5 API

```
POST /v1/analysis/paraxial
```

近軸量一式をJSONで返す。他の解析エンドポイントも応答に paraxial セクションを含められる。

---

## 15. 光線生成とfield定義

### 15.1 無限遠物点

通常の写真レンズでは、物点を角度で定義する。

```yaml
fields:
  - id: center
    type: angular
    theta_y_deg: 0.0
    theta_z_deg: 0.0
  - id: upper
    type: angular
    theta_y_deg: 0.0
    theta_z_deg: 20.0
  - id: lower
    type: angular
    theta_y_deg: 0.0
    theta_z_deg: -20.0
```

光軸がX方向なので、角度はX軸からの傾きとして扱う。方向ベクトルへの合成は4.3節のtanベース規約に従う。

### 15.2 有限距離物点

有限距離物点は3次元座標で定義する。

```yaml
object_points:
  - id: P0
    position_mm: [-1000.0, 0.0, 0.0]
    ray_bundle:
      mode: aim_to_stop        # 【v2改訂】既定はray aiming
      samples: 256
```

### 15.3 瞳サンプリング分布

光線束のサンプリング分布は以下から選ぶ。サンプリングの基準面・aiming方法は第16章で定義する。

| distribution | 内容 |
|---|---|
| grid | 矩形グリッド |
| polar | 極座標グリッド |
| hexapolar | 光学解析向けの同心円・六角配置 |
| gaussian_quadrature | 半径方向ガウス求積×等間隔方位角（既定3リング×6方位）。滑らかな収差のRMS系評価値を数十本で高精度に積分できる。最適化モードの既定【v2.2追加】 |
| random | ランダム（seed必須：25.5節の決定論規約） |
| sobol | 準乱数（seed必須：同上） |
| fan_y | Y方向ray fan |
| fan_z | Z方向ray fan |

---

## 16. 瞳モデルとRay Aiming【v2新設】

### 16.1 背景と方針

実レンズでは、入射瞳の位置・径はfieldごとに変化する（瞳収差）。特に広角レンズ・偏芯系では、近軸入射瞳を狙って光線を生成すると、開口絞りを均一に埋められず、以下の解析が系統的に歪む。

* spot / PSF の統計量（絞りを埋め切れない、または過剰に外れる）
* 周辺光量・ケラレ評価（通過率の分母が不正確になる）
* 主光線依存の評価（歪曲、M/S像面、倍率色収差、CRA）

したがって本エンジンでは、**開口絞り面を瞳サンプリングの基準面**とし、ray aimingを標準機構として実装する。

### 16.2 主光線のray aiming

主光線は「物点（またはfield方向）から出て、開口絞り面の中心を通る実光線」として定義する。

求め方：

1. 近軸主光線（14.2節）から初期の射出方向（無限遠field）または第1面通過点（有限距離）を推定する
2. 実光線追跡で絞り面到達点 (y_stop, z_stop) を求める
3. 目標 (0, 0) との残差に対して2次元Newton法（数値ヤコビアン）または割線法で射出パラメータを更新する
4. 残差ノルムが収束閾値（既定 1e-6 mm）以下になるまで反復する

```yaml
ray_aiming:
  mode: full            # full | paraxial | off
  target_surface: STOP  # 省略時は開口絞り面
  tolerance_mm: 1.0e-6
  max_iterations: 20
  fallback: paraxial    # 収束失敗時の挙動
```

* mode: full — 全光線をaimingする（解析・最適化の既定）
* mode: paraxial — 近軸入射瞳を狙って生成し、aiming反復をしない（教育previewの既定。高速だが広角で不正確）
* mode: off — 第1面を直接狙う（デバッグ・教材の単レンズ用）

収束失敗した光線は status: aiming_failed とし、統計から除外した上で件数を応答に含める。

### 16.3 瞳全体のaiming

周辺光線を含む光線束は、正規化瞳座標 (px, pz) ∈ 単位円 を絞り面上の実座標へ写像して生成する。

1. 主光線aimingで絞り中心対応を求める
2. 絞り縁の4点（±py, ±pz方向）をaimingし、fieldごとの実効瞳のアフィン近似（中心＋楕円）を得る
3. 中間の瞳座標はこのアフィン写像で補間して射出し、必要精度に応じて個別に追加反復する

previewモードでは手順3の追加反復を省略し、アフィン近似のみで生成する。解析モードでは補間後の絞り面到達誤差が閾値を超える光線のみ追加反復する（27章の高速化と整合）。

### 16.4 偏芯・チルト系での扱い

decenters / tilts が存在する場合、瞳の中心・形状はY/Z非対称になるため、mode: full を強制する（paraxialへの自動フォールバックは警告付きで許可）。絞り縁サンプル点は4点ではなく8点以上に増やし、非対称な実効瞳形状を捉える。

### 16.5 周辺光量のためのサンプリング定義

周辺光量（relative illumination）を光線通過率で評価する場合、「どの空間で均一にサンプリングするか」が結果を決める。本エンジンでは以下を標準定義とする。

```
物体空間の各field方向について、
入射瞳の見込み立体角内で放射輝度一様（等立体角）に
光線を生成し、センサー到達エネルギーを積算する。
```

この定式化では、cos^4則（瞳の見込み立体角減少・斜入射投影）は**別途の近似項ではなく、光線追跡から自然に導出される**。旧仕様の「cos^4則による自然周辺減光：近似対応」は本定義に置き換える。

実装上は、絞り面上の等面積サンプリングに対し、光線ごとに幾何学的重み

```
weight = cos(theta_incident_on_stop) * (視線方向との投影因子)
```

を付与する方式でもよい（等立体角サンプリングと数学的に等価になるよう重みを定義する）。どちらの実装かはAPI応答のmetadataに明記する。

センサー入射角による感度低下（CRA感度）は従来通りオプションの乗算項として扱う。

---

## 17. 順方向光線追跡

順方向追跡は、物体側から像面側へ進む。

```
object / field
  ↓ (ray aiming: 第16章)
S1
  ↓
S2
  ↓
...
  ↓
sensor / eye_reference
```

### 17.1 各面での処理

1. 光線を面ローカル座標へ変換
2. 面との交点を求める
3. 有効径・絞り判定
4. 面法線を計算
5. 屈折・反射・薄レンズ変換を行う
6. 光線状態・propagation_signを更新
7. 光線経路を保存
8. 次面へ進む

### 17.2 交点計算

* 平面・球面は閉形式解を使う
* 非球面は球面（ベース曲率）交点を初期値としたNewton反復（27.7節の収束対策を適用）
* 交点は伝播方向前方（光路長 > 0）の解のみ採用する

### 17.3 有効径判定

面ローカル座標で sqrt(y^2 + z^2) > semi_diameter_mm の場合、光線を遮光する。annulus開口では inner/outer の両判定を行う。

### 17.4 ミラーを含む系の追跡【v2新設】

* ミラー面通過時に propagation_sign を反転する
* 次面への転送は thickness_after_mm の符号（6.3節）と propagation_sign の整合を前提とする
* 交点探索は伝播方向前方のみを対象とする（逆行解の誤採用を防ぐ）
* 副鏡遮蔽はannulus開口（6.4節）で表現する

初期版の対象は同軸反射系のみ。CompiledSystemのビルド時に、ミラー枚数・thickness符号・同軸性を検査する。

---

## 18. 逆方向光線追跡

逆方向追跡は、センサー側から物体側へ戻る。

```
sensor
  ↓
last surface
  ↓
...
  ↓
S1
  ↓
object side
```

逆方向では以下を行う。

* 面列を逆順に処理する
* 屈折率のbefore / afterを入れ替える
* ミラーは同じ反射式を使う（propagation_signも逆順で整合させる）
* 薄レンズは逆方向用の方向変換を行う
* センサー上の点と射出瞳サンプリングから光線を生成する（射出瞳位置は近軸計算またはaimingで求める）

用途は以下。

* センサー画素が見ている物体方向の推定
* 歪曲マップ生成
* ケラレ評価
* センサー入射角評価
* レンダリング連携
* 双眼鏡・望遠鏡の射出瞳評価

---

## 19. 絞り・有効径

### 19.1 面ごとの有効径

各面は semi_diameter_mm を持つ。

```yaml
semi_diameter_mm: 18.5
```

面ローカル座標で以下を満たさない場合、光線は遮光される。

```
sqrt(y^2 + z^2) <= semi_diameter_mm
```

### 19.2 固定絞り

```yaml
- id: MECH_AP_1
  kind: mechanical_aperture
  aperture:
    shape: circle
    semi_diameter_mm: 12.0
  thickness_after_mm: 3.0
```

### 19.3 可動絞り

```yaml
- id: IRIS
  kind: aperture_stop
  aperture:
    shape: circle
    semi_diameter_mm:
      variable: iris_radius_mm
      default: 5.6
```

API呼び出し時に以下のように指定する。

```json
{
  "variables": {
    "iris_radius_mm": 4.0
  }
}
```

可動絞り径の変更はray aimingの瞳写像キャッシュを無効化する（周辺光線aimingの再計算が必要。主光線aimingは絞り中心が不変なら再利用可能。27.6節参照）。

---

## 20. 光線サンプリング密度

### 20.1 基本パラメータ

解析ごとに光線密度を指定できるようにする。

```yaml
ray_sampling:
  samples_per_field: 1024
  pupil_distribution: hexapolar
  pupil_radius_normalized: 1.0
  include_chief_ray: true
  include_marginal_rays: true
  ray_aiming:
    mode: full
```

### 20.2 解析別の推奨値

| 解析 | 推奨サンプル |
|---|---|
| 教育用光線表示 | 5〜100 rays / field |
| Ray fan | 21〜101 rays / fan |
| Spot diagram | 256〜4096 rays / field |
| 幾何PSF | 4096〜100000 rays / field |
| M/S像面探索 | 256〜4096 rays / field |
| 周辺光量 | 1000〜100000 rays / field |
| 歪曲 | 主光線中心。ただしケラレ評価時は複数ray |
| 白色MTF | 複数波長 × PSF用サンプル |

---

## 21. 写真レンズ向け評価

### 21.1 基本出力

写真レンズ向けには、撮像面上の品質を評価する。

主な出力は以下。

| 出力 | 内容 |
|---|---|
| ray path | 光線経路 |
| spot diagram | センサー上の光線分布 |
| ray fan | 瞳座標に対する横収差 |
| longitudinal aberration | 縦収差 |
| chromatic aberration | 色収差 |
| distortion | 歪曲 |
| field curvature | 像面湾曲 |
| astigmatism | 非点収差 |
| M/S image surface | M像面・S像面 |
| PSF | 点像分布 |
| MTF | 空間周波数応答 |
| relative illumination | 周辺光量 |
| chief ray angle | センサー入射角 |

### 21.2 M像面・S像面【v2改訂】

M像面はメリディオナル像面、S像面はサジタル像面である。

**メリディオナル面**：光軸方向・field方向・主光線を含む平面。
**サジタル面**：主光線を含み、メリディオナル面に直交する平面。

算出方式は2種類を実装し、系の性質に応じて使い分ける。

**方式A：Coddington方程式（同軸系の既定）**

aimingで求めた主光線に沿って、Coddington方程式（微分光線追跡）を各面で適用し、メリディオナル・サジタルの像点位置を解析的に求める。

* 高速（主光線1本の追跡＋面ごとの漸化式のみ）
* 瞳サンプリングノイズがなく、field方向に滑らかな曲線が得られる
* 像面湾曲・非点収差図の生成に適する

**方式B：RMS最小探索（偏芯系・検証用）**

1. fieldを選ぶ
2. 瞳上に光線をサンプリングする（ray aiming適用）
3. メリディオナル方向・サジタル方向の光線群を抽出する
4. センサー近傍の複数X位置で交点分布を評価する
5. RMS幅が最小となるX位置をそれぞれ求める

* 偏芯・チルト系で主光線周りの局所対称性が崩れた場合でも定義可能
* ノイズに弱く低速なため、サンプル数と探索範囲を明示する

**使い分け規約**

| 系の状態 | 既定方式 |
|---|---|
| 同軸系 | Coddington（RMS探索はオプションで相互検証に使用） |
| decenters / tilts あり | RMS探索 |

両方式の結果差は検証項目とする（30.2節）。

出力例：

```json
{
  "field_id": "theta_z_20",
  "method": "coddington",
  "m_image_x_mm": 42.31,
  "s_image_x_mm": 41.86,
  "astigmatic_difference_mm": 0.45,
  "m_rms_um": 8.2,
  "s_rms_um": 6.9
}
```

### 21.3 歪曲【v2改訂】

通常レンズでは、理想像高を以下で定義する。

```
h_ideal = f_ref * tan(theta)
```

**基準焦点距離 f_ref の定義**

f_ref は「基準同軸状態（14.4節）・主波長における近軸EFL」とする。実光線ベースの実効焦点距離やfieldごとの局所倍率は使わない。この固定により、同一系に対する歪曲値が解析条件によって揺れることを防ぐ。

**実像高 h_actual の定義**

h_actual は、ray aimingで求めた主光線のセンサー面交点の像高とする。

```
h_actual = sqrt(sensor_y^2 + sensor_z^2)   （主光線の交点）
```

歪曲率は以下。

```
distortion_percent = 100 * (h_actual - h_ideal) / h_ideal
```

偏芯系では像高が方向依存になるため、fieldごとに (Δy, Δz) の2成分ベクトルとしても出力する。

初期版では、中心射影系レンズを対象とする。
180°超魚眼ではこの式が破綻するため、将来拡張で別投影モデル（等距離射影・等立体角射影など）を扱う。field角度の方向合成規約（4.3節）は投影モデルごとに切り替えられる構造としておく。

### 21.4 周辺光量【v2改訂】

周辺光量は、中心fieldを100%とした相対値で出力する。

```
relative_illumination(field) =
100 * flux(field) / flux(center)
```

**flux の定義**

flux は、16.5節で定義した放射量論的サンプリング（等立体角サンプリング、または等価な重み付き絞り面サンプリング）のもとで、センサーに到達した光線の重み和とする。

```
flux(field) = Σ weight(ray_i)   for rays that hit sensor
```

初期版で扱う要因は以下。

| 要因 | 対応 |
|---|---|
| 絞り・鏡筒によるケラレ | 対応（光線遮光として自然に反映） |
| レンズ有効径による遮光 | 対応（同上） |
| cos^4則による自然周辺減光 | **対応（16.5節の定式化により光線追跡から自然に導出。別途の近似項としない）** |
| センサー入射角による感度低下 | オプション（CRA感度カーブの乗算） |
| コーティング透過率 | 非対応 |
| ガラス吸収 | 非対応または簡易対応 |

サンプリング方式（等立体角 or 重み付き絞り面）と光線数は応答metadataに明記し、再現性を担保する。

### 21.5 評価面と image_plane_policy【v2.1新設】

**背景**

spot・PSF・MTF・ray fanなどの像面依存解析は「どのX位置で評価するか」に結果が強く依存する。物理センサー面（系定義内のsensor）と解析用評価面を分離し、評価面の決め方をエンジンAPIのパラメータとして一級市民化する。クライアント（UI・最適化）が best-focus solve と解析を2段呼び出しでオーケストレーションする方式は、sweep・merit探索で往復回数が増えるため採用しない。**評価面の解決はエンジン側の責務**とする。

**image_plane_policy**

像面依存の解析エンドポイント（spot / ray-fan / psf / mtf / white-psf / white-mtf / relative-illumination / chromatic-aberration）は、リクエストに image_plane_policy を受け取る。

```json
"image_plane_policy": {
  "mode": "best_focus_rms",
  "apply_to": "evaluation_plane",
  "criteria": {
    "fields": [{"field_id": "center", "weight": 1.0}],
    "wavelengths": [{"wavelength_nm": 587.56, "weight": 1.0}]
  },
  "search": {
    "initial": "paraxial_image",
    "range_mm": 5.0,
    "tolerance_mm": 0.001
  }
}
```

| mode | 内容 | 主用途 |
|---|---|---|
| fixed_sensor | 系定義内のsensor位置で評価する | 実機センサー固定。**既定** |
| paraxial_image | 近軸像面（14章、基準同軸状態・主波長）で評価する | 初期確認、教育、近軸との整合確認 |
| best_focus_rms | 指定field/波長重みでRMS spot最小位置を探索する | spot評価 |
| best_focus_mtf | 指定空間周波数のMTF最大位置を探索する（criteriaに frequency_lpmm 必須） | MTF評価 |
| best_focus_merit | 複数field/波長/metricの重み付きmeritで最良像面を探索する | 設計比較 |
| custom_offset | sensor基準の指定offset位置で評価する（offset_mm 必須） | デフォーカス評価 |
| sweep | sensor近傍の指定範囲・ステップを掃引し、focus curve（metric対X位置）を返す | フォーカス感度確認 |

**探索仕様**

* 初期値は近軸像面位置（基準同軸状態）を既定とする
* 探索は黄金分割法または放物線補間による1次元最小化とし、range_mm（既定 ±5.0 mm）、tolerance_mm（既定 0.001 mm）を持つ
* 探索の各評価点は同一の瞳サンプリング・aiming結果を再利用する（光線追跡は1回、評価面との交点計算のみ掃引する。27章の高速化と整合）
* 探索失敗（範囲端で単調など）は status: solve_not_converged としてrange端の値と警告を返す

**apply_to と責務分界**

| apply_to | 内容 | 実装側 |
|---|---|---|
| evaluation_plane | sensor面は動かさず、解析用仮想面のみ移動して評価する | エンジン。**既定** |
| focus_group | sensorは固定し、指定focus groupのX移動量を探索して合焦させる。解決したshift_x_mmをruntime configurationとして適用した状態で評価する（focus_group_id 必須） | エンジン |
| report_only | 位置（またはgroup移動量）のみ計算して返し、解析は fixed_sensor で行う | エンジン |
| （sensor_surface） | 求めた像面位置を系定義のsensor面へ書き戻す | **エンジン非対応**。エンジンはstatelessであり系定義を書き換えない。クライアントが solve 結果（solved_evaluation_plane_x_mm）を用いて系定義を編集し、再validate / registerする |

**応答metadata**

image_plane_policy を受けた解析応答は、必ず以下を含める。

```json
"evaluation_plane": {
  "policy_mode": "best_focus_rms",
  "evaluation_plane_x_mm": 42.113,
  "sensor_x_mm": 42.000,
  "offset_from_sensor_mm": 0.113,
  "solved_focus_group_shift_mm": null,
  "solve_status": "converged"
}
```

**afocal系での扱い**

system_type: afocal ではX位置の評価面という概念が成立しないため、image_plane_policy は適用外とする（指定された場合はvalidation error）。対応する概念は仮想視度掃引（24.2節）であり、将来 diopter_policy として同型のパラメータ体系で詳細化する。

**/v1/solve/best-focus の拡張**

単独エンドポイントとしてのbest-focus solveも、上記と同じ criteria / search / apply_to（report_only相当）を受け取り、solved位置・focus curve（sweep時）を返す。解析エンドポイント内蔵のpolicyと単独solveは同一の実装を共有する。

---

## 22. PSF・MTF

### 22.1 幾何PSF

初期版では、光線のセンサー到達点を2Dヒストグラム化してPSFとする。

```yaml
psf:
  mode: geometric
  grid_size: [256, 256]
  pixel_size_um: 1.0
```

出力例：

```json
{
  "field_id": "theta_z_20",
  "wavelength_nm": 587.56,
  "rms_radius_um": 12.4,
  "encircled_energy_80_radius_um": 24.1,
  "psf_image": "artifact://psf/psf_001.png",
  "psf_array": "artifact://psf/psf_001.npy"
}
```

### 22.2 回折PSF

将来拡張では、瞳面上のOPDからFFTで回折PSFを計算する。

```
P(u, v) = A(u, v) exp(i 2π OPD(u, v) / λ)
PSF = |FFT(P)|^2
```

反射望遠鏡では、瞳振幅 A(u, v) にannulus遮蔽（中央遮蔽・スパイダー）を反映することで、遮蔽込みの回折PSF・星像を評価できる構造とする。

### 22.3 MTF

初期版では、幾何PSFからフーリエ変換して簡易MTFを求める。

```json
{
  "field_id": "edge",
  "wavelength_nm": 587.56,
  "mtf": {
    "spatial_frequency_lpmm": [10, 20, 30, 40, 50],
    "sagittal": [0.92, 0.81, 0.66, 0.51, 0.38],
    "meridional": [0.88, 0.72, 0.55, 0.39, 0.25]
  }
}
```

幾何MTFは回折限界を含まないため、高F値・高周波数域では実際より楽観的な値になる。応答metadataに "diffraction_included": false を明記する。

### 22.4 白色PSF・白色MTF

白色光で評価する場合、波長ごとのPSFを重み付き合成してからMTF化する。

```
PSF_white =
Σ weight(λ) * PSF(λ)
MTF_white =
abs(FFT(PSF_white))
```

波長ごとのMTFを単純平均するよりも、波長ごとの像位置ずれや倍率色収差を反映しやすい。

---

## 23. 白色光源・波長ウェイト

### 23.1 光源スペクトル

白色光源は波長ごとの重みとして定義する。

```yaml
light_sources:
  - id: D65
    type: sampled_spectrum
    wavelengths_nm: [450, 486.13, 546.07, 587.56, 656.27, 700]
    weights: [0.70, 0.85, 1.00, 0.95, 0.80, 0.55]
    normalize: true
```

### 23.2 センサー分光感度

撮像系として評価する場合、センサーの分光感度も考慮できるようにする。

```
effective_weight(λ) =
light_spectrum(λ)
* sensor_sensitivity(λ)
* optional_filter_transmission(λ)
```

データ例：

```yaml
sensor_spectral_response:
  mode: rgb
  wavelengths_nm: [450, 486.13, 546.07, 587.56, 656.27, 700]
  R: [0.05, 0.10, 0.35, 0.70, 1.00, 0.75]
  G: [0.20, 0.55, 1.00, 0.85, 0.20, 0.05]
  B: [0.90, 1.00, 0.45, 0.10, 0.02, 0.00]
```

### 23.3 初期実装用の簡易波長セット

初期版では、以下の3〜5波長でよい。

```yaml
wavelength_weights:
  - wavelength_nm: 486.13
    weight: 0.25
  - wavelength_nm: 546.07
    weight: 0.30
  - wavelength_nm: 587.56
    weight: 0.25
  - wavelength_nm: 656.27
    weight: 0.20
```

---

## 24. 双眼鏡・望遠鏡向け評価

### 24.1 評価モード

写真レンズ用評価を以下とする。

```
sensor_image_quality
```

双眼鏡・望遠鏡用評価を以下とする。

```
visual_quality_at_eye
```

双眼鏡・望遠鏡では、センサー上の像ではなく、人間の眼に渡される角度像、射出瞳、アイレリーフ、アイボックスを評価する。

### 24.2 アフォーカル評価パイプライン【v2新設】

visual_quality_at_eye モードでは、system_type: afocal（9.2節）の系に対し、以下のパイプラインで評価する。

```
object angular field
  ↓ ray aiming（絞り = 通常は対物有効径 or 内部絞り）
optical system（対物 + プリズム展開 + 接眼）
  ↓
eye_reference 面（射出瞳位置）
  ↓
射出角度分布 (theta_y', theta_z') の統計
```

* spot相当量：射出角度分布の広がり（RMS、arcmin単位）
* PSF相当量：角度空間の2Dヒストグラム（角度PSF）
* MTF相当量：角度PSFのFFT（cycles/degree、24.6節）
* 合焦品質：射出光束の残存発散/収束（ディオプター）
* 眼の調節を模擬するため、評価時に仮想視度（-4〜+4 diopter程度）を掃引して最良角度spotを求めるオプションを持つ

sensorを終端とする従来パイプラインとは、終端要素・記録量・単位が異なるだけで、光線追跡カーネル自体は共通とする。

### 24.3 基本評価値

| カテゴリ | 評価値 |
|---|---|
| 基本仕様 | 倍率、有効口径、焦点距離、F値 |
| 視野 | 実視界、見かけ視界、視野絞り制限 |
| 射出瞳 | 射出瞳径、射出瞳位置、射出瞳形状 |
| 眼適合 | アイレリーフ、アイボックス、ブラックアウト感度 |
| 像質 | 角分解能、角度MTF、角度spot、角度PSF |
| 収差 | 球面収差、コマ、非点、像面湾曲、色収差 |
| 明るさ | 周辺光量、ケラレ、透過率近似 |
| 双眼鏡固有 | 左右倍率差、左右像位置差、左右回転差、光軸平行度 |
| 望遠鏡固有 | 接眼込み倍率、遮蔽率、回折PSF、星像径 |

倍率・射出瞳径・射出瞳位置は近軸計算（第14章）から求め、実光線評価（逆方向追跡・射出瞳マッピング）と相互検証する。

### 24.4 射出瞳

双眼鏡・望遠鏡では射出瞳が重要である。

```
射出瞳径 = 対物レンズ有効径 / 倍率
```

出力すべき値は以下。

| 評価値 | 内容 |
|---|---|
| exit_pupil_diameter_mm | 射出瞳径 |
| exit_pupil_position_mm | 最終接眼面から射出瞳までの距離 |
| exit_pupil_shape | 射出瞳の形状 |
| exit_pupil_vignetting | fieldごとの射出瞳の欠け |
| eye_box_size_mm | 眼位置許容範囲 |

### 24.5 アイレリーフ・アイボックス

アイレリーフは、接眼レンズから射出瞳までの距離である。

アイボックス評価では、眼の瞳孔を仮想的な円形開口（eye_reference面）として置き、眼位置をY/Z/X方向に動かしたときの光線通過率を評価する。

出力例：

```json
{
  "eye_relief_mm": 17.5,
  "eye_box": {
    "pupil_diameter_mm": 4.0,
    "allowable_shift_y_mm": 2.1,
    "allowable_shift_z_mm": 1.8,
    "allowable_shift_x_mm": 3.0
  },
  "blackout_sensitivity": "medium"
}
```

### 24.6 実視界・見かけ視界・角度MTF

| 種類 | 意味 |
|---|---|
| 実視界 | 双眼鏡を動かさずに見える実際の角度範囲 |
| 見かけ視界 | 接眼側で観察者が感じる視界の広さ |

エンジンでは以下の変換を評価する。

```
object angular field
  ↓
optical system
  ↓
eyepiece angular field
```

出力値：

| 評価値 | 内容 |
|---|---|
| true_field_of_view_deg | 実視界 |
| apparent_field_of_view_deg | 見かけ視界 |
| field_stop_limited | 視野絞りで制限されているか |
| edge_vignetting_ratio | 視野端のケラレ |
| usable_field_ratio | 実用的にシャープな視野範囲 |

角度MTFは、見かけ視界における角度周波数で評価する。

```
cycles/degree in apparent visual field
```

出力例：

```json
{
  "field_id": "edge",
  "angular_mtf": {
    "frequency_cpd": [5, 10, 20, 30, 40],
    "sagittal": [0.95, 0.86, 0.64, 0.41, 0.22],
    "meridional": [0.92, 0.78, 0.55, 0.32, 0.15]
  }
}
```

### 24.7 双眼鏡の左右差評価【v2改訂】

双眼鏡では、左右の像が脳内で融合されるため、左右差が重要である。

評価すべき項目は以下。

| 評価値 | 内容 |
|---|---|
| 左右倍率差 | 左右で像の大きさが違う |
| 左右像位置差 | 左右で像の中心がずれる |
| 左右回転差 | 片側だけ像が傾く |
| 左右焦点差 | 片側だけピント位置が違う（ディオプター差） |
| 左右収差差 | 片側だけ像が甘い |
| 左右射出瞳位置差 | 眼の置きやすさが左右で違う |
| 左右光軸平行度 | コリメーションの良否 |

双眼鏡定義では、各チャンネルのposeにシフトに加えて**チルト・ロール**を持たせる。コリメーション誤差（光軸平行度不良）はpose側のチルトで模擬する。

```yaml
binocular_system:
  left_channel:
    optical_system: {}
    pose:
      shift_y_mm: -32.0
      shift_z_mm: 0.0
      tilt_y_deg: 0.0       # 【v2追加】光軸の上下振れ
      tilt_z_deg: 0.02      # 【v2追加】光軸の左右振れ（コリメーション誤差）
      roll_x_deg: 0.0       # 【v2追加】像回転
  right_channel:
    optical_system: {}
    pose:
      shift_y_mm: 32.0
      tilt_y_deg: 0.0
      tilt_z_deg: 0.0
      roll_x_deg: 0.0
  interpupillary_distance_mm: 64.0
```

出力例：

```json
{
  "binocular_alignment": {
    "vertical_image_error_arcmin": 2.0,
    "horizontal_image_error_arcmin": 5.5,
    "rotation_error_deg": 0.12,
    "magnification_difference_percent": 0.3,
    "focus_difference_diopter": 0.05
  }
}
```

### 24.8 望遠鏡評価

望遠鏡は、対物系または主鏡系だけを評価する場合と、接眼レンズ込みで評価する場合を分ける。

```
telescope_objective_mode      → system_type: focal（焦点面評価）
visual_instrument_mode        → system_type: afocal（眼基準評価）
```

対物側評価：

| 評価値 | 内容 |
|---|---|
| 焦点距離 | 望遠鏡本体の基本仕様（近軸計算から） |
| F値 | 明るさ・収差補正難度 |
| 焦点面でのspot | 対物系の像質 |
| field curvature | 周辺ピント |
| coma | 放物面鏡系などで重要 |
| chromatic aberration | 屈折望遠鏡で重要 |
| central obstruction | 反射望遠鏡で重要（annulus開口で表現） |
| diffraction PSF | 口径・遮蔽込みの点像（将来拡張、22.2節） |

接眼込み評価：

| 評価値 | 内容 |
|---|---|
| 倍率 | 対物焦点距離 / 接眼焦点距離（近軸角倍率と相互検証） |
| 射出瞳径 | 口径 / 倍率 |
| アイレリーフ | 覗きやすさ |
| 見かけ視界 | 視野の広さ |
| 周辺像質 | 視野端の星像（角度spot） |
| ブラックアウト耐性 | 眼位置ずれへの強さ |
| 歪曲 | 地上観察・流し見で重要 |

---

## 25. 最適化・評価値

### 25.1 方針

自動最適化そのものは外部エンジンで実行してよい。
本エンジンは、設計候補に対して評価値を返す。

```
optimizer
  ↓ candidate lens parameters
optics engine
  ↓ merit values
optimizer
```

### 25.2 評価値

初期版で対応すべき評価値は以下。

| 評価値 | 意味 | 最適化での扱い |
|---|---|---|
| rms_spot_radius | スポットのRMS半径 | 小さいほどよい |
| geo_spot_radius | 最大または包含率スポット半径 | 小さいほどよい |
| encircled_energy_radius | 指定エネルギーを含む半径 | 小さいほどよい |
| ray_fan_error | Ray fanの横収差 | 小さいほどよい |
| longitudinal_aberration | 縦収差 | 小さいほどよい |
| distortion | 歪曲率 | 目標値に近いほどよい |
| field_curvature | 像面湾曲 | 小さいほどよい |
| astigmatism | M/S像面差 | 小さいほどよい |
| lateral_color | 倍率色収差 | 小さいほどよい |
| axial_color | 軸上色収差 | 小さいほどよい |
| relative_illumination | 周辺光量 | 高いほどよい |
| vignetting_ratio | ケラレ率 | 高いほどよい |
| geometric_mtf | 幾何MTF | 高いほどよい |
| white_mtf | 白色MTF | 高いほどよい |
| chief_ray_angle | センサー入射角 | 制約内がよい |
| back_focal_length | バックフォーカス | 制約内がよい |
| effective_focal_length | 実効焦点距離 | 目標値に近いほどよい |
| f_number | F値 | 目標値に近いほどよい |
| total_track_length | 光学全長 | 小さいほどよい |
| element_count | レンズ枚数 | 少ないほどよい |
| glass_penalty | 特殊硝材ペナルティ | 小さいほどよい |
| min_air_gap | 最小空気間隔 | 制約内がよい（10.3節） |
| edge_thickness | レンズ周縁厚（sag込み。10.3節） | 制約内がよい【v2.2追加】 |

back_focal_length, effective_focal_length, f_number は近軸計算（第14章）から求める。

### 25.3 オペランドと残差【v2.2改訂】

**背景**

レンズ設計の局所最適化は、実務上ほぼ例外なく減衰最小二乗法（DLS / Levenberg-Marquardt）系であり、これはスカラーmeritではなく**オペランドごとの残差ベクトル**（およびそのヤコビアン）を要求する。旧仕様の「正規化値の重み付き和」は、(1) 残差ベクトルを外部に渡せない、(2) 「normalized」の定義が未規定で重みの意味が定まらない、という2点で最適化に使えないため、オペランド形式へ全面改訂する。

**オペランド定義**

評価リクエストは operands 配列で指定する。

```json
"operands": [
  {
    "metric": "rms_spot_radius",
    "field_id": "edge",
    "wavelength_nm": 587.56,
    "target": 0.0,
    "tolerance": 5.0,
    "weight": 1.0
  },
  {
    "metric": "effective_focal_length",
    "target": 100.0,
    "tolerance": 0.5
  },
  {
    "metric": "distortion",
    "field_id": "edge",
    "target": 0.0,
    "tolerance": 1.0
  }
]
```

| フィールド | 意味 |
|---|---|
| metric | 評価値名（25.2節の一覧） |
| field_id / wavelength_nm | 対象field・波長。metricが系全体量（EFL等）の場合は省略 |
| target | 目標値。metricの自然単位 |
| tolerance | 正規化スケール。「この量だけ外れたら残差1」を意味する。**旧仕様の未定義だったnormalizedの定義をこれで確定する** |
| weight | 追加重み（既定1.0） |

**残差**

各オペランドの残差を以下で定義する。

```
residual_i = weight_i * (value_i - target_i) / tolerance_i
```

応答は、全オペランドについて value / residual を配列で返す。

### 25.4 Merit Function【v2.2改訂】

meritは独立に定義される量ではなく、残差ベクトルからの**導出値**とする。

```
merit = Σ residual_i^2 + Σ penalty_j^2
```

* lower_is_better固定
* penalty はソフトペナルティ疑似オペランド（25.5節）の残差
* DLS慣例（残差二乗和最小化）と一致し、外部最適化器はmeritを見ずに残差ベクトルだけで動作できる

応答例：

```json
{
  "status": "ok",
  "merit": {
    "total": 3.42,
    "definition": "sum_of_squared_residuals_plus_penalties"
  },
  "operands": [
    {
      "metric": "rms_spot_radius",
      "field_id": "edge",
      "wavelength_nm": 587.56,
      "value": 8.7,
      "target": 0.0,
      "tolerance": 5.0,
      "residual": 1.74
    }
  ],
  "penalties": [
    {
      "type": "ray_failure_ratio",
      "field_id": "edge",
      "value": 0.02,
      "residual": 0.2
    }
  ],
  "constraints": {
    "back_focal_length_mm": 18.2,
    "total_track_length_mm": 72.5,
    "min_air_gap_mm": 0.8,
    "min_edge_thickness_mm": 1.2
  }
}
```

実現不能な候補（10.3節のエラー級違反：負の空気間隔・群交差）には status: infeasible と violations を返し、トレースは実行しない。外部最適化が探索空間から即時除外できるようにする。

### 25.5 光線破綻の連続ペナルティと決定論【v2.2新設】

**連続ペナルティ**

最適化は必ず病的な領域を探索する。光線の一部がTIR・ケラレ・aiming失敗で落ちる状態を、一律のエラーや固定ペナルティ定数で返すと、最適化器はその方向の勾配情報を失い探索が壁に張り付く。そこで、破綻の程度に比例した**連続な**ペナルティを定義する。

```
ray_loss_ratio(field, λ) =
  1 - Σ weight(センサー/eye到達光線) / Σ weight(生成光線)
```

各field×波長の ray_loss_ratio を疑似オペランドとして自動的に残差ベクトルへ追加する。

```
penalty_residual = ray_loss_ratio / ray_loss_tolerance
（ray_loss_tolerance 既定 0.1。リクエストで変更可能）
```

破綻区分の扱い：

| 区分 | 例 | 扱い |
|---|---|---|
| ハードinfeasible | 負の空気間隔、群交差 | status: infeasible。トレースせず即時返却 |
| ソフト劣化 | TIR、有効径ケラレ、aiming失敗、missed_surface | ray_loss_ratioに比例した連続ペナルティ。評価は続行 |

意図的なケラレ（口径食による周辺光量調整）と区別したい場合のため、ペナルティ対象のstatusをリクエストで選択できるようにする（既定：total_internal_reflection, missed_surface, aiming_failed, numerical_error。blocked_by_apertureは既定で除外）。

**決定論**

準ニュートン系・信頼領域系の最適化は、評価値の再現性を前提とする。以下を保証する。

1. 同一のリクエスト（バイト同一）に対し、全数値出力はビット同一とする
2. hexapolar / gaussian_quadrature / grid / polar / fan は決定論的サンプリングとする。random / sobol は seed 指定を必須とする
3. aiming の warm start（27.6節）は反復回数のみに影響し、収束解は初期値によらず tolerance_mm 内で一意でなければならない。warm start有無で評価値が tolerance を超えて変わる場合は実装バグとして扱う
4. 並列実行時のreduction順序による浮動小数点非決定性を避けるため、評価値の集計は光線インデックス順の逐次和（またはpairwise固定順）とする

### 25.6 最適化変数の空間とキー体系【v2.2新設】

**曲率空間の推奨**

radius_mm を最適化変数にすると、面が平面をまたぐ瞬間（R: +∞ → −∞）に変数空間が特異になる。**曲率 c = 1/R を変数とすれば、平面は c = 0 として滑らかに通過できる**（本エンジンの radius_mm = 0 = 平面規約（5.2節）と整合する）。最適化用途では curvature キーを推奨し、radiusキーは互換用とする。

**変数キー一覧**

| キーパターン | 対象 | 備考 |
|---|---|---|
| {surface_id}_curvature | 面の曲率 c [1/mm] | **最適化推奨**。c=0は平面 |
| {surface_id}_radius_mm | 曲率半径 | 互換用。平面近傍で特異のため最適化非推奨（使用時は警告） |
| {surface_id}_thickness_after_mm | 面後間隔 | |
| {surface_id}_conic | コーニック定数 | |
| {surface_id}_A4 / _A6 / _A8 ... | 偶数次非球面係数 | |
| {surface_id}_semi_diameter_mm | 有効径 | 通常は制約側で扱う |
| {group_id}_shift_x_mm | 群X位置 | ズーム・フォーカス変数 |
| {group_id}_shift_y_mm / _shift_z_mm | 群シフト | 偏芯最適化・公差用 |
| iris_radius_mm | 可動絞り半径 | |
| thin_lens {surface_id}_focal_length_mm | 薄レンズ焦点距離 | |

これらはすべてCompiledSystemの構造を壊さない**ランタイムパラメータ**として注入する（26.2節）。硝材の変更は離散変数であり variables では扱わない。外部最適化側で候補硝材を離散列挙し、system構造の変更（別system_hash）として評価する。

### 25.7 ヤコビアンバッチモード【v2.2新設】

**動機**

外部で有限差分すると、変数 n 個に対し 1反復あたり n+1 回のevaluate呼び出しが必要になる。エンジン内でまとめれば、摂動候補間で CompiledSystem・瞳サンプリング点・aiming解（warm start）・近軸量を共有でき、n+1回分をほぼ1回強のコストにできる（27章のバッチカーネル・キャッシュ設計がそのまま前提インフラとなる）。

**リクエスト**

evaluateリクエストに jacobian を追加する。

```json
"jacobian": {
  "mode": "forward_diff",
  "variables": ["S1_curvature", "S2_curvature", "S2_thickness_after_mm"],
  "steps": {
    "S1_curvature": 1.0e-5
  }
}
```

* mode: forward_diff（既定）| central_diff（精度2倍・コスト2倍）
* steps 省略時は変数種別ごとの既定ステップを使う：

| 変数種別 | 既定ステップ |
|---|---|
| curvature | max(1e-6, \|c\| × 1e-4) [1/mm] |
| thickness | max(1e-4, \|t\| × 1e-4) [mm] |
| conic | max(1e-4, \|k\| × 1e-4) |
| 非球面係数 | max(係数次数ごとのfloor, \|A\| × 1e-3) |
| 群shift / 絞り半径 | max(1e-4, \|v\| × 1e-4) [mm] |

**応答**

```json
"jacobian": {
  "mode": "forward_diff",
  "variables": ["S1_curvature", "S2_curvature", "S2_thickness_after_mm"],
  "residuals": [1.74, 0.31, -0.85],
  "matrix_shape": [3, 3],
  "matrix": "artifact://jacobian/jac_001.npy",
  "steps_used": {"S1_curvature": 1.0e-5, "S2_curvature": 1.0e-5,
                 "S2_thickness_after_mm": 1.0e-4}
}
```

matrixは行=オペランド（＋ペナルティ疑似オペランド）、列=変数の ∂residual/∂variable。小規模（要素数1000以下目安）ならJSONインライン返却も許可する。

**実装規約**

* 基準点＋n摂動点の全光線を1つのバッチとしてトレースする（候補次元を配列に含める）
* aiming は基準点の解を全摂動点のwarm startに使う
* 摂動後の系がハードinfeasibleになった場合、該当列は片側差分へフォールバックし、応答にフラグを立てる

### 25.8 将来の勾配提供

将来拡張として、微分可能トレースカーネル（27.5節のJAX方針）により有限差分を自動微分へ差し替える。**その際も25.7節のリクエスト/応答形状は変えない**（modeに autodiff が加わるのみ）。外部最適化器から見た契約を固定するため、25.7節のAPIを先に凍結する。これにより評価回数を有限差分比でさらに削減できる可能性がある。

---

## 26. API仕様

### 26.1 基本方針

* HTTP API
* JSON入出力
* 大きな配列は .npz, .npy, .parquet などで返却可能
* 図はPNG/SVG/JSONで返却可能
* エンジン本体は原則stateless。ただし**性能のためのキャッシュ（CompiledSystem等）は透過的に保持してよい**（結果の意味論には影響しない）【v2改訂】
* 光学系定義は毎回requestに含めるか、事前登録IDを使う

### 26.2 システム登録とキャッシュキー【v2新設】

最適化ループ・教育UIの反復呼び出しでは、system JSONの再送・再検証・再コンパイルが支配的コストになり得る（27.2節）。以下の仕組みを一級市民とする。

```
POST /v1/systems/register
  → { "system_id": "sys_ab12...", "system_hash": "sha256:..." }
```

* system定義の正規化JSON（キー順序・数値表現を正規化）のハッシュをキャッシュキーとする
* 以後のリクエストは "system_id" 参照で呼び出せる
* variables / decenters / tilts / zoom_position は**キャッシュを破壊しないランタイムパラメータ**として設計する。すなわちCompiledSystemは「構造」をコンパイルし、これらの値は実行時に注入する
* 未登録でもsystemをインライン送信した場合、エンジンは内部でハッシュを取り同一系のCompiledSystemを再利用してよい

### 26.3 エンドポイント一覧

```
GET  /v1/health                       【v2.1新設】
GET  /v1/meta                         【v2.1新設】
GET  /v1/artifacts/{category}/{id}    【v2.1新設】
POST /v1/systems/validate
POST /v1/systems/register            【v2新設】
POST /v1/analysis/paraxial           【v2新設】
POST /v1/trace/forward
POST /v1/trace/reverse
POST /v1/analysis/spot
POST /v1/analysis/ray-fan
POST /v1/analysis/longitudinal-aberration
POST /v1/analysis/chromatic-aberration
POST /v1/analysis/distortion
POST /v1/analysis/field-curvature
POST /v1/analysis/ms-image-surface
POST /v1/analysis/relative-illumination
POST /v1/analysis/psf
POST /v1/analysis/mtf
POST /v1/analysis/white-psf
POST /v1/analysis/white-mtf
POST /v1/analysis/visual-instrument
POST /v1/analysis/exit-pupil
POST /v1/analysis/eye-box
POST /v1/analysis/angular-mtf
POST /v1/analysis/binocular-alignment
POST /v1/optics/evaluate               【v2.2拡張: operands / jacobian / solves対応。25.3〜25.7節】
POST /v1/optics/evaluate-batch
POST /v1/education/preview
POST /v1/solve/best-focus             【v2.1拡張: criteria(rms/mtf/merit)・sweep対応。21.5節】
POST /v1/solve/paraxial-image-distance 【v2.2新設: 指定空気間隔を近軸像面一致に解決】
POST /v1/materials/refractive-index
```

像面依存の解析エンドポイントは image_plane_policy を受け取る（21.5節）。

教育UIの連続操作（絞りスライダー等）向けには、将来オプションとしてWebSocketセッション（system_idに紐づく常駐CompiledSystem＋差分パラメータ送信）を追加できる構造としておく。初期版はHTTP + system_id参照で足りる想定とする。

### 26.4 順方向追跡リクエスト例

```json
{
  "system_id": "sys_ab12...",
  "configuration": {
    "variables": {
      "iris_radius_mm": 4.0
    },
    "zoom_position": "wide",
    "decenters": [
      {
        "group": "OIS_G",
        "shift_y_mm": 0.1,
        "shift_z_mm": 0.0
      }
    ],
    "tilts": [
      {
        "from_surface": "S5",
        "to_surface": "S7",
        "tilt_y_deg": 1.0,
        "rotation_center": {
          "reference": "from_surface_vertex",
          "offset_x_mm": 0.0,
          "offset_y_mm": 0.0,
          "offset_z_mm": 0.0
        }
      }
    ]
  },
  "fields": [
    { "id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0 },
    { "id": "upper",  "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 20.0 },
    { "id": "lower",  "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": -20.0 }
  ],
  "ray_sampling": {
    "samples_per_field": 1024,
    "pupil_distribution": "hexapolar",
    "ray_aiming": { "mode": "full" }
  },
  "wavelengths_nm": [486.13, 587.56, 656.27],
  "options": {
    "store_path": true
  }
}
```

### 26.5 教育用preview API

```json
{
  "system_id": "sys_ab12...",
  "lesson_mode": "aperture_effect",
  "controls": {
    "iris_radius_mm": 3.0,
    "focus_group_shift_mm": 1.2
  },
  "display": {
    "show_rays": true,
    "show_blocked_rays": true,
    "show_sensor_hits": true,
    "show_focus_point": true,
    "show_aperture": true
  },
  "ray_sampling": {
    "samples_per_field": 15,
    "fields": ["center", "mid", "edge"],
    "ray_aiming": { "mode": "paraxial" }
  }
}
```

### 26.6 評価API【v2.2改訂】

```json
{
  "system_id": "sys_ab12...",
  "configuration": {
    "solves": [
      {"type": "paraxial_image_distance", "thickness_of": "S2"}
    ]
  },
  "fields": [
    {"id": "center", "type": "angular", "theta_y_deg": 0, "theta_z_deg": 0},
    {"id": "mid",    "type": "angular", "theta_y_deg": 0, "theta_z_deg": 10},
    {"id": "edge",   "type": "angular", "theta_y_deg": 0, "theta_z_deg": 20}
  ],
  "evaluation": {
    "operands": [
      {"metric": "rms_spot_radius", "field_id": "center",
       "wavelength_nm": 587.56, "target": 0.0, "tolerance": 5.0, "weight": 1.0},
      {"metric": "rms_spot_radius", "field_id": "edge",
       "wavelength_nm": 587.56, "target": 0.0, "tolerance": 5.0, "weight": 0.6},
      {"metric": "distortion", "field_id": "edge",
       "target": 0.0, "tolerance": 1.0},
      {"metric": "lateral_color", "field_id": "edge",
       "target": 0.0, "tolerance": 3.0},
      {"metric": "effective_focal_length",
       "target": 100.0, "tolerance": 0.5},
      {"metric": "edge_thickness", "surface_pair": ["S1", "S2"],
       "target": 2.0, "tolerance": 0.5, "one_sided": "lower"}
    ],
    "ray_loss_tolerance": 0.1
  },
  "jacobian": {
    "mode": "forward_diff",
    "variables": ["S1_curvature", "S2_curvature", "S2_thickness_after_mm"]
  },
  "ray_sampling": {
    "samples_per_field": 18,
    "pupil_distribution": "gaussian_quadrature"
  }
}
```

**solves【v2.2新設】**

configuration.solves は、評価前にエンジンが解決するランタイム束縛を指定する。

| type | 内容 |
|---|---|
| paraxial_image_distance | 指定面の thickness_after_mm を、近軸像面（基準同軸状態・主波長）がsensorに一致するよう解決する |

これにより「最終空気間隔=近軸像距離」という最頻出の等式制約が外部最適化の変数・制約から消える。solveされた値は応答の configuration_resolved に含める。単独エンドポイント /v1/solve/paraxial-image-distance も同じ実装を共有する。

**one_sided オペランド**

制約型のオペランド（edge_thickness、min_air_gap、back_focal_length等）は one_sided: lower | upper を指定でき、目標側に満たしている場合は residual = 0 とする（片側不等式制約のペナルティ表現）。

### 26.7 バッチ評価API

```json
{
  "base_system_id": "sys_ab12...",
  "candidates": [
    {
      "id": "candidate_001",
      "variables": {
        "S1_radius_mm": 48.0,
        "S2_radius_mm": -52.0,
        "air_gap_1_mm": 4.2
      }
    },
    {
      "id": "candidate_002",
      "variables": {
        "S1_radius_mm": 50.0,
        "S2_radius_mm": -49.0,
        "air_gap_1_mm": 4.6
      }
    }
  ],
  "evaluation": {
    "preset": "fast_design_score"
  }
}
```

評価presetは、v2.2以降**オペランドセットのテンプレート**として定義する（preset展開後の実体は25.3節のoperands配列＋ray_sampling設定）。応答には展開後のoperands定義を含め、presetの中身がバージョン間で暗黙に変わることを防ぐ。バッチの各候補は operands / jacobian / solves を個別に上書きできる。

曲率・間隔を variables 化できる場合、これらもCompiledSystemの構造を壊さないランタイムパラメータとして注入する（26.2節）。バッチ全体で1回のコンパイル＋N回のパラメータ注入評価となることを設計目標とする。

### 26.8 Artifact取得と生存期間【v2.1新設】

**URI形式と取得**

大容量データ（PSF配列、spot点群、focus curve、図画像など）は、応答JSON内に artifact URI として参照を返す。

```
artifact://{category}/{id}
例: artifact://psf/psf_001.npy
```

取得は以下のエンドポイントで行う。

```
GET /v1/artifacts/{category}/{id}
  → バイナリ本体（Content-Typeはartifact種別に応じる:
     application/octet-stream(.npy/.npz), application/vnd.apache.parquet,
     image/png, image/svg+xml, application/json）
```

存在しない・期限切れのartifactには 404 と error type: artifact_expired / artifact_not_found を返す。

**生存期間（重要）**

artifactは**揮発性**とする。

* エンジンは原則statelessであり、artifactは一時ストレージに置く
* TTLは既定30分（起動オプションで変更可）。応答JSONのmetadataに expires_at を含める
* プロセス再起動でartifactは消滅する
* **永続化はクライアント責務**とする。比較・再表示・snapshot保存に必要なデータは、クライアントがTTL内に GET /v1/artifacts で取得し、自身の保存領域（Project / Snapshot）へ埋め込むこと

この規約により、エンジンはartifactのガベージコレクションを単純なTTL削除で実装でき、statelessスケール（複数ワーカー化）の障害にならない。複数プロセス構成では、artifactストアを共有ディレクトリまたは共有オブジェクトストアに置き、URIの解決を全ワーカーで一貫させる。

### 26.9 メタ情報・ヘルスチェック【v2.1新設】

```
GET /v1/health
  → { "status": "ok" }
```

軽量な死活確認用。認証・重い処理を含めない。

```
GET /v1/meta
  → {
      "engine_version": "0.1.0",
      "api_schema_version": "0.1.0",
      "result_schema_version": "0.1.0",
      "material_catalog_version": "0.1.0",
      "preset_version": "0.1.0",
      "capabilities": {
        "diffraction_psf": false,
        "async_jobs": false,
        "image_plane_policy_modes": ["fixed_sensor", "paraxial_image",
          "best_focus_rms", "best_focus_mtf", "best_focus_merit",
          "custom_offset", "sweep"],
        "system_types": ["focal", "afocal"]
      },
      "build": {
        "python_version": "3.12.x",
        "numba_enabled": true
      },
      "enumerations": {
        "metrics": ["rms_spot_radius", "geo_spot_radius", "distortion",
                    "lateral_color", "edge_thickness", "..."],
        "error_codes": ["negative_air_gap", "group_overlap",
                        "missing_aperture_stop", "solve_not_converged", "..."],
        "warning_codes": ["edge_thickness_below_min", "radius_key_deprecated",
                          "..."],
        "ray_status_codes": ["alive", "hit_sensor", "blocked_by_aperture",
                             "total_internal_reflection", "aiming_failed",
                             "..."],
        "variable_key_patterns": ["{surface_id}_curvature",
                                  "{surface_id}_thickness_after_mm",
                                  "{group_id}_shift_x_mm", "..."]
      }
    }
```

**enumerations【v2.3追加】**は、エンジンが応答に含め得る識別子の全列挙である。クライアントはこれを用いて、表示ラベル・用語集・エラーカタログの網羅性をCIで機械検証する（Workbench UI仕様v0.3 27.6節）。エンジン側は、新しいmetric・コードを追加する際、必ずこの列挙にも追加する（列挙とテストの対応は30.7節に追加してよい）。

クライアントは起動時に /v1/meta を取得し、schema versionの不一致検出・未実装機能のUI無効化（capabilities参照）に用いる。version体系はsemantic versioningとし、api_schema_version のmajor不一致はクライアント側でエラー、minor不一致は警告とする。

### 26.10 エラー・警告コード規約【v2.3新設】

**方針**

エンジンは多言語化しない。ロケール・翻訳をサーバーに持ち込まず、全エラー・警告を以下の構造で返す。表示文言の組み立て・翻訳はクライアント責務である。

```json
{
  "severity": "error",
  "code": "negative_air_gap",
  "params": {
    "surface_ids": ["S4", "S5"],
    "group_ids": ["G2"],
    "gap_mm": -0.35
  },
  "message_en": "Air gap between S4 and S5 is negative (-0.35 mm)."
}
```

**規約**

1. code は snake_case の安定識別子とする。一度公開したcodeの意味・params構造を変えない（変える場合は新codeを追加する）。
2. params は表示文言の穴埋めに必要な構造化値をすべて含める。message_en に含まれる情報は必ずparamsからも取得可能でなければならない（クライアントはmessage_enをパースしない）。
3. message_en は開発者向け・未登録コード時のフォールバック表示用の英語文。ログにもこれを使う。
4. severity は error | warning | info。infeasible応答のviolations（10.3節）、validation結果、solve失敗（21.5節 solve_not_converged）、artifact系（26.8節）もすべて本形式に従う。
5. 全codeは /v1/meta の enumerations に列挙する（26.9節）。
6. 本仕様書内の各エラー例（10.3節のviolations等）は本形式へ読み替える。フィールド名は type ではなく code に統一する。


---

## 27. 高速化方針【v2全面改訂】

### 27.1 基本方針

本エンジンは、教育用UIでの即時反応と、最適化ループでの大量評価の両方を想定する。

そのため、以下を分けて扱う。

```
preview mode:
  高速 / 粗い / 少ない光線 / ray aiming簡略（paraxial） / UI向け
analysis mode:
  高密度 / 再現性重視 / ray aiming full / 評価値向け
optimization mode:
  バッチ評価 / キャッシュ重視 / 粗密2段階評価 / infeasible即時棄却
```

### 27.2 ボトルネックの見立て【v2新設】

10〜20面程度の系に対する数千〜数万本の光線追跡は、NumPyベクトル化（Level 1）で1秒未満が標準的であり、**27.3節の性能目標はLevel 1でほぼ達成可能**と見込む。したがって高速化の主戦場はトレースカーネルそのものではなく、以下にある。

| ボトルネック候補 | 内容 | 対策 |
|---|---|---|
| system JSONのパース・validation | statelessで毎回送ると評価1回あたり数十ms級 | system_id登録＋CompiledSystemキャッシュ（26.2節） |
| CompiledSystemビルド | Pydantic→配列構造への変換 | systemハッシュで再利用。variablesは構造を壊さず注入 |
| ray aiming反復 | 光線ごとの実追跡×反復 | 瞳アフィン近似（16.3節）＋主光線のみ厳密反復 |
| 非球面Newton反復 | 光線ごとに反復回数が異なる | Numba化の主対象（27.4節） |
| HTTP往復・シリアライズ | 教育UIの連続操作時 | system_id参照、応答の最小化、将来WebSocket |
| プロセス並列時のデータ転送 | multiprocessingのpickleコスト | 常駐ワーカー＋共有メモリ（27.6節） |

性能計測は「トレース時間」だけでなく「API呼び出しend-to-end時間」で行い、上記の切り分けができるよう各段階の所要時間を応答metadataに含められるようにする（profiling: true オプション）。

### 27.3 定量的な性能目標

以下は初期設計段階の目標値であり、実測によって調整する。

想定環境は、一般的なノートPCまたはミドルクラスデスクトップPCのCPU実行を基準とする。
GPU高速化は将来拡張とする。目標時間は**API呼び出しend-to-end**（CompiledSystemキャッシュヒット時）とする。

| 用途 | 条件 | 目標 |
|---|---|---|
| 教育用preview | 3 field × 1波長 × 25 rays | 50〜100 ms以内 |
| インタラクティブ操作 | 絞り・群移動の連続操作 | 10 fps程度 |
| 光線経路表示 | 3 field × 1波長 × 100 rays | 200 ms以内 |
| Spot簡易解析 | 5 field × 3波長 × 512 rays | 1秒以内 |
| 詳細Spot解析 | 9 field × 3波長 × 2048 rays | 3〜10秒以内 |
| 周辺光量解析 | 9 field × 1波長 × 10000 rays | 5〜15秒以内 |
| 幾何PSF | 1 field × 1波長 × 50000 rays | 5〜20秒以内 |
| 最適化粗評価 | 1候補あたり簡易merit | 100〜500 ms以内 |
| バッチ最適化 | 100候補の粗評価 | 10〜60秒以内 |

初期MVPでは、教育用previewと簡易spot解析を優先する。
詳細PSFや白色MTFは、最初からリアルタイムにする必要はない。

なお、この目標はLevel 1実装で十分達成可能な水準に置いてある。未達の場合、まずトレースカーネルではなく27.2節のボトルネック（キャッシュ不備・aiming過剰反復・シリアライズ）を疑う。

### 27.4 高速化レベル【v2改訂】

| Level | 内容 | 用途 | 位置づけ |
|---|---|---|---|
| 0 | 素朴なPython実装 | 数式検証・リファレンス実装 | 常に保持（Golden Testの基準） |
| 1 | NumPyベクトル化 | 数百〜数万本の光線 | **初期実装の主体。性能目標達成の主手段** |
| 2 | Numba JIT | 非球面交点Newton反復・aiming反復 | 初期実装で部分適用 |
| 3 | バッチ処理API | 最適化ループ | Level 1の上に構築 |
| 4 | 並列実行 | field / wavelength / candidate並列 | 常駐ワーカー前提（27.6節） |
| 5 | JAX微分可能カーネル | **勾配提供（速度目的ではない）** | 将来拡張。設計上の布石は初期から打つ（27.5節） |
| 6 | GPU | 大量PSF / 数千候補バッチ | 将来拡張。当面不要 |

Rust / C++ coreは、Numba（Level 2）で必要性能に届く見込みが高いため、v2では独立レベルから外し「Level 2で不足が実測された場合の代替手段」に位置づけを下げる。

**Numba適用の前提**

NumbaカーネルにはPythonオブジェクトを渡せない。CompiledSystemは以下のような構造化配列に落とす。

```
surface_type:     int8[n_surf]      # 面種別enum
curvature:        float64[n_surf]
conic:            float64[n_surf]
asphere_coeffs:   float64[n_surf, max_order]
semi_diameter:    float64[n_surf]
inner_diameter:   float64[n_surf]   # annulus用
n_before:         float64[n_surf, n_wavelengths]
n_after:          float64[n_surf, n_wavelengths]
local_transform:  float64[n_surf, 4, 4]
inverse_transform:float64[n_surf, 4, 4]
propagation_sign: int8[n_surf]
```

### 27.5 JAXと微分可能トレース【v2新設】

JAXの採用価値は実行速度よりも**自動微分**にある。トレースカーネルが微分可能であれば、meritの設計変数勾配を外部最適化へ返せる（25.4節）。有限差分による勾配推定（変数数×2回の評価）が不要になるため、評価回数を1〜2桁削減できる可能性があり、Level 5相当の実行速度向上より効果が大きい。

将来のJAX移植コストを下げるため、初期実装のトレースカーネルは以下の規律で書く。

* カーネル関数は純関数とする（グローバル状態・in-place副作用を持たない）
* データ依存の分岐を最小化し、マスク演算（where）で表現する
* 光線の遮光・失敗は削除ではなく weight=0 / statusマスクで表す（配列shape不変）
* 反復（非球面交点・aiming）は固定回数上限＋収束マスク方式で書く

この規律はNumPy/Numba実装の性能・可読性も損なわないため、初期版から適用する。

### 27.6 バッチ配列処理・並列・キャッシュ

**バッチ配列処理**

光線1本ずつオブジェクトで処理せず、配列として扱う。

```
origins:    shape = [N, 3]
directions: shape = [N, 3]
wavelength: shape = [N]
status:     shape = [N]
weight:     shape = [N]
prop_sign:  shape = [N]
```

面ごとに以下をまとめて処理する。

```
for surface in surfaces:
    intersect all alive rays
    check aperture
    refract / reflect all valid rays   # マスク演算で分岐を回避
```

**並列実行**

field × wavelength × candidate はembarrassingly parallelである。ただしPythonのmultiprocessingを素朴に使うと、候補ごとのsystemシリアライズ（pickle）コストが27.2節のボトルネックを再発させる。以下を前提とする。

* プロセス常駐ワーカープール（ワーカーはCompiledSystemをsystem_idでキャッシュ保持）
* ワーカーへの送信はランタイムパラメータ（variables / decenters / tilts）差分のみ
* 大配列の回収は共有メモリまたはファイル（.npy）経由
* Numbaカーネル内では nogil / prange によるスレッド並列も選択肢とする

**キャッシュ対象と部分無効化【v2改訂】**

| キャッシュ対象 | キー | 無効化条件 |
|---|---|---|
| CompiledSystem（構造） | system正規化ハッシュ | system構造の変更のみ。variables等では無効化しない |
| 面のグローバル変換行列 | system_id + 配置パラメータ | **部分無効化**：decenter/tilt/群移動の対象群に属する面のみ再計算し、他は再利用 |
| 材料の波長別屈折率 | 材料ID + 波長 | 材料定義変更のみ |
| pupil sampling点（正規化座標） | sampling設定 | 設定変更のみ |
| 主光線aiming解・瞳アフィン写像 | system_id + 配置 + field + 波長 + 絞り径 | 配置パラメータ・絞り径の変更で該当fieldのみ無効化。前回解をwarm startの初期値に使う |
| field direction | field定義 | field変更のみ |
| validation結果 | system正規化ハッシュ | system変更のみ |
| 近軸量 | system_id + zoom_position + 波長 | 構造・ズーム・波長変更のみ（decenter/tiltでは不変：14.4節） |

最適化でdecenter/tiltや群位置そのものが変数になる場合、変換行列キャッシュは反復ごとに部分無効化される。この場合でも「変更群以外の行列」「aimingのwarm start」「近軸量（基準同軸で不変）」は再利用できるため、キャッシュ設計はこの粒度を前提とする。

### 27.7 数値的な懸念と対策

**非球面交点計算**

非球面は反復計算が必要になりやすい。

懸念：

* Newton法が収束しない
* 周辺光線で誤った交点を拾う
* チルト・偏芯時に初期値が悪くなる

対策：

* 球面（ベース曲率）近似による初期交点を使う
* 反復回数上限を設ける（固定上限＋収束マスク：27.5節の規律と整合）
* 収束しない光線は numerical_error とする
* 交点計算ログをデバッグ出力できるようにする
* 伝播方向前方の解のみ採用する（17.2節）

**ray aiming**

懸念：

* 広角・偏芯系で主光線aimingが収束しない
* 光線数×反復でコストが増える

対策：

* 近軸主光線を初期値とする
* 前回配置の解をwarm startに使う（連続操作・最適化反復で有効）
* 収束失敗は aiming_failed として除外・報告する
* 瞳アフィン近似（16.3節）で個別反復を最小化する

**偏芯・チルト**

懸念：

* field数が増える
* 光線本数が増える
* 最適化評価が重くなる
* M/S像面の解釈が複雑になる

対策：

* 対称系モードと非対称系モードを分ける
* decenter / tilt が存在する場合は自動的に±field評価へ切り替える
* previewではfieldを間引く
* final評価では全fieldを評価する
* M/SはRMS探索方式へ自動切替する（21.2節）

**Pythonオブジェクトのオーバーヘッド**

対策：

```
YAML / JSON optical system
  ↓
Pydantic validation
  ↓
CompiledSystem（構造化配列）
  ↓
array-based ray tracing kernel（NumPy / Numba）
```

外部APIは読みやすいオブジェクト構造にし、内部計算は配列・構造体・NumPy/Numba向け構造に変換する。

---

## 28. 実装モジュール構成

```
optics_engine/
  core/
    ray.py
    vector.py
    transform.py
    intersection.py
    refraction.py
    reflection.py
    thin_lens.py
  paraxial/                    # 【v2新設】
    ynu_trace.py
    first_order.py             # EFL / BFL / 瞳 / 主点
    afocal.py                  # 角倍率
  geometry/
    surfaces.py
    spherical.py
    aspherical.py
    plane.py
    apertures.py               # circle / annulus / polygon
    sensor.py
    eye_reference.py           # 【v2新設】
  materials/
    material.py
    sellmeier.py
    catalog.py
  system/
    optical_system.py
    sequence.py
    groups.py
    decenter.py
    tilt.py
    validation.py              # 群干渉・空気間隔・ミラー符号検査を含む
    compiled_system.py         # 構造化配列 + systemハッシュ
    system_cache.py            # 【v2新設】部分無効化ロジック
  tracing/
    forward.py
    reverse.py
    ray_generators.py
    pupil_sampling.py
    ray_aiming.py              # 【v2新設】主光線aiming・瞳アフィン写像
  analysis/
    spot.py
    ray_fan.py
    longitudinal.py
    chromatic.py
    distortion.py
    field_curvature.py
    ms_image_surface.py        # coddington / rms_search 両方式
    coddington.py              # 【v2新設】
    relative_illumination.py
    psf_geometric.py
    psf_diffraction.py
    mtf.py
    white_psf.py
    white_mtf.py
  visual/
    afocal_evaluation.py       # 【v2新設】角度spot / 角度PSF / ディオプター
    exit_pupil.py
    eye_box.py
    angular_mtf.py
    binocular_alignment.py
    telescope.py
  optimization/
    evaluate.py
    merit.py
    presets.py
    batch.py
    feasibility.py             # 【v2新設】infeasible即時判定
  education/
    preview.py
    lesson_modes.py
  api/
    main.py
    schemas.py
    routes_systems.py          # 【v2新設】register / validate
    routes_trace.py
    routes_analysis.py
    routes_visual.py
    routes_optimization.py
    routes_education.py
  io/
    yaml_loader.py
    json_loader.py
    csv_loader.py
    table_importer.py
    axis_convention.py         # 【v2新設】Z軸光軸系との相互変換（4.1節）
  tests/
    test_plane_refraction.py
    test_spherical_surface.py
    test_asphere.py
    test_thin_lens.py
    test_single_lens.py
    test_mirror.py
    test_paraxial.py           # 【v2新設】
    test_ray_aiming.py         # 【v2新設】
    test_decenter.py
    test_tilt.py
    test_ms_image_surface.py
    test_coddington_vs_rms.py  # 【v2新設】
    test_relative_illumination.py
    test_exit_pupil.py
    test_afocal.py             # 【v2新設】
    golden/                    # 【v2新設】既知設計との突き合わせ
      test_doublet_reference.py
      test_double_gauss_patent.py
      test_cassegrain.py
      test_vs_external_oss.py
```

---

## 29. MVP実装順序

### Phase 1：+X光軸の基本光線追跡と近軸計算

* +X光軸座標系
* 3D Ray（propagation_sign含む）
* 平面・球面
* 屈折・反射
* センサー交差
* 有効径判定
* 光線経路出力
* **近軸y-nuトレース（EFL / BFL / F値 / 瞳位置・径）**【v2でPhase 1へ前倒し】

近軸計算をPhase 1に置く理由：Phase 2のray aiming初期値、教育UIの焦点距離表示、以降すべての導出評価値の基盤になるため。

### Phase 2：絞り・薄レンズ・Ray Aiming・教育preview

* 固定絞り・可動絞り（circle / annulus）
* 理想薄レンズ
* **主光線ray aiming（絞り中心基準）**【v2新設】
* **瞳アフィン写像による光線束生成**【v2新設】
* 教育用preview API（aiming mode: paraxial）
* Spot diagram
* system登録・CompiledSystemキャッシュ【v2でPhase 2へ】

### Phase 3：材料・非球面・色収差

* Sellmeier材料
* 波長別屈折率
* 非球面（Newton反復・収束対策）
* 軸上色収差
* 倍率色収差

### Phase 4：群移動

* 群定義
* ズーム群・フォーカス群
* シフト群・手ブレ補正群
* **群移動バリデーション（空気間隔・干渉：10.3節）**【v2新設】

### Phase 5：チルト・非対称解析

* 面範囲チルト・回転中心指定
* 偏芯光学系（aiming mode: full強制）
* ±field計算
* M像面・S像面（Coddington + RMS探索）
* 非点収差・像面湾曲

### Phase 6：PSF・MTF・周辺光量

* 幾何PSF・Encircled energy
* 幾何MTF
* 白色PSF・白色MTF
* Relative illumination（放射量論的サンプリング：16.5節）

### Phase 7：最適化評価

* evaluate API / evaluate-batch API
* merit function・評価プリセット
* 粗密2段階評価
* infeasible即時棄却
* 常駐ワーカー並列

### Phase 8：双眼鏡・望遠鏡

* afocal系データモデル・eye_reference
* 射出瞳・アイレリーフ・アイボックス
* 角度spot・角度MTF・ディオプター評価
* 双眼鏡左右差（poseチルト含む）
* 望遠鏡接眼込み評価
* 同軸反射系（カセグレン）・annulus遮蔽

---

## 30. 検証項目

### 30.1 基本検証

| 検証 | 内容 |
|---|---|
| 平面屈折 | Snellの法則と一致すること |
| 球面交差 | 球との交点が正しいこと |
| 平面センサー交差 | センサー到達点が正しいこと |
| 球面ミラー | 近軸焦点が R/2 に近いこと |
| 薄レンズ | 薄レンズ公式と一致すること |
| 絞り | 有効径外の光線が遮光されること |
| annulus | 内径以下の光線が遮光されること |
| ミラー伝播 | 反射後の-X伝播・thickness負値が正しく処理されること |

### 30.2 近軸・aiming・解析検証

| 検証 | 内容 |
|---|---|
| 近軸トレース | 単レンズ・ダブレットで薄レンズ公式・レンズメーカー公式と一致すること |
| 近軸 vs 実光線 | 微小口径・微小画角の実光線追跡が近軸量に収束すること |
| ray aiming | 主光線が絞り中心を閾値内で通ること。広角で収束すること |
| 瞳充填 | aiming後の光線束が絞り面を均一に埋めること |
| Spot diagram | 軸上単レンズで合理的なスポットが出ること |
| Ray fan | 瞳座標に対して連続的な収差曲線が出ること |
| 色収差 | 波長ごとの焦点差が出ること |
| 周辺光量 | 遮光のない理想薄レンズ系でcos^4則を再現すること |
| M/S像面 | 非点収差系でM/S差が出ること。**同軸系でCoddington方式とRMS探索方式が一致すること** |
| 歪曲 | 像高の差から歪曲率が出ること。基準fが近軸EFLであること |

### 30.3 偏芯・チルト検証

| 検証 | 内容 |
|---|---|
| シフト群 | 光線束がY/Z方向に移動すること |
| チルト群 | 像面・スポットが非対称に変化すること |
| ±field | 上下左右で異なる結果が出ること |
| 回転中心 | 指定中心まわりに正しく回転すること |
| 偏芯時aiming | 主光線が偏芯後の絞り中心を通ること |

### 30.4 双眼鏡・望遠鏡検証

| 検証 | 内容 |
|---|---|
| 射出瞳径 | 口径/倍率に近いこと（近軸計算と実光線評価の両方で） |
| アイレリーフ | 射出瞳位置が妥当であること |
| アイボックス | 眼位置ずれでケラレが増えること |
| 左右差 | 左右チャンネル差分（poseチルト含む）が評価できること |
| 角度MTF | センサーlp/mmではなく角度単位で出力できること |
| ディオプター | 理想アフォーカル系で残存発散が0になること |
| カセグレン | 同軸2ミラー系の近軸焦点距離が理論値と一致すること |

### 30.5 Golden Test【v2新設】

単体テストでは捕まりにくい符号規約バグ（曲率符号・厚み符号・角度符号・座標写像）を検出するため、既知設計との突き合わせ試験を整備する。

| 検証 | 内容 |
|---|---|
| 教科書ダブレット | 文献値のあるアクロマートダブレットで、EFL・BFL・球面収差・色収差カーブを許容差内で再現すること |
| 特許ダブルガウス | 公開特許のレンズデータで、spot・歪曲・像面湾曲が参照計算と整合すること |
| カセグレン望遠鏡 | 古典的な設計例で焦点距離・遮蔽率・spotが理論値と整合すること |
| 外部OSS突き合わせ | rayoptics・Optiland等の既存OSSで同一系を追跡し、光線座標・近軸量を許容差内で一致させること（Z軸光軸系との座標写像は4.1節の規約でテストコード側が変換する） |
| Level 0リファレンス | 素朴Python実装（Level 0）とベクトル化実装（Level 1/2）が全テスト系でビット近傍一致すること |

Golden TestはCIで常時実行し、カーネル最適化（Numba化・並列化）による回帰を防ぐ。

### 30.6 性能検証【v2新設】

* 27.3節の各目標を、profiling有効化したend-to-end計測で確認する
* CompiledSystemキャッシュのヒット時/ミス時の差を計測し、26.2節の効果を実証する
* aimingのwarm start有無での反復回数を比較する

---

## 31. 重要な設計判断まとめ

本エンジンの中核方針は以下である。

1. 光軸は+X方向（外部Z軸系とは4.1節の写像で相互変換）
2. radius_mm = 0 は平面
3. 面形状はローカル座標で軸対称
4. 配置は3Dでシフト・チルト可能
5. 光線追跡は常に3D
6. 非対称系では上下左右対称を仮定しない
7. **瞳サンプリングは開口絞り基準のray aimingを標準とする**【v2】
8. **近軸計算を一級市民とし、導出評価値・歪曲基準・aiming初期値の基盤とする。偏芯系の近軸量は基準同軸状態で定義する**【v2】
9. **ミラー後はpropagation_signと負thicknessで伝播を管理し、初期版は同軸反射系までとする**【v2】
10. 教育用途と設計用途をpreview / analysisで分ける
11. 最適化は外部、評価値算出はエンジン側。**将来は微分可能カーネルで勾配も返せる構造としておく**【v2】
12. 写真レンズは撮像面評価（focal系）
13. **双眼鏡・望遠鏡は眼に渡す角度像と射出瞳評価（afocal系）とし、データモデル・単位系・終端要素を仕様レベルで分ける**【v2】
14. **性能はまずNumPyベクトル化＋CompiledSystemキャッシュで達成し、Numbaは非球面・aiming反復に限定適用する。GPU・Rust/C++は必要が実測されるまで着手しない**【v2】

本ソフトは、単なる光線描画ツールではなく、以下を統合する。

```
教育用の見える光学
+
簡易設計用の評価エンジン
+
写真レンズ・双眼鏡・望遠鏡を扱える共通光線追跡基盤
```

そもそも、写真レンズ、双眼鏡、望遠鏡はすべて「光を制御する装置」ではあるが、最終的に評価すべき対象が違う。

```
写真レンズ：
  センサー上にどれだけ良い像を作るか
双眼鏡・望遠鏡：
  人間の眼にどれだけ見やすい角度像を届けるか
```

この違いを仕様上分けておくことで、同じ光線追跡エンジンを使いながら、異なる光学製品を無理なく評価できる。
