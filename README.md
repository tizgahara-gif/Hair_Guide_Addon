# Hair Guide Designer

## 概要

Hair Guide Designer は、Blender 4.x向けの髪制作補助アドオンです。アニメ調・VRC向けキャラクターの髪を作る前段階で、ガイドライン、毛束の根元候補、編集可能なBezierカーブ毛束、先細りカーブ形状、根元集中チェックを使って髪型設計を支援します。

このアドオンは非破壊を前提にしています。頭部メッシュを編集せず、既存モディファイアを削除せず、カーブを自動でメッシュ化しません。生成物は `HairGuideSystem` Collection配下にまとめられます。

- アドオン名: **Hair Guide Designer**
- 内部モジュール名: `hair_guide_designer`
- 作者: 地図ヶ原
- 対象: Blender 4.x（Blender 4.2 LTS優先）

## インストール方法

BlenderにインストールするZIPは、`hair_guide_designer` フォルダを直接ZIP化したものを使用してください。GitHubの **Download ZIP** をそのままインストールしないでください。
配布ZIPは必ずZIP直下に `hair_guide_designer/` が来る構造にしてください。GitHubのソースZIP（リポジトリ名のフォルダが直下に入る形式）はBlenderインストール用ZIPとして扱わないでください。

正しいZIP構造:

```text
hair_guide_designer.zip
└─ hair_guide_designer
   ├─ __init__.py
   ├─ properties.py
   ├─ operators.py
   ├─ ui.py
   └─ utils.py
```

リリース用ZIPを作る場合の例:

```bash
zip -r hair_guide_designer.zip hair_guide_designer -x '*/__pycache__/*' '*.pyc'
```

配布用ZIPはリポジトリに含めません。リリース時のみ、ローカルで `hair_guide_designer` フォルダをZIP化してください。

Blenderでは **Edit > Preferences > Add-ons > Install...** からローカルで作成したZIPを選択し、**Hair Guide Designer** を有効化してください。UIは3D Viewportサイドバーの **ヘアガイド** タブに表示されます。

## リポジトリ内容 / 開発メモ

このリポジトリにはソースコードとドキュメントのみを含めます。キャッシュ、Blenderファイル、メディアファイル、圧縮ファイル、バイナリアセットはコミットしないでください。

開発時の注意:

- バイナリファイルを作成・コミットしない。
- `.blend` ファイルをリポジトリ内に作成しない。
- 画像・動画・音声ファイルを作成しない。
- ZIPなどの圧縮ファイルをリポジトリに含めない。
- `__pycache__`、`.pyc` などの生成キャッシュをコミットしない。
- 必要なファイルはPython、Markdown、テキスト設定に限定する。

## 基本操作

Blender上の **クイック操作** から始め、通常作業はサイドバーのPanelを上から順に進めます。

サイドパネル最上部の **ヘルプを表示** をOFFにすると、説明文を隠してUIを簡潔にできます。
操作に迷った場合はONに戻してください。

1. 頭部登録
2. 基本ガイドを生成
3. 配置点生成
4. カーブ生成で通常Curve/ツイストCurve生成
5. カーブ編集で長さ・太さ・解像度・テーパー・個体差を調整
6. CARD表示でCurve/Solid/CARD切替とCARDプレビュー調整
7. 必要なら出力でCARD Mesh実体化または扁平Mesh出力

長さ・太さ・解像度・テーパー・個体差は **カーブ編集** パネルで管理します。生成後のCurveへ太さやテーパーを反映したい場合も **カーブ編集** パネルの形状適用ボタンを使用してください。

## クイック操作

サイドバー最上部の「クイック操作」から、以下の順で最低限の髪ガイド作成を進められます。

1. 頭部登録
2. 基本ガイド生成
3. 配置点生成
4. カーブ生成

---- 表示モード ----

5. 選択対象へ適用
6. 全Curveへ適用

---- 出力 ----

7. CARD Mesh出力
8. 扁平Mesh出力

詳細な数値調整は、下部の機能別Panelで行います。

## 新UI構成

通常作業は上から順に進めます。低頻度設定は各Panelの **詳細を表示** に格納され、初期状態では折りたたまれます。Panel背景色はBlender標準UIでは自由に変更しにくいため、色分け相当としてPanel見出しのアイコンとbox内ラベル接頭辞を統一しています。生成ObjectのObject Colorは既存の部位別カラーを維持します。

1. **クイック操作**: 簡易状態、作業ロック、頭部登録、基本ガイド生成、配置点生成、カーブ生成、表示モード適用、出力ショートカット。細かい数値設定は置きません。
2. **セットアップ** `[SETUP]` / `TOOL_SETTINGS`: 頭部登録、ガイド倍率、ガイド距離。
3. **ガイド・配置点** `[GUIDE]` / `OUTLINER_OB_CURVE`: ガイド表示、基本ガイド生成、配置点生成/削除、領域表示、前後ガイド左右対称化、側頭部ガイドミラー。
4. **カーブ生成** `[CURVE]` / `CURVE_BEZCURVE`: 生成タイプ、選択配置点からCurve生成、最低限のツイスト設定。ツイスト詳細は **詳細を表示** に格納します。
5. **カーブ編集** `[CURVE]` / `CURVE_BEZCURVE`: 毛束長さ、太さ、解像度、テーパー、個体差、形状適用、選択カーブ設定読み込み、配置点から根元更新、ツイスト更新。
6. **CARD表示** `[CARD]` / `MESH_PLANE`: CARD幅プリセット、Root/Mid/Tip幅、同期幅、CARD Mid位置、CARDプレビュー更新、CARD Control Emptyによる方向制御、編集Curveを開く。表示モードEnumと適用ボタンは **クイック操作** へ集約されています。CARDサンプル数など低頻度設定は **詳細を表示** に格納します。
7. **出力** `[OUTPUT]` / `MESH_DATA`: CARD Mesh実体化、扁平Mesh出力、Subdivision設定、扁平Mesh幅/厚み。サンプル数と断面分割数は **詳細を表示** に格納します。
8. **整理・削除** `[CLEANUP]` / `TRASH`: CARDプレビュー削除、警告削除、配置点削除、ガイド削除、全生成物削除、カーブ整理、部位別カラー反映。保守系操作は **詳細を表示** に格納します。
9. **検証** `[CHECK]` / `ERROR`: 根元密集チェック、警告表示、警告削除。
10. **詳細設定**: 互換Property、低頻度設定、デバッグ/保守用Operatorを格納します。通常UIには表示しません。

## 各パネル説明

### クイック操作

簡易状態と通常作業ショートカットを表示します。基本ガイド数、配置点数、表示カーブ数、CARDプレビュー数、出力メッシュ数を確認できます。

### セットアップ

選択中の頭部メッシュを登録します。既存メッシュは変更されません。

### ガイド・配置点

髪型設計の基準となるガイドラインを生成・表示・削除します。

基本ガイドは意図的に最小限です。初期生成では以下のみ作成します。

```text
HAIR_GUIDE_Hairline
HAIR_GUIDE_SideBoundary_L
HAIR_GUIDE_SideBoundary_R
HAIR_GUIDE_BackVolume
HAIR_GUIDE_Nape
HAIR_GUIDE_Center
```

**基本ガイドを生成** は、上記6本の基本ガイドを作成します。既存の基本ガイドがある場合は、同じ固定名とその `.001` / `.002` などの派生名を先に完全削除してから作り直します。再生成後も `HAIR_GUIDE_SideBoundary_L/R` などを固定名で参照できます。配置点、カーブ、警告、頭部メッシュは削除しません。

基本ガイドの初期位置は頭部Bounding Boxを基準にします。`HAIR_GUIDE_Hairline` は額前面側、`HAIR_GUIDE_BackVolume` と `HAIR_GUIDE_Nape` は後頭部・首側の外側へ余裕を持って生成します。Front/Backガイドは頭部に沿う浅い弧として生成されます。多少の頭部メッシュへの食い込みは許容し、直線よりも髪の流れを把握しやすい形を優先しています。`HAIR_GUIDE_SideBoundary_L/R` はFrontとBackを端から端まで長く横断する線ではなく、Front HairlineとBack Volumeの間をつなぐ短めの補助ガイドとして生成します。

基本ガイド生成後は、Object Modeで各ガイドを髪型に合わせて手動調整してから **配置点を生成/更新** を実行してください。配置点生成は調整後の `HAIR_GUIDE_SideBoundary_L/R` を含む基本ガイド位置を参照します。

基本ガイドCurveは、生成時にObject Originが各ガイドの中央付近に設定されます。Curve制御点はOrigin基準のローカル座標になるため、ガイド単位の移動・回転・スケールを扱いやすくなります。

### 領域表示

髪の領域を表示・非表示します。

領域表示パネルでは、現在の表示状態に応じてボタンがグレーアウトします。表示中の領域では「表示」ボタンが無効化され、非表示中の領域では「非表示」ボタンが無効化されます。一部だけ表示されている場合は両方のボタンを押せます。

- 頭頂部: 前髪・横髪・後ろ髪へ分かれる毛流れの起点
- 前髪: 前髪の開始位置
- 側頭部: 耳周辺から後頭部へ流れる領域
- 後頭部上層: 髪全体のボリューム
- 後頭部中層: 大きな毛束を配置する領域
- 襟足: 首へ向かって落ちる短い毛束領域

### 配置点について

毛束の根元候補を生成します。同じ位置から髪が生えて見える問題を避けるための目安です。

**配置点を生成/更新** は、現在の基本ガイド位置を優先して参照します。ユーザーが `HAIR_GUIDE_Hairline`、`HAIR_GUIDE_SideBoundary_L/R`、`HAIR_GUIDE_BackVolume`、`HAIR_GUIDE_Nape`、`HAIR_GUIDE_Center` をObject Modeで移動・回転・拡縮した場合、そのWorld座標を使って配置点が再生成されます。

再生成時の挙動:

- 既存の配置点は `HairGuideSystem/PlacementPoints` 内だけでなく、別Collectionへ移動済みの `hair_guide_type == "placement_point"` オブジェクトも削除して作り直します。
- 配置点は生成前に同じ固定名とその `.001` / `.002` などの派生名を削除するため、`POINT_Back_Middle_01_L/R` などを固定名で参照できます。
- 既存の警告は `HairGuideSystem/Warnings` 内だけ削除します。
- 既存のカーブ毛束、頭部メッシュは削除しません。
- 基本ガイドがない場合は頭部Bounding Box基準で補完します。
- 同じガイド位置と同じ乱数シードなら同じ配置になります。

主な設定:

- 乱数シード: 同じ値なら同じ配置になります。
- 密度: 配置点の数や間隔を調整します。
- 左右対称性: 高いほど左右対称になります。
- 高さの揺らぎ(cm): 上下方向のランダム変化。初期値は0で左右対称に生成します。
- 幅の揺らぎ(cm): 左右方向のランダム変化。初期値は0で左右対称に生成します。
- 奥行きの揺らぎ(cm): 前後方向のランダム変化。初期値は0で左右対称に生成します。
- サイズの揺らぎ: 配置点表示と推奨サイズの変化。初期値は0です。
- 長さの揺らぎ: 生成Curveの長さブレに使う設定です。初期値は0です。

標準生成数:

```text
Top: 5
Front: 7
Side_L: 4
Side_R: 4
Back_Upper: 6
Back_Middle: 6
Nape: 5
Total: 37
```

Back_Middleは後頭部の大毛束配置ガイドとして、初期生成時に左右ペアを優先します。標準の6点では `POINT_Back_Middle_01_L` / `POINT_Back_Middle_01_R` のように3組の左右ペアを作り、各ペアはhead centerを基準にX座標だけを反転し、Y/Z座標と推奨サイズを共有します。BackVolumeガイドを参照する場合も片側のサンプル位置からX反転で反対側を作るため、Seed Randomizeや配置点の揺らぎを使っても左右ペア関係は維持されます。

配置点数は `Edit > Preferences > Add-ons > Hair Guide Designer` から領域別に変更できます。Topは0〜5、その他の領域は0〜64の範囲で指定できます。0にした領域は配置点を生成しません。

Top / 頭頂部は、髪全体の流れの起点です。前髪・側頭部・後頭部へ毛流れを分けるために使います。Top / 頭頂部の配置点は、頭部最高点より少し上（0.01m）に生成され、頭頂面へ埋まりにくくなっています。

Back_Upper / 後頭部上層の配置点は、頭頂部とBack_Middle / 後頭部中層の間を補間する高さに生成されます。頭頂部に寄りすぎないよう、初期値では中段寄りに配置されます。Back_Middleは後頭部中段の高さを維持し、左右ペアの対称配置を保ったまま後頭部表面より少し外側に生成されます。

## カーブ生成

**カーブ生成** パネルは、選択した配置点から新しいCurveを作るための場所です。

ここでは生成タイプだけを選びます。

- 通常カーブ: 1本の編集可能なBezier髪束ガイドを生成します。
- ツイストカーブ: 1本の制御カーブとドリル状・縦ロール状の表示カーブを生成します。

表示モードの切り替えと適用ボタンは **クイック操作** パネルへ集約されています。CARD表示パネルにはCARD幅、CARD Mid位置、CARD方向制御、CARD Previewを現在設定で更新だけを残しています。太さ・Taper・位置ブレ・長さブレなどの数値は **カーブ編集** に集約されています。

## CARD表示

Curveは削除されず、編集用データとして残ります。表示方式だけを切り替えます。

- カーブ: 制御線のみ表示します。
- ソリッド: Curve Bevel + Taperで立体表示します。
- CARDプレビュー: 元Curve線 + Preview Mesh表示で板ポリ状に確認する制作中表示です。

CARDプレビューはsource curveを表示したまま `HairGuideSystem/CardPreviews` に追従用一時Meshを作る非破壊確認用プレビューです。CARDモードでは元CurveはWIRE表示・太さ0になり、Preview Meshと合わせて確認します。CARDプレビューをON/OFFしても、出力済みの扁平メッシュや実体化済みCARD Meshは変更されません。CARD幅はcm単位で入力し、内部計算ではBlender標準のmへ変換します。

表示モードがCARDで **新規Curveへ現在の表示モードを自動適用** がONの場合、配置点から新規Curveを生成すると同時に `HairGuideSystem/CardPreviews` へCARDプレビューも作成されます。OFFの場合は、生成後に **選択Curveへ表示モード適用** または **全Curveへ表示モード適用** を押してください。

CARD Preview、CARD Mesh、Flat Meshを選択した状態で **選択Curveへ表示モード適用** を押すと、選択中のPreview/Mesh本体ではなく参照元Curveへ表示モードが適用されます。ツイスト制御Curveを選択した場合は、対応する表示用 `twist_strand` へ適用されます。

CARDプレビューは表示用Meshであり、選択はできますが直接編集対象ではありません。CARDプレビューとCARD実体Mesh、扁平メッシュには `hair_source_curve` が保存されているため、形を変える場合は **選択CARDの編集Curveを選択** で編集対象へ選択を移してからCurveを編集してください。通常CARDの場合は元の通常Curveへ、ツイストCARDの場合は表示用 `twist_strand` ではなく `twist_control` へ選択を移します。CARDプレビューはリアルタイム追従しません。制御Curveまたは通常Curveを編集した後、**CARD Previewを現在設定で更新** を押すと現在のCurve形状からPreviewを再生成します。リアルタイム更新は重いため、明示更新方式にしています。CARD実体化したMeshは出力物です。再調整は元Curveまたはツイスト制御Curveで行うことを推奨します。

**CARD Previewを現在設定で更新** は、現在のCARD幅（Root / Mid / Tip / 同期幅）、Mid位置、幅補間、サンプル数を選択Curveへ同期してから既存PreviewのMesh Dataだけを差し替えます。参照EmptyはCurveごとの割当を保持するため、この更新操作ではScene値から無条件に上書きしません。参照Emptyを変更したい場合は、専用の割当・共有・解除ボタンを使ってからPreviewを更新してください。


## CARD Control Empty

CARDの向きは、Curveに割り当てたCARD Control Emptyで手動制御できます。通常は共有Emptyを1つ作成し、複数Curveで同じEmptyを使います。

手順:

1. CARD PreviewまたはCurveを選択
2. CARD表示 > 共有CARD Control Empty作成/割り当て
3. 作成または再利用された共有Emptyを頭部内側など向けたい方向の基準位置へ移動
4. CARD Previewを現在設定で更新

「共有CARD Control Empty作成/割り当て」は、既存共有Empty `HGD_CARD_CTRL_SHARED` や参照Emptyがあれば再利用し、無ければ1つだけ作成して選択Curve群へ同じ `hair_card_control_empty` 名を保存します。Curveごとに個別Emptyが必要な場合のみ、CARD表示の **詳細を表示** から **選択Curveごとに個別Empty作成** を使用してください。

参照Emptyの選択欄には、通常のEmptyは表示されません。Hair Guideが生成したCARD Control Empty、または一度割り当て済みのEmptyだけが候補になります。

CARD Control Emptyが存在する状態でCurveを生成すると、生成Curveには最新のCARD Control Emptyが自動割り当てされます。参照Empty欄にEmptyを指定している場合は、そのEmptyが優先されます。ツイストCurve生成時も `twist_control` と表示用 `twist_strand` に同じ参照Emptyが保存されるため、手動割当前でもCARD Preview / Flat Mesh Previewの方向制御に利用できます。

初期設定では、Emptyの位置をCARD方向ターゲットとして使います。Emptyを頭部内側へ置くと、CARD面が内側を向くように生成されます。回転で制御したい場合は、CARD Control方式を「Empty X軸」に切り替えてください。Empty未設定の場合は、自動フレーム方式（Parallel Transport Frame + CurveごとのRoll値）で生成されます。CARD Preview / CARD Mesh / Flat Meshを選択して作成・割り当てを行った場合も、保存された `hair_source_curve` から参照元Curveを解決し、そのCurveへ `hair_card_control_empty` が保存されます。

複数のCurveで同じCARD Control Emptyを共有できます（標準運用）。共有したいEmpty（または既に参照Emptyを持つCurve / CARD Preview）と対象Curve・CARD Preview・CARD Mesh・Flat Meshを選択し、**参照Emptyを選択Curveへ共有** を押すと、各参照元Curveへ同じ `hair_card_control_empty` 名が保存されます。割当解除は **CARD Control Empty割当解除** を使います。この操作はCurve側の参照情報だけを削除し、Empty自体は削除しません。対象Curveの参照Emptyを探す場合は **参照Emptyを選択** を使ってください。

共有Emptyを移動・回転してもCARDプレビューはリアルタイム更新されません。既存仕様通り、変更を見た目へ反映するには **CARD Previewを現在設定で更新**、**選択対象へ表示モード適用**、または **全Curveへ表示モード適用** を押してください。共有Emptyを削除した場合、Curve側の `hair_card_control_empty` は残ることがありますが、CARD生成時に参照Emptyが見つからなければ自動フレーム方式へフォールバックします。

## CARD幅プリセット

CARDプレビューには4つの幅プリセットがあります。

- 均一カード: 6 / 6 / 6 cm
  仮配置、UV確認、幅一定の板ポリ向け

- 標準テーパー: 8 / 6 / 2 cm
  汎用毛束向け

- シャープ毛先: 7 / 4 / 0.3 cm
  前髪やアニメ調の鋭い毛先向け

- ボリューム毛束: 12 / 10 / 4 cm
  後頭部や大きな毛束向け

プリセットはRoot/Mid/Tip幅だけを変更します。
CARD方向、ロール角、サンプル数、同期設定は変更しません。

CARD幅同期ON中は同期幅が表示に使われます。プリセット値を見た目へ反映したい場合は、CARD幅同期をOFFにしてください。プリセット反映後、既存CARDプレビューの見た目を更新するには **CARD Previewを現在設定で更新**、**選択Curveへ表示モード適用**、または **全Curveへ表示モード適用** を押してください。

## CARD Mid位置

CARD Mid位置は、Root/Mid/Tip幅のうちMid幅をCurve上のどこに置くかを指定します。

- 0.25: Root寄りにMid幅が来る
- 0.50: 中央
- 0.75: Tip寄りにMid幅が来る

Curve自体を編集しても幅補間のMid位置は変わらないため、毛束の膨らみ位置を変えたい場合はCARD Mid位置を調整してください。Mid位置をRoot側へ寄せると根元付近で膨らみや絞りが出ます。Tip側へ寄せると毛先側まで太さを維持できます。

CARD Mid位置やCARD幅補間を変更した後、既存CARDプレビューの見た目は自動更新されません。既存仕様通り、**CARD Previewを現在設定で更新** または **選択対象へ表示モード適用** を押して再生成してください。CARD幅プリセットはRoot/Mid/Tip幅だけを変更し、CARD Mid位置は変更しません。

## 出力

**出力** パネルでは、選択Curveから別Meshを生成します。扁平メッシュ出力とCARDプレビュー実体化をまとめた、VRC向けの最終調整やUV作成に使う出力機能です。

Mesh実体化操作では、実行前に確認ダイアログが表示されます。Preview更新や表示モード切替では確認は表示されません。

対象:

- 通常Curve
- ツイスト表示Curve

対象外:

- ツイスト制御Curve

扁平メッシュ出力では、表示用Curveを評価サンプリングし、楕円断面リングを連続配置した `HGD_FLAT_MESH_元Curve名` Meshを `HairGuideSystem/FlatMeshes` に生成します。扁平メッシュ幅・厚みはcm単位で入力し、内部計算ではmへ変換します。元Curveは削除されず、編集用として残ります。

CARD実体化では、CARDプレビュー未生成の通常Curve/ツイスト表示Curveも対象にし、プレビュー相当ロジックで同じ板ポリ形状を `HGD_CARD_MESH_元Curve名` Meshとして `HairGuideSystem/CardMeshes` に生成します。元CurveとCARDプレビューは削除されません。既存同名Objectがある場合はBlenderの連番名で新規作成します。

CARD Previewは非破壊表示用です。CARD Previewを選択してTABを押すと、参照元CurveのEdit Modeへ移動します。

CARD Mesh / Flat Meshは出力確定済みMeshです。これらを選択してTABを押した場合、通常通りMesh編集モードへ入ります。元Curveへは自動遷移しません。

扁平メッシュ出力では、Solidify Modifierは自動追加されません。厚み付けが必要な場合は、生成後に手動でSolidifyを追加してください。Subdivision Surfaceは設定に応じて viewport 1 / render 1 で自動追加できます。

Curve表示上の扁平断面Profileと旧Profile Operatorは廃止済みです。扁平化はCARDプレビュー、CARD実体化、または扁平メッシュ出力を使用してください。旧 create_flat_mesh 系Operatorは互換用で、通常操作では「選択Curveを扁平メッシュ出力」を使用します。

## カーブ編集

**カーブ編集** パネルでは、Curve生成/調整に必要な長さ・太さ・解像度・テーパー・個体差をまとめて管理します。操作箇所が分散しないよう、形状適用ボタンと選択カーブ設定の読み込みもこのパネルに集約しています。

ツイスト詳細は **カーブ生成 > 詳細を表示** に格納しています。互換設定は **詳細設定** に格納し、通常UIには表示しません。

### 基本

- 毛束長さ(cm): 新規生成Curveの基準長さです。Curve生成時の長さは常にこの値を使用します。個体差の「長さのブレ率」が0の場合、その長さがそのまま反映されます。
- カーブの太さ(cm): Curve Bevel Depthとして使う太さです。内部ではmに変換します。
- 解像度: Curveの滑らかさです。
- 制御点数: 新規生成時の制御点数です。

### 先細り

- 共有テーパーを使用: 共有Taper Objectをカーブへ割り当てます。
- 新規カーブへ自動適用: 以後生成するカーブ毛束に同じテーパーを自動適用します。
- テーパープリセット: アニメ標準、鋭い、ロング向け、均一、カスタムから選びます。
- プリセットを反映: 選択したプリセット値をRoot/Mid/Tipへ反映します。CUSTOMの場合は現在値を維持します。
- Root / Mid / Tip: 先細り形状を決めます。

プリセットを選び、**プリセットを反映** を押すとRoot/Mid/Tipが更新されます。手動変更時は必要に応じてプリセットをカスタムへ変更してください。共有Taper Objectは `HGD_Default_Taper` として `HairGuideSystem/TaperObjects` に作成されます。

### 個体差

生成したカーブが完全に同じ位置・同じ長さに見える場合、**カーブの個体差** を有効にします。個体差設定は新規Curve生成時にのみ使用されます。既存Curveへ形状適用しても、個体差は再適用されません。

配置点は変更せず、生成されるカーブだけに以下を加えます。

- 根元 / 中間 / 毛先の位置ブレ
- 長さのブレ

根元の位置ブレは小さく、毛先の位置ブレは大きく設定できます。Curve個体差の位置ブレは、cm固定値ではなく毛束長さに対する比率で指定します。短い毛束では小さく、長い毛束では大きくブレるため、髪全体の見た目が揃いやすくなります。たとえば毛束長さ50cm、毛先ブレ率 `0.10` の場合、毛先は最大約5cmブレます。根元制御点は配置点に固定され、根元以外の制御点へ段階的に位置ブレを加えます。

毛束長さ(cm)は新規Curve生成時の基準長さです。個体差の「長さのブレ率」が0の場合、その長さがそのまま反映されます。長さのブレ率が0より大きい場合、生成されたCurveは指定長からランダムに増減します。長さのブレ率 `0.15` は、約85%〜115%の長さ差を意味します。長さのブレは根元を基準に適用されるため、Placement Point自体は動きません。既存Curveへブレを繰り返し加えると形状が累積して崩れるため、形状適用では位置ブレの再ランダム化を行いません。旧仕様の根元/中間/毛先の位置ブレ(cm)設定は互換用に残りますが、新規Curve生成では使用しません。


## cm単位入力

Hair Guide Designerでは、内部計算はBlender標準のm単位で行います。ただしUIでは、毛束長さ・Curve太さ・ツイスト表示太さ・CARD幅・扁平メッシュ幅/厚み・配置点の幅/高さ/奥行き揺らぎをcm単位で入力できます。Curve個体差の根元/中間/毛先の位置ブレは毛束長さに対する比率で指定します。

例:

- 55cm = 0.55m
- 3.5cm = 0.035m

Side_L / Side_R は見た目が重なりやすいため、生成時ブレをやや強めにしています。同じ配置点から複数Curveを生成した場合も、配置点名だけでなくCurve名・領域・種類をSeedに混ぜるため、完全一致しにくくなります。

**生成ごとにシードをランダム化** をONにすると、カーブ生成ごとに内部Seedを変えるため、同じ配置点から生成しても形が一致しにくくなります。OFFの場合は、個体差シードとCurve名をもとに再現性のあるブレになります。ON時の実際のSeedは生成Curveの `hair_curve_variation_runtime_seed` に保存されます。

### 三つ編み機能について

三つ編み機能は品質安定性の問題により削除しました。現在対応するCurve生成タイプは、通常カーブとツイストカーブです。

## ツイストカーブ

ツイストカーブは、1本の制御カーブからドリル状・縦ロール状の表示カーブを生成します。

生成されるもの:

- `HGD_TWIST_CTRL_###`: 形状制御専用
- `HGD_TWIST_STRAND_###`: 髪として見える表示用カーブ

基本手順:

1. 配置点を選択
2. 生成タイプを「ツイストカーブ」にする
3. カーブ毛束を生成
4. `HGD_TWIST_CTRL` を編集
5. 「選択ツイストを更新」を押す

主な設定:

- 分割数: ツイスト表示カーブのサンプル数。
- 巻き半径: 制御カーブの周囲を回る半径。
- 巻き数: 根元から毛先までに何回巻くか。
- 開始角度: 巻き始めの角度。
- ツイスト表示太さ(cm): ツイスト表示カーブの太さ。
- 解像度: 表示カーブの滑らかさ。
- 毛先細り: 毛先へ向かって巻き半径を細くする強さ。

注意:

`HGD_TWIST_CTRL` は制御専用で、太さ・断面・テーパーは付きません。表示用の `HGD_TWIST_STRAND` は更新時に削除・再生成されます。個別編集した `HGD_TWIST_STRAND` は更新時に失われます。

`twist_strand` は制御カーブから再生成されるため、表示用カーブを直接編集しても更新時に失われます。形状調整は `HGD_TWIST_CTRL` を編集してください。

## カーブ更新

**カーブ編集** パネルでは、配置点や制御Curveを編集した後に既存Curveを更新します。形状設定の読み込み、形状適用、根元更新、ツイスト更新を同じPanelに集約しています。

- 配置点から更新: 配置点を移動した後、通常カーブ、ツイスト制御カーブの根元を追従させます。
- 選択ツイストを更新 / 全ツイストを更新: ツイスト制御カーブから表示用Curveを再生成します。
- ツイスト表示Curveを選択不可にする: 表示専用のツイスト表示Curveをロックし、制御Curveだけを編集しやすくします。

形状適用の対象は通常カーブ、ツイスト表示カーブです。ツイスト制御カーブは形状制御専用のため、断面・Taper・太さ適用の対象外です。ツイスト表示Curveは表示専用で、編集するのは制御Curveだけです。

### ミラー

ガイド・配置点Panelと整理・削除Panelのミラー項目では以下を扱います。

- 側頭部ガイドの左右ミラー
- Front/Back/Napeガイドの左右対称化
- Side_L / Side_R 配置点・Curve・ツイスト制御Curveの左右ミラー
- flow_side L/R を持つ配置点の左右ミラー

側頭部のガイドCurve、配置点、生成Curveを反対側へミラーできます。

側頭部ガイドCurveのミラーは、編集済みの `HAIR_GUIDE_SideBoundary_L` / `HAIR_GUIDE_SideBoundary_R` を既存の反対側ガイドへ反映します。コピー先Object名は維持し、Bezier制御点と左右ハンドルをWorld X=0基準で反転します。生成済みの配置点やCurveは削除しません。

- 左側頭ガイド → 右へミラー (`hgd.mirror_side_guide_l_to_r`)
- 右側頭ガイド → 左へミラー (`hgd.mirror_side_guide_r_to_l`)
- 前後ガイドを左右対称化 (`hgd.symmetrize_front_back_guides`): `HAIR_GUIDE_Hairline`、`HAIR_GUIDE_BackVolume`、`HAIR_GUIDE_Nape` の1本のガイド内の左右差を整えます。手動調整後に使ってください。
- 左側→右側へミラー
- 右側→左側へミラー

ガイドミラー後に **配置点を生成/更新** を実行すると、新しい側頭部ガイド位置を参照して側頭部の配置点が再生成されます。将来的には頭部中心X基準への拡張を想定しています。

MVPではX軸固定です。配置点はObject位置を反転し、カーブはObject transformを反転せず、Bezierのローカル座標のみ反転します。

Side Mirrorは通常生成Curve向けの簡易機能です。Curve Object自体をObject Modeで移動・回転・拡縮した後にミラーすると、期待とずれる場合があります。形状調整はできるだけEdit Modeで制御点を編集してください。

### 整理・削除

生成したカーブは部位別Collectionへ整理できます。

Top / Front / Side_L / Side_R / Back_Upper / Back_Middle / Nape / Twist に分かれるため、Outliner上で管理しやすくなります。

**カーブを部位別に整理** を押すと、既存の生成カーブも現在の `hair_region` と `hair_guide_type` に応じた部位別Collectionへ移動できます。

**部位別カラーを反映** を押すと、領域ごとにカーブ色が変わります。色を確認するにはViewport ShadingのColorをObjectにしてください。

### 検証機能について

同じ場所から毛束が生えて見える問題を検出します。

**根元集中チェック** は、同じ領域内で近すぎる配置点ペアを検出します。警告数は警告対象オブジェクト数ではなく、近すぎる配置点ペア数です。

警告色や領域色を確認するには、Viewport ShadingのColorをObjectに設定してください。

### 整理・削除と最前面表示

表示切替と削除をまとめています。削除は `HairGuideSystem` 内の生成物のみ対象です。頭部メッシュは削除されません。

ガイドや配置点、表示用カーブが頭部メッシュに隠れる場合は、**整理・削除** パネルの **詳細を表示** の **最前面表示にする** を押してください。解除したい場合は同じ場所に表示される **最前面表示を解除** を押します。この設定は新規生成されるガイド、領域線、配置点、警告、通常Curve、ツイスト表示Curveにも反映されます。

最前面表示トグルは、ガイド・配置点・警告・通常Curve・ツイスト表示Curveに適用されます。ツイスト制御Curveは編集用のため、常に最前面表示されます。

CARDプレビューは表示用一時Meshです。不要になった場合は **整理・削除 > CARDプレビュー削除** で削除できます。元Curveや出力Meshは削除されません。

### ヘルプ

Blender上だけで、このアドオンでできること・できないこと・推奨手順を確認できます。

## 生成Collection構造

```text
HairGuideSystem
├─ Guides
├─ Regions
├─ PlacementPoints
├─ Curves
│  ├─ Top
│  ├─ Front
│  ├─ Side_L
│  ├─ Side_R
│  ├─ Back_Upper
│  ├─ Back_Middle
│  ├─ Nape
│  └─ Twist
├─ Warnings
├─ TaperObjects
├─ CardPreviews
├─ CardMeshes
└─ FlatMeshes
```

生成物には `hair_guide_type` などのCustom Propertyが付与され、削除や表示切替はこの情報を使って安全に行います。

## 既知の制限

MVPでは以下は未対応です。

- 髪メッシュ自動生成
- カーブからメッシュ生成
- Geometry Nodes連携
- 頭部メッシュ表面への厳密なスナップ
- 前髪クリアランスの自動判定
- 襟足位置チェック
- Unity設定
- PhysBone設定
- 自動リギング
- プリセット保存
- 自動・リアルタイム左右ミラー同期
- 板ポリ髪生成 / 高度な断面形状制御

## 動作確認チェックリスト

1. Blender 4.2 LTSでAdd-onを有効化できる。
2. Meshを頭部として登録できる。
3. **基本ガイドを生成** で6本の最小ガイドだけが生成される。
4. 配置点を生成/更新できる。
5. Top / 頭頂部の配置点が5個生成される。
6. 基本ガイドを移動後、配置点再生成にその位置が反映される。
7. 配置点再生成時に既存配置点と警告が重複せず上書きされる。
8. 配置点の揺らぎは初期値0のため左右対称。揺らぎ値やSeedを変えるとランダム変化が加わる。
9. 同じSeedと同じガイド位置では同じ配置点になる。
10. 選択した配置点から通常カーブ毛束が生成される。
11. Top配置点から `HAIR_TOP_###` カーブが生成される。
12. 生成タイプをツイストカーブにして、制御カーブ1本と表示用Curveが生成される。
13. 制御カーブ編集後に選択ツイスト/全ツイストを更新できる。
14. カーブ編集で長さ、太さ、解像度、Taper、個体差をまとめて設定できる。
15. 選択カーブまたは全カーブへ形状をまとめて適用できる。
16. 新規カーブ生成時に設定したTaperが自動適用される。
17. カーブ編集で既存Curveの形状反映、根元追従、ツイスト更新ができる。
18. 配置点移動後に通常カーブとツイスト制御カーブが追従できる。
19. ガイド・配置点/整理・削除でSide_L / Side_Rの配置点、カーブ、ツイストを複製できる。
20. 根元集中チェックで近い点が警告される。
21. 警告削除で警告色とWarning markerが消える。
22. 生成物をすべて削除しても頭部メッシュは削除されない。

## リポジトリ内での簡易確認

`__pycache__` を生成しないよう、Python AST parseで `hair_guide_designer/*.py` を確認できます。配布ZIPはリポジトリに保存しません。リリース時のみローカルで作成してください。Blender上の実動作は、Blender 4.2 LTSへインストールして確認してください。

### ツイストCurveの編集ルール

ツイストCurveは、ユーザーが編集する `twist_control` と、髪として見える表示専用の `twist_strand` に分かれます。
形状調整は制御Curveだけを編集してください。表示用ツイストCurveは選択不可で、ツイスト更新時に制御Curveから再生成されるため、直接編集する前提ではありません。
既存データの表示用ツイストCurveを選択不可にしたい場合は、カーブ更新パネルの **ツイスト表示Curveを選択不可にする** を実行してください。

### CARD幅同期

CARDプレビューでは **CARD幅を同期** をONにすると、Root/Mid/Tipが同じ **CARD同期幅(cm)** で表示・実体化されます。
OFFの場合は従来通り、Root幅(cm)、Mid幅(cm)、Tip幅(cm)を補間して根元から毛先へ幅変化します。
同期ONは表示計算に同期幅を使うだけで、Root/Mid/Tipの入力値は上書きしません。

## 作業ロック

作業ロックをONにすると、Hair Guide編集対象以外のオブジェクトを一時的に選択不可にします。

選択可能:
- ガイド
- 領域線
- 配置点
- 警告
- 通常Curve
- ツイスト制御Curve
- CARDプレビュー

選択不可:
- 頭部メッシュ
- 背景
- ツイスト表示Curve
- CARD Mesh
- 扁平Mesh
- その他一般オブジェクト

解除すると、ON前の選択可否へ戻ります。

## 配置点基準のCurve Origin

配置点から生成される通常Curveとツイスト制御Curveは、Object Originが元配置点の位置になります。
Curve内部の制御点は配置点を基準としたローカル座標で保持されます。
これにより、根元基準の移動・回転・スケールがしやすくなります。

Curve生成時の長さは、常に **カーブ編集 > 毛先長さ(cm)（新規生成時のみ）** を使用します。毛先長さは新規Curve生成時の初期値です。生成済みCurveへ再適用しても変更されません。生成後の長さ調整は通常のCurve編集で行ってください。配置点は位置と方向の目安であり、長さは保持しません。

この仕様は新規生成Curveから適用されます。旧バージョンで生成したCurveは必要に応じて再生成してください。

### 扁平メッシュ表示モードとPreview

表示モードに「扁平メッシュ」を追加しました。このモードは確定出力Meshを作らず、元Curveから再生成される非破壊の `flat_mesh_preview` を表示します。CARD Previewと扁平メッシュPreviewは表示モード切替時に `hide_viewport` で切り替わり、出力済みの `flat_mesh` は勝手に削除されません。

扁平メッシュの確定出力は「出力」Panelの扁平メッシュ設定から行います。Preview (`flat_mesh_preview`) と確定Mesh (`flat_mesh`) は同じ生成ロジックを使うため、幅・厚み・サンプル数・断面分割数・Subdivision設定を共有し、見た目が一致します。断面分割数は4〜32で、各Curveサンプルごとに楕円リング断面を作成し、4では四角断面に近く、8/16/32ではより滑らかな扁平断面になります。

CurveにCARD Control Emptyが割り当てられている場合、扁平メッシュPreviewと扁平メッシュ確定出力もCARDと同じEmptyを参照して面方向を揃えます。Control方式がEmpty位置ターゲットの場合はEmpty位置、Empty X軸の場合はEmptyローカルX軸を使います。

「側面エッジをSharpにする」をONにすると、扁平メッシュの楕円断面における左右端・上下端に相当する縦方向Edgeへ自動でSharpを設定し、Subdivision時も断面の境界感を保ちやすくなります。整理・削除Panelからは「扁平メッシュPreview削除」で `flat_mesh_preview` だけを削除できます。

CARD Preview / 扁平メッシュPreviewの表示更新では、既存Preview Objectを削除せず、Objectを再利用してMesh Dataだけを差し替えます。そのため、ユーザーがPreview Objectへ追加したObject Modifier、Transform、Collection所属、Object Custom Propertyは更新後も保持されます。

PreviewはCurveや設定から再生成される表示用Mesh Dataのため、Mesh Data内の手編集頂点、Shape Key、手編集UV、Vertex Groupは更新時に保持されません。これらのMesh Data編集が必要な場合は、CARD Mesh / 扁平メッシュの確定出力後に編集してください。整理・削除PanelのCARD Preview削除 / 扁平メッシュPreview削除を実行した場合はPreview Object自体を削除するため、追加Modifierも削除されます。


### ツイストCurveの表示モードと扁平メッシュ

ツイストCurveでは、制御用の `twist_control` 自体にはCARD Preview / Flat Mesh Previewを作成しません。表示モードを適用すると、選択中の `twist_control` や既存Preview/出力メッシュから対応する表示用 `twist_strand` を自動的に解決し、その `twist_strand` へPreviewを生成・更新します。

扁平メッシュ生成では、通常Curveは従来通りCARD Control EmptyなどのCARD方向設定を使用します。ツイストCurveのみ、「ツイスト扁平面を内側へ向ける」設定により、頭部中心または参照Empty方向を基準に面を内側へ揃えた扁平メッシュを生成できます。Previewと確定出力は同じ向き計算を使用します。

## 最終編集モード

CARD MeshまたはFlat Meshを出力した後、「最終編集モード」を押すと出力Meshだけが表示されます。

非表示になるもの:
- ガイド
- 配置点
- Curve
- Preview
- CARD Control Empty
- Warning

削除はされません。
解除すると、ON前の表示/選択状態へ戻ります。

## Hair Guide Designer: 新UI制作フロー

サイドバーは制作フロー順に再構成されています。通常作業は **HGD Quick Flow** だけで完結し、細かい数値設定は機能別Panelに分離されています。

1. **HGD Quick Flow** で頭部を登録
2. **基本ガイド生成**
3. **配置点生成**
4. **Curve生成**
5. 表示モードを **Curve / Solid / CARD / Flat Mesh Preview** から選択
6. **CARD / Flat Preview更新**
7. **CARD Mesh / Flat Mesh出力**
8. **Final Edit Mode** で出力Meshだけを表示して最終編集

### Panel構成

1. HGD Quick Flow
2. `[SETUP] Setup`
3. `[GUIDE] Guide / Points`
4. `[CURVE] Curve Shape`
5. `[DISPLAY] Display Mode`
6. `[CARD] CARD / Flat Preview`
7. `[OUTPUT] Output Mesh`
8. `[FINAL] Final Edit`
9. `[CLEANUP] Cleanup / Utility`
10. Advanced

CARD幅や方向制御は `CARD / Flat Preview`、Flat Meshの幅・厚み・サンプル数・断面分割などの出力設定は `Output Mesh` に集約されています。削除系操作は `Cleanup / Utility`、低頻度のDebug/互換項目は `Advanced` にまとめています。

### 左ツールバー

3D View左ツールバーに **Hair Guide** ツールを追加しました。数値設定は置かず、次の実行操作だけを配置しています。

- Select / Edit Curve
- Create Curve
- Update CARD Preview with Current Settings
- Output Mesh
- Final Edit Mode

### Pie Menu

**Hair Guide Pie** のデフォルトショートカットは **Alt + J** です。

Pie Menuには表示モード適用、CARD Previewを現在設定で更新、Flat Mesh Preview更新、Mesh出力、最終編集モード、参照Empty作成/共有、編集Curveを開く、Cleanup / Preview削除を配置しています。

ショートカットは **Addon Preferences** から変更できます。

- Pie Menu Key
- Ctrl
- Shift
- Alt
- Keymap再登録ボタン

### Collection整理

生成物は `hair_guide` Collection配下に整理されます。

- `00_Guides`
- `01_PlacementPoints`
- `02_Curves`
- `03_Previews`
- `04_Outputs`
- `05_Empties`
- `06_Warnings`
- `99_Internal`
