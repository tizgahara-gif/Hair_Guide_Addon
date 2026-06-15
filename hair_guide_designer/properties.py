import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty

STRAND_TYPES = (
    ("FRONT", "前髪", "前髪用の毛束"),
    ("SIDE", "側頭部", "側頭部用の毛束"),
    ("BACK", "後頭部", "後頭部用の毛束"),
    ("NAPE", "襟足", "襟足用の毛束"),
)

PROPERTY_NAMES = (
    "hair_target_head_object", "hair_guide_scale", "hair_guide_offset",
    "hair_seed", "hair_density", "hair_symmetry_bias",
    "hair_height_variation", "hair_width_variation", "hair_depth_variation",
    "hair_size_variation", "hair_length_variation", "hair_strand_type",
    "hair_curve_length", "hair_curve_bevel_depth", "hair_curve_resolution",
    "hair_curve_root_radius", "hair_curve_tip_radius", "hair_curve_taper_strength",
    "hair_curve_segment_count", "hair_warning_count", "hair_root_cluster_threshold",
    "hair_batch_curve_length", "hair_batch_curve_bevel_depth", "hair_batch_curve_resolution",
    "hair_follow_keep_tip_offset", "hair_follow_update_selected_only",
    "hair_mirror_axis", "hair_mirror_overwrite_existing", "hair_mirror_copy_custom_properties",
)


def register():
    scene = bpy.types.Scene
    scene.hair_target_head_object = PointerProperty(
        name="頭部オブジェクト",
        type=bpy.types.Object,
        description="髪ガイド生成の基準にする頭部メッシュオブジェクト",
    )
    scene.hair_guide_scale = FloatProperty(
        name="ガイド倍率",
        default=1.0,
        min=0.05,
        max=10.0,
        description="頭部バウンディングボックスから生成するガイドラインの倍率",
    )
    scene.hair_guide_offset = FloatProperty(
        name="ガイド距離",
        default=0.04,
        min=-1.0,
        max=1.0,
        description="ガイドラインを頭部から少し離して配置する距離",
    )

    scene.hair_seed = IntProperty(
        name="乱数シード",
        default=7,
        min=0,
        description="乱数シード。同じ値なら同じ配置になります。",
    )
    scene.hair_density = FloatProperty(
        name="密度",
        default=1.0,
        min=0.1,
        max=3.0,
        description="配置点の数や間隔を調整します。",
    )
    scene.hair_symmetry_bias = FloatProperty(
        name="左右対称性",
        default=0.75,
        min=0.0,
        max=1.0,
        description="高いほど左右対称になります。1.0でより対称、0.0でよりランダムです。",
    )

    scene.hair_height_variation = FloatProperty(
        name="高さの揺らぎ",
        default=0.04,
        min=0.0,
        max=1.0,
        description="上下方向のランダム変化。",
    )
    scene.hair_width_variation = FloatProperty(
        name="幅の揺らぎ",
        default=0.035,
        min=0.0,
        max=1.0,
        description="左右方向のランダム変化。",
    )
    scene.hair_depth_variation = FloatProperty(
        name="奥行きの揺らぎ",
        default=0.04,
        min=0.0,
        max=1.0,
        description="前後方向のランダム変化。",
    )
    scene.hair_size_variation = FloatProperty(
        name="サイズの揺らぎ",
        default=0.25,
        min=0.0,
        max=2.0,
        description="配置点の表示サイズと推奨毛束サイズのランダム変化。",
    )
    scene.hair_length_variation = FloatProperty(
        name="長さの揺らぎ",
        default=0.25,
        min=0.0,
        max=2.0,
        description="推奨毛束長さのランダム変化。",
    )

    scene.hair_strand_type = EnumProperty(
        name="毛束タイプ",
        items=STRAND_TYPES,
        default="FRONT",
        description="生成カーブ毛束に保存する分類情報",
    )
    scene.hair_curve_length = FloatProperty(
        name="毛束長さ",
        default=0.55,
        min=0.01,
        max=5.0,
        description="生成するカーブ毛束の基準長さ。",
    )
    scene.hair_curve_bevel_depth = FloatProperty(
        name="太さ",
        default=0.012,
        min=0.0,
        precision=4,
        description="生成するカーブ毛束の表示上の太さ。",
    )
    scene.hair_curve_resolution = IntProperty(
        name="解像度",
        default=12,
        min=1,
        max=64,
        description="カーブの滑らかさ。",
    )
    scene.hair_curve_root_radius = FloatProperty(
        name="根元半径",
        default=0.035,
        min=0.0,
        precision=4,
        description="将来の先細り対応用に保存する根元半径。",
    )
    scene.hair_curve_tip_radius = FloatProperty(
        name="毛先半径",
        default=0.004,
        min=0.0,
        precision=4,
        description="将来の先細り対応用に保存する毛先半径。",
    )
    scene.hair_curve_taper_strength = FloatProperty(
        name="先細り強度",
        default=0.75,
        min=0.0,
        max=1.0,
        description="将来の先細り対応用に保存する先細り強度。",
    )
    scene.hair_curve_segment_count = IntProperty(
        name="制御点数",
        default=3,
        min=2,
        max=12,
        description="カーブ毛束を作成するときに使う制御点数。",
    )

    scene.hair_warning_count = IntProperty(
        name="警告数",
        default=0,
        min=0,
        description="根元集中チェックで見つかった近すぎる配置点ペア数",
    )
    scene.hair_root_cluster_threshold = FloatProperty(
        name="判定距離",
        default=0.08,
        min=0.001,
        max=1.0,
        description="近すぎる配置点を検出する距離しきい値。",
    )

    scene.hair_batch_curve_length = FloatProperty(
        name="長さ倍率",
        default=1.0,
        min=0.01,
        max=5.0,
        description="選択または生成済みカーブ毛束の長さを根元基準で倍率変更します。1.0で現状維持。",
    )
    scene.hair_batch_curve_bevel_depth = FloatProperty(
        name="太さ",
        default=0.02,
        min=0.0,
        precision=4,
        description="生成済みカーブへ一括適用する表示上の太さ。",
    )
    scene.hair_batch_curve_resolution = IntProperty(
        name="解像度",
        default=3,
        min=1,
        max=64,
        description="生成済みカーブへ一括適用する滑らかさ。",
    )

    scene.hair_follow_keep_tip_offset = BoolProperty(
        name="毛先位置を維持",
        default=True,
        description="根元の移動量でカーブ全体を動かし、形と毛先位置を維持します。",
    )
    scene.hair_follow_update_selected_only = BoolProperty(
        name="選択カーブのみ",
        default=True,
        description="全生成カーブではなく、選択中の生成カーブのみ更新します。",
    )

    scene.hair_mirror_axis = EnumProperty(
        name="軸",
        items=(("X", "X", "X軸でミラー"),),
        default="X",
        description="ミラー軸。MVPではX軸のみ対応します。",
    )
    scene.hair_mirror_overwrite_existing = BoolProperty(
        name="既存を上書き",
        default=True,
        description="同名の生成済みミラー先オブジェクトを削除してから作成します。",
    )
    scene.hair_mirror_copy_custom_properties = BoolProperty(
        name="カスタムプロパティをコピー",
        default=True,
        description="ミラー時に元オブジェクトのカスタムプロパティをコピーし、左右情報とミラー情報を更新します。",
    )


def unregister():
    for name in PROPERTY_NAMES:
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
