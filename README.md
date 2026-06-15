# Hair Guide Designer

Hair Guide Designer is a Blender 4.x add-on for Object Mode hair-planning support. It creates non-destructive visual guides, placement points, editable curve strands, and root-clustering warnings for anime/VRC-style character hair. It does **not** automatically generate final hair meshes, edit the target head mesh, remove existing modifiers, or delete objects outside `HairGuideSystem`.

- Add-on name: **Hair Guide Designer**
- Internal module: `hair_guide_designer`
- Author: 地図ヶ原
- Target: Blender 4.x, with Blender 4.2 LTS prioritized

## Installation

1. Zip the `hair_guide_designer/` folder so the archive contains `hair_guide_designer/__init__.py` at its root level.
2. In Blender, open **Edit > Preferences > Add-ons > Install...**.
3. Select the zip file and enable **Hair Guide Designer**.
4. Open the 3D Viewport sidebar and use the **Hair Guide** tab.

## Usage workflow

1. 頭部メッシュを選択する。
2. **Set Selected As Target Head**を押す。
3. **Create Hair Guides**を押す。
4. 必要に応じて領域ガイドを表示・非表示する。
5. **Generate Placement Points**を押す。
6. 配置点の位置を必要に応じて手動調整する。
7. 配置点を選択する。
8. **Create Curve From Selected Points**を押す。
9. 生成されたCurveを編集して髪束設計に使う。
10. **Check Root Clustering**で根元集中を確認する。

## Generated collection structure

`Create Hair Guides` and related operators create and reuse this structure without duplicating collections:

```text
HairGuideSystem
├─ Guides
├─ Regions
├─ PlacementPoints
├─ Curves
└─ Warnings
```

Only generated objects inside this collection tree are deleted by delete/clear operators. The target head mesh, existing hair meshes, and existing modifiers are left untouched.

## Generated guide concepts

The add-on estimates rough areas from the target head object's world-space bounding box. These guides are intended as editable starting points, not anatomical detection:

- Top, hairline, hachi, ear upper/back, occipital, nape, center, and side-boundary guide curves.
- Front region lines for bang start, forehead clearance, three-way split, and flow direction.
- Side region lines for ear-area flow, ear-back transition, and ear volume limits.
- Back upper cap and volume boundary lines.
- Back middle placement variation guides to avoid uniform center-root clumping.
- Nape lower-edge and neck-flow guide lines.

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

## Validation

**Check Root Clustering** compares placement points in the same region. If points are closer than `Root Cluster Threshold` and have similar height/size/length, the add-on colors the involved points red, creates warning markers in `HairGuideSystem/Warnings`, and updates `Warning Count`. **Clear Warnings** removes warning markers and restores placement point colors.

## Known limitations

- Bounding box estimates are intentionally approximate and should be manually adjusted by the artist.
- Root clustering validation is an MVP heuristic focused on placement points; curve-root validation can be added later.
- No advanced heatmap, exact head-surface distance check, automatic bang clearance, auto mirror, mesh batch conversion, hair cap generation, presets, multi-character management, mini diagrams, or Geometry Nodes integration is included in this MVP.

## Quick verification

In this repository, Python syntax was checked with `python3 -m py_compile hair_guide_designer/*.py`. Full runtime behavior should be verified by installing the add-on in Blender 4.2 LTS and exercising the **Hair Guide** tab.
