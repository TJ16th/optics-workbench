# R99：UI/UXレイアウト全面見直し 設計提案書

> **本書は設計提案であり、実装報告ではない。** Production code、UI仕様書、テストコードは変更していない。最終的な採否・仕様確定・実装順は人間とClaude側の判断対象とする。

## 1. 調査範囲

以下を現行コードと実画面で確認した。

- UI実装：`apps/workbench-ui/src/ui/App.tsx`
- レイアウト・描画色：`apps/workbench-ui/src/styles.css`
- チャート色：`apps/workbench-ui/src/ui/chartTheme.ts`
- SVG export色：`apps/workbench-ui/src/ui/exportSvg.ts`
- E2E：`apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
- 実測条件：Edge headless、viewport `1920×1080`、英語UI、P013、ローカルAPI接続済み
- UIの実質的な調査基準コミット：`a42cb438b2ed657c26ed05845d571011ae4a22c0`

## 2. 現状分析

### 2.1 画面構造

現行は48pxのCarbon Headerと、次の固定3列で構成される。

```text
┌──────────────────────────────── Header 48px ────────────────────────────────┐
│ Left 250-300px        │ Center min420px / flex          │ Right 280-330px   │
│ preset                │ System / Preview / Analysis     │ API               │
│ validate/register     │ Compare / Debug ContentSwitcher│ Analysis Conditions│
│ system summary        │ 結果・編集本体                   │ Image Plane       │
│                       │                                  │ Group / Aperture   │
│                       │                                  │ Decenter / Export  │
└─────────────────────────────────────────────────────────────────────────────┘
```

`styles.css`の`.app-shell`と`.workbench-grid`が`height: 100vh`、`overflow: hidden`でページ全体のスクロールを抑止し、`.left-pane`、`.center-pane`、`.right-pane`がそれぞれ`overflow-y: auto`を持つ。

1920px幅では実測列幅が`300 / 1288 / 330px`となる。1120px以下では3列を1列へ変更し、各ペインのoverflowを解除する。720px以下では結果・チャート・field入力等のグリッドを1列化する。中間幅専用のレイアウトはなく、1121px以上では3列、1120px以下では全面縦積みという二段階である。

### 2.2 ナビゲーションと状態保持

- 中央上部のCarbon `ContentSwitcher`が`System / Preview / Analysis / Compare / Debug`の5画面を切り替える。
- `activeTab`はReactローカルstateで、各画面は条件レンダーされる。
- `system`、field、wavelength、sampling、runtime configuration、trace、chart result、snapshot等は`App`直下のstateにあるため、タブを切り替えても状態は保持される。
- `Run Preview`成功時はPreview、`Run Charts`・Through-focus MTF・focus solve成功時はAnalysis、Snapshot保存時はCompareへ自動遷移する。
- preset変更時はsystem、解析結果、条件、focus policy等をまとめて初期化する。
- health/metaだけTanStack Queryを使用する。snapshotはメモリ上だけで、リロード後には残らない。
- `App.tsx`は3,675行、named function 93、`useState`出現43、`useMutation`出現8であり、レイアウト変更時に状態ロジックまで巻き込みやすい。

### 2.3 1920×1080スクロール実測

ページ全体は全ケースで`clientHeight=1080 / scrollHeight=1080`であり、body scrollは発生しなかった。一方、独立ペイン内では次の超過がある。

| 画面・状態 | Center client / scroll | Center超過 | Right client / scroll | Right超過 |
|---|---:|---:|---:|---:|
| System / P013 | 1032 / 1032px | 0px | 1032 / 3411px | 2379px |
| Preview実行後 / P013 | 1032 / 1227px | 195px | 1032 / 3419px | 2387px |
| Analysis実行後 / P013 | 1032 / 2556px | 1524px | 1032 / 3419px | 2387px |
| Debug実行後 | 1032 / 1032px | 0px | 1032 / 3419px | 2387px |
| Compare / snapshot 1件 | 1032 / 1032px | 0px | 1032 / 3419px | 2387px |

問題は「ページがスクロールする」ことではなく、右ペインに全用途の設定が常時縦積みされ、現在の作業に関係なく約2.3画面分をスクロールすること、Analysis結果が全チャート縦積みで約1.5画面超過することである。

### 2.4 操作と結果の往復

良い点：

- field、wavelength、sampling等の解析条件は右ペインに常駐し、Preview/Analysis結果と横並びで確認できる。
- group、iris、decenter/tiltはdebounced previewを持ち、操作結果をPreviewへ戻して確認できる。
- PreviewはLayout、spot概要、trace summaryを同じ中央画面に置く。

改善点：

- System編集は中央全面をSurface/Group tableが占有し、Layoutとの同時表示ができない。編集後はPreviewへ切り替える必要がある。
- Analysis Conditionsは右ペインの上方、Group/Aperture/Decenter等は下方に離れ、関連設定へ長距離スクロールが必要になる。
- Analysisは標準収差、ray fan、MTF、distortion、field curvature、relative illumination等を縦に並べるため、条件を調整しながら対象チャートを比較する際に上下移動が多い。
- Through-focus MTFはAnalysis内の二次`ContentSwitcher`にあり、グローバル画面と解析種別の二階層が同じタブ状UIで表現される。
- Snapshot保存はCompareへ自動遷移するため、連続条件調整中はPreview/Analysisへ戻る操作が発生する。
- API、言語、validation、exportが解析条件と同じ右ペインに混在し、日常操作と低頻度操作の優先度が区別されていない。

### 2.5 プリセット選択UI

通常表示はP001〜P013のうちP005非表示とV001を含む13件で、単一Carbon `Dropdown`へフラットに並ぶ。

実測値：

- menu：`234×220px`
- menu content：`scrollHeight=520px`、40px×13件
- option文字領域：202px
- 全13件で`scrollWidth > clientWidth`
- 最長P013：`scrollWidth=442px`
- 選択中label：表示領域170px、`scrollWidth=202px`

IDと正式名称だけで、focal/afocal/visual、単レンズ/写真レンズ/望遠鏡、F値、非球面、focus group等のカテゴリや属性は表示されない。検索、最近使用、favorite、説明プレビューもない。件数だけでなく、全項目が横幅を超え、選択前に違いを比較できないことが「見づらい」主因である。

### 2.6 ダークモード対応状況

現状はlight固定である。

- `:root { color-scheme: light; }`
- Carbon Theme wrapperや`g90/g100`切替はない。
- CSS先頭に背景・panel・border・text等9個の`--ow-*`変数はある。
- 一方、`styles.css`には色literal 70箇所、27種類が残る。
- `App.tsx`にはチャートseries色literal 19箇所、6種類がある。
- `chartTheme.ts`は5色、`exportSvg.ts`は白背景を含む3色を固定する。
- Layout Viewのglass、air gap、surface、ray、marker、warning、chart axis/label/backgroundにも固定色がある。

したがって、背景だけ暗くする変更では文字、軸、glass fill、air gap、orange warning marker等のコントラストが崩れる。

## 3. 推奨案

### 3.1 結論

**左サイドバー＋開閉可能なアコーディオンナビゲーション、中央ワークスペース、右コンテキストインスペクター**を推奨する。

左は「どこへ移動するか」、中央は「結果と編集対象」、右は「現在の対象へ作用する設定」に責務を分ける。人間の希望する左アコーディオンを採用しつつ、すべての設定を左へ詰め込まず、操作と結果の同一画面表示を維持する。

### 3.2 推奨ワイヤーフレーム

1920×1080、expanded時：

```text
┌ Header 48px ─ Project/Preset search ─ command ─ theme ─ engine/status ─────┐
├──────────────┬──────────────────────────────────────────┬───────────────────┤
│ Navigation   │ Workspace toolbar                        │ Context inspector │
│ 280px        │                                          │ 360px             │
│              ├──────────────────────────────────────────┤                   │
│ DESIGN       │                                          │ current task only │
│ ▾ Optical    │  live Layout / Surface editor / Charts   │ ▾ Fields          │
│   Surfaces   │                                          │ ▸ Wavelengths     │
│   Groups     │  primary result is always first viewport │ ▸ Sampling        │
│ EVALUATE     │                                          │                   │
│ ▾ Layout     │                                          │ sticky Run action │
│ ▾ Analysis   │                                          │                   │
│   Standard   │                                          │                   │
│   Through... │                                          │                   │
│ REVIEW       │                                          │                   │
│   Compare    │                                          │                   │
│ SYSTEM       │                                          │                   │
│   Diagnostics│                                          │                   │
└──────────────┴──────────────────────────────────────────┴───────────────────┘
```

左をcollapsedにすると56pxのicon railとし、中央へ224px返す。右も閉じられ、閉じた場合は設定iconだけを残す。開閉状態はlocalStorageへ保存し、初回は左expanded、右expandedを既定とする。

### 3.3 情報アーキテクチャ

| セクション | 項目 | 中央workspace | 右context |
|---|---|---|---|
| Design | Surfaces | table 60%＋live mini-layout 40% | selected surface / aperture |
| Design | Groups | group table＋live layout | focus/OIS/decenter/tilt |
| Evaluate | Layout | main optical layout＋spot/trace compact rail | fields / wavelengths / sampling / image plane |
| Evaluate | Analysis | 選択中chartを主表示、比較用2〜4 panel | analysis kind / fields / wavelengths / MTF |
| Review | Compare | snapshot A/Bの同期比較 | snapshot selection / diff filters / export |
| System | Diagnostics | request/response/build info | API / language / validation |

API、language、build infoはHeader statusから開くutility popoverまたはDiagnosticsへ移す。Validationは全画面共通statusとしてHeaderへ要約し、詳細はcontext内の折りたたみ領域に置く。

### 3.4 操作と結果の同一画面化

1. **Surface/Group編集**：tableの右または下にlive mini-layoutを常設する。行選択で対応面をhighlightし、編集結果をdebounced previewする。
2. **Layout**：main layoutを第一viewportへ固定し、spot/trace summaryは右端または下端のcompact result stripにする。現在のようなlegendの大面積常設はやめ、折りたたみlegendまたはcanvas内popoverにする。
3. **Analysis**：全チャート縦積みをやめ、chart pickerで主chartを選ぶ。標準初期表示はLongitudinal Aberration / Field Curvature / Distortionの3面、下段に選択中のRay FanまたはMTFを1面表示する。必要なchartだけ差し替える。
4. **Through-focus MTF**：Analysis accordionの子項目に昇格し、同じchart workspace shellを再利用する。
5. **Snapshot**：保存後にCompareへ強制遷移せず、toast＋「Compareで開く」actionにする。連続測定を中断しない。

### 3.5 プリセット選択の改善

通常の234px Dropdownを、Headerまたは左上の**検索可能なpreset browser**へ置き換える。

推奨仕様：

- triggerには`P013`と短い名称だけを表示し、正式名称はpopover内で折り返す。
- 検索対象はID、日英名称、summary、属性。
- グループは`Photographic / Simple & Educational / Telescope & Afocal / Visual / Fixtures`。
- 各行に`focal/afocal`、EFL、F number、element count、asphere、focus等の小さな属性を表示する。
- keyboardで検索、上下選択、Enter決定、Esc閉じる。
- RecentとPinnedを先頭に置く。現在の自然ID順もsort optionとして残す。
- 右側preview paneにsummaryと小さなlayout thumbnailを表示する。
- P005の非表示規約とfixture queryの挙動は維持する。

Carbon `ComboBox`だけへ置換する小変更でも検索性は得られるが、カテゴリ・比較・説明の問題は残る。最終形は`ComposedModal`ではなく、作業を遮らないpopover/side panel型を推奨する。

### 3.6 スクロール方針

「一切スクロールしない」ではなく、**主要操作と主要結果を第一viewportに固定し、詳細だけ局所スクロール**と定義する。

- body scroll：禁止を維持。
- Navigation：項目が増えた場合だけ内部scroll。
- Workspace：通常Layoutと選択中Analysisはscroll excess 0を目標。table/raw JSON/多数snapshotは内部scrollを許可。
- Context：現在の画面に関係するaccordionだけ表示し、既定expandedは最大2項目。Run/Apply actionはbottom sticky。
- chart：固定aspect-ratioとmin/max heightを定義し、chart選択で入れ替える。全種類を縦に連結しない。
- 1920×1080受け入れ目標：Preset選択→条件変更→Run→主要結果確認まで、Navigation/Workspace/Contextのscroll操作0回。

### 3.7 UXシナリオ

```text
Preset search
  -> Design/Surfacesで処方とlive layoutを確認
  -> Evaluate/Layoutでfield・samplingを調整しRun
  -> Evaluate/Analysisでchartを選択しRun
  -> Snapshot保存（その場に留まる）
  -> Review/Compareで条件差を確認
```

現在のstateとmutationは再利用できる。変更の中心は「activeTabの表示先」と「右ペインの常時全表示」を、route/view modelとcontext registryへ分離することである。

## 4. 代替案比較

### 案A：左アコーディオン＋右context（推奨）

長所：

- 階層が増えてもAnalysis配下へ自然に追加できる。
- 左collapsed時に中央へ幅を返せる。
- current taskだけを右に出すため、2,387pxのright excessを大幅に削減できる。
- 操作と結果の横並びを維持できる。
- 人間のナビゲーション嗜好と合う。

短所：

- 左右両方がexpandedだと約640pxを使用し、現行の630pxと占有幅はほぼ同じ。
- Accordionをnavigationとformの両方へ乱用すると階層が曖昧になるため、左はnavigation専用にする規律が必要。
- App分割とE2E更新を伴う中〜大規模変更になる。

### 案B：上部タブ維持＋右ペインcontext化

長所：

- 最小変更で、既存Carbon `ContentSwitcher`とE2Eを多く維持できる。
- 横幅をNavigationへ追加消費しない。
- System/Preview/Analysisの5項目だけなら一覧性が高い。

短所：

- Analysisの子階層が増えると上部tabと二次switcherが重なる。
- 画面追加に弱く、DebugやCompareを主要workflowと同格に見せ続ける。
- 人間の左ナビゲーション嗜好に応えず、preset browserとの統合もしにくい。

判断：Phase 1の低リスク改善としては有効だが、全面見直しの最終形には推奨しない。

### 案C：IDE型4ペイン＋bottom results dock

構成：左Project/Preset、中央Layout/Surface、右Properties、下部にAnalysis/Debug/Compare dockを置く。

長所：

- Surface編集、Layout、log/analysisを同時表示できる。
- 光学設計ツールとして高密度で、keyboard中心の熟練利用に向く。
- panel resizeにより作業別カスタマイズが可能。

短所：

- 1080px高さでbottom dockがLayoutの高さを奪う。
- resize、focus order、保存レイアウト、mobile fallbackが必要で実装規模が最大。
- 初学者には情報量が多く、Carbon標準パターンから外れやすい。

判断：将来のprofessional mode候補として残すが、初回再設計では却下する。

### 比較表

| 観点 | 案A 左Accordion | 案B 上部Tab | 案C IDE型 |
|---|---|---|---|
| 1920×1080占有 | 左280/56＋右360/0 | 左なし＋右360/0 | 左260＋右320＋下250 |
| 階層拡張 | 高 | 低〜中 | 高 |
| 同一画面操作/結果 | 高 | 中〜高 | 最高 |
| 初学者理解 | 高 | 最高 | 低 |
| 実装リスク | 中 | 小 | 大 |
| 推奨 | **採用** | 移行段階 | 将来候補 |

## 5. Dark / Light mode提案

### 5.1 実装方式

1. App rootをCarbon `Theme`で包み、light=`g10`、dark=`g100`とする。
2. Header右端へSun/Moon icon buttonを置き、Toggletipで名称を示す。選択肢は`System / Light / Dark`の3値とする。
3. OSの`prefers-color-scheme`をSystem時だけ監視し、明示選択はlocalStorageへ保存する。
4. `--ow-*`をCarbon tokenまたはsemantic aliasへ置き換える。物理的意味を持つ色は背景tokenと分離する。

推奨token分類：

- surface：background / panel / elevated / hover / selected
- content：text-primary / text-secondary / disabled
- structure：border-subtle / border-strong / grid / axis
- semantic：success / warning / error / focus
- optics：wavelength-F/d/e/C、chief/marginal/density、glass、air-gap、STOP、IMG

### 5.2 対応必須箇所

- `styles.css`：27種類、70箇所のliteralをsemantic tokenへ移す。
- `App.tsx`：19箇所のseries色を`chartTheme`へ集約する。
- `chartTheme.ts`：light/dark paletteを返す関数へ変更する。
- `exportSvg.ts`：画面themeとは別にexport themeを引数化し、既定は印刷向けlightを維持する。
- Layout SVG：axis、label、glass fill、air gap、cemented surface、warning、aiming failure。
- Chart SVG：background、axis、grid、label、legend、marker outline。
- Carbon component：Theme適用後のTag、Accordion、Dropdown、NumberInput、CodeSnippet、Notificationのcontrastを確認する。

波長色は単なる装飾色ではなく識別規約であるため、dark時もF/d/e/Cの意味を維持し、色相を入れ替えず明度・彩度だけを調整する。色だけに依存せずdash/marker/legend labelも残す。

## 6. 規模感

| 範囲 | 規模 | 目安 | 主な内容 |
|---|---|---:|---|
| Preset ComboBox化＋右contextの既定折りたたみ | 小 | 2〜4人日 | 検索、label改善、accordion state |
| Theme token化＋light/dark | 中 | 5〜8人日 | CSS/SVG/chart/Carbon visual QA |
| 左navigation shell＋context registry | 中〜大 | 7〜12人日 | App分割、view model、responsive、E2E |
| Analysis選択式workspace＋Surface live split | 大 | 10〜18人日 | chart composition、table/layout連携、状態整理 |
| 全面移行合計 | 大 | 24〜40人日 | 設計レビュー、実装、visual regression込み |

単純なCSS変更として扱うと、3,675行の`App.tsx`にlayoutとstate/mutationが同居しているため回帰リスクを過小評価する。shell変更前にcomponent/view model分離が必要である。

## 7. 段階的導入ロードマップ

### Phase 0：仕様決定

- 案A/B/Cの採否、left/rightのexpanded既定値、Analysis初期chart、themeのSystem扱いを決定する。
- 1920×1080のscroll budgetとkeyboard navigation受け入れ条件をUI仕様へ追記する。

### Phase 1：基盤と低リスク改善

- preset browserを検索可能にし、正式名称を折り返し表示する。
- right paneを画面別にフィルタし、低頻度API/exportを折りたたむ。
- theme semantic tokenと`Theme` wrapperを導入するが、レイアウトは維持する。
- DOM scroll measurement E2Eを追加する。

### Phase 2：Navigation shell

- App state/mutationをhooksまたはWorkbench controllerへ分離する。
- 左Accordion navigation、collapsed rail、Header utilityを導入する。
- 旧`activeTab` keyを新view keyへ一対一mappingし、機能を変えずshellだけ移す。

### Phase 3：同一画面workspace

- Surface/Group＋live mini-layoutを導入する。
- Layoutのlegend/result stripをcompact化する。
- Snapshot保存後の強制遷移を廃止する。

### Phase 4：Analysis再構成

- chart pickerと2〜4 panel workspaceを導入する。
- Through-focus MTFをAnalysis配下へ統合する。
- chart selection、panel layout、left/right開閉をsnapshot/workspace stateへ保存する。

### Phase 5：Responsive・アクセシビリティ・仕上げ

- 1120pxの一括縦積みを、compact rail＋drawer方式へ変更する。
- keyboard focus order、Accordion ARIA、theme contrast、pseudo locale overflowを検証する。
- light/dark、1920×1080、1366×768、tabletのvisual regressionを固定する。

## 8. テスト影響

現行`npm run ci`のPlaywrightは42件で、次の依存が強い。

- `getByRole('tab', { name: ... })`：左navigation移行で全面更新が必要。
- preset `combobox/option`：新preset browserのrole設計に応じて更新。
- `#layout-svg`、chart `data-testid`、field/surface input ID：可能な限り維持し、機能E2Eの書き換えを抑える。
- right pane scroll独立テスト：context panelの新scroll budgetへ置換。
- layout scale、ray path、chart point count等の数値E2E：DOM移動後もそのまま再利用できる。

追加すべきテスト：

- 1920×1080でbody scroll 0、主要workflowのworkspace/context scroll 0。
- left/right開閉時にLayoutのstable dimensionsとchart aspect-ratioが変形しない。
- preset検索、カテゴリ、keyboard選択、長い日英/pseudo labelが欠けない。
- theme切替後にLayout/Chart/Carbon componentのcontrastとseries識別が維持される。
- theme、navigation、panel開閉状態がreload後も保持される。
- Snapshot保存後に現在の作業画面へ留まる。

既存selectorを壊してから一括修正するのではなく、stable `data-testid`を先に追加し、旧shellと新shellの双方で同じ機能E2Eを一時実行する移行が安全である。

## 9. 将来実装の受け入れ条件案

- 1920×1080でPreset選択、条件変更、Layout run、主要結果確認にscroll操作を要求しない。
- Analysis標準初期画面の主要3パネルが第一viewport内に収まる。
- 13件以上のpresetをID/名称/属性で検索でき、正式名称が読める。
- left navigationとright contextを独立して開閉でき、中央canvasが安定して再配置される。
- light/dark両方でCarbon、Layout、Chart、warning/statusがWCAG AA相当のcontrastを満たす。
- 現行の数値結果、request payload、snapshot内容、i18n識別子を変更しない。
- `npm run ci`、`npm run ui:build:pseudo`、追加visual/scroll E2Eがグリーンである。

## 10. 人間・Claude側で決める論点

1. 左Navigationの既定はexpandedかcollapsedか。推奨は1920pxでexpanded、1440px未満でcollapsed。
2. 右Contextを常時表示するか、操作時だけdrawer表示するか。推奨は1920pxで表示、1366px以下でdrawer。
3. Analysis初期表示を標準3パネル固定にするか、前回選択を復元するか。推奨は初回標準3パネル、その後は復元。
4. Preset categoryを仕様上固定するか、metadata駆動にするか。推奨はpreset metadata駆動。
5. dark exportを提供するか。推奨は画面themeと切り離し、export dialogでLight/Darkを選択、既定Light。
6. Snapshot保存時のCompare自動遷移を廃止してよいか。推奨は廃止し、明示actionへ変更。
7. 1120px以下をdesktop compactとmobile stackedのどこで分けるか。実機利用条件を確認してbreakpointを決める必要がある。

## 11. 最終提案

最初からIDE型へ振り切らず、**案AをPhase 1〜4で段階導入**することを提案する。優先順位は次のとおり。

1. preset browser改善
2. right paneの画面別context化
3. light/dark semantic token基盤
4. 左Accordion navigation shell
5. Surface live splitとAnalysis選択式workspace

この順序なら、最も目立つpresetの可読性と2,387pxの右ペイン超過を先に改善し、state/API挙動を変えずに効果を確認できる。その後、左navigationと中央workspaceを段階的に置き換えられる。
