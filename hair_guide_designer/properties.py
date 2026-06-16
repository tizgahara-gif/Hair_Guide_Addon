import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty

STRAND_TYPES = (
    ("FRONT", "前髪", "前髪用の毛束"),
    ("SIDE", "側頭部", "側頭部用の毛束"),
    ("BACK", "後頭部", "後頭部用の毛束"),
    ("NAPE", "襟足", "襟足用の毛束"),
)

TAPER_PRESETS = (
    ("ANIME", "アニメ標準", "根元を太く、毛先を尖らせる標準的なアニメ髪設定"),
    ("SHARP_ANIME", "鋭いアニメ髪", "中間から毛先へ強く細くなるシャープな設定"),
    ("SOFT", "柔らかめ", "毛先を少し残して柔らかく見せる設定"),
    ("REALISTIC", "自然寄り", "全体を控えめにして自然寄りに見せる設定"),
    ("CUSTOM", "カスタム", "現在の手動設定を使用します"),
)

STRAND_GENERATION_TYPES = (
    ("NORMAL_CURVE", "通常カーブ", "1本の髪束ガイドカーブを生成します"),
    ("BRAID_CURVE", "三つ編みカーブ", "1本の制御カーブと三つ編み表示を生成します"),
    ("TWIST_CURVE", "ツイストカーブ", "1本の制御カーブからドリル状・縦ロール状の表示カーブを生成します"),
)

CURVE_PROFILE_TYPES = (
    ("ROUND", "丸", "CurveのBevel Depthで丸い断面を表示します"),
)

PROPERTY_NAMES = (
    "hair_target_head_object", "hair_guide_scale", "hair_guide_offset",
    "hair_seed", "hair_density", "hair_symmetry_bias",
    "hair_height_variation", "hair_width_variation", "hair_depth_variation",
    "hair_size_variation", "hair_length_variation", "hair_strand_type",
    "hair_curve_length", "hair_curve_bevel_depth", "hair_curve_resolution",
    "hair_curve_root_radius", "hair_curve_tip_radius", "hair_curve_taper_strength",
    "hair_curve_segment_count", "hair_curve_variation_enabled", "hair_curve_variation_seed",
    "hair_curve_variation_randomize_seed_per_generation",
    "hair_curve_root_jitter", "hair_curve_mid_jitter", "hair_curve_tip_jitter",
    "hair_curve_length_variation", "hair_curve_profile_type", "hair_flat_profile_fallback_to_round", "hair_curve_flat_width",
    "hair_curve_flat_thickness", "hair_flat_mesh_width", "hair_flat_mesh_thickness",
    "hair_flat_mesh_samples", "hair_flat_mesh_ring_segments", "hair_flat_mesh_solidify_thickness",
    "hair_flat_mesh_add_subdivision", "hair_warning_count", "hair_root_cluster_threshold",
    "hair_batch_curve_length", "hair_batch_curve_bevel_depth", "hair_batch_curve_resolution",
    "hair_follow_keep_tip_offset", "hair_follow_update_selected_only",
    "hair_mirror_axis", "hair_mirror_overwrite_existing", "hair_mirror_copy_custom_properties",
    "hair_use_shared_taper", "hair_taper_preset", "hair_taper_root_radius",
    "hair_taper_mid_radius", "hair_taper_tip_radius", "hair_taper_bevel_depth",
    "hair_taper_resolution", "hair_auto_apply_taper_to_new_curves",
    "hair_strand_generation_type", "hair_braid_segments", "hair_braid_radius",
    "hair_braid_width", "hair_braid_taper", "hair_braid_twist",
    "hair_braid_resolution", "hair_braid_bevel_depth", "hair_braid_auto_update",
    "hair_twist_segments", "hair_twist_radius", "hair_twist_turns",
    "hair_twist_phase", "hair_twist_bevel_depth", "hair_twist_resolution",
    "hair_twist_taper_strength",
    "hair_show_braid_settings", "hair_show_twist_settings", "hair_show_advanced_curve_settings",
    "hair_show_guides_in_front", "hair_show_inline_help",
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
    scene.hair_show_guides_in_front = BoolProperty(
        name="最前面表示中",
        default=True,
        description="生成したガイド、領域線、配置点、警告、表示用カーブの最前面表示状態です。",
    )
    scene.hair_show_inline_help = BoolProperty(
        name="ヘルプを表示",
        default=True,
        description="サイドパネル内の説明文と補足ヘルプを表示します。",
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
    scene.hair_strand_generation_type = EnumProperty(
        name="生成タイプ",
        items=STRAND_GENERATION_TYPES,
        default="NORMAL_CURVE",
        description="通常カーブまたは三つ編みカーブのどちらを生成するか選択します。",
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
    scene.hair_curve_variation_enabled = BoolProperty(
        name="カーブの個体差を有効化",
        default=True,
        description="生成時にCurveへ小さな位置差と長さ差を加え、完全な重なりを防ぎます。",
    )
    scene.hair_curve_variation_seed = IntProperty(
        name="個体差シード",
        default=1,
        min=0,
        description="Curveの位置ブレと長さブレを再現するための乱数シード。同じ値なら同じ個体差になります。",
    )
    scene.hair_curve_variation_randomize_seed_per_generation = BoolProperty(
        name="生成ごとにシードをランダム化",
        default=False,
        description="有効にすると、カーブ生成ごとに個体差Seedを変え、同じ配置点から生成しても違うブレになります。",
    )
    scene.hair_curve_root_jitter = FloatProperty(
        name="根元の位置ブレ",
        default=0.01,
        min=0.0,
        max=1.0,
        precision=4,
        description="生成時にCurveへ小さな位置差と長さ差を加え、完全な重なりを防ぎます。根元付近の位置ブレ量です。",
    )
    scene.hair_curve_mid_jitter = FloatProperty(
        name="中間の位置ブレ",
        default=0.035,
        min=0.0,
        max=1.0,
        precision=4,
        description="生成時にCurveへ小さな位置差と長さ差を加え、完全な重なりを防ぎます。中間付近の位置ブレ量です。",
    )
    scene.hair_curve_tip_jitter = FloatProperty(
        name="毛先の位置ブレ",
        default=0.06,
        min=0.0,
        max=1.0,
        precision=4,
        description="生成時にCurveへ小さな位置差と長さ差を加え、完全な重なりを防ぎます。毛先付近の位置ブレ量です。",
    )
    scene.hair_curve_length_variation = FloatProperty(
        name="長さのブレ",
        default=0.15,
        min=0.0,
        max=1.0,
        description="生成時にCurveへ小さな位置差と長さ差を加え、完全な重なりを防ぎます。0.15なら約85%〜115%の長さ差です。",
    )
    scene.hair_curve_profile_type = EnumProperty(
        name="断面タイプ",
        items=CURVE_PROFILE_TYPES,
        default="ROUND",
        description="互換用設定です。Curve表示は丸断面のみ使用し、扁平化はメッシュ生成で行います。",
    )
    scene.hair_flat_profile_fallback_to_round = BoolProperty(
        name="扁平断面が不安定な場合は丸断面に戻す",
        default=True,
        description="扁平断面でジオメトリが表示されない環境向けに、丸断面へ自動Fallbackします。",
    )
    scene.hair_curve_flat_width = FloatProperty(
        name="横幅",
        default=0.08,
        min=0.001,
        max=2.0,
        precision=4,
        description="扁平断面Profile Objectの横幅です。",
    )
    scene.hair_curve_flat_thickness = FloatProperty(
        name="厚み",
        default=0.015,
        min=0.001,
        max=2.0,
        precision=4,
        description="扁平断面Profile Objectの厚みです。",
    )
    scene.hair_flat_mesh_width = FloatProperty(
        name="扁平メッシュ幅",
        default=0.08,
        min=0.001,
        max=2.0,
        precision=4,
        description="扁平メッシュ生成時の楕円断面の横幅です。",
    )
    scene.hair_flat_mesh_thickness = FloatProperty(
        name="扁平メッシュ厚み",
        default=0.012,
        min=0.001,
        max=2.0,
        precision=4,
        description="扁平メッシュ生成時の楕円断面の厚みです。",
    )
    scene.hair_flat_mesh_samples = IntProperty(
        name="サンプル数",
        default=24,
        min=2,
        max=512,
        description="扁平メッシュ生成時にCurveを評価サンプリングする点数です。",
    )
    scene.hair_flat_mesh_ring_segments = IntProperty(
        name="断面分割数",
        default=8,
        min=4,
        max=32,
        description="扁平メッシュの楕円断面リング分割数です。",
    )
    scene.hair_flat_mesh_solidify_thickness = FloatProperty(
        name="Solidify厚み",
        default=0.01,
        min=0.0,
        max=1.0,
        precision=4,
        description="生成した扁平メッシュへ追加するSolidify Modifierの厚みです。",
    )
    scene.hair_flat_mesh_add_subdivision = BoolProperty(
        name="Subdivisionを追加",
        default=True,
        description="生成した扁平メッシュへSubdivision Surface Modifierを追加します。",
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

    scene.hair_use_shared_taper = BoolProperty(
        name="共有テーパーを使用",
        default=True,
        description="HairGuideSystem/TaperObjects内の共有テーパーをカーブ毛束へ割り当てます。",
    )
    scene.hair_taper_preset = EnumProperty(
        name="テーパープリセット",
        items=TAPER_PRESETS,
        default="ANIME",
        description="髪束らしい先細り形状を作るためのプリセット。",
    )
    scene.hair_taper_root_radius = FloatProperty(
        name="根元の太さ",
        default=1.0,
        min=0.0,
        max=5.0,
        description="共有テーパーの根元側の太さ。大きいほど根元が太くなります。",
    )
    scene.hair_taper_mid_radius = FloatProperty(
        name="中間の太さ",
        default=0.65,
        min=0.0,
        max=5.0,
        description="共有テーパーの中間部分の太さ。",
    )
    scene.hair_taper_tip_radius = FloatProperty(
        name="毛先の太さ",
        default=0.0,
        min=0.0,
        max=5.0,
        description="共有テーパーの毛先側の太さ。0にすると先端が尖ります。",
    )
    scene.hair_taper_bevel_depth = FloatProperty(
        name="全体の太さ",
        default=0.035,
        min=0.0,
        precision=4,
        description="カーブに適用するCurve Bevel Depth。髪束全体の太さです。",
    )
    scene.hair_taper_resolution = IntProperty(
        name="解像度",
        default=3,
        min=1,
        max=64,
        description="共有テーパーと適用先カーブの滑らかさ。",
    )
    scene.hair_auto_apply_taper_to_new_curves = BoolProperty(
        name="新規カーブへ自動適用",
        default=True,
        description="新しく生成するカーブ毛束へ共有テーパーを自動で適用します。",
    )

    scene.hair_show_braid_settings = BoolProperty(
        name="三つ編み設定を表示",
        default=False,
        description="三つ編みの詳細パラメータを表示します。",
    )
    scene.hair_show_twist_settings = BoolProperty(
        name="ツイスト設定を表示",
        default=False,
        description="ツイストの詳細パラメータを表示します。",
    )
    scene.hair_show_advanced_curve_settings = BoolProperty(
        name="詳細/互換設定を表示",
        default=False,
        description="将来互換用のカーブ詳細パラメータを表示します。",
    )

    scene.hair_braid_segments = IntProperty(
        name="編み目数",
        default=8,
        min=2,
        max=64,
        description="三つ編み表示の交差ユニット数。1つが1回の編み目です。",
    )
    scene.hair_braid_radius = FloatProperty(
        name="交差の奥行き",
        default=0.04,
        min=0.001,
        max=2.0,
        description="中央交差時の前後方向のふくらみ。大きいほど房の上下差が強く見えます。",
    )
    scene.hair_braid_width = FloatProperty(
        name="横幅",
        default=0.12,
        min=0.001,
        max=5.0,
        description="三つ編み全体の横幅。大きいほど左右の房が広がります。",
    )
    scene.hair_braid_taper = FloatProperty(
        name="毛先細り",
        default=0.45,
        min=0.0,
        max=1.0,
        description="毛先へ向かう三つ編みの細り具合。高いほど毛先が細くなります。",
    )
    scene.hair_braid_twist = FloatProperty(
        name="編み込み倍率",
        default=1.0,
        min=0.0,
        max=4.0,
        description="編み目パターンの進み方を調整します。通常は1.0で使用します。",
    )
    scene.hair_braid_resolution = IntProperty(
        name="解像度",
        default=3,
        min=1,
        max=16,
        description="制御カーブをサンプリングするときの滑らかさ。",
    )
    scene.hair_braid_bevel_depth = FloatProperty(
        name="表示太さ",
        default=0.018,
        min=0.0,
        precision=4,
        description="三つ編み表示用カーブの太さ。制御カーブはWire表示で太さを持ちません。",
    )
    scene.hair_braid_auto_update = BoolProperty(
        name="自動更新",
        default=False,
        description="将来拡張用です。現在は更新ボタンで三つ編み表示を再生成してください。",
    )
    scene.hair_twist_segments = IntProperty(
        name="分割数",
        default=32,
        min=4,
        max=256,
        description="ツイスト表示カーブを生成するサンプル分割数。",
    )
    scene.hair_twist_radius = FloatProperty(
        name="巻き半径",
        default=0.08,
        min=0.0,
        max=2.0,
        description="制御カーブの周囲に作るツイストの半径。",
    )
    scene.hair_twist_turns = FloatProperty(
        name="巻き数",
        default=5.0,
        min=0.0,
        max=64.0,
        description="根元から毛先までに何回巻くかを指定します。",
    )
    scene.hair_twist_phase = FloatProperty(
        name="開始角度",
        default=0.0,
        min=-6.28318,
        max=6.28318,
        description="ツイストの開始角度をラジアンで調整します。",
    )
    scene.hair_twist_bevel_depth = FloatProperty(
        name="表示太さ",
        default=0.02,
        min=0.0,
        max=1.0,
        precision=4,
        description="ツイスト表示カーブの太さ。",
    )
    scene.hair_twist_resolution = IntProperty(
        name="解像度",
        default=3,
        min=0,
        max=12,
        description="ツイスト表示カーブの滑らかさ。",
    )
    scene.hair_twist_taper_strength = FloatProperty(
        name="毛先細り",
        default=0.6,
        min=0.0,
        max=1.0,
        description="毛先へ向かって巻き半径を細くする強さ。",
    )


def unregister():
    for name in PROPERTY_NAMES:
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
