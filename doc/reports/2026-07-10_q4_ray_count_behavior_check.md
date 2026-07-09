# Ray Count Behavior Check

Date: 2026-07-10

## Scope

`doc/work_orders/done/codex_q4_ray_count_behavior_check.md` に基づき、Workbench UIの「Rays / field」変更が、実際のPreview/Analysis requestで意図しない条件連動を起こしていないか確認した。

## Findings

コード上のrequest生成では、`samples_per_field`、`pupil_distribution`、`ray_aiming.mode`、`fields` は独立して扱われていた。

```text
ray_sampling.samples_per_field = samplesPerField
ray_sampling.pupil_distribution = pupilDistribution
ray_sampling.ray_aiming.mode = aimingMode
fields = analysisFields
```

ただし、従来のDebugタブではraw JSONを読む必要があり、人間が「直近requestで何が変わったか」を即座に確認しづらかった。

## Changes

- Debugタブに `Ray Sampling Request` パネルを追加した。
  - `samples_per_field`
  - `pupil_distribution`
  - `ray_aiming.mode`
  - `fields`
  - `wavelengths_nm`
- P002でRays / fieldだけを変える回帰E2Eを追加した。

## Verification

追加E2E:

- `ray count edits only change samples per field in preview requests`

確認パターン:

| samples_per_field | fields | wavelengths | expected rays |
| ---: | ---: | ---: | ---: |
| 5 | 3 | 3 | 45 |
| 9 | 3 | 3 | 81 |
| 15 | 3 | 3 | 135 |
| 25 | 3 | 3 | 225 |

各パターンで以下を確認した。

- `ray_sampling.samples_per_field` のみ指定値へ変わる。
- `ray_sampling.pupil_distribution = hexapolar` が維持される。
- `ray_sampling.ray_aiming.mode = full` が維持される。
- `fields` のJSON signatureが全パターンで同一。
- Layout Viewの `data-total-rays` が `fields * wavelengths * samples_per_field` と一致。
- Debugタブの `Ray Sampling Request` パネルに最終requestの `25 / hexapolar / full / center, edge-y, edge-z` が表示される。

実行済み:

```text
npm.cmd run ui:build
npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts -g "ray count edits"
```

結果:

- UI build: passed
- Targeted E2E: passed, 1 test

## Conclusion

Rays / field変更による意図しないfields/distribution/aiming連動は確認されなかった。見た目のray pattern変化は、同じfields/wavelengthsに対してpupil sample密度が増えることによる自然な変化と判断する。
