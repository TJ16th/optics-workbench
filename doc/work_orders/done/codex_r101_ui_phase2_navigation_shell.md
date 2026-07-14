# R101：UI/UX見直し Phase 2（左Accordionナビゲーションシェル・状態分離） 指示書（Codex向け）

## 背景

R99の設計提案（案A：左Accordionナビゲーション＋右context）を最終形として採用し、R100でPhase 1（プリセット検索化・右ペインcontext化・ダーク/ライトモード基盤）を完了した。実測で右ペインscroll超過を大幅に削減（System/Compare/Debug各100%減、Preview 80.5%減、Analysis 61.5%減）し、レイアウト構造（3列構成・上部`ContentSwitcher`によるタブ切替）自体は意図通り維持したままだった。

続いて、R99が提示した段階導入ロードマップのPhase 2「Navigation shell」に進む。R99時点の分析で、`App.tsx`が3,675行・named function 93・`useState`出現43・`useMutation`出現8であり、レイアウト変更が状態ロジックまで巻き込みやすいと指摘されている。本タスクはこの構造的リスクを踏まえ、**状態管理の分離を先に行った上で**ナビゲーションshellを導入する。

## 作業

### 1. 状態・mutationの分離

1. `App.tsx`直下に集約されているsystem、field、wavelength、sampling、runtime configuration、trace、chart result、snapshot等のstate/mutationを、hooksまたはWorkbench controller相当の単位へ分離する。
2. 分離後も既存の状態保持挙動（タブ切替で状態が消えない、preset変更時にsystem・解析結果・条件等がまとめて初期化される、等）を変えないこと。
3. 分離はレイアウト変更の前提整備であり、本作業単体で画面の見た目・操作性を変えないこと（純粋なリファクタリングとして扱う）。

### 2. 左Accordionナビゲーションシェルの導入

1. 現行の中央上部`ContentSwitcher`（System/Preview/Analysis/Compare/Debug）を、左サイドバーの開閉可能なAccordion形式ナビゲーションへ置き換える。
2. 旧`activeTab`のkeyと新しいview keyを一対一でmappingし、**画面遷移の機能自体は変えず、shellだけを移す**（R99 7.3節の推奨方針どおり）。
3. 左ナビゲーションはハンバーガー等の操作で開閉可能にし、collapsed時はicon railとして機能を維持する（R99 3.2節のワイヤーフレーム相当：expanded 280px、collapsed 56px程度を目安とするが、既存デザイントークンとの整合を優先して構わない）。
4. 開閉状態はlocalStorageへ保存し、reload後も維持する。
5. **既定の開閉状態**：1920px幅ではexpandedを既定とする。1440px未満ではcollapsedを既定とする（R99 10節の論点1への回答として、この閾値・既定値を採用する）。
6. Header utility（言語切替、theme切替、API/build info等、R100で低頻度Accordionへ整理済みのもの）は、左ナビゲーション導入後も引き続きアクセス可能な位置に配置する。既存のR100実装（右ペインcontext化）を後退させないこと。
7. 右Contextパネルの表示可否は、1920pxでは常時表示、1366px以下ではdrawer表示（開いたときだけ表示）とする（R99 10節の論点2への回答として、この閾値を採用する）。

### 3. 既存機能・回帰への配慮

1. Preview/Analysis/Compare/Debug/Systemそれぞれの既存機能（Run Preview、Run Charts、Snapshot保存、Validate/Register等）は、shell変更後も同じ操作で同じ結果が得られること。
2. R100で導入したプリセット検索UI、右ペインcontext化、ダーク/ライトモードは、ナビゲーションshell変更後も正しく機能すること（回帰させないこと）。
3. Layout SVG・Chart SVGの寸法・aspect比は、左右パネルの開閉操作によって崩れたり不安定な再配置が起きたりしないこと。

### 4. 回帰テスト整備

1. 既存の`getByRole('tab', { name: ... })`に依存するE2Eを、新しいナビゲーション構造に応じたセレクタへ更新する。可能な限り`#layout-svg`、chart系`data-testid`、field/surface input ID等の既存の安定したセレクタは維持する。
2. 左右パネルの開閉操作でLayout/Chartの寸法が安定していることを確認するE2Eを追加する。
3. 1920px・1440px・1366px付近でのナビゲーション既定表示状態（expanded/collapsed、右context表示/drawer）を固定するE2Eを追加する。
4. ナビゲーション開閉状態がreload後も保持されることを確認するE2Eを追加する。
5. R100で追加したscroll実測・preset検索・theme切替のE2Eが、shell変更後も引き続きグリーンであることを確認する。

## 完了条件

- 左Accordionナビゲーションが導入され、既存の5画面（System/Preview/Analysis/Compare/Debug）へ機能的に同じ内容でアクセスできることが確認されている。
- 開閉可能で、開閉状態がlocalStorageで永続化されることが実測で示されている。
- 1920px幅でexpanded、1440px未満でcollapsedが既定になっていることがE2Eで固定されている。
- 右Contextパネルの表示条件（1920pxで常時、1366px以下でdrawer）がE2Eで固定されている。
- R100で実装したプリセット検索・右ペインcontext化・ダーク/ライトモードが回帰していないことを確認している。
- 状態管理の分離により、`App.tsx`の行数・関数数がどの程度整理されたかを報告する（数値で示す）。
- 既存の数値結果・request payload・snapshot内容・i18n識別子に影響がないことを確認している。
- `npm run ci`が全てグリーンである。
- 完了報告前にプロセスを再起動し、`build_info.git_commit`がHEADと一致することを断定形で記載する（未来形で締めない）。
- **完了報告の実装根拠には、コミットメッセージだけでなく実際のコミットハッシュ値を必ず併記する。**

## 注意

- 本タスクはR99提案のPhase 2（Navigation shell）のみを対象とする。Surface live split、Analysis chart picker、Snapshot自動遷移の廃止はPhase 3以降で別途発注する。範囲を超えて先取り実装しないこと。
- 状態分離とナビゲーションshell変更を同時に行うと問題切り分けが難しくなるため、作業1（状態分離）を先に完了・確認してから作業2（shell導入）へ進むことを推奨する（1タスクずつの完了報告は必須としないが、コミットは分離しておくこと）。
- R54/R99で繰り返し指摘された教訓（「見た目が変わった」ことと「レイアウト構造・状態管理が壊れていない」ことは別問題）を踏まえ、目視の印象ではなくDOM実測・既存テストのグリーン化で裏付けること。
