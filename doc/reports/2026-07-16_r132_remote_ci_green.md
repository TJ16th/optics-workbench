# R132 リモートCI green化 完了報告

## 着手前見積もり

- 見積もり: 20〜35分（実装、ローカル全検証、push、Actions監視）
- 難易度: 中
- 対象: engine CIのNode依存、PIIベースライン、回帰テスト、運用規約、リモートCI確認
- 対象外: 製品コード、既存検出patternの弱体化、force push、履歴書き換え

## 結論

**Done**。R131で失敗したengine・piiジョブを修正し、GitHub Actionsのengine・ui・pii全3ジョブがgreenになった。

- 実装commit: `a6d8749551fec7ad97fcb47090691cbb9651b620`
- Actions run: [29447731288](https://github.com/TJ16th/optics-workbench/actions/runs/29447731288)
- push: 通常push成功（force、rebase、履歴書き換えなし）

## 修正内容

### engine CI

`.github/workflows/ci.yml`のengineジョブへ、uiジョブと同じNode 20の`actions/setup-node@v4`と`npm ci`を追加した。これにより`tests/test_preset_api_smoke.py`が利用する`require('typescript')`をCIでも解決でき、ローカルとCIの検証範囲が一致した。

### PIIベースライン

- `scripts/pii_baseline.json`へR130で人間承認済みの39件だけを登録した。
- 照合キーはpath、検出pattern、行内容のSHA-256、出現数とした。
- 同じファイルへの新規検出、承認行内容の変更、承認数を超える重複は失敗する。
- 承認行が消えた場合もstale baselineとして失敗し、不要な例外を残さない。
- `AGENTS.md`へ、ベースライン追加・更新には人間の明示承認が必要という運用規約を追記した。
- `tests/test_pii_scan.py`へ現行39件、新規検出、重複数超過の回帰テストを追加した。

## 承認済み39件一覧

形式: `path | pattern | line SHA-256`

1. `AGENTS.md` | `codex_runtime_cache` | `6a0f94b0bfd7a15bb2470ec6c2f4fdfbd27870d967248d9b1fba5e7be48783ed`
2. `AGENTS.md` | `workspace_absolute_path` | `a953e938c1925fcd19ff63d617e2b450ac4f9cf9ab8e41d8304acd0d1b82c568`
3. `AGENTS.md` | `workspace_absolute_path` | `bc1468dc047f9416e6d963c8afd4185128a828060f5c42b35681077047f0d0ac`
4. `AGENTS.md` | `workspace_absolute_path` | `bd2531215b1284240598793f31948c37a3fbb7c925dc2fc7179982b861bc865e`
5. `AGENTS.md` | `workspace_absolute_path` | `d4169fd924ed68b9d151548d9459cf2e056c386a5d7ec12fb02334eaae5f8cb8`
6. `AGENTS.md` | `workspace_absolute_path` | `e292c43a476b4380cd85962a8f4ba333cf9d94ce0ab71fba9cb9d50d225dafb1`
7. `doc/reports/2026-07-11_r33_p005_legend_and_ray_display.md` | `workspace_absolute_path` | `401ec926fb374bcd4039c716548cf4857e58cf416b7df86720d8787de6d83db2`
8. `doc/reports/2026-07-11_r33_p005_legend_and_ray_display.md` | `workspace_absolute_path` | `f6ca43abf375750256b02080adaf73050ee0d49ce80c17a6fea533450a2ad6a0`
9. `doc/reports/2026-07-12_r55_cross_workspace_doc_sync.md` | `codex_runtime_cache` | `9729f4cd4d91db397c73609580f0906147e31de2f7c4f7b7f238460f565984e9`
10. `doc/reports/2026-07-12_r55_cross_workspace_doc_sync.md` | `workspace_absolute_path` | `55660f97a1925bc179e41a7e3611ba52d1edc700b4600b21b334750a3d064597`
11. `doc/reports/2026-07-12_r55_cross_workspace_doc_sync.md` | `workspace_absolute_path` | `e146c5dff1b1087e03cbdafd915504f87df2c5423cc01bad04217e5b8d69cacb`
12. `doc/reports/2026-07-12_r55_cross_workspace_doc_sync.md` | `workspace_absolute_path` | `e4761acdf3e1a9fcc7e55314a05be4e54efa085d588fbde52f378b987e4ac593`
13. `doc/reports/2026-07-12_r55_cross_workspace_doc_sync.md` | `workspace_absolute_path` | `fdb398b6481c92d898a14b06df17952d560f55149a5a93f619dbd80822e85ced`
14. `doc/reports/2026-07-12_r56_agents_md_sync.md` | `workspace_absolute_path` | `8e549c908cb7627fe376b73f82631b6f22549eec5c6021a04bf365484f7bd009`
15. `doc/reports/2026-07-12_r56_agents_md_sync.md` | `workspace_absolute_path` | `b384d567b892fc071bd9f005d72bb16f56032b21ae2edbacc64f85b16309d35c`
16. `doc/reports/2026-07-13_r65_followup_ui_spec_hash_mismatch.md` | `workspace_absolute_path` | `40bf6935d11453d66fe871a774623e5d09d23329bef93a1f9ee51c7cd27ae16c`
17. `doc/reports/2026-07-13_r65_spec_doc_sync_and_preset_count_check.md` | `workspace_absolute_path` | `d8bf0c47b6f053701cb64cbda99f017a6d0bd13ea75d0885c8d9468c0d41d7e1`
18. `doc/reports/2026-07-13_r65_spec_doc_sync_and_preset_count_check.md` | `workspace_absolute_path` | `f1b24d1ed93702dedbbbc8cbb4e5462d22d2e74ac1d5df6b030000c3716797e6`
19. `doc/reports/2026-07-15_unmerged_implementation_check.md` | `workspace_absolute_path` | `ef6dba2e69352eff9fef9377176968941e06ae089b297ccc1eea42f2ef5efc53`
20. `doc/work_orders/done/codex_r55_cross_workspace_doc_sync.md` | `workspace_absolute_path` | `0c799da1d14897722262d40d527a0e9fb819b1d8183821cc0998b55c653d9706`
21. `doc/work_orders/done/codex_r55_cross_workspace_doc_sync.md` | `workspace_absolute_path` | `7243955f3b33daf743a35d62663c3a63999cece75b5bc7522e53e4c96b7a8d06`
22. `doc/work_orders/done/codex_r55_cross_workspace_doc_sync.md` | `workspace_absolute_path` | `b5f652274ef3ae75e822a402a28b9f287ee0f605553f358055bf824815eb63fe`
23. `doc/work_orders/done/codex_r56_agents_md_sync.md` | `codex_runtime_cache` | `18464c19eb299f611ee86b9e486d33e02ae25dc14b63c4ae3ba18c9ca2eb3c01`
24. `doc/work_orders/done/codex_r56_agents_md_sync.md` | `workspace_absolute_path` | `8d8b728de941c6d4d0affa05953a27a1e7ade19d9a9976ef0c2e28b946c88f9e`
25. `doc/work_orders/done/codex_r56_agents_md_sync.md` | `workspace_absolute_path` | `f920e6b392959f5eaf57450ce8e9952143aa8935ac3dd28fb733c35f4f2dad18`
26. `doc/work_orders/done/codex_r65_followup_ui_spec_hash_mismatch.md` | `workspace_absolute_path` | `e2784aceff4db7ccf591336affa7bec90ec1fdbc2a533f05d2c3f6e0eb975bec`
27. `doc/work_orders/done/codex_r65_followup_ui_spec_hash_mismatch.md` | `workspace_absolute_path` | `f2e97b1cda0fe06a5164f29f808de5649aed2fcacc02da386411efa11b4bd1e9`
28. `doc/work_orders/done/codex_r65_spec_doc_sync_and_preset_count_check.md` | `workspace_absolute_path` | `08c0b3ba92a6913bbe0f1f3c2f771707c9b91189a7af7b5cfa1c4a4454ccb2cd`
29. `doc/work_orders/done/codex_r65_spec_doc_sync_and_preset_count_check.md` | `workspace_absolute_path` | `2041de2439e356e0a5f8ef7fe85eda4ba0dbd9261afa65e3f3ec746f443987c4`
30. `doc/work_orders/done/codex_r65_spec_doc_sync_and_preset_count_check.md` | `workspace_absolute_path` | `2b20f46833cb64f0b383c7d88f627dc19ee190dc2068b2e6e253c663d67992df`
31. `scripts/sync_cross_workspace_docs.ps1` | `codex_runtime_cache` | `3cf552dedde11167f657d38264c8ff6e2aa27fff9e257c97556496ec3c44b200`
32. `scripts/sync_cross_workspace_docs.ps1` | `workspace_absolute_path` | `170fc725333e07e69dcb6645ae9d3e464b9b26e7ef3cf425a84cbe0eac6b8109`
33. `scripts/sync_cross_workspace_docs.ps1` | `workspace_absolute_path` | `227451b9aa7d7ce3ff7eb2313653a2b4b1fa845c38aca84c4d49065befb6ba99`
34. `scripts/sync_cross_workspace_docs.ps1` | `workspace_absolute_path` | `4f2b5f1ad0f1426f5c79a2c7fa8daea8a91c6bc9935ae002c108856fe0a5ef36`
35. `scripts/sync_cross_workspace_docs.ps1` | `workspace_absolute_path` | `4f37a537686abb7a332a922d191662770b3ebde9b3f860324f171a251acdbf19`
36. `scripts/sync_cross_workspace_docs.ps1` | `workspace_absolute_path` | `65aedc9d40ae2b0f461f55ed730e9394ede647160a783d6b4d943c63cc9e3514`
37. `scripts/sync_cross_workspace_docs.ps1` | `workspace_absolute_path` | `797084a435f6638f614c1d42550e0b6c757481b120caa88d0541f026d12e45ba`
38. `scripts/sync_cross_workspace_docs.ps1` | `workspace_absolute_path` | `ce94c0ee1d5dd800eae488c000d5b89c67d241324d382583dc69006477e0eafa`
39. `scripts/sync_cross_workspace_docs.ps1` | `workspace_absolute_path` | `e82c3d9ae4a1700765b7147bddb56f8dae94c57abceba349f2039257cfa17df6`

## ローカル検証

- `python scripts/pii_scan.py`: `pii:scan ok (39 approved baseline findings)`
- 未登録probe追加時: exit 1、`Unexpected findings: r132_pii_probe.txt:1: workspace_absolute_path`を確認し、probeを削除して再度exit 0を確認した。
- `python -m pytest -q tests/test_pii_scan.py`: `3 passed`
- `python -m pytest -q`: `201 passed, 1 skipped, 1 warning in 24.66s`
- `npm.cmd run ci`: 成功、Playwright `65 passed (1.7m)`
- `npm.cmd run ui:build:pseudo`: 成功

## リモート検証

GitHub Actions run [29447731288](https://github.com/TJ16th/optics-workbench/actions/runs/29447731288):

| job | 結果 | 所要時間 |
|---|---|---:|
| `engine` | success | 1m12s |
| `ui` | success | 2m54s |
| `pii` | success | 4s |

Node.js 20 deprecation annotationは残るが、全ジョブの結論はsuccessである。

## 完了対象範囲

- engineジョブでpreset smokeに必要なNode/TypeScript依存を導入
- R130承認済み39件のみを許可するPIIベースライン
- 未登録・重複超過・stale entryを失敗させる回帰保護
- ベースライン更新の人間承認ルール
- ローカル全検証およびリモート3ジョブgreen確認

製品コードは変更していない。
