# R100：UI/UX見直し Phase 1（プリセット検索化・右ペインcontext化・ダーク/ライトモード基盤） 指示書（Codex向け）

## 背景

R99でUI/UXレイアウト全面見直しの設計提案を受け、人間が内容を確認した。Claude側の独自モックアップとCodex提案は「左サイドバー＋開閉可能なアコーディオンナビゲーション＋右context領域」という基本構成で独立に一致し、この方向（R99提案の案A）を最終形として採用する方針を確認した。ただし全面移行は規模「大」（24〜40人日）のため、R99が提示したPhase 0〜5の段階導入ロードマップのうち、**Phase 1（低リスク改善）から着手する**ことを人間が選択した。

R99の現状分析で判明した主な問題（本タスクの対象）：

1. プリセット選択dropdownは13件全てが横幅を超過し、カテゴリ・属性・検索機能が一切ない（`234×220px`のCarbon `Dropdown`にフラット表示、最長P013で`scrollWidth=442px`）。
2. 右ペインは画面（System/Preview/Analysis/Compare/Debug）に関わらずAPI・言語・validation・export・解析条件・group/aperture/decenter等の設定が常時全表示され、実測で最大約2,387pxの内部スクロール超過が発生している。
3. ダークモードは現状ライト固定（`:root { color-scheme: light; }`）で、`styles.css`に色literalが27種類70箇所、`App.tsx`のチャート系列色が6種類19箇所、`chartTheme.ts`・`exportSvg.ts`にも固定色があり、単純な背景反転ではコントラストが崩れる。

Phase 1では**レイアウト構造（3列構成、上部`ContentSwitcher`によるタブ切替）自体は変更しない**。左Accordionナビゲーション本体・Surface live split・Analysis chart picker等はPhase 2以降のスコープであり、本タスクには含めない。

## 作業

### 1. プリセット選択UIの改善

1. 現行の単一Carbon `Dropdown`を、検索可能なUIへ置き換える（R99 3.5節の推奨に従う：Carbon `ComboBox`ベースの改善で可。`ComposedModal`のような作業を遮る形式は避ける）。
2. 検索対象はID・日英名称・summary・属性とする。
3. プリセットのグルーピングを追加する。カテゴリは`Photographic / Simple & Educational / Telescope & Afocal / Visual / Fixtures`のようなpreset側のmetadataから駆動する方式とし、UIコード側にハードコードした分岐にしない（将来プリセットが増えても仕様書とUIを個別に直す必要がないようにする）。
4. 各項目に`focal/afocal`、EFL、F number、element count、asphere有無、focus group有無等の短い属性を表示する。
5. 選択中の正式名称が省略されず読める表示にする（trigger部は短縮表示＋popover内で折り返し等、可読性が確保できる形式でよい）。
6. keyboardでの検索・上下選択・Enter決定・Esc閉じるに対応する。
7. P005の非表示規約、`?fixture=all-presets`等の既存クエリ挙動は変更しない。

### 2. 右ペインの画面別context化

1. 現行、画面（System/Preview/Analysis/Compare/Debug）に関わらず右ペインへ常時全表示されている設定群を、現在の画面で実際に使う項目だけを表示する形へ絞り込む。
2. API情報・言語切替・build info・validation詳細等の低頻度操作は、折りたたみ領域または専用のutility領域へ移す（R99 3.3節の「Diagnostics」相当の扱いでよいが、独立画面へ完全分離するか折りたたみに留めるかはCodexの実装判断に委ねる。ただし、どちらの場合も既存機能へのアクセス経路が失われないこと）。
3. 目標は、R99実測の右ペインscroll超過（System/Preview/Analysis/Compare/Debug各画面で最大約2,387px）を大幅に削減することである。厳密なゼロは本タスクの必須要件としないが、削減量を実測で報告すること。
4. 既存のfield・wavelength・sampling・runtime configuration等、頻繁に操作する設定の位置・操作性は维持または改善する（後退させない）。

### 3. ダーク/ライトモード基盤の実装

1. R99 5.1節の実装方針に従い、App rootをCarbon `Theme`でラップし、light=`g10`、dark=`g100`とする。
2. Header等へ`System / Light / Dark`を切り替えるUIを追加する。`System`選択時のみOSの`prefers-color-scheme`を監視し、明示選択時はlocalStorageへ保存して次回も維持する。
3. `styles.css`の色literal（27種類70箇所）・`App.tsx`のチャート系列色literal（6種類19箇所）を、R99 5.1節が提案するsemantic token分類（surface/content/structure/semantic/optics）へ置き換える。波長色（F/d/e/C線等）は識別規約であるため、dark時も色相を変えず明度・彩度のみ調整し、dash/marker/legend labelによる識別も維持すること。
4. `chartTheme.ts`をlight/dark両方のpaletteを返せる形へ変更する。
5. `exportSvg.ts`は画面themeと独立させ、SVG export自体は既定でlight（印刷向け）を維持する。dark export提供の要否は本タスクのスコープ外とする（将来課題）。
6. Layout SVG（axis、label、glass fill、air gap、cemented surface、warning/aiming failure表示）、Chart SVG（background、axis、grid、label、legend、marker outline）、Carbon component（Tag、Accordion、Dropdown/ComboBox、NumberInput、CodeSnippet、Notification等）について、light/dark両方でWCAG AA相当のコントラストを確認する。
7. **レイアウト構造自体（3列構成、タブ切替）は変更しない。** 色・コントラストの切替のみが本タスクのスコープである。

### 4. 回帰テスト整備

1. 1920×1080でのDOM scroll実測を固定するE2Eを追加する（R99 2.3節の測定方法を踏襲し、作業2実施後の削減効果を数値で固定する）。
2. プリセット検索・カテゴリ表示・keyboard操作・長い日英/pseudo localeラベルが欠けないことを確認するE2Eを追加する。
3. light/dark切替後にLayout/Chart/Carbon componentのcontrastと系列識別（波長色の見分け）が維持されることを確認するE2Eを追加する。
4. theme選択状態・right pane開閉状態がreload後も保持されることを確認するE2Eを追加する（該当する場合）。
5. 既存の`getByRole('tab', ...)`・preset `combobox/option`セレクタに依存するE2Eが本タスクの変更で壊れる場合、機能E2Eとして書き直す。可能な限り既存の`data-testid`（`#layout-svg`、chart系、field/surface input ID等）は維持する。

## 完了条件

- プリセット選択が検索・カテゴリ・属性表示・keyboard操作に対応し、正式名称が省略されず確認できることがDOM実測で示されている。
- 右ペインの内部scroll超過が、System/Preview/Analysis/Compare/Debug各画面でR99実測値と比較して実際に削減されたことが数値（before/after）で示されている。
- ダーク/ライトモード切替が実際に機能し、Layout・Chart・Carbon componentのコントラストがlight/dark両方でWCAG AA相当を満たすことが確認されている（波長色の識別が失われていないことも含む）。
- レイアウト構造（3列構成、上部タブ）自体は変更されていないことを確認している（Phase 2以降のスコープと切り分ける）。
- 既存の数値結果・request payload・snapshot内容・i18n識別子に影響がないことを確認している。
- `npm run ci`が全てグリーンであり、本タスクで追加した回帰テスト（scroll実測・preset検索・theme切替）も含めてグリーンである。
- 完了報告前にプロセスを再起動し、`build_info.git_commit`がHEADと一致することを断定形で記載する（未来形で締めない）。
- **完了報告の実装根拠には、コミットメッセージだけでなく実際のコミットハッシュ値を必ず併記する。**

## 注意

- 本タスクはR99提案のPhase 1（低リスク改善）のみを対象とする。左Accordionナビゲーション本体、Surface live split、Analysis chart picker、Snapshot自動遷移の廃止等はPhase 2以降で別途発注する。範囲を超えて先取り実装しないこと。
- 「見た目が変わった」ことと「レイアウト構造・状態管理が壊れていない」ことは別問題である。R54/R99が指摘した過去の教訓（描画・見た目だけでなく仕様・データ・状態整合まで確認する）を踏まえ、目視の印象ではなくDOM実測・既存テストのグリーン化で裏付けること。
- プリセットカテゴリはUIコードへのハードコード分岐ではなくpreset側metadataから駆動する設計とし、将来のプリセット追加時にUIコード修正が不要な形にすること。
- 波長色（F/d/e/C線）はdark modeでも色相を変えないこと（識別規約の一貫性維持）。
