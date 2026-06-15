# Hair Guide Designer

Hair Guide Designer is a Blender 4.x add-on for Object Mode hair-planning support. It creates non-destructive visual guide lines, placement points, editable curve strands, and root-clustering warnings for anime/VRC-style character hair. It does **not** automatically generate final hair meshes, edit the target head mesh, remove existing modifiers, or delete objects outside `HairGuideSystem`.

- Add-on name: **Hair Guide Designer**
- Internal module: `hair_guide_designer`
- Author: 地図ヶ原
- Target: Blender 4.x, with Blender 4.2 LTS prioritized

## Installation and ZIP packaging

BlenderにインストールするZIPは、`hair_guide_designer` フォルダを直接ZIP化したものを使用してください。GitHubの **Download ZIP** をそのままインストールしないでください。GitHub ZIPは `Hair_Guide_Addon-main/` のようなリポジトリフォルダがZIP直下に入り、BlenderのAdd-on Installで失敗する可能性があります。

Correct install ZIP structure:

```text
hair_guide_designer.zip
└─ hair_guide_designer
   ├─ __init__.py
   ├─ properties.py
   ├─ operators.py
   ├─ ui.py
   └─ utils.py
```

Recommended command from the repository root:

```bash
zip -r hair_guide_designer.zip hair_guide_designer -x '*/__pycache__/*' '*.pyc'
```

Distribution ZIP files are not stored in this repository. Create the installable ZIP only when packaging a release.

配布用ZIPはリポジトリに含めません。リリース時のみ、`hair_guide_designer` フォルダをZIP化してください。

Then in Blender, open **Edit > Preferences > Add-ons > Install...**, select the locally created `hair_guide_designer.zip`, enable **Hair Guide Designer**, and open the 3D Viewport sidebar **Hair Guide** tab.


## Repository Contents / Development Notes

This repository should contain only source files and documentation. Do not commit generated caches, Blender files, media files, archives, or binary assets.

このリポジトリにはソースコードとドキュメントのみを含めます。キャッシュ、Blenderファイル、メディアファイル、圧縮ファイル、バイナリアセットはコミットしないでください。

Codex and other development workflows should follow these rules:

- Do not create or commit binary files.
- Do not create `.blend` files in the repository.
- Do not create image, video, or audio files in the repository.
- Do not create ZIP/archive files in the repository.
- Do not commit `__pycache__`, `.pyc`, or other generated cache files.
- Keep required files limited to Python, Markdown, and text configuration files.
- If temporary verification artifacts are needed, create them outside the repository and do not include them in the final patch.

## UI Help

The add-on includes a **Quick Start** panel and **Help** panel in the Blender sidebar. Follow the panels from top to bottom: **Setup → Guide Lines → Placement Points → Curve Strand → Validation**. The UI also shows current Target Head, Guide, Placement Point, Curve, and Warning counts so you can see what to do next without reading this README.

## Quick Start workflow

1. Select head mesh
2. Set Target Head
3. Create Hair Guides
4. Generate Placement Points
5. Select placement points
6. Create Curve Strands
7. Check Root Clustering

## Sidebar panel layout

The **Hair Guide** tab is organized as:

1. **Hair Guide: Quick Start** — workflow and current status.
2. **Setup** — register the selected head mesh; the mesh is not edited.
3. **Guide Lines** — show, hide, regenerate, or delete visual guide lines.
4. **Regions** — toggle Front, Side, Side_L, Side_R, Back Upper, Back Middle, and Nape references.
5. **Placement Points** — generate seed-based strand root suggestions and adjust variation.
6. **Curve Strand** — create editable Bezier curve strands from selected points.
7. **Curve Batch Adjust** — batch-edit generated curve length scale, bevel depth, and resolution.
8. **Curve Follow** — reconnect generated curve roots to moved placement points.
9. **Side Mirror** — mirror selected Side_L / Side_R placement points and curves across X.
10. **Validation** — check root clustering and explain Warning Count.
11. **Display / Cleanup** — grouped display and delete commands; cleanup affects only HairGuideSystem.
12. **Help** — explains what the add-on does and does not do.

## Generated collection structure

`Regenerate Guide Lines` and related operators create and reuse this structure without duplicating collections:

```text
HairGuideSystem
├─ Guides
├─ Regions
├─ PlacementPoints
├─ Curves
└─ Warnings
```

Only generated objects with `obj.get("hair_guide_type")` inside this collection tree are deleted by delete/clear operators. The target head mesh, existing hair meshes, and existing modifiers are left untouched.

If same-named `Guides / Regions / PlacementPoints / Curves / Warnings` Collections already exist, the add-on reuses them. To avoid collisions, do not rename or repurpose the HairGuideSystem-dedicated collection names.

## Generated guide concepts

The add-on estimates rough areas from the target head object's world-space bounding box. These guides are intended as editable starting points, not anatomical detection:

- Top, hairline, hachi, ear upper/back, occipital, nape, center, and side-boundary guide curves.
- Front region lines for bang start, forehead clearance, three-way split, and flow direction.
- Side region lines for ear-area flow, ear-back transition, and ear volume limits.
- Back upper cap and volume boundary lines.
- Back middle placement variation guides to avoid uniform center-root clumping.
- Nape lower-edge and neck-flow guide lines.

Pressing **Regenerate Guide Lines** again regenerates guide and region lines by first clearing existing generated objects in `HairGuideSystem/Guides` and `HairGuideSystem/Regions`. It does not delete Placement Points, Curves, Warnings, the Target Head, or existing hair meshes.

## Placement points and curve strands

**Generate Placement Points** creates UV sphere markers with reproducible seed-based variation. Default MVP point counts are:

```text
Front: 7
Side_L: 4
Side_R: 4
Back_Upper: 6
Back_Middle: 9
Nape: 5
```

Each placement point stores region, recommended size, recommended direction, recommended length, flow side, and center/outer position metadata. **Create Curve From Selected Points** uses that direction and length to create normal editable Blender Bezier curves in `HairGuideSystem/Curves`; it does not convert them to mesh.

## Curve adjustment, follow, and side mirror

### Curve Batch Adjust

Generated hair curves can be adjusted together. **Length Scale** changes strand length relative to its root: `1.0` keeps the current length, `0.8` shortens by 20%, and `1.2` lengthens by 20%. Batch settings can be applied to selected generated curves or to all generated curves. Bevel Depth and Resolution update both the Blender Curve data and the curve custom properties.

### Curve Follow

If placement points are moved after curve creation, use **Update Curve Roots From Points** to reconnect curve roots to their source points. With **Keep Tip Offset** enabled, the whole curve moves by the root delta and the strand shape is preserved. With it disabled, only the first Bezier point is moved, which may deform the strand.

### Side Mirror

Select `Side_L` placement points or generated curves and run **Mirror Side_L to Side_R**, or select `Side_R` objects and run **Mirror Side_R to Side_L**. The mirrored objects are copied across the X axis. Placement point custom properties are side-flipped, and mirrored curves try to reference the mirrored placement point when the source point was mirrored in the same operation.

Mirror operates on selected Side_L / Side_R objects only in this MVP. It does not generate final hair meshes, does not use Geometry Nodes, and does not perform live mirror synchronization.

## Validation and colors

**Check Root Clustering** compares placement points in the same region. If points are closer than `Root Cluster Threshold`, the add-on colors the involved points red, creates warning markers in `HairGuideSystem/Warnings`, and updates `Warning Count`.

Warning Countは警告対象オブジェクト数ではなく、近すぎる配置点ペアの数です。

警告色や領域色を確認するには、Viewport ShadingのColorをObjectに設定してください。The add-on stores region and warning colors in `obj.color`.

**Clear Warnings** removes warning markers and restores placement point colors.

## Delete and clear behavior

- **Delete Guide Lines** removes generated guide and region line objects only.
- **Clear Placement Points** removes generated placement point objects only.
- **Clear Warnings** removes warning markers and resets warning colors/count.
- **Clear All Generated Objects** removes generated guide, region, placement point, curve, and warning objects inside `HairGuideSystem` only.

These commands never delete the Target Head Object, never delete objects outside `HairGuideSystem`, and never edit existing modifiers.

## MVP limitations

MVPでは以下は未対応です:

- 頭部メッシュ表面への厳密なスナップ
- 前髪クリアランスの自動判定
- 襟足位置チェック
- カーブからメッシュ生成
- 自動・リアルタイム左右ミラー
- プリセット保存

Additional limitations:

- Bounding box estimates are intentionally approximate and should be manually adjusted by the artist.
- Root clustering validation is an MVP heuristic focused on placement points; curve-root validation can be added later.
- No advanced heatmap, exact head-surface distance check, automatic bang clearance, live auto mirror, mesh batch conversion, hair cap generation, presets, multi-character management, mini diagrams, or Geometry Nodes integration is included in this MVP.
- `mesh_strip.py` was removed because strip mesh generation is outside the current MVP scope.

## Verification Checklist

1. Blender 4.2 LTSでAdd-onを有効化できる。
2. MeshをTarget Headに設定できる。
3. Create Hair Guidesを2回押してもガイドが重複増殖しない。
4. Generate Placement Pointsで各領域の配置点が生成される。
5. Seedを変えると配置点の揺らぎが変わる。
6. 同じSeedでは同じ配置点になる。
7. 選択したPlacement PointからCurveが生成される。
8. Check Root Clusteringで近い点が警告される。
9. Clear Warningsで警告色とWarning markerが消える。
10. Delete Guide LinesでGuides / Regionsのみ消える。
11. Clear All Generated ObjectsでHairGuideSystem配下の生成物だけ消える。
12. Target Head Objectは削除されない。

## Quick verification in this repository

In this repository, source parsing can be checked without generating cache files by running a Python AST parse over `hair_guide_designer/*.py`. Distribution ZIP files are intentionally not stored in the repository; create the install ZIP locally only when packaging a release. Full runtime behavior should be verified by installing the locally packaged add-on in Blender 4.2 LTS and exercising the **Hair Guide** tab.
