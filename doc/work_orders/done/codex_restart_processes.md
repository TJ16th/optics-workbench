# エンジン・UIプロセスの再起動 指示書（Codex向け）

## 背景

人間がブラウザで動作確認する際に接続しているエンジンAPI（想定ポート8000）とUI開発サーバー（想定ポート5173）が、コード修正後も再起動されておらず、古いプロセスのまま動作している疑いがある。実際、`education/preview`のレスポンスに`paths`が含まれておらず、Layout Viewの表示も直っていないことが人間のブラウザ確認で判明した。

## 作業

1. 現在ポート8000・5173（またはREADMEに記載の実際のポート）で待ち受けているプロセスを確認する（Windows環境なので `netstat -ano | findstr :8000` 相当、または `Get-NetTCPConnection -LocalPort 8000` 等で調べる）。
2. 該当プロセスを停止する。
3. 現在のHEAD（最新コミット）のコードで、エンジンAPI・UI開発サーバーを改めて起動する：
   - エンジン：README記載のコマンド（`python -m uvicorn optics_engine.api.main:app --host 127.0.0.1 --port 8000`）
   - UI：README記載のコマンド（`npm run ui:dev`）
   - どちらも人間がブラウザから継続してアクセスできるよう、バックグラウンド/デタッチした状態で起動する。
4. 起動後、`GET /v1/meta`を叩き、`build_info.git_commit`（`codex_verify_fix_and_build_info.md`で実装済みであれば）が現在のHEADと一致することを確認する。未実装であれば、先に`codex_verify_fix_and_build_info.md`のbuild_info部分を完了させてから本タスクを行う。
5. `POST /v1/education/preview`を実際に叩き、レスポンスに`paths`が含まれることをこの再起動後のプロセスに対して確認する。
6. 何ポートで何が起動しているか、起動に使った正確なコマンドを完了報告に明記する（人間がブラウザで再確認する際に参照できるように）。

## 完了条件

- 新しいプロセスが起動しており、`build_info.git_commit`が最新HEADと一致する。
- 再起動後のプロセスに対する`education/preview`呼び出しで`paths`が含まれることが確認されている。
- 人間がブラウザで参照すべきURL（エンジン・UI）が完了報告に明記されている。

## 人間側の作業

このタスク完了報告を受けたら、ブラウザを完全に閉じて開き直すか、ハードリロード（Ctrl+Shift+R）した上で、報告されたURLへ再度アクセスし、Layout Viewと`education/preview`のNetwork タブを再確認する。
