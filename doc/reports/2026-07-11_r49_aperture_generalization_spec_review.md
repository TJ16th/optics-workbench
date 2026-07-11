# R49 絞り定義一般化の仕様検討 完了報告

## 結論

現行仕様は、局所的な外径制限と専用annulus面による内径遮蔽を扱える。一方、実体を持つ後続面が前段光束へ作る遮蔽、configuration別の可変径、矩形・実用polygon輪郭は未対応または予約段階である。

## A: 固定的な遮蔽

### ②-a 実体を持つ後続面による遮蔽

現状は未対応。面の`semi_diameter_mm`はその面自身で外径超過を遮光するだけで、M2の径を前段位置へ投影して中央遮蔽として扱わない。実現には非局所制約のモデル化に加え、ray aiming、pupil sampling、paraxial pupil、実光線traceを同じ遮蔽定義へ接続する必要がある。

変更規模は大。単純なデータ項目追加ではなく、コンパイル済み遮蔽モデルとaiming/sampling契約の設計変更になる。

### ②-b 実体を持たない機械的な固定遮蔽

エンジンは`mechanical_aperture` + `shape: annulus`を受理し、各面のaperture判定でinner未満・outer超過を遮光できる。R47によりSystemタブのinner/outer表示・編集もannulus kind共通で利用可能になった。

ただしLayout Viewのannulus専用表示は現時点で`aperture_stop`を対象としており、mechanical annulusの表示・仕様上の併用規則は未整備である。変更規模は小〜中で、エンジン基盤の新設よりUI・validation・横断テストの整備が中心となる。

## B: フォーカス・ズーム連動の副絞り

groupsは連続面範囲を持ち、`group_positions`はX/Y/Z shiftを持つため、mechanical apertureを群に含めた位置移動は現行構造で表現可能である。一方、configurationごとの`semi_diameter_mm`、`inner_semi_diameter_mm`、`outer_semi_diameter_mm` overrideは存在しない。`iris_radius_mm`は主`aperture_stop`専用であり、固定副絞り一般には使えない。

変更規模は中。位置移動は既存機構の仕様化・テスト追加で済むが、可変径はモデル、configuration解決、validation、cache hash、trace、UIを横断する追加が必要になる。

## 軸③: 開口輪郭

`Aperture.shape`は`polygon`を型として予約しているが、頂点・辺数・回転等の実用データを持たず、rectangleは列挙されていない。本タスクでは規模見積もりや実装を行わず、rectangleとpolygonを別Issueとして登録した。

## R47・R48からの反映

- R47でP005のinner `40 mm`、outer `100 mm`が単一annulus面に属し、Systemタブから編集可能になった。
- R48でP005は計算上の基準stopを必要とするため`aperture_stop`を維持した。固定物理絞りとray aiming基準面が同じkindに束縛される点は、②-a/②-bおよびBの設計時に分離を検討する必要がある。
- R48の結論は②-aと②-bの分類を変更しない。むしろ、物理的遮蔽と計算上の主stopを別概念として扱う必要性を補強した。

## Backlog登録

`doc/reports/issues_backlog.md`へ次の5件を追加した。

1. 実体を持つ後続面による内径側の固定遮蔽
2. 実体を持たない固定内径遮蔽のannulus定義とUI
3. mechanical_apertureのフォーカス・ズーム連動可変位置・可変径
4. mechanical_apertureのrectangle形状
5. mechanical_apertureのpolygon・花形輪郭

実際のIssue化には、人間による`Create Issues From Backlog`ワークフローの手動起動が必要である。

## 検証根拠

- 正本参照: `doc/engine_spec.md` 6.4節、9.1節、10章
- 実装参照: `optics_engine/models.py`、`optics_engine/system.py`、`optics_engine/tracing.py`
- R47コミット: `1b6bed7`
- R48コミット: `2093dd8`
- 本報告とbacklog追記: 本報告と同一のR49コミット（`docs: review generalized aperture model (R49)`）

本タスクではエンジン・UI実装および正本仕様の変更は行っていない。
