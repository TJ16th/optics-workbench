# /v1/education/preview への paths 欠落修正 指示書（Codex向け）

## 背景

ブラウザのNetwork タブで実際に確認した結果、`POST /v1/education/preview` のレスポンスに `paths` フィールドが含まれていないことが判明した（`status`配列のみで、`paths`キーはレスポンス全文検索でも存在しない）。

先の `codex_ui_ray_path_verification.md` 対応では `POST /v1/trace/forward` のレスポンスに `paths` を追加したが、**`POST /v1/education/preview` は同じ修正が入っていなかった**可能性が高い。Phase 3（P3-2〜P3-5）のスライダー操作はすべてこの `education/preview` エンドポイントを使う設計であり、Layout Viewの光線経路がスライダー操作時に直線のまま（または屈折を反映しない状態）に見えていた直接の原因はこれだと考えられる。

## 作業

1. `optics_engine/api/main.py` 内の `/v1/education/preview` ハンドラを確認し、`/v1/trace/forward` と同様に `paths`（または`store_path=True`相当の経路データ）をレスポンスへ含めているか確認する。含まれていない場合、その理由（意図的な軽量化か、単なる実装漏れか）を報告する。
2. `paths` を含めるよう修正する。ただし `/v1/education/preview` は軽量・高頻度呼び出しを想定したエンドポイントである（Phase 3のドラッグ中は`samples_per_field=5`程度の少数光線）ため、`paths`を含めることでレイテンシに悪影響が出ないか確認する。影響があれば、教育preview用に必要最小限のpath情報（各光線のsurface hit点のみ、余分なメタデータは含めない等）に絞ることを検討し、その設計判断を報告する。
3. UI側（`apps/workbench-ui/src/domain/types.ts`、`App.tsx`）が `education/preview` レスポンスの `paths` も同じロジックで描画に使っているか確認する。`trace/forward`用の型・描画分岐と共通化されているか、別実装になっていて片方だけ直った状態になっていないか確認する。
4. **なぜ今回この欠落が見過ごされたのかを一言で分析する**：`codex_ui_ray_path_verification.md`の完了条件チェック時、`/v1/trace/forward`のみをテスト・確認し、Phase 3で実際に使われる`education/preview`側の動作確認をしていなかったためと考えられる。今後同種の見落としを防ぐため、`AGENTS.md`または該当work orderのテンプレートに「複数エンドポイントが同種のレスポンス項目を持つ場合、修正時は全エンドポイントを横断確認する」旨を一言追記する。
5. 修正後、実際にブラウザ（またはPlaywright E2E）でPhase 3のスライダー操作を行い、Network タブ相当の確認で`education/preview`レスポンスに`paths`が含まれ、Layout Viewが屈折した光線経路を表示することを確認する。P002・P003両方で確認する。

## 完了条件

- `/v1/education/preview`のレスポンスに`paths`が含まれる。
- Phase 3のスライダー操作時、Layout Viewが実際の面交点に基づく折れ線を表示する（目視確認のスクリーンショット、またはE2Eでのpath検証の両方を報告する）。
- レイテンシへの影響有無が報告されている（P3-5のベンチ条件で再計測し、大きな悪化がないか確認する）。
- 「なぜ見過ごされたか」の分析とAGENTS.md等への再発防止の一言追記が完了している。

## この後

これが完了して初めて、Phase 3の「見える光学」の土台（曲率・aperture性能・光線屈折）が実際の操作画面で完結する。この確認が取れてからP3-6（Phase 3受け入れ確認）に進む。
