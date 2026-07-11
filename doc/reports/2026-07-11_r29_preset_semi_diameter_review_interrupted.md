# R29 全プリセット有効径見直し 中断報告

## 実施内容

- `doc/work_orders/active/codex_r29_preset_semi_diameter_review.md`を確認した。
- R29の評価条件として、UI既定のfieldと各プリセットの波長samplesを使用した。
  - field: `center`, `edge-y`, `edge-z`
  - ray sampling: `samples_per_field=9`, `pupil_distribution=hexapolar`, `ray_aiming.mode=full`
  - options: `store_path=true`, `profiling=true`, `include_layout_baseline_rays=true`
- `apps/workbench-ui/src/domain/presets.ts`のP001〜P007を読み出し、ローカルAPIの`/v1/systems/register`と`/v1/education/preview`で`metadata.layout_baseline_rays`を集計した。

## 集計できたプリセット

| Preset | Surface | Current `semi_diameter_mm` | Max marginal height mm | Margin |
|---|---:|---:|---:|---:|
| P001 | STOP | 6.25 | 6.250000 | 0.0% |
| P001 | TL1 | 12.5 | 6.250000 | 100.0% |
| P002 | STOP | 8 | 8.000000 | 0.0% |
| P002 | S1 | 15 | 8.480388 | 76.9% |
| P002 | S2 | 15 | 8.673265 | 72.9% |
| P003 | STOP | 10 | 10.000000 | 0.0% |
| P003 | S1 | 14 | 10.418690 | 34.4% |
| P003 | S2 | 14 | 10.520362 | 33.1% |
| P003 | S3 | 14 | 10.713988 | 30.7% |
| P007 | S1 | 18 | 14.479624 | 24.3% |
| P007 | S2 | 17 | 13.748756 | 23.6% |
| P007 | STOP | 13.2 | 13.221977 | -0.2% |

## 中断理由

- P005とP006で、`/v1/education/preview`が`400`を返し、marginal ray高さを取得できなかった。
- 追加切り分けとして、`/v1/education/preview`と`/v1/trace/forward`の両方で、`ray_aiming.mode`を`full` / `paraxial` / `off`に変えて確認したが、すべて以下のエラーになった。

```text
{"severity":"error","code":"optics_value_error","params":{},"message_en":"Out of range float values are not JSON compliant: nan"}
```

- R29の完了条件は「P001〜P007全プリセット」の評価と調整であるため、P005/P006を評価できない状態で値調整へ進むと、仕様と矛盾する可能性がある。
- R31のバッチ実行規約に従い、想定外の不具合発見としてここでバッチを中断した。

## 実行しなかった作業

- `semi_diameter_mm`の値変更。
- 調整前後の近軸量比較。
- 調整後のケラレ確認。

## バックログ

- `doc/reports/issues_backlog.md`に、P005/P006のpreview/traceがNaN JSON serializationで400になる問題を追加した。

## 検証

- 調査のみでコード変更は行っていない。
- テストは未実行。
