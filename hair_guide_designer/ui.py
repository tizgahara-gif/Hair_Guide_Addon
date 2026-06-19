import bpy
from . import utils


def _count_generated(guide_type=None):
    return len(utils.generated_objects(guide_type))


def _draw_status(layout, scene):
    box = layout.box()
    box.label(text="現在の状態:", icon='INFO')
    head = scene.hair_target_head_object
    if head and head.type == 'MESH':
        box.label(text=f"頭部: {head.name}", icon='CHECKMARK')
    else:
        box.label(text="頭部: 未設定", icon='ERROR')
        box.label(text="先に頭部メッシュを選択してください。")
    guide_objects = [obj for obj in utils.generated_objects() if obj.get("hair_guide_type") in {"guide", "region"}]
    basic_count = len([obj for obj in guide_objects if obj.get("hair_guide_level") == "basic"])
    point_count = _count_generated("placement_point")
    display_curve_count = _count_generated("curve") + _count_generated("twist_strand")
    twist_control_count = _count_generated("twist_control")
    card_preview_count = _count_generated("card_preview")
    output_mesh_count = _count_generated("card_mesh") + _count_generated("flat_mesh")
    warning_count = _count_generated("warning")
    box.label(text=f"基本ガイド: {basic_count}", icon='OUTLINER_OB_CURVE')
    box.label(text=f"配置点: {point_count}", icon='MESH_UVSPHERE')
    box.label(text=f"表示カーブ: {display_curve_count}", icon='OUTLINER_OB_CURVE')
    box.label(text=f"制御カーブ: {twist_control_count}", icon='CURVE_BEZCURVE')
    box.label(text=f"CARDプレビュー: {card_preview_count}", icon='MESH_PLANE')
    box.label(text=f"出力メッシュ: {output_mesh_count}", icon='MESH_DATA')
    box.label(text=f"警告: {scene.hair_warning_count or warning_count}", icon='ERROR' if (scene.hair_warning_count or warning_count) else 'CHECKMARK')


def _quick_status_counts(scene, context):
    head = scene.hair_target_head_object
    guide_objects = [obj for obj in utils.generated_objects() if obj.get("hair_guide_type") in {"guide", "region"}]
    selected_points = [
        obj for obj in context.selected_objects
        if obj.get("hair_guide_type") == "placement_point"
    ]
    return {
        "has_head": bool(head and head.type == 'MESH'),
        "basic_guides": len([obj for obj in guide_objects if obj.get("hair_guide_level") == "basic"]),
        "placement_points": _count_generated("placement_point"),
        "selected_points": len(selected_points),
        "display_curves": _count_generated("curve") + _count_generated("twist_strand"),
        "card_previews": _count_generated("card_preview"),
        "output_meshes": _count_generated("card_mesh") + _count_generated("flat_mesh"),
    }


def _draw_quick_status(layout, counts):
    box = layout.box()
    box.label(text="簡易状態:", icon='INFO')
    row = box.row(align=True)
    row.label(text=f"頭部: {'OK' if counts['has_head'] else '未設定'}", icon='CHECKMARK' if counts['has_head'] else 'ERROR')
    row.label(text=f"ガイド: {counts['basic_guides']}", icon='OUTLINER_OB_CURVE')
    row = box.row(align=True)
    row.label(text=f"配置点: {counts['placement_points']}", icon='MESH_UVSPHERE')
    row.label(text=f"選択配置点: {counts['selected_points']}", icon='RESTRICT_SELECT_OFF')
    row = box.row(align=True)
    row.label(text=f"Curve: {counts['display_curves']}", icon='OUTLINER_OB_CURVE')
    row.label(text=f"CARD: {counts['card_previews']}", icon='MESH_PLANE')
    box.label(text=f"Mesh: {counts['output_meshes']}", icon='MESH_DATA')


REGION_STATE_LABELS = {
    "VISIBLE": ("表示中", 'CHECKMARK'),
    "HIDDEN": ("非表示中", 'HIDE_ON'),
    "MIXED": ("一部表示", 'ERROR'),
    "EMPTY": ("対象なし", 'QUESTION'),
}


def _region_buttons(layout, label, region, note, show_help=True):
    state = utils.get_region_visibility_state(region)
    state_label, state_icon = REGION_STATE_LABELS.get(state, ("不明", 'QUESTION'))
    row = layout.row(align=True)
    sub = row.row(align=True)
    sub.enabled = state != "VISIBLE"
    op = sub.operator('hgd.region_visibility', text=f"{label}を表示", icon='HIDE_OFF')
    op.region = region
    op.action = 'SHOW'
    sub = row.row(align=True)
    sub.enabled = state != "HIDDEN"
    op = sub.operator('hgd.region_visibility', text=f"{label}を非表示", icon='HIDE_ON')
    op.region = region
    op.action = 'HIDE'
    layout.label(text=f"状態: {state_label}", icon=state_icon)
    if show_help:
        layout.label(text=note, icon='INFO')


def _all_region_buttons(layout):
    state = utils.get_region_visibility_state("ALL")
    sub = layout.row(align=True)
    show_col = sub.row(align=True)
    show_col.enabled = state != "VISIBLE"
    op = show_col.operator('hgd.region_visibility', text='全領域表示', icon='HIDE_OFF')
    op.region = 'ALL'
    op.action = 'SHOW'
    hide_col = sub.row(align=True)
    hide_col.enabled = state != "HIDDEN"
    op = hide_col.operator('hgd.region_visibility', text='全領域非表示', icon='HIDE_ON')
    op.region = 'ALL'
    op.action = 'HIDE'
    state_label, state_icon = REGION_STATE_LABELS.get(state, ("不明", 'QUESTION'))
    layout.label(text=f"全領域の状態: {state_label}", icon=state_icon)


class HGD_PT_base(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ヘアガイド'


class HGD_PT_inline_help_toggle(HGD_PT_base):
    bl_label = 'ヘルプ表示'
    bl_order = -1

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, 'hair_show_inline_help', icon='INFO')


class HGD_PT_quick_start(HGD_PT_base):
    bl_label = 'クイックスタート'
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            box = layout.box()
            box.label(text="作業手順", icon='INFO')
            box.label(text="1. 頭部登録")
            box.label(text="2. 基本ガイドを生成")
            box.label(text="3. 配置点生成")
            box.label(text="4. カーブ形状で長さ・太さ・テーパー・個体差設定")
            box.label(text="5. 配置点から通常Curve/ツイストCurve生成")
            box.label(text="6. 表示モードでCurve/Solid/CARD切替")
            box.label(text="7. 必要ならCARD実体化または扁平メッシュ出力")
        _draw_status(layout, scene)


class HGD_PT_quick_actions(HGD_PT_base):
    bl_label = "クイック操作"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        counts = _quick_status_counts(scene, context)

        _draw_quick_status(layout, counts)

        lock_box = layout.box()
        if scene.hair_work_mode_lock_enabled:
            lock_box.label(text="作業ロック: ON", icon='LOCKED')
            lock_box.operator('hgd.toggle_work_mode_lock', text='作業ロックを解除', icon='UNLOCKED')
        else:
            lock_box.label(text="作業ロック: OFF", icon='UNLOCKED')
            lock_box.operator('hgd.toggle_work_mode_lock', text='作業ロックを有効化', icon='LOCKED')
        if scene.hair_show_inline_help:
            lock_box.label(text="ONにすると、ガイド・配置点・通常Curve・ツイスト制御Curve以外を選択不可にします。", icon='INFO')
            lock_box.label(text="頭部や背景を誤って選択しにくくなります。")

        if scene.hair_show_inline_help:
            box = layout.box()
            box.label(text="この順に押すと、最小手順で髪ガイドからCurve生成まで進めます。", icon='INFO')
            box.label(text="詳細調整は下の各Panelで行います。")
            box.label(text="カーブ生成前に配置点を選択してください。")

        layout.separator()

        row = layout.row()
        row.operator('hgd.set_target_head', text='1. 頭部登録', icon='CHECKMARK')

        row = layout.row()
        row.enabled = counts["has_head"]
        row.operator('hgd.create_hair_guides', text='2. 基本ガイド生成', icon='OUTLINER_OB_CURVE')

        row = layout.row()
        row.enabled = counts["has_head"]
        row.operator('hgd.generate_placement_points', text='3. 配置点生成', icon='MESH_UVSPHERE')

        if counts["placement_points"] > 0 and counts["selected_points"] == 0:
            layout.label(text="カーブ生成前に配置点を選択してください。", icon='ERROR')
        row = layout.row()
        row.enabled = counts["placement_points"] > 0
        row.operator('hgd.create_curve_from_points', text='4. カーブ生成', icon='OUTLINER_OB_CURVE')

        row = layout.row(align=True)
        row.enabled = counts["display_curves"] > 0
        row.operator('hgd.apply_display_mode_to_selected_curves', text='5. 選択Curveへ表示モード適用', icon='RESTRICT_VIEW_OFF')
        row.operator('hgd.apply_display_mode_to_all_curves', text='全Curve')

        row = layout.row()
        row.enabled = counts["display_curves"] > 0
        row.operator('hgd.export_flat_mesh_from_selected_curves', text='6A. 扁平メッシュ出力', icon='MESH_DATA')
        row = layout.row(align=True)
        row.enabled = counts["display_curves"] > 0
        row.operator('hgd.convert_selected_card_preview_to_mesh', text='6B. CARD実体化', icon='MESH_PLANE')
        row.operator('hgd.convert_all_card_previews_to_mesh', text='全CARD実体化')

        if scene.hair_show_inline_help:
            box = layout.box()
            box.label(text="扁平メッシュ出力とCARD実体化は元Curveを残します。", icon='INFO')
            box.label(text="最終調整用Meshは専用Collectionに作成されます。")


class HGD_PT_setup(HGD_PT_base):
    bl_label = 'セットアップ'
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="選択中の頭部メッシュを登録します。", icon='INFO')
            layout.label(text="既存メッシュは変更されません。")
        if not scene.hair_target_head_object:
            layout.label(text="頭部が未設定です。", icon='ERROR')
            layout.label(text="先に頭部メッシュを選択してください。")
        col = layout.column(align=True)
        col.prop(scene, 'hair_target_head_object')
        col.operator('hgd.set_target_head', text='選択メッシュを頭部として登録', icon='CHECKMARK')
        layout.separator()
        layout.prop(scene, 'hair_guide_scale')
        layout.prop(scene, 'hair_guide_offset')


class HGD_PT_guide_lines(HGD_PT_base):
    bl_label = 'ガイドライン'
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="髪型設計の基準となるガイドラインです。", icon='INFO')
            layout.label(text="基本は生え際・側面境界・後頭部・襟足・正中線です。")
        row = layout.row(align=True)
        op = row.operator('hgd.show_hide_guides', text='ガイド表示', icon='HIDE_OFF')
        op.hide = False
        op = row.operator('hgd.show_hide_guides', text='ガイド非表示', icon='HIDE_ON')
        op.hide = True
        layout.operator('hgd.create_hair_guides', text='基本ガイドを生成', icon='OUTLINER_OB_CURVE')
        if scene.hair_show_inline_help:
            layout.label(text="基本ガイドのみ生成します。")
        layout.operator('hgd.delete_hair_guides', text='ガイド削除', icon='TRASH')
        if scene.hair_show_inline_help:
            layout.label(text="生成されたガイドのみ削除します。")
            layout.label(text="頭部メッシュは削除されません。")


class HGD_PT_regions(HGD_PT_base):
    bl_label = '領域表示'
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        show_help = scene.hair_show_inline_help
        if show_help:
            layout.label(text="髪の領域を表示・非表示します。", icon='INFO')
        _region_buttons(layout, "頭頂部", "Top", "頭頂部：前髪・横髪・後ろ髪へ分かれる毛流れの起点です。", show_help)
        _region_buttons(layout, "前髪", "Front", "前髪：前髪の開始位置。", show_help)
        _region_buttons(layout, "側頭部", "Side", "側頭部：耳周辺から後頭部へ流れる領域。", show_help)
        _region_buttons(layout, "左側", "Side_L", "左側のみ表示・非表示します。", show_help)
        _region_buttons(layout, "右側", "Side_R", "右側のみ表示・非表示します。", show_help)
        _region_buttons(layout, "後頭部上層", "Back_Upper", "後頭部上層：髪全体のボリューム。", show_help)
        _region_buttons(layout, "後頭部中層", "Back_Middle", "後頭部中層：大きな毛束を配置する領域。", show_help)
        _region_buttons(layout, "襟足", "Nape", "襟足：首へ向かって落ちる短い毛束領域。", show_help)
        _all_region_buttons(layout)


class HGD_PT_placement(HGD_PT_base):
    bl_label = '配置点'
    bl_order = 5

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="基本ガイドの位置を参照して、", icon='MESH_UVSPHERE')
            layout.label(text="毛束の根元候補を生成します。")
            layout.label(text="ガイドを動かしてから再生成すると、配置点も更新されます。")
        if not scene.hair_target_head_object:
            layout.label(text="頭部が未設定です。先にセットアップしてください。", icon='ERROR')
        if _count_generated("placement_point") == 0:
            layout.label(text="配置点がありません。", icon='ERROR')
            layout.label(text="配置点を生成/更新してください。")
        layout.operator('hgd.generate_placement_points', text='配置点を生成/更新', icon='MESH_UVSPHERE')
        if scene.hair_show_inline_help:
            layout.label(text="既存の配置点と警告は上書きされます。")
            layout.label(text="既存のカーブ毛束は削除されません。")
        layout.operator('hgd.clear_placement_points', icon='TRASH')
        layout.separator()
        if scene.hair_show_inline_help:
            layout.label(text="乱数シード：同じ値なら同じ配置になります。", icon='INFO')
            layout.label(text="左右対称性：高いほど左右対称になります。")
        layout.prop(scene, 'hair_seed')
        layout.prop(scene, 'hair_density')
        layout.prop(scene, 'hair_symmetry_bias')
        layout.prop(scene, 'hair_height_variation_cm')
        layout.prop(scene, 'hair_width_variation_cm')
        layout.prop(scene, 'hair_depth_variation_cm')
        layout.prop(scene, 'hair_size_variation')
        layout.prop(scene, 'hair_length_variation')


class HGD_PT_curve_strand(HGD_PT_base):
    bl_label = 'カーブ生成'
    bl_order = 6

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="配置点から新しいCurveを作成します。", icon='OUTLINER_OB_CURVE')
            layout.label(text="形状や太さは「カーブ形状」で管理します。")
        if _count_generated("placement_point") == 0:
            layout.label(text="配置点がありません。", icon='ERROR')
        if _count_generated("curve") == 0:
            layout.label(text="カーブ毛束はまだありません。", icon='INFO')
        layout.prop(scene, 'hair_strand_generation_type')
        if scene.hair_show_inline_help:
            layout.label(text="通常カーブ：1本の髪束ガイドを生成します。", icon='INFO')
            layout.label(text="ツイスト：制御カーブとドリル状の表示カーブを生成します。")
        layout.operator('hgd.create_curve_from_points', text='カーブ毛束を生成', icon='OUTLINER_OB_CURVE')


class HGD_PT_display_mode(HGD_PT_base):
    bl_label = '表示モード'
    bl_order = 7

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="Curveを維持したまま表示方式を切り替えます。", icon='OUTLINER_OB_CURVE')
            layout.label(text="CARDは元Curve線 + Preview Mesh表示の制作中プレビューです。")
            layout.label(text="CARDプレビューは表示確認用です。編集する場合は元Curveを選択してください。")
        layout.prop(scene, 'hair_curve_display_mode')
        active = context.active_object
        if active and active.get("hair_guide_type") == "card_preview":
            box = layout.box()
            box.label(text='CARDプレビューが選択されています。', icon='INFO')
            box.label(text='編集する場合は元Curveを選択してください。')
            box.operator('hgd.select_source_curve_from_card_preview', text='選択CARDの元Curveを選択', icon='RESTRICT_SELECT_OFF')
        row = layout.row(align=True)
        row.operator('hgd.apply_display_mode_to_selected_curves', text='選択Curveへ表示モード適用')
        row.operator('hgd.apply_display_mode_to_all_curves', text='全Curveへ表示モード適用')
        layout.operator('hgd.select_source_curve_from_card_preview', text='選択CARDの元Curveを選択', icon='RESTRICT_SELECT_OFF')
        layout.operator('hgd.update_card_previews_from_curves', text='CARDプレビューを更新', icon='FILE_REFRESH')
        layout.operator('hgd.lock_card_previews', text='CARDプレビューを選択可能にする', icon='RESTRICT_SELECT_OFF')
        icon = 'TRIA_DOWN' if scene.hair_show_display_mode_settings else 'TRIA_RIGHT'
        layout.prop(scene, 'hair_show_display_mode_settings', text='表示モード詳細', icon=icon, toggle=True)
        if scene.hair_show_display_mode_settings:
            box = layout.box()
            box.label(text='CARDプレビュー', icon='MESH_PLANE')
            box.prop(scene, 'hair_card_sync_widths')
            if scene.hair_card_sync_widths:
                box.prop(scene, 'hair_card_synced_width_cm')
            else:
                box.prop(scene, 'hair_card_width_root_cm')
                box.prop(scene, 'hair_card_width_mid_cm')
                box.prop(scene, 'hair_card_width_tip_cm')
            box.prop(scene, 'hair_card_samples')
            box.prop(scene, 'hair_card_auto_apply_to_new_curves')
            box.prop(scene, 'hair_card_auto_update_preview')
            box.operator('hgd.update_card_previews_from_curves', text='CARDプレビューを更新', icon='FILE_REFRESH')
            box.operator('hgd.select_source_curve_from_card_preview', text='選択CARDの元Curveを選択', icon='RESTRICT_SELECT_OFF')
            if scene.hair_show_inline_help:
                box.label(text='元Curveは削除されず、CardPreviewsに一時Meshを作ります。')
                box.label(text='CARDプレビューは選択できますが、編集対象は元Curveです。')
                box.label(text='自動適用ON + CARDでは新規Curve生成直後にCARDプレビューも作成します。')
                box.label(text='CARDを選んだ後、元Curveを選択すると編集対象へ移動できます。')


class HGD_PT_curve_variation(HGD_PT_base):
    bl_label = 'カーブ形状設定'
    bl_order = 8

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="このPanelで、Curve生成時の長さ、太さ、先細り、個体差をまとめて管理します。", icon='OUTLINER_OB_CURVE')
            layout.label(text="個体差は新規生成時にだけ反映されます。")
            layout.label(text="既存Curveの太さやテーパー変更は形状適用ボタンを使ってください。")

        box = layout.box()
        box.label(text="カーブ基本", icon='CHECKMARK')
        box.prop(scene, 'hair_curve_length_cm')
        box.prop(scene, 'hair_curve_bevel_depth_cm')
        box.prop(scene, 'hair_curve_resolution')
        box.prop(scene, 'hair_curve_segment_count')

        box = layout.box()
        box.label(text="テーパー", icon='OUTLINER_OB_CURVE')
        box.prop(scene, 'hair_use_shared_taper')
        box.prop(scene, 'hair_auto_apply_taper_to_new_curves')
        box.prop(scene, 'hair_taper_preset')
        box.operator('hgd.apply_taper_preset', icon='CHECKMARK')
        box.prop(scene, 'hair_taper_root_radius', text='Root')
        box.prop(scene, 'hair_taper_mid_radius', text='Mid')
        box.prop(scene, 'hair_taper_tip_radius', text='Tip')

        box = layout.box()
        box.label(text="個体差", icon='INFO')
        if scene.hair_show_inline_help:
            box.label(text="個体差は新規生成時のブレ設定です。")
            box.label(text="既存Curveへの形状適用では再ランダム化しません。")
            box.label(text="位置ブレ率は毛束長さに対する割合です。")
            box.label(text="例: 毛束長さ50cm、毛先ブレ率0.10なら最大5cm程度ブレます。")
            box.label(text="長さのブレ率が0なら毛束長さ(cm)がそのまま使われます。")
            box.label(text="0.15なら約85%〜115%に変化します。")
        box.prop(scene, 'hair_curve_variation_enabled')
        box.prop(scene, 'hair_curve_variation_seed')
        box.prop(scene, 'hair_curve_variation_randomize_seed_per_generation')
        box.prop(scene, 'hair_curve_root_jitter_ratio')
        box.prop(scene, 'hair_curve_mid_jitter_ratio')
        box.prop(scene, 'hair_curve_tip_jitter_ratio')
        box.prop(scene, 'hair_curve_length_variation', text='長さのブレ率')

        box = layout.box()
        box.label(text="適用", icon='CHECKMARK')
        row = box.row(align=True)
        row.operator('hgd.apply_shape_to_selected_curves', text='選択Curveへ形状を適用')
        row.operator('hgd.apply_shape_to_all_curves', text='全Curveへ形状を適用')
        box.operator('hgd.load_selected_curve_settings', text='選択カーブ設定を読み込み', icon='CHECKMARK')
        row = box.row(align=True)
        row.operator('hgd.clear_shape_from_selected_curves', text='選択カーブの形状を解除')
        row.operator('hgd.clear_shape_from_all_curves', text='全カーブの形状を解除')

        twist_box = layout.box()
        twist_icon = 'TRIA_DOWN' if scene.hair_show_twist_settings else 'TRIA_RIGHT'
        twist_box.prop(scene, 'hair_show_twist_settings', text='ツイスト設定', icon=twist_icon, toggle=True)
        if scene.hair_show_twist_settings:
            twist_box.prop(scene, 'hair_twist_segments')
            twist_box.prop(scene, 'hair_twist_radius')
            twist_box.prop(scene, 'hair_twist_turns')
            twist_box.prop(scene, 'hair_twist_phase')
            twist_box.prop(scene, 'hair_twist_bevel_depth_cm')
            twist_box.prop(scene, 'hair_twist_resolution')
            twist_box.prop(scene, 'hair_twist_taper_strength')
            if scene.hair_show_inline_help:
                twist_box.label(text="ツイスト制御カーブは形状制御専用です。髪として見えるのは表示用カーブです。")
        else:
            twist_box.label(text="ツイスト詳細は非表示です。", icon='TRIA_RIGHT')



class HGD_PT_flat_mesh(HGD_PT_base):
    bl_label = 'メッシュ出力'
    bl_order = 9

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="選択した表示用Curveから出力用Meshを生成します。", icon='MESH_DATA')
            layout.label(text="CARDプレビューとは別機能です。元Curveは削除されません。")
        layout.prop(scene, 'hair_flat_mesh_width_cm')
        layout.prop(scene, 'hair_flat_mesh_thickness_cm')
        layout.prop(scene, 'hair_flat_mesh_samples')
        layout.prop(scene, 'hair_flat_mesh_ring_segments')
        layout.prop(scene, 'hair_flat_mesh_add_subdivision')
        layout.operator('hgd.export_flat_mesh_from_selected_curves', text='選択Curveを扁平メッシュ出力', icon='MESH_DATA')
        layout.separator()
        layout.operator('hgd.convert_selected_card_preview_to_mesh', text='選択CurveのCARDプレビューを実体化', icon='MESH_PLANE')
        layout.operator('hgd.convert_all_card_previews_to_mesh', text='全CARDプレビューを実体化', icon='MESH_GRID')


class HGD_PT_curve_apply_update(HGD_PT_base):
    bl_label = 'カーブ適用・更新'
    bl_order = 10

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="配置点や制御Curveを編集した後に、既存Curveを更新します。", icon='OUTLINER_OB_CURVE')
            layout.label(text="ツイスト表示Curveは表示専用です。編集するのは制御Curveだけです。")
        if scene.hair_show_inline_help:
            layout.label(text="配置点を動かした後は根元更新を使います。", icon='INFO')
            layout.label(text="毛先位置を維持しない場合、形が崩れることがあります。")
        layout.prop(scene, 'hair_follow_update_selected_only')
        layout.prop(scene, 'hair_follow_keep_tip_offset')
        if not scene.hair_follow_keep_tip_offset:
            layout.label(text="毛先位置を維持しない場合、形が崩れることがあります。", icon='ERROR')
        layout.operator('hgd.update_curve_roots_from_points', icon='OUTLINER_OB_CURVE')
        layout.separator()
        if scene.hair_show_inline_help:
            layout.label(text="制御カーブ編集後はツイストを更新してください。", icon='INFO')
        row = layout.row(align=True)
        row.operator('hgd.update_selected_twists', text='選択ツイストを更新')
        row.operator('hgd.update_all_twists', text='全ツイストを更新')
        layout.operator('hgd.lock_twist_visual_curves', text='ツイスト表示Curveを選択不可にする', icon='LOCKED')


class HGD_PT_side_mirror(HGD_PT_base):
    bl_label = '左右ミラー'
    bl_order = 11

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="側頭部の配置点、カーブ、ツイストを", icon='INFO')
            layout.label(text="反対側へ複製します。")
            layout.label(text="選択中の左右対象のみ処理します。", icon='ERROR')
        layout.prop(scene, 'hair_mirror_axis')
        if scene.hair_show_inline_help:
            layout.label(text="MVPではX軸のみ対応します。")
        layout.prop(scene, 'hair_mirror_overwrite_existing')
        layout.prop(scene, 'hair_mirror_copy_custom_properties')
        layout.label(text="側頭部ガイドCurve")
        row = layout.row(align=True)
        row.operator('hgd.mirror_side_guide_l_to_r', text='左側頭ガイド → 右へミラー')
        row.operator('hgd.mirror_side_guide_r_to_l', text='右側頭ガイド → 左へミラー')
        layout.separator()
        layout.label(text="前後ガイド")
        layout.operator('hgd.symmetrize_front_back_guides', text='前後ガイドを左右対称化', icon='MOD_MIRROR')
        if scene.hair_show_inline_help:
            layout.label(text="Front/Back/Napeガイドの左右差を整えます。")
            layout.label(text="手動調整後に使ってください。")
        layout.separator()
        layout.label(text="生成済み配置点 / Curve / ツイスト")
        row = layout.row(align=True)
        row.operator('hgd.mirror_side_l_to_r', text='左側→右側へミラー')
        row.operator('hgd.mirror_side_r_to_l', text='右側→左側へミラー')


class HGD_PT_validation(HGD_PT_base):
    bl_label = '検証'
    bl_order = 12

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="同じ場所から毛束が生えて見える問題を検出します。", icon='INFO')
            layout.label(text="根元が近すぎる箇所を確認します。")
        if _count_generated("placement_point") == 0:
            layout.label(text="配置点がありません。", icon='ERROR')
            layout.label(text="検証前に配置点を生成してください。")
        layout.operator('hgd.check_root_clustering', icon='ERROR')
        layout.operator('hgd.clear_warnings', icon='TRASH')
        layout.prop(scene, 'hair_root_cluster_threshold')
        layout.prop(scene, 'hair_warning_count')
        if scene.hair_show_inline_help:
            layout.label(text="警告数は近すぎる配置点ペア数です。", icon='INFO')
            layout.label(text="赤色は根元が近すぎる警告です。")
            layout.label(text="Viewport ShadingのColorをObjectにしてください。")


class HGD_PT_curve_organization(HGD_PT_base):
    bl_label = 'カーブ整理'
    bl_order = 13

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="生成済みカーブを部位別Collectionへ分け、", icon='OUTLINER_COLLECTION')
            layout.label(text="領域ごとの色を反映します。")
        layout.operator('hgd.organize_curves_by_region', text='カーブを部位別に整理', icon='OUTLINER_COLLECTION')
        layout.operator('hgd.apply_curve_region_colors', text='部位別カラーを反映', icon='MATERIAL')
        if scene.hair_show_inline_help:
            layout.label(text="色を確認するにはViewport Shadingの", icon='INFO')
            layout.label(text="ColorをObjectにしてください。")


class HGD_PT_display_cleanup(HGD_PT_base):
    bl_label = '表示と削除'
    bl_order = 14

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.hair_show_inline_help:
            layout.label(text="表示切替と削除を行います。", icon='INFO')
            layout.label(text="ガイド、配置点、表示用カーブを頭部メッシュより手前に表示します。")
        if scene.hair_show_guides_in_front:
            layout.label(text="最前面表示: ON", icon='CHECKMARK')
            layout.operator('hgd.toggle_in_front_generated_helpers', text='最前面表示を解除', icon='HIDE_ON')
        else:
            layout.label(text="最前面表示: OFF", icon='HIDE_OFF')
            layout.operator('hgd.toggle_in_front_generated_helpers', text='最前面表示にする', icon='HIDE_OFF')
        layout.separator()
        row = layout.row(align=True)
        op = row.operator('hgd.show_hide_guides', text='ガイド表示', icon='HIDE_OFF')
        op.hide = False
        op = row.operator('hgd.show_hide_guides', text='ガイド非表示', icon='HIDE_ON')
        op.hide = True
        _all_region_buttons(layout)
        layout.separator()
        if scene.hair_show_inline_help:
            layout.label(text="HairGuideSystem内の生成物のみ削除します。", icon='INFO')
        layout.operator('hgd.clear_warnings', icon='TRASH')
        layout.operator('hgd.clear_card_previews', text='CARDプレビューを削除', icon='TRASH')
        layout.operator('hgd.clear_placement_points', icon='TRASH')
        layout.operator('hgd.delete_hair_guides', text='ガイド削除', icon='TRASH')
        if scene.hair_show_inline_help:
            layout.label(text="すべて削除はガイド、配置点、")
            layout.label(text="カーブ、警告、テーパー、CARDを削除します。")
            layout.label(text="頭部メッシュは削除されません。")
        layout.operator('hgd.clear_all_generated', icon='TRASH')


class HGD_PT_help(HGD_PT_base):
    bl_label = 'ヘルプ'
    bl_order = 15
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if not scene.hair_show_inline_help:
            layout.label(text="ヘルプは非表示です。上部の「ヘルプを表示」をONにしてください。", icon='INFO')
            return
        box = layout.box()
        box.label(text="このアドオンでできること", icon='INFO')
        box.label(text="・髪のガイド生成")
        box.label(text="・毛束配置点生成")
        box.label(text="・Bezierカーブ毛束生成")
        box.label(text="・カーブ毛束の先細り形状設定")
        box.label(text="・根元集中チェック")
        box = layout.box()
        box.label(text="できないこと", icon='ERROR')
        box.label(text="・髪メッシュ自動生成")
        box.label(text="・頭部メッシュ編集")
        box.label(text="・カーブの自動メッシュ化")
        box.label(text="・Unity設定 / PhysBone設定")
        box = layout.box()
        box.label(text="推奨手順", icon='CHECKMARK')
        box.label(text="1. 基本ガイドを生成")
        box.label(text="2. 配置点生成")
        box.label(text="3. 必要なら配置点調整")
        box.label(text="4. カーブ毛束生成")
        box.label(text="5. カーブ編集 / 根元集中チェック")
        box = layout.box()
        box.label(text="カーブ形状について", icon='OUTLINER_OB_CURVE')
        box.label(text="生成直後は円柱状に見える場合があります。")
        box.label(text="共有テーパーで毛先を細くします。")
        box.label(text="1. プリセットを選ぶ")
        box.label(text="2. プリセットを反映")
        box.label(text="3. テーパー形状を作成/更新")
        box.label(text="4. 選択または全カーブへ適用")
        box.label(text="自動適用ONなら新規カーブにも反映されます。")
        box.label(text="扁平化は選択Curveから別メッシュとして生成します。")
        box.label(text="元Curveは編集用として残ります。")
        box = layout.box()
        box.label(text="カーブの個体差について", icon='OUTLINER_OB_CURVE')
        box.label(text="配置点は動かさず、生成カーブだけに")
        box.label(text="位置ブレと長さブレを加えます。")
        box.label(text="同じSeedなら再現しやすくなります。")
        box.label(text="既存Curveへの形状適用では再ランダム化しません。")
        box = layout.box()
        box.label(text="配置点について", icon='MESH_UVSPHERE')
        box.label(text="現在の基本ガイド位置を参照します。")
        box.label(text="基本ガイド移動後は「配置点を生成/更新」を押してください。")
        box.label(text="配置点と警告は上書きされます。")
        box.label(text="既存のカーブ毛束は削除されません。")


classes = (
    HGD_PT_inline_help_toggle,
    HGD_PT_quick_actions,
    HGD_PT_quick_start,
    HGD_PT_setup,
    HGD_PT_guide_lines,
    HGD_PT_regions,
    HGD_PT_placement,
    HGD_PT_curve_strand,
    HGD_PT_display_mode,
    HGD_PT_curve_variation,
    HGD_PT_flat_mesh,
    HGD_PT_curve_apply_update,
    HGD_PT_side_mirror,
    HGD_PT_validation,
    HGD_PT_curve_organization,
    HGD_PT_display_cleanup,
    HGD_PT_help,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
