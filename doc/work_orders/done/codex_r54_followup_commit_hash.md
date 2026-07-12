# R54フォローアップ：完了報告へのコミットハッシュ明記 指示書（Codex向け）

## 背景

`doc/reports/2026-07-12_r54_annulus_marker_cross_section.md`（annulus STOPマーカーの断面表現修正）の内容自体（正円0件・境界縦線4本、inner/outerのpx換算値、凡例アイコン変更、テスト結果）は実測値に基づいており妥当と評価している。

しかし、AGENTS.md「完了主張の根拠明記」節が定める以下の要件を満たしていない箇所が1点ある：

- 「根拠となるコミットハッシュ...を必ず明記すること」
- 「`build_info.git_commit`が報告コミットと一致しているかを確認する」「一致確認の結果（`build_info.git_commit`とHEADの値）を完了報告に含める」

現在の報告書「プロセス整合」節・「テスト」節は、実装コミットのメッセージ文言（`fix(ui): render annulus stop as cross section (R54)`）のみを記載しており、**実際のコミットハッシュ文字列そのもの**を一度も明記していない。「HEADと一致することを確認して完了した」という断定形の記述はあるが、値が示されていないため第三者が検証できない。

これはコード修正ではなく、完了報告の記載不足を補うドキュメント整備タスクである。

## 作業

1. R54の実装変更を含むコミットのハッシュ（短縮形または完全形）を`git log`等で特定する。
2. 現在のプロセスで`GET /v1/meta`を叩き、`build_info.git_commit`の値を取得する。`git rev-parse HEAD`（または短縮形）と一致することを確認する。もし現時点でHEADが当該コミットから進んでいる場合は、その旨と現在のHEADの値も明記する（無理に一致させようとしない）。
3. `doc/reports/2026-07-12_r54_annulus_marker_cross_section.md`の「プロセス整合」節を更新し、以下を明記する：
   - R54実装コミットのハッシュ値
   - 確認時点の`build_info.git_commit`の値
   - 確認時点の`HEAD`（またはその時点のコミット）の値
   - 両者が一致していることの断定的な記述（未来形で締めない）
4. `doc/work_orders/active/codex_r54_annulus_marker_cross_section.md`がまだ`active/`に残っている場合、本追記のコミットと同一コミットで`doc/work_orders/done/`へ移動する（AGENTS.md「Completion Report Move Rule」に従う）。

## スコープ外

- annulusマーカーの描画ロジック自体の再修正は不要（既に妥当と評価済み）。
- 新たなテスト実行は必須ではないが、報告書の記載更新のみでコードに変更がなければ`python -m pytest -q`等の再実行は不要（ドキュメントのみの変更のため、AGENTS.mdの「プロセス再起動」要件はそもそも対象外である点を確認した上で、該当しないことのみ一言触れる）。

## 完了条件

- `doc/reports/2026-07-12_r54_annulus_marker_cross_section.md`に、実装コミットのハッシュ値・確認時点の`build_info.git_commit`値・HEAD値が具体的な文字列として明記されている。
- 一致（または不一致とその理由）が断定形で記載されている。
- `doc/work_orders/active/`と`doc/work_orders/done/`の状態が整合している。

## 注意

これは1タスク=1コミットの軽微な追記作業であり、番号は既存のR54に対するフォローアップとして扱う（新規のR番号は付与しない。台帳側の表記は人間が別途整理する）。
