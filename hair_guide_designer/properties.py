import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty

STRAND_TYPES = (
    ("FRONT", "前髪", "前髪用の毛束"),
    ("SIDE", "側頭部", "側頭部用の毛束"),
    ("BACK", "後頭部", "後頭部用の毛束"),
    ("NAPE", "襟足", "襟足用の毛束"),
)

TAPER_PRESETS = (
    ("ANIME", "アニメ標準", "根元を太く、中間を少し細く、毛先を細くする標準設定"),
    ("SHARP", "鋭い", "中間から毛先へ強く細くなるシャープな設定"),
    ("LONG", "ロング向け", "長い毛束で中間の太さを残し、毛先だけ細くする設定"),
    ("STRAIGHT", "均一", "Root/Mid/Tipを同じ太さにする設定"),
    ("CUSTOM", "カスタム", "現在の手動設定を使用します"),
)

CARD_WIDTH_PRESETS = (
    ("UNIFORM", "均一カード", "Root/Mid/Tipを同じ幅にします。仮配置やUV確認向け"),
    ("STANDARD", "標準テーパー", "汎用毛束向けの自然な幅変化"),
    ("SHARP_TIP", "シャープ毛先", "前髪やアニメ調の鋭い毛先向け"),
    ("VOLUME", "ボリューム毛束", "後頭部や大きい束向け"),
    ("CUSTOM", "カスタム", "現在の手動設定を使用します"),
)

STRAND_GENERATION_TYPES = (
    ("NORMAL_CURVE", "通常カーブ", "1本の髪束ガイドカーブを生成します"),
    ("TWIST_CURVE", "ツイストカーブ", "1本の制御カーブからドリル状・縦ロール状の表示カーブを生成します"),
)


def cm_to_m(value):
    return float(value) * 0.01


def m_to_cm(value):
    return float(value) * 100.0


def _get_twist_radius_cm(scene):
    if "_hair_twist_radius_m" in scene:
        return m_to_cm(scene["_hair_twist_radius_m"])
    return m_to_cm(scene.get("hair_twist_radius", 0.08))


def _set_twist_radius_cm(scene, value):
    scene["_hair_twist_radius_m"] = cm_to_m(value)


CURVE_PROFILE_TYPES = (
    ("ROUND", "丸", "CurveのBevel Depthで丸い断面を表示します"),
)

PROPERTY_NAMES = (
    "hair_target_head_object", "hair_selected_card_control_empty", "hair_guide_scale", "hair_guide_offset",
    "hair_seed", "hair_density", "hair_symmetry_bias",
    "hair_height_variation", "hair_width_variation", "hair_depth_variation",
    "hair_height_variation_cm", "hair_width_variation_cm", "hair_depth_variation_cm",
    "hair_size_variation", "hair_length_variation", "hair_strand_type",
    "hair_curve_length", "hair_curve_bevel_depth", "hair_curve_bevel_depth_cm", "hair_curve_resolution",
    "hair_curve_length_cm",
    "hair_curve_root_radius", "hair_curve_tip_radius", "hair_curve_taper_strength",
    "hair_curve_segment_count", "hair_curve_variation_enabled", "hair_curve_variation_seed",
    "hair_curve_variation_randomize_seed_per_generation",
    "hair_curve_root_jitter", "hair_curve_mid_jitter", "hair_curve_tip_jitter",
    "hair_curve_root_jitter_cm", "hair_curve_mid_jitter_cm", "hair_curve_tip_jitter_cm",
    "hair_curve_root_jitter_ratio", "hair_curve_mid_jitter_ratio", "hair_curve_tip_jitter_ratio",
    "hair_curve_length_variation", "hair_curve_display_mode", "hair_curve_origin_to_reference_empty",
    "hair_card_width_preset",
    "hair_card_width_root", "hair_card_width_root_cm", "hair_card_width_mid", "hair_card_width_mid_cm",
    "hair_card_width_tip", "hair_card_width_tip_cm", "hair_card_mid_position", "hair_card_width_interpolation", "hair_card_sync_widths", "hair_card_synced_width_cm", "hair_card_samples",
    "hair_card_use_parallel_transport", "hair_card_default_roll_angle",
    "hair_card_control_empty_mode", "hair_card_flip_side", "hair_auto_assign_latest_card_control_empty",
    "hair_card_auto_apply_to_new_curves", "hair_card_auto_update_preview", "hair_card_auto_select_edit_curve", "hair_show_display_mode_settings",
    "hair_curve_profile_type", "hair_flat_profile_fallback_to_round", "hair_curve_flat_width",
    "hair_curve_flat_thickness", "hair_flat_mesh_width", "hair_flat_mesh_width_cm", "hair_flat_mesh_thickness", "hair_flat_mesh_thickness_cm",
    "hair_flat_mesh_samples", "hair_flat_mesh_ring_segments", "hair_flat_mesh_solidify_thickness",
    "hair_flat_mesh_add_subdivision", "hair_flat_mesh_mark_side_sharp", "hair_twist_flat_mesh_force_inner_side", "hair_twist_flat_mesh_inner_mode", "hair_warning_count", "hair_root_cluster_threshold",
    "hair_batch_curve_length", "hair_batch_curve_bevel_depth", "hair_batch_curve_resolution",
    "hair_follow_keep_tip_offset", "hair_follow_update_selected_only",
    "hair_mirror_mode_enabled", "hair_mirror_source_side", "hair_mirror_axis_mode", "hair_mirror_axis", "hair_mirror_overwrite_existing", "hair_mirror_copy_custom_properties",
    "hair_use_shared_taper", "hair_taper_preset", "hair_taper_root_radius",
    "hair_taper_mid_radius", "hair_taper_tip_radius", "hair_taper_bevel_depth",
    "hair_taper_resolution", "hair_auto_apply_taper_to_new_curves",
    "hair_strand_generation_type", "hair_twist_segments", "hair_twist_radius", "hair_twist_turns",
    "hair_twist_phase", "hair_twist_bevel_depth", "hair_twist_bevel_depth_cm", "hair_twist_resolution",
    "hair_twist_taper_strength",
    "hair_show_twist_settings", "hair_show_advanced_curve_settings",
    "hair_ui_show_curve_advanced", "hair_ui_show_card_advanced",
    "hair_ui_show_output_advanced", "hair_ui_show_cleanup_advanced",
    "hair_ui_show_debug",
    "hair_show_guides_in_front", "hair_show_inline_help", "hair_work_mode_lock_enabled",
    "hair_final_edit_mode_enabled",
)


def poll_card_control_empty(self, obj):
    return (
        obj is not None
        and obj.type == 'EMPTY'
        and obj.get("hair_guide_type") == "card_control_empty"
    )


def register():
    scene = bpy.types.Scene
    scene.hair_target_head_object = PointerProperty(
        name="頭部オブジェクト",
        type=bpy.types.Object,
        description="髪ガイド生成の基準にする頭部メッシュオブジェクト",
    )
    scene.hair_selected_card_control_empty = PointerProperty(
        name="参照Empty",
        type=bpy.types.Object,
        poll=poll_card_control_empty,
        description="Hair Guideが生成したCARD Control Emptyのみ選択できます",
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
    scene.hair_work_mode_lock_enabled = BoolProperty(
        name="作業中は他オブジェクトを選択不可",
        default=False,
        description="ONにすると、ガイド・配置点・Curve以外のオブジェクトを一時的に選択不可にします。",
    )
    scene.hair_final_edit_mode_enabled = BoolProperty(
        name="最終編集モード",
        default=False,
        description="ONにすると出力Meshのみ表示し、ガイドやCurveを非表示にします。",
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
        default=0.0,
        min=0.0,
        max=1.0,
        description="上下方向のランダム変化。",
    )
    scene.hair_width_variation = FloatProperty(
        name="幅の揺らぎ",
        default=0.0,
        min=0.0,
        max=1.0,
        description="左右方向のランダム変化。",
    )
    scene.hair_depth_variation = FloatProperty(
        name="奥行きの揺らぎ",
        default=0.0,
        min=0.0,
        max=1.0,
        description="前後方向のランダム変化。",
    )
    scene.hair_height_variation_cm = FloatProperty(
        name="高さの揺らぎ(cm)",
        default=0.0,
        min=0.0,
        max=100.0,
        description="配置点生成時の上下方向のランダム変化をcm単位で指定します。内部ではmへ変換します。",
    )
    scene.hair_width_variation_cm = FloatProperty(
        name="幅の揺らぎ(cm)",
        default=0.0,
        min=0.0,
        max=100.0,
        description="配置点生成時の左右方向のランダム変化をcm単位で指定します。内部ではmへ変換します。",
    )
    scene.hair_depth_variation_cm = FloatProperty(
        name="奥行きの揺らぎ(cm)",
        default=0.0,
        min=0.0,
        max=100.0,
        description="配置点生成時の前後方向のランダム変化をcm単位で指定します。内部ではmへ変換します。",
    )
    scene.hair_size_variation = FloatProperty(
        name="サイズの揺らぎ",
        default=0.0,
        min=0.0,
        max=2.0,
        description="配置点の表示サイズと推奨毛束サイズのランダム変化。",
    )
    scene.hair_length_variation = FloatProperty(
        name="長さの揺らぎ",
        default=0.0,
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
        description="通常カーブまたはツイストカーブのどちらを生成するか選択します。",
    )
    scene.hair_curve_length = FloatProperty(
        name="毛束長さ",
        default=0.55,
        min=0.01,
        max=5.0,
        description="生成するカーブ毛束の基準長さ。",
    )
    scene.hair_curve_length_cm = FloatProperty(
        name="毛束長さ(cm)",
        default=55.0,
        min=0.1,
        max=500.0,
        description="生成するカーブ毛束の基準長さをcm単位で指定します。内部ではmへ変換します。",
    )
    scene.hair_use_placement_recommended_length = BoolProperty(
        name="配置点の推奨長さを使用",
        default=False,
        description="有効にすると配置点生成時に保存された推奨長さを使います。無効の場合は現在の毛束長さ(cm)を使います。",
    )
    scene.hair_curve_bevel_depth = FloatProperty(
        name="太さ(m・互換用)",
        default=0.012,
        min=0.0,
        precision=4,
        description="互換用のm単位カーブ太さです。通常UIではcm単位を使用します。",
    )
    scene.hair_curve_bevel_depth_cm = FloatProperty(
        name="カーブの太さ(cm)",
        default=1.2,
        min=0.0,
        max=200.0,
        precision=2,
        description="生成するカーブ毛束の表示上の太さをcm単位で指定します。内部ではmへ変換します。",
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
        description="新規生成時にだけCurveへ小さな位置差と長さ差を加え、完全な重なりを防ぎます。既存Curveへの形状適用では再ランダム化しません。",
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
    scene.hair_curve_root_jitter_cm = FloatProperty(
        name="根元の位置ブレ(cm)",
        default=1.0,
        min=0.0,
        max=100.0,
        description="根元付近の位置ブレ量をcm単位で指定します。内部ではmへ変換します。",
    )
    scene.hair_curve_mid_jitter_cm = FloatProperty(
        name="中間の位置ブレ(cm)",
        default=3.5,
        min=0.0,
        max=100.0,
        description="中間付近の位置ブレ量をcm単位で指定します。内部ではmへ変換します。",
    )
    scene.hair_curve_tip_jitter_cm = FloatProperty(
        name="毛先の位置ブレ(cm)",
        default=6.0,
        min=0.0,
        max=100.0,
        description="毛先付近の位置ブレ量をcm単位で指定します。内部ではmへ変換します。",
    )
    scene.hair_curve_root_jitter_ratio = FloatProperty(
        name="根元の位置ブレ率",
        default=0.0,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
        description="生成Curveの全体長に対する位置ブレ率です。",
    )
    scene.hair_curve_mid_jitter_ratio = FloatProperty(
        name="中間の位置ブレ率",
        default=0.035,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
        description="生成Curveの全体長に対する位置ブレ率です。",
    )
    scene.hair_curve_tip_jitter_ratio = FloatProperty(
        name="毛先の位置ブレ率",
        default=0.08,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
        description="生成Curveの全体長に対する位置ブレ率です。",
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
        name="長さのブレ率",
        default=0.0,
        min=0.0,
        max=1.0,
        description="0なら毛束長さ(cm)がそのまま使われます。0.15なら約85%〜115%に変化します。",
    )
    scene.hair_curve_display_mode = EnumProperty(
        name="表示モード",
        items=(
            ("CURVE", "カーブ", "制御線のみ"),
            ("SOLID", "ソリッド", "Curve Bevel + Taper"),
            ("CARD", "CARDプレビュー", "板ポリ状の非破壊プレビュー"),
            ("FLAT_MESH", "扁平メッシュ", "Curveから扁平メッシュPreviewを生成して表示します"),
        ),
        default="SOLID",
        description="Curveを維持したまま表示方式を切り替えます。",
    )
    scene.hair_card_width_preset = EnumProperty(
        name="CARD幅プリセット",
        items=CARD_WIDTH_PRESETS,
        default="STANDARD",
        description="用途別のCARD Root/Mid/Tip幅プリセットを選択します。反映ボタンで幅だけを更新します。",
    )
    scene.hair_card_width_root = FloatProperty(
        name="CARD Root幅(m・互換用)",
        default=0.08, min=0.001, max=2.0, precision=4,
        description="互換用のm単位CARD幅です。通常UIではcm単位を使用します。",
    )
    scene.hair_card_width_root_cm = FloatProperty(name="CARD Root幅(cm)", default=8.0, min=0.0, max=200.0, precision=2, description="CARDプレビュー根元側の幅をcm単位で指定します。内部ではmへ変換します。")
    scene.hair_card_width_mid = FloatProperty(
        name="CARD Mid幅(m・互換用)",
        default=0.06, min=0.001, max=2.0, precision=4,
        description="互換用のm単位CARD幅です。通常UIではcm単位を使用します。",
    )
    scene.hair_card_width_mid_cm = FloatProperty(name="CARD Mid幅(cm)", default=6.0, min=0.0, max=200.0, precision=2, description="CARDプレビュー中間の幅をcm単位で指定します。内部ではmへ変換します。")
    scene.hair_card_width_tip = FloatProperty(
        name="CARD Tip幅(m・互換用)",
        default=0.005, min=0.0, max=2.0, precision=4,
        description="互換用のm単位CARD幅です。通常UIではcm単位を使用します。",
    )
    scene.hair_card_width_tip_cm = FloatProperty(name="CARD Tip幅(cm)", default=0.5, min=0.0, max=200.0, precision=2, description="CARDプレビュー毛先側の幅をcm単位で指定します。内部ではmへ変換します。")
    scene.hair_card_mid_position = FloatProperty(
        name="CARD Mid位置",
        default=0.5,
        min=0.05,
        max=0.95,
        subtype="FACTOR",
        description="RootからTipまでのどの位置をMid幅として扱うかを指定します。0.25ならRoot寄り、0.75ならTip寄りです。",
    )
    scene.hair_card_width_interpolation = EnumProperty(
        name="CARD幅補間",
        items=(
            ("LINEAR", "線形", "直線的に補間します"),
            ("SMOOTH", "スムーズ", "滑らかに補間します"),
            ("SHARP", "シャープ", "Root/Mid/Tipの変化を強めます"),
        ),
        default="SMOOTH",
        description="Root/Mid/Tip間のCARD幅補間カーブを指定します。",
    )
    scene.hair_card_sync_widths = BoolProperty(
        name="CARD幅を同期",
        default=False,
        description="ONにするとRoot/Mid/Tip幅を同じ値で扱います。Root/Mid/Tipの保存値は上書きしません。",
    )
    scene.hair_card_synced_width_cm = FloatProperty(
        name="CARD同期幅(cm)",
        default=8.0,
        min=0.0,
        max=200.0,
        precision=2,
        description="CARD幅同期ON時にRoot/Mid/Tipへ共通して使う幅をcm単位で指定します。",
    )
    scene.hair_card_samples = IntProperty(
        name="CARDサンプル数",
        default=24,
        min=2,
        max=512,
        description="CARDプレビューMeshを生成するためのCurve評価サンプル数です。",
    )
    scene.hair_card_use_parallel_transport = BoolProperty(
        name="平行移動フレームでねじれ補正",
        default=True,
        description="CARD幅方向を前サンプルから連続的に輸送し、途中反転を抑制します。",
    )
    scene.hair_card_default_roll_angle = FloatProperty(
        name="CARD標準ロール角",
        default=0.0,
        min=-180.0,
        max=180.0,
        description="新規Curve/CARD生成時の初期Roll角です。",
    )
    scene.hair_card_control_empty_mode = EnumProperty(
        name="CARD Control方式",
        items=(
            ("AXIS", "Empty X軸", "EmptyのローカルX軸をCARD幅方向にします"),
            ("TARGET_POSITION", "Empty位置ターゲット", "CurveからEmpty位置への方向をCARD向きに使います"),
        ),
        default="TARGET_POSITION",
        description="CARD Control EmptyをCARD方向へ反映する方式です。",
    )
    scene.hair_card_flip_side = BoolProperty(
        name="CARD向きを反転",
        default=False,
        description="CARD Control Emptyから計算したCARD向きを反転します。",
    )
    scene.hair_card_auto_apply_to_new_curves = BoolProperty(
        name="新規Curveへ現在の表示モードを自動適用",
        default=True,
        description="ONの場合、表示モードがCARDなら新規Curve生成直後にCARDプレビューも作成されます。",
    )
    scene.hair_card_auto_update_preview = BoolProperty(
        name="Curve編集時にCARD自動更新",
        default=True,
        description="元Curveの形状変更を検出し、CARDプレビューを自動再生成します。",
    )
    scene.hair_show_display_mode_settings = BoolProperty(
        name="表示モード詳細を表示",
        default=True,
        description="CARDプレビューの幅やサンプル数などの詳細設定を表示します。",
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
        name="扁平メッシュ幅(m・互換用)",
        default=0.08, min=0.001, max=2.0, precision=4,
        description="互換用のm単位幅です。通常UIではcm単位を使用します。",
    )
    scene.hair_flat_mesh_width_cm = FloatProperty(name="扁平メッシュ幅(cm)", default=8.0, min=0.0, max=200.0, precision=2, description="扁平メッシュ生成時の楕円断面の横幅をcm単位で指定します。内部ではmへ変換します。")
    scene.hair_flat_mesh_thickness = FloatProperty(
        name="扁平メッシュ厚み(m・互換用)",
        default=0.012, min=0.001, max=2.0, precision=4,
        description="互換用のm単位厚みです。通常UIではcm単位を使用します。",
    )
    scene.hair_flat_mesh_thickness_cm = FloatProperty(name="扁平メッシュ厚み(cm)", default=1.2, min=0.0, max=200.0, precision=2, description="CARD幅に厚みを与えて扁平メッシュ化する際の厚みです。")
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
        description="CARD幅方向を基準にした扁平断面の分割数です。",
    )
    scene.hair_flat_mesh_solidify_thickness = FloatProperty(
        name="Solidify厚み(互換用)",
        default=0.01,
        min=0.0,
        max=1.0,
        precision=4,
        description="互換用の未使用設定です。扁平メッシュ出力ではSolidifyを自動追加しません。",
    )
    scene.hair_flat_mesh_add_subdivision = BoolProperty(
        name="Subdivisionを追加",
        default=True,
        description="生成した扁平メッシュへSubdivision Surface Modifierを追加します。",
    )
    scene.hair_flat_mesh_mark_side_sharp = BoolProperty(
        name="側面エッジをSharpにする",
        default=True,
        description="扁平メッシュの側面境界にSharpを設定します。",
    )
    scene.hair_twist_flat_mesh_force_inner_side = BoolProperty(
        name="ツイスト扁平面を内側へ向ける",
        default=True,
        description="ツイストCurveから扁平メッシュを生成する際、各面を頭部中心側へ向けます。",
    )
    scene.hair_twist_flat_mesh_inner_mode = EnumProperty(
        name="ツイスト内向き基準",
        items=(
            ("HEAD_CENTER", "頭部中心", "登録頭部の中心方向へ面を向けます"),
            ("TARGET_EMPTY", "参照Empty", "CARD Control Empty方向を内向き基準にします"),
        ),
        default="HEAD_CENTER",
        description="ツイストCurveの扁平メッシュ面を内側へ向ける基準を選択します。",
    )
    scene.hair_card_auto_select_edit_curve = BoolProperty(
        name="CARD選択時に編集Curveへ切替",
        default=False,
        description="CARDプレビューを選択した時、自動で対応する編集Curveを選択します。",
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

    scene.hair_mirror_mode_enabled = BoolProperty(
        name="ミラーモード",
        default=False,
        description="ON中は生成時に左右ペアを作成し、同期ボタンで反対側へ形状を反映します。OFF後は独立編集できます。",
    )
    scene.hair_mirror_source_side = EnumProperty(
        name="ミラー元",
        items=(("L", "左", "左側を元に右側へ反映"), ("R", "右", "右側を元に左側へ反映")),
        default="L",
        description="ミラーモードで生成・同期するときのコピー元です。",
    )
    scene.hair_mirror_axis_mode = EnumProperty(
        name="ミラー軸モード",
        items=(("WORLD_X", "World X", "World X=0を基準に反転"), ("HEAD_CENTER_X", "Head Center X", "頭部中心Xを基準に反転")),
        default="HEAD_CENTER_X",
        description="左右反転の基準軸です。",
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
        default=0.15,
        min=0.0,
        max=5.0,
        description="共有テーパーの毛先側の太さ。小さいほど先端が尖ります。",
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

    scene.hair_ui_show_curve_advanced = BoolProperty(
        name="詳細を表示",
        default=False,
        description="カーブ生成/編集の低頻度・詳細設定を表示します。",
    )
    scene.hair_ui_show_card_advanced = BoolProperty(
        name="詳細を表示",
        default=False,
        description="CARD表示の低頻度・詳細設定を表示します。",
    )
    scene.hair_ui_show_output_advanced = BoolProperty(
        name="詳細を表示",
        default=False,
        description="出力の低頻度・詳細設定を表示します。",
    )
    scene.hair_ui_show_cleanup_advanced = BoolProperty(
        name="詳細を表示",
        default=False,
        description="整理・削除の低頻度・保守操作を表示します。",
    )
    scene.hair_ui_show_debug = BoolProperty(
        name="詳細を表示",
        default=False,
        description="互換Propertyやデバッグ/保守用設定を表示します。",
    )
    scene.hair_auto_assign_latest_card_control_empty = BoolProperty(
        name="Curve生成時に最新参照Emptyを自動割当",
        default=True,
        description="Curve生成時、参照可能なCARD Control Emptyがあれば参照Emptyを優先し、なければ最新のEmptyを自動割り当てします。",
    )
    scene.hair_curve_origin_to_reference_empty = BoolProperty(
        name="Curve原点を参照Emptyへ移動",
        default=True,
        description="Curve生成時、参照Emptyがある場合はCurveの見た目を維持したままObject原点をEmpty位置へ移動します。",
    )

    scene.hair_twist_segments = IntProperty(
        name="分割数",
        default=32,
        min=4,
        max=256,
        description="ツイスト表示カーブを生成するサンプル分割数。",
    )
    scene.hair_twist_radius = FloatProperty(
        name="巻き半径(cm)",
        default=8.0,
        min=0.0,
        max=200.0,
        precision=2,
        get=_get_twist_radius_cm,
        set=_set_twist_radius_cm,
        description="制御カーブの周囲に作るツイスト半径をcm単位で指定します。内部ではmへ変換し、既存Blendのm保存値は描画時にcm換算します。",
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
        name="表示太さ(m・互換用)",
        default=0.02,
        min=0.0,
        max=1.0,
        precision=4,
        description="互換用のツイスト表示カーブの太さ。UIではcm入力を使用します。",
    )
    scene.hair_twist_bevel_depth_cm = FloatProperty(
        name="ツイスト表示太さ(cm)",
        default=2.0,
        min=0.0,
        max=100.0,
        precision=2,
        description="ツイスト表示カーブの太さをcm単位で指定します。内部ではmへ変換します。",
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
