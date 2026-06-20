import bpy
from . import utils


def _section_box(layout, title, icon='NONE', prefix=''):
    box = layout.box()
    box.label(text=f"{prefix} {title}" if prefix else title, icon=icon)
    return box


def _foldout(layout, scene, prop_name, label):
    row = layout.row()
    icon = 'TRIA_DOWN' if getattr(scene, prop_name) else 'TRIA_RIGHT'
    row.prop(scene, prop_name, text=label, icon=icon, toggle=True)
    return getattr(scene, prop_name)


def _has_selected_card_preview(context):
    return any(obj.get("hair_guide_type") == "card_preview" for obj in context.selected_objects)


def _draw_card_edit_redirect(layout, context):
    if not _has_selected_card_preview(context):
        return
    box = layout.box()
    box.label(text="CARDプレビューが選択されています。編集は元Curveで行います。", icon='INFO')
    box.label(text="出力Meshは通常のMeshとして編集できます。")
    box.label(text="ツイストCARDの場合は表示用twist_strandではなくtwist_controlを選択します。")
    box.operator('hgd.edit_source_curve', text='編集Curveを開く', icon='CURVE_BEZCURVE')


def _count_generated(guide_type=None):
    return len(utils.generated_objects(guide_type))


def _draw_status(layout, scene):
    box = _section_box(layout, "簡易状態", 'INFO')
    head = scene.hair_target_head_object
    box.label(text=f"頭部: {head.name}" if head and head.type == 'MESH' else "頭部: 未設定", icon='CHECKMARK' if head and head.type == 'MESH' else 'ERROR')
    guide_objects = [obj for obj in utils.generated_objects() if obj.get("hair_guide_type") in {"guide", "region"}]
    basic_count = len([obj for obj in guide_objects if obj.get("hair_guide_level") == "basic"])
    warning_count = _count_generated("warning")
    for text, icon in [
        (f"基本ガイド: {basic_count}", 'OUTLINER_OB_CURVE'),
        (f"配置点: {_count_generated('placement_point')}", 'MESH_UVSPHERE'),
        (f"表示カーブ: {_count_generated('curve') + _count_generated('twist_strand')}", 'OUTLINER_OB_CURVE'),
        (f"制御カーブ: {_count_generated('twist_control')}", 'CURVE_BEZCURVE'),
        (f"CARDプレビュー: {_count_generated('card_preview')}", 'MESH_PLANE'),
        (f"出力メッシュ: {_count_generated('card_mesh') + _count_generated('flat_mesh')}", 'MESH_DATA'),
        (f"警告: {scene.hair_warning_count or warning_count}", 'ERROR' if (scene.hair_warning_count or warning_count) else 'CHECKMARK'),
    ]:
        box.label(text=text, icon=icon)


def _quick_status_counts(scene, context):
    head = scene.hair_target_head_object
    guide_objects = [obj for obj in utils.generated_objects() if obj.get("hair_guide_type") in {"guide", "region"}]
    selected_points = [obj for obj in context.selected_objects if obj.get("hair_guide_type") == "placement_point"]
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
    box = _section_box(layout, "簡易状態", 'INFO')
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



def _region_buttons(layout, label, region, note, show_help=True):
    state = utils.get_region_visibility_state(region)
    row = layout.row(align=True)
    sub = row.row(align=True); sub.enabled = state != "VISIBLE"
    op = sub.operator('hgd.region_visibility', text=f"{label}を表示", icon='HIDE_OFF'); op.region = region; op.action = 'SHOW'
    sub = row.row(align=True); sub.enabled = state != "HIDDEN"
    op = sub.operator('hgd.region_visibility', text=f"{label}を非表示", icon='HIDE_ON'); op.region = region; op.action = 'HIDE'
    if show_help: layout.label(text=note, icon='INFO')


def _all_region_buttons(layout):
    state = utils.get_region_visibility_state("ALL")
    sub = layout.row(align=True)
    show_col = sub.row(align=True); show_col.enabled = state != "VISIBLE"
    op = show_col.operator('hgd.region_visibility', text='全領域表示', icon='HIDE_OFF'); op.region = 'ALL'; op.action = 'SHOW'
    hide_col = sub.row(align=True); hide_col.enabled = state != "HIDDEN"
    op = hide_col.operator('hgd.region_visibility', text='全領域非表示', icon='HIDE_ON'); op.region = 'ALL'; op.action = 'HIDE'


class HGD_PT_base(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ヘアガイド'

class HGD_PT_inline_help_toggle(HGD_PT_base):
    bl_label = 'ヘルプ表示'
    bl_order = -1
    def draw(self, context):
        self.layout.prop(context.scene, 'hair_show_inline_help', icon='INFO')

class HGD_PT_quick_actions(HGD_PT_base):
    bl_label = 'クイック操作'
    bl_order = 0
    def draw(self, context):
        layout, scene = self.layout, context.scene
        counts = _quick_status_counts(scene, context)
        _draw_quick_status(layout, counts)
        box = _section_box(layout, '作業ロック', 'LOCKED' if scene.hair_work_mode_lock_enabled else 'UNLOCKED')
        box.operator('hgd.toggle_work_mode_lock', text='作業ロックを解除' if scene.hair_work_mode_lock_enabled else '作業ロックを有効化', icon='UNLOCKED' if scene.hair_work_mode_lock_enabled else 'LOCKED')
        box = _section_box(layout, '通常作業ショートカット', 'CHECKMARK')
        box.operator('hgd.set_target_head', text='1. 頭部登録', icon='CHECKMARK')
        row = box.row(); row.enabled = counts['has_head']; row.operator('hgd.create_hair_guides', text='2. 基本ガイド生成', icon='OUTLINER_OB_CURVE')
        row = box.row(); row.enabled = counts['has_head']; row.operator('hgd.generate_placement_points', text='3. 配置点生成', icon='MESH_UVSPHERE')
        row = box.row(); row.enabled = counts['placement_points'] > 0; row.operator('hgd.create_curve_from_points', text='4. カーブ生成', icon='CURVE_BEZCURVE')
        display_box = box.box()
        display_box.label(text='---- 表示モード ----', icon='RESTRICT_VIEW_OFF')
        display_box.prop(scene, 'hair_curve_display_mode', text='表示モード')
        row = display_box.row(align=True); row.enabled = counts['display_curves'] > 0; row.operator('hgd.apply_display_mode_to_selected_curves', text='5. 選択対象へ適用', icon='RESTRICT_VIEW_OFF')
        row = display_box.row(align=True); row.enabled = counts['display_curves'] > 0; row.operator('hgd.apply_display_mode_to_all_curves', text='6. 全Curveへ適用', icon='RESTRICT_VIEW_OFF')
        output_box = box.box()
        output_box.label(text='---- 出力 ----', icon='MESH_DATA')
        row = output_box.row(align=True); row.enabled = counts['display_curves'] > 0; row.operator('hgd.convert_selected_card_preview_to_mesh', text='7. CARD Mesh出力', icon='MESH_PLANE')
        row = output_box.row(align=True); row.enabled = counts['display_curves'] > 0; row.operator('hgd.export_flat_mesh_from_selected_curves', text='8. 扁平Mesh出力', icon='MESH_DATA')
        output_box.operator(
            'hgd.toggle_final_edit_mode',
            text='7. 最終編集モード解除' if scene.hair_final_edit_mode_enabled else '7. 最終編集モード',
            icon='HIDE_OFF' if scene.hair_final_edit_mode_enabled else 'MESH_DATA',
        )
        if scene.hair_show_inline_help:
            output_box.label(text='出力Meshのみ表示し、ガイド・配置点・Curve・Preview・Emptyを非表示にします。', icon='INFO')
            output_box.label(text='Mesh編集に集中したい時に使います。')
        _draw_card_edit_redirect(layout, context)

class HGD_PT_setup(HGD_PT_base):
    bl_label = 'セットアップ'
    bl_order = 1
    def draw(self, context):
        scene=context.scene; box=_section_box(self.layout, 'セットアップ', 'TOOL_SETTINGS', '[SETUP]')
        box.prop(scene, 'hair_target_head_object'); box.operator('hgd.set_target_head', text='選択メッシュを頭部として登録', icon='CHECKMARK')
        box.prop(scene, 'hair_guide_scale'); box.prop(scene, 'hair_guide_offset')

class HGD_PT_guides_points(HGD_PT_base):
    bl_label = 'ガイド・配置点'
    bl_order = 2
    def draw(self, context):
        scene=context.scene; layout=self.layout; box=_section_box(layout, 'ガイド・配置点', 'OUTLINER_OB_CURVE', '[GUIDE]')
        row=box.row(align=True); op=row.operator('hgd.show_hide_guides', text='ガイド表示', icon='HIDE_OFF'); op.hide=False; op=row.operator('hgd.show_hide_guides', text='ガイド非表示', icon='HIDE_ON'); op.hide=True
        box.operator('hgd.create_hair_guides', text='基本ガイドを生成', icon='OUTLINER_OB_CURVE')
        box.operator('hgd.generate_placement_points', text='配置点を生成/更新', icon='MESH_UVSPHERE')
        box.operator('hgd.clear_placement_points', text='配置点を削除', icon='TRASH')
        region=_section_box(layout, '領域表示', 'HIDE_OFF', '[GUIDE]')
        for args in [("頭頂部","Top","頭頂部：前髪・横髪・後ろ髪へ分かれる毛流れの起点です。"),("前髪","Front","前髪：前髪の開始位置。"),("側頭部","Side","側頭部：耳周辺から後頭部へ流れる領域。"),("左側","Side_L","左側のみ表示・非表示します。"),("右側","Side_R","右側のみ表示・非表示します。"),("後頭部上層","Back_Upper","後頭部上層：髪全体のボリューム。"),("後頭部中層","Back_Middle","後頭部中層：大きな毛束を配置する領域。"),("襟足","Nape","襟足：首へ向かって落ちる短い毛束領域。")]: _region_buttons(region,*args,show_help=scene.hair_show_inline_help)
        _all_region_buttons(region)
        mirror=_section_box(layout, '左右対称・ミラー', 'MOD_MIRROR', '[GUIDE]')
        mirror.operator('hgd.symmetrize_front_back_guides', text='前後ガイドを左右対称化', icon='MOD_MIRROR')
        row=mirror.row(align=True); row.operator('hgd.mirror_side_guide_l_to_r', text='左側頭ガイド → 右へミラー'); row.operator('hgd.mirror_side_guide_r_to_l', text='右側頭ガイド → 左へミラー')

class HGD_PT_curve_generate(HGD_PT_base):
    bl_label = 'カーブ生成'
    bl_order = 3
    def draw(self, context):
        scene=context.scene; box=_section_box(self.layout, 'カーブ生成', 'CURVE_BEZCURVE', '[CURVE]')
        box.prop(scene, 'hair_strand_generation_type'); box.operator('hgd.create_curve_from_points', text='選択配置点からCurve生成', icon='CURVE_BEZCURVE')
        box.prop(scene, 'hair_twist_radius'); box.prop(scene, 'hair_twist_turns')
        if _foldout(self.layout, scene, 'hair_ui_show_curve_advanced', '詳細を表示'):
            adv=_section_box(self.layout, 'ツイスト詳細', 'CURVE_BEZCURVE', '[CURVE]')
            for p in ['hair_twist_segments','hair_twist_phase','hair_twist_bevel_depth_cm','hair_twist_resolution','hair_twist_taper_strength']: adv.prop(scene,p)

class HGD_PT_curve_edit(HGD_PT_base):
    bl_label = 'カーブ編集'
    bl_order = 4
    def draw(self, context):
        scene=context.scene; layout=self.layout; box=_section_box(layout, 'カーブ編集', 'CURVE_BEZCURVE', '[CURVE]')
        box.prop(scene, 'hair_curve_length_cm', text='毛先長さ(cm)')
        box.label(text='（新規生成時のみ）', icon='INFO')
        for p in ['hair_curve_bevel_depth_cm','hair_curve_resolution','hair_curve_segment_count','hair_use_shared_taper','hair_auto_apply_taper_to_new_curves','hair_taper_preset']: box.prop(scene,p)
        box.operator('hgd.apply_taper_preset', icon='CHECKMARK')
        for p,t in [('hair_taper_root_radius','Root'),('hair_taper_mid_radius','Mid'),('hair_taper_tip_radius','Tip')]: box.prop(scene,p,text=t)
        for p in ['hair_curve_variation_enabled','hair_curve_variation_seed','hair_curve_variation_randomize_seed_per_generation','hair_curve_root_jitter_ratio','hair_curve_mid_jitter_ratio','hair_curve_tip_jitter_ratio','hair_curve_length_variation']: box.prop(scene,p)
        row=box.row(align=True); row.operator('hgd.apply_shape_to_selected_curves', text='選択Curveへ形状適用'); row.operator('hgd.apply_shape_to_all_curves', text='全Curveへ形状適用')
        box.operator('hgd.mirror_selected_curves', text='選択Curveを左右ミラー', icon='MOD_MIRROR')
        box.operator('hgd.load_selected_curve_settings', text='選択カーブ設定読み込み', icon='CHECKMARK')
        for p in ['hair_follow_update_selected_only','hair_follow_keep_tip_offset']: box.prop(scene,p)
        box.operator('hgd.update_curve_roots_from_points', text='配置点から根元更新', icon='OUTLINER_OB_CURVE')
        row=box.row(align=True); row.operator('hgd.update_selected_twists', text='選択ツイスト更新'); row.operator('hgd.update_all_twists', text='全ツイスト更新')


class HGD_PT_card_display(HGD_PT_base):
    bl_label = 'CARD表示'
    bl_order = 5
    def draw(self, context):
        scene=context.scene; layout=self.layout; box=_section_box(layout, 'CARD表示', 'MESH_PLANE', '[CARD]')
        box.prop(scene, 'hair_card_width_preset'); box.operator('hgd.apply_card_width_preset', icon='CHECKMARK')
        box.prop(scene, 'hair_card_sync_widths')
        if scene.hair_card_sync_widths: box.prop(scene, 'hair_card_synced_width_cm')
        else:
            for p in ['hair_card_width_root_cm','hair_card_width_mid_cm','hair_card_width_tip_cm']: box.prop(scene,p)
        box.prop(scene, 'hair_card_mid_position')
        box.prop(scene, 'hair_card_width_interpolation')
        if scene.hair_show_inline_help:
            box.label(text='Mid位置をRoot側へ寄せると根元付近、Tip側へ寄せると毛先側まで幅を維持できます。', icon='INFO')
        box.operator('hgd.update_card_previews_from_curves', text='CARDプレビュー更新', icon='FILE_REFRESH')
        ctrl_box = box.box()
        ctrl_box.label(text='CARD方向制御', icon='EMPTY_SINGLE_ARROW')
        ctrl_box.prop(scene, 'hair_card_control_empty_mode')
        ctrl_box.prop(scene, 'hair_card_flip_side')
        ctrl_box.operator('hgd.create_card_control_empty', text='共有CARD Control Empty作成/割り当て', icon='EMPTY_SINGLE_ARROW')
        if hasattr(scene, 'hair_selected_card_control_empty'):
            ctrl_box.prop(scene, 'hair_selected_card_control_empty', text='参照Empty')
            if scene.hair_show_inline_help:
                ctrl_box.label(text='参照Emptyには、Hair Guideが生成または割り当て済みのCARD Control Emptyのみ表示されます。', icon='INFO')
            ctrl_box.operator('hgd.assign_pointer_card_control_empty', text='選択Curveへ割り当て', icon='CONSTRAINT')
        ctrl_box.operator('hgd.share_card_control_empty_to_selected_curves', text='参照Emptyを選択Curveへ共有', icon='LINKED')
        ctrl_box.operator('hgd.select_shared_card_control_empty', text='参照Emptyを選択', icon='RESTRICT_SELECT_OFF')
        ctrl_box.operator('hgd.clear_card_control_empty', text='CARD Control Empty割当解除', icon='X')
        ctrl_box.operator('hgd.update_card_previews_from_curves', text='CARDプレビューを更新', icon='FILE_REFRESH')
        if scene.hair_show_inline_help:
            ctrl_box.label(text='Empty位置ターゲットでは、Emptyの位置がCARD面の向きの基準になります。', icon='HELP')
            ctrl_box.label(text='髪を内側に向けたい場合は、Emptyを頭部内側へ配置してください。')
            ctrl_box.label(text='Empty X軸方式では、Emptyの回転で向きを制御します。')
            ctrl_box.label(text='Empty未設定の場合は自動フレームで生成します。')
            ctrl_box.label(text='複数Curveへ同じEmptyを割り当てると、EmptyひとつでCARD方向をまとめて制御できます。')
        box.operator('hgd.edit_source_curve', text='編集Curveを開く', icon='CURVE_BEZCURVE')
        _draw_card_edit_redirect(layout, context)
        if _foldout(layout, scene, 'hair_ui_show_card_advanced', '詳細を表示'):
            adv=_section_box(layout, 'CARD詳細', 'MESH_PLANE', '[CARD]')
            for p in ['hair_card_samples','hair_card_auto_apply_to_new_curves','hair_card_auto_update_preview','hair_card_auto_select_edit_curve']: adv.prop(scene,p)
            adv.operator('hgd.create_card_control_empty_per_curve', text='選択Curveごとに個別Empty作成', icon='EMPTY_ARROWS')
            adv.operator('hgd.lock_card_previews', text='CARDプレビューを選択可能にする', icon='RESTRICT_SELECT_OFF')

class HGD_PT_output(HGD_PT_base):
    bl_label = '出力'
    bl_order = 6
    def draw(self, context):
        scene=context.scene; layout=self.layout; box=_section_box(layout, '出力', 'MESH_DATA', '[OUTPUT]')
        box.operator('hgd.convert_selected_card_preview_to_mesh', text='選択CurveのCARD Mesh実体化', icon='MESH_PLANE'); box.operator('hgd.convert_all_card_previews_to_mesh', text='全CARD Mesh実体化', icon='MESH_GRID')
        flat_box=_section_box(layout, '扁平メッシュ設定', 'MESH_DATA', '[OUTPUT]')
        flat_box.prop(scene, 'hair_flat_mesh_width_cm'); flat_box.prop(scene, 'hair_flat_mesh_thickness_cm'); flat_box.prop(scene, 'hair_flat_mesh_samples')
        flat_box.prop(scene, 'hair_flat_mesh_add_subdivision'); flat_box.prop(scene, 'hair_flat_mesh_mark_side_sharp')
        flat_box.prop(scene, 'hair_twist_flat_mesh_force_inner_side'); flat_box.prop(scene, 'hair_twist_flat_mesh_inner_mode')
        if scene.hair_show_inline_help:
            flat_box.label(text='通常CurveはCARD Control Empty方向を使います。', icon='INFO')
            flat_box.label(text='ツイストCurveのみ、頭部中心側または参照Empty方向へ面を向けられます。')
        row=flat_box.row(align=True); row.operator('hgd.export_flat_mesh_from_selected_curves', text='選択Curveを扁平Mesh出力', icon='MESH_DATA'); row.operator('hgd.create_flat_mesh_from_all_curves', text='全Curveを扁平Mesh出力', icon='MESH_GRID')
        box.operator('hgd.toggle_final_edit_mode', text='最終編集モード解除' if scene.hair_final_edit_mode_enabled else '最終編集モード', icon='HIDE_OFF' if scene.hair_final_edit_mode_enabled else 'MESH_DATA')
        if _foldout(layout, scene, 'hair_ui_show_output_advanced', '詳細を表示'):
            adv=_section_box(layout, '出力詳細', 'MESH_DATA', '[OUTPUT]'); adv.prop(scene,'hair_flat_mesh_ring_segments')

class HGD_PT_cleanup(HGD_PT_base):
    bl_label = '整理・削除'
    bl_order = 7
    def draw(self, context):
        scene=context.scene; layout=self.layout; box=_section_box(layout, '整理・削除', 'TRASH', '[CLEANUP]')
        box.operator('hgd.toggle_final_edit_mode', text='最終編集モード解除' if scene.hair_final_edit_mode_enabled else '最終編集モード', icon='HIDE_OFF' if scene.hair_final_edit_mode_enabled else 'MESH_DATA')
        box.operator('hgd.clear_card_previews', text='CARDプレビュー削除', icon='TRASH'); box.operator('hgd.clear_flat_mesh_previews', text='扁平メッシュPreview削除', icon='TRASH'); box.operator('hgd.clear_warnings', text='警告削除', icon='TRASH'); box.operator('hgd.clear_placement_points', text='配置点削除', icon='TRASH'); box.operator('hgd.delete_hair_guides', text='ガイド削除', icon='TRASH'); box.operator('hgd.clear_all_generated', text='全生成物削除', icon='TRASH')
        box.operator('hgd.organize_curves_by_region', text='カーブ整理', icon='OUTLINER_COLLECTION'); box.operator('hgd.apply_curve_region_colors', text='部位別カラー反映', icon='MATERIAL')
        if _foldout(layout, scene, 'hair_ui_show_cleanup_advanced', '詳細を表示'):
            adv=_section_box(layout, '表示・保守', 'TRASH', '[CLEANUP]')
            adv.operator('hgd.toggle_in_front_generated_helpers', text='最前面表示切替', icon='HIDE_OFF')
            adv.operator('hgd.cleanup_card_control_empties', text='未使用CARD Control Emptyを削除', icon='TRASH')
            row=adv.row(align=True); row.operator('hgd.clear_shape_from_selected_curves', text='選択カーブ形状解除'); row.operator('hgd.clear_shape_from_all_curves', text='全カーブ形状解除')
            row=adv.row(align=True); row.operator('hgd.mirror_side_l_to_r', text='左側→右側へミラー'); row.operator('hgd.mirror_side_r_to_l', text='右側→左側へミラー')
            for p in ['hair_mirror_axis','hair_mirror_overwrite_existing','hair_mirror_copy_custom_properties','hair_show_guides_in_front']: adv.prop(scene,p)

class HGD_PT_validation(HGD_PT_base):
    bl_label = '検証'
    bl_order = 8
    def draw(self, context):
        scene=context.scene; box=_section_box(self.layout, '検証', 'ERROR', '[CHECK]')
        box.operator('hgd.check_root_clustering', text='根元密集チェック', icon='ERROR'); box.operator('hgd.clear_warnings', text='警告表示を削除', icon='TRASH')
        box.prop(scene, 'hair_root_cluster_threshold'); box.prop(scene, 'hair_warning_count')

class HGD_PT_advanced(HGD_PT_base):
    bl_label = '詳細設定'
    bl_order = 9
    bl_options = {'DEFAULT_CLOSED'}
    def draw(self, context):
        scene=context.scene; layout=self.layout
        if not _foldout(layout, scene, 'hair_ui_show_debug', '詳細を表示'):
            layout.label(text='低頻度・互換・デバッグ項目は非表示です。', icon='INFO'); return
        box=_section_box(layout, '互換Property / 保守', 'PREFERENCES', '[DEBUG]')
        for p in ['hair_curve_bevel_depth','hair_curve_root_radius','hair_curve_tip_radius','hair_curve_taper_strength','hair_curve_profile_type','hair_flat_profile_fallback_to_round','hair_curve_flat_width','hair_curve_flat_thickness','hair_flat_mesh_width','hair_flat_mesh_thickness','hair_flat_mesh_solidify_thickness','hair_card_width_root','hair_card_width_mid','hair_card_width_tip','hair_twist_bevel_depth','hair_show_display_mode_settings','hair_show_twist_settings','hair_show_advanced_curve_settings']: box.prop(scene,p)
        box.operator('hgd.lock_twist_visual_curves', text='ツイスト表示Curveを選択不可にする', icon='LOCKED')

class HGD_PT_help(HGD_PT_base):
    bl_label = 'ヘルプ'
    bl_order = 10
    bl_options = {'DEFAULT_CLOSED'}
    def draw(self, context):
        layout=self.layout; scene=context.scene
        if not scene.hair_show_inline_help:
            layout.label(text='ヘルプは非表示です。上部の「ヘルプを表示」をONにしてください。', icon='INFO'); return
        box=_section_box(layout, '推奨手順', 'CHECKMARK')
        for t in ['1. クイック操作またはセットアップで頭部登録','2. ガイド・配置点を生成','3. カーブ生成','4. カーブ編集 / CARD表示','5. 出力 / 検証 / 整理・削除']:
            box.label(text=t)

classes = (HGD_PT_inline_help_toggle, HGD_PT_quick_actions, HGD_PT_setup, HGD_PT_guides_points, HGD_PT_curve_generate, HGD_PT_curve_edit, HGD_PT_card_display, HGD_PT_output, HGD_PT_cleanup, HGD_PT_validation, HGD_PT_advanced, HGD_PT_help)

def register():
    for cls in classes: bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes): bpy.utils.unregister_class(cls)
