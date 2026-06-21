import bpy
from bpy.types import WorkSpaceTool
from . import utils


def _section_box(layout, title, icon='NONE', prefix=''):
    box = layout.box(); box.label(text=f"{prefix} {title}" if prefix else title, icon=icon); return box

def _foldout(layout, scene, prop_name, label):
    row=layout.row(); icon='TRIA_DOWN' if getattr(scene, prop_name) else 'TRIA_RIGHT'; row.prop(scene, prop_name, text=label, icon=icon, toggle=True); return getattr(scene, prop_name)

def _region_button_text_and_icon(region):
    state = utils.get_region_visibility_state(region)
    if state in {"VISIBLE", "MIXED"}:
        return "非表示にする", "HIDE_ON"
    return "表示する", "HIDE_OFF"


def _region_buttons(layout, label, region):
    text, icon = _region_button_text_and_icon(region)
    op=layout.operator('hgd.toggle_region_visibility', text=f'{label} {text}', icon=icon)
    op.region=region


def _all_region_buttons(layout, label='全領域'):
    text, icon = _region_button_text_and_icon('ALL')
    layout.operator('hgd.toggle_all_region_visibility', text=f'{label} {text}', icon=icon)

def _display_mode_buttons(layout, scene):
    layout.prop(scene, 'hair_curve_display_mode', text='表示モード')
    row=layout.row(align=True)
    for mode in ('CURVE','SOLID','CARD','FLAT'):
        if mode in {item.identifier for item in scene.bl_rna.properties['hair_curve_display_mode'].enum_items}:
            op=row.operator('hgd.apply_display_mode_to_selected_curves', text=mode); scene.hair_curve_display_mode=scene.hair_curve_display_mode

class HGD_PT_base(bpy.types.Panel):
    bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category='ヘアガイド'

class HGD_PT_quick_flow(HGD_PT_base):
    bl_label='HGD Quick Flow'; bl_order=0
    def draw(self, context):
        scene=context.scene; box=_section_box(self.layout,'Quick Flow','CHECKMARK')
        box.operator('hgd.set_target_head', text='1. 頭部登録', icon='CHECKMARK')
        box.operator('hgd.create_hair_guides', text='2. 基本ガイド生成', icon='OUTLINER_OB_CURVE')
        box.operator('hgd.generate_placement_points', text='3. 配置点生成', icon='MESH_UVSPHERE')
        box.operator('hgd.create_curve_from_points', text='4. Curve生成', icon='CURVE_BEZCURVE')
        box.prop(scene,'hair_curve_display_mode', text='5. 表示モード')
        box.operator('hgd.apply_display_mode_to_selected_curves', text='6. 選択対象へ表示モード適用', icon='RESTRICT_VIEW_OFF')
        row=box.row(align=True); row.operator('hgd.update_card_previews_from_curves', text='7. CARD Previewを現在設定で更新', icon='FILE_REFRESH'); row.operator('hgd.update_flat_mesh_previews_from_curves', text='Flat Preview更新', icon='MESH_DATA')
        row=box.row(align=True); row.operator('hgd.convert_selected_card_preview_to_mesh', text='8. CARD Mesh出力', icon='MESH_PLANE'); row.operator('hgd.export_flat_mesh_from_selected_curves', text='Flat Mesh出力', icon='MESH_DATA')
        box.operator('hgd.toggle_final_edit_mode', text='9. 最終編集モード OFF' if scene.hair_final_edit_mode_enabled else '9. 最終編集モード ON', icon='HIDE_OFF' if scene.hair_final_edit_mode_enabled else 'MESH_DATA')

class HGD_PT_setup(HGD_PT_base):
    bl_label='[SETUP] Setup'; bl_order=1
    def draw(self, context):
        scene=context.scene; box=_section_box(self.layout,'Setup','TOOL_SETTINGS','[SETUP]')
        box.prop(scene,'hair_target_head_object'); box.operator('hgd.set_target_head', text='頭部登録', icon='CHECKMARK')
        box.prop(scene,'hair_guide_scale'); box.prop(scene,'hair_guide_offset')

class HGD_PT_guides_points(HGD_PT_base):
    bl_label='[GUIDE] Guide / Points'; bl_order=2
    def draw(self, context):
        box=_section_box(self.layout,'Guide / Points','OUTLINER_OB_CURVE','[GUIDE]')
        box.operator('hgd.create_hair_guides', text='基本ガイド生成'); box.operator('hgd.generate_placement_points', text='配置点生成')
        _all_region_buttons(box)
        for args in [('頭頂部','Top'),('前髪','Front'),('側頭部','Side'),('左側','Side_L'),('右側','Side_R'),('後頭部上層','Back_Upper'),('後頭部中層','Back_Middle'),('襟足','Nape')]: _region_buttons(box,*args)
        box.operator('hgd.symmetrize_front_back_guides', text='前後ガイド左右対称化', icon='MOD_MIRROR')
        row=box.row(align=True); row.operator('hgd.mirror_side_guide_l_to_r', text='左→右'); row.operator('hgd.mirror_side_guide_r_to_l', text='右→左')

class HGD_PT_curve_shape(HGD_PT_base):
    bl_label='[CURVE] Curve Shape'; bl_order=3
    def draw(self, context):
        scene=context.scene; box=_section_box(self.layout,'Curve Shape','CURVE_BEZCURVE','[CURVE]')
        box.prop(scene,'hair_strand_generation_type'); box.operator('hgd.create_curve_from_points', text='Curve生成')
        box.prop(scene,'hair_curve_origin_to_reference_empty'); box.operator('hgd.move_selected_curve_origins_to_reference_empty', text='選択Curve原点を参照Emptyへ移動')
        box.label(text='参照EmptyがあるCurveは見た目を維持して原点をEmpty位置へ移動します。', icon='INFO')
        box.prop(scene,'hair_curve_length_cm', text='毛束長さ(cm)'); box.label(text='毛先長さは新規生成時のみ反映されます。', icon='INFO')
        for p in ['hair_curve_bevel_depth_cm','hair_curve_segment_count','hair_use_shared_taper','hair_taper_preset','hair_taper_root_radius','hair_taper_mid_radius','hair_taper_tip_radius','hair_curve_variation_enabled']:
            box.prop(scene,p)
        if _foldout(self.layout, scene, 'hair_ui_show_curve_advanced', 'ツイスト詳細 / 個体差詳細'):
            adv=_section_box(self.layout,'詳細','PREFERENCES','[CURVE]')
            for p in ['hair_twist_radius','hair_twist_turns','hair_twist_segments','hair_twist_phase','hair_twist_bevel_depth_cm','hair_twist_resolution','hair_twist_taper_strength','hair_curve_variation_seed','hair_curve_variation_randomize_seed_per_generation','hair_curve_root_jitter_ratio','hair_curve_mid_jitter_ratio','hair_curve_tip_jitter_ratio','hair_curve_length_variation']:
                adv.prop(scene,p)

class HGD_PT_display_mode(HGD_PT_base):
    bl_label='[DISPLAY] Display Mode'; bl_order=4
    def draw(self, context):
        scene=context.scene; box=_section_box(self.layout,'Display Mode','RESTRICT_VIEW_OFF','[DISPLAY]')
        box.prop(scene,'hair_curve_display_mode'); box.operator('hgd.apply_display_mode_to_selected_curves', text='選択対象へ適用'); box.operator('hgd.apply_display_mode_to_all_curves', text='全Curveへ適用')

class HGD_PT_card_flat_preview(HGD_PT_base):
    bl_label='[CARD] CARD / Flat Preview'; bl_order=5
    def draw(self, context):
        scene=context.scene; box=_section_box(self.layout,'CARD','MESH_PLANE','[CARD]')
        for p in ['hair_card_width_preset','hair_card_width_root_cm','hair_card_width_mid_cm','hair_card_width_tip_cm','hair_card_mid_position','hair_card_width_interpolation']: box.prop(scene,p)
        box.label(text='CARD Root/Mid/Tip幅とCARDサンプル数はFlat Mesh生成にも使用されます。', icon='INFO')
        box.operator('hgd.apply_card_width_preset'); box.operator('hgd.update_card_previews_from_curves', text='CARD Previewを現在設定で更新')
        flat=_section_box(self.layout,'Flat Preview','MESH_DATA','[CARD]'); flat.operator('hgd.update_flat_mesh_previews_from_curves', text='Flat Mesh Preview更新'); flat.operator('hgd.clear_flat_mesh_previews', text='Preview削除')
        ctrl=_section_box(self.layout,'CARD方向制御','EMPTY_SINGLE_ARROW','[CARD]')
        ctrl.operator('hgd.create_card_control_empty', text='共有CARD Control Empty作成/割当')
        ctrl.prop(scene,'hair_selected_card_control_empty', text='参照Empty')
        ctrl.label(text='Curve生成時、参照可能なCARD Control Emptyが存在する場合は自動で最新のEmptyを割り当てます。', icon='INFO')
        ctrl.label(text='特定Emptyを使いたい場合は「参照Empty」に指定してください。')
        ctrl.operator('hgd.load_card_control_empty_from_selected', text='選択Curveから参照Empty読み込み')
        ctrl.operator('hgd.assign_pointer_card_control_empty', text='参照Emptyを選択Curveへ割当')
        ctrl.operator('hgd.share_card_control_empty_to_selected_curves', text='参照Empty共有')
        ctrl.operator('hgd.clear_card_control_empty', text='参照Empty解除')
        ctrl.operator('hgd.select_shared_card_control_empty', text='参照Empty選択')

class HGD_PT_output_mesh(HGD_PT_base):
    bl_label='[OUTPUT] Output Mesh'; bl_order=6
    def draw(self, context):
        scene=context.scene; card=_section_box(self.layout,'CARD Mesh','MESH_PLANE','[OUTPUT]')
        card.operator('hgd.convert_selected_card_preview_to_mesh', text='選択CARD Mesh出力'); card.operator('hgd.convert_all_card_previews_to_mesh', text='全CARD Mesh出力')
        flat=_section_box(self.layout,'Flat Mesh','MESH_DATA','[OUTPUT]')
        flat.label(text='扁平メッシュの幅と分割数はCARD設定を使用します。', icon='INFO')
        flat.label(text='Root/Mid/Tipやサンプル数はCARD / Flat Preview側で調整してください。')
        for p in ['hair_flat_mesh_thickness_cm','hair_flat_mesh_ring_segments','hair_flat_mesh_mark_side_sharp','hair_flat_mesh_add_subdivision']: flat.prop(scene,p)
        flat.operator('hgd.export_flat_mesh_from_selected_curves', text='選択Flat Mesh出力'); flat.operator('hgd.create_flat_mesh_from_all_curves', text='全Flat Mesh出力')

class HGD_PT_final_edit(HGD_PT_base):
    bl_label='[FINAL] Final Edit'; bl_order=7
    def draw(self, context):
        scene=context.scene; box=_section_box(self.layout,'Final Edit','MESH_DATA','[FINAL]')
        box.operator('hgd.toggle_final_edit_mode', text='最終編集モード OFF' if scene.hair_final_edit_mode_enabled else '最終編集モード ON')
        box.label(text='ON: card_mesh / flat_meshのみ表示し、出力Meshを選択可能にします。')

class HGD_PT_cleanup_utility(HGD_PT_base):
    bl_label='[CLEANUP] Cleanup / Utility'; bl_order=8
    def draw(self, context):
        box=_section_box(self.layout,'Cleanup / Utility','TRASH','[CLEANUP]')
        for op,text in [('hgd.clear_card_previews','CARD Preview削除'),('hgd.clear_flat_mesh_previews','Flat Mesh Preview削除'),('hgd.clear_placement_points','配置点削除'),('hgd.delete_hair_guides','ガイド削除'),('hgd.clear_warnings','Warning削除'),('hgd.cleanup_card_control_empties','未使用CARD Control Empty削除'),('hgd.organize_curves_by_region','hair_guideへ整理')]: box.operator(op,text=text, icon='TRASH')
        box.operator('hgd.clear_all_generated', text='全生成物削除（確認あり）', icon='ERROR')

class HGD_PT_advanced(HGD_PT_base):
    bl_label='Advanced'; bl_order=9; bl_options={'DEFAULT_CLOSED'}
    def draw(self, context):
        scene=context.scene; box=_section_box(self.layout,'Advanced','PREFERENCES','[DEBUG]')
        box.label(text='Debug / 互換設定 / 旧仕様掃除 / 個別Empty作成')
        box.operator('hgd.create_card_control_empty_per_curve', text='個別Empty作成')
        box.operator('hgd.lock_twist_visual_curves', text='ツイスト表示Curveを選択不可')
        box.operator('hgd.toggle_in_front_generated_helpers', text='最前面表示切替')
        box.label(text='Seedランダム化: Curve Shapeの個体差詳細を開いて設定します。', icon='INFO')
        for p in ['hair_curve_bevel_depth','hair_curve_root_radius','hair_curve_tip_radius','hair_flat_profile_fallback_to_round','hair_card_auto_apply_to_new_curves','hair_card_auto_update_preview','hair_card_auto_select_edit_curve','hair_auto_assign_latest_card_control_empty']:
            box.prop(scene,p)

class HGD_MT_hair_guide_pie(bpy.types.Menu):
    bl_label='Hair Guide Pie'; bl_idname='HGD_MT_hair_guide_pie'
    def draw(self, context):
        pie=self.layout.menu_pie()
        pie.operator('hgd.edit_source_curve', text='編集Curveを開く', icon='CURVE_BEZCURVE')
        pie.operator('hgd.update_card_previews_from_curves', text='CARD Previewを現在設定で更新', icon='FILE_REFRESH')
        pie.operator('hgd.apply_display_mode_to_selected_curves', text='表示モード適用', icon='RESTRICT_VIEW_OFF')
        pie.operator('hgd.convert_selected_card_preview_to_mesh', text='Mesh出力', icon='MESH_DATA')
        pie.operator('hgd.toggle_final_edit_mode', text='最終編集モード', icon='MESH_DATA')
        pie.operator('hgd.create_card_control_empty', text='参照Empty作成/共有', icon='EMPTY_SINGLE_ARROW')
        pie.operator('hgd.clear_card_previews', text='Cleanup / Preview削除', icon='TRASH')
        pie.operator('hgd.update_flat_mesh_previews_from_curves', text='Flat Mesh Preview更新', icon='MESH_DATA')

class HGD_WST_hair_guide(WorkSpaceTool):
    bl_space_type='VIEW_3D'; bl_context_mode='OBJECT'; bl_idname='hgd.hair_guide_tool'; bl_label='Hair Guide'; bl_description='Hair Guide execution shortcuts'; bl_icon='ops.curve.draw'; bl_widget=None; bl_keymap=()
    def draw_settings(context, layout, tool):
        col=layout.column(align=True)
        col.operator('hgd.edit_source_curve', text='Select / Edit Curve')
        col.operator('hgd.create_curve_from_points', text='Create Curve')
        col.operator('hgd.update_card_previews_from_curves', text='Update CARD Preview with Current Settings')
        col.operator('hgd.convert_selected_card_preview_to_mesh', text='Output Mesh')
        col.operator('hgd.toggle_final_edit_mode', text='Final Edit Mode')

classes=(HGD_PT_quick_flow,HGD_PT_setup,HGD_PT_guides_points,HGD_PT_curve_shape,HGD_PT_display_mode,HGD_PT_card_flat_preview,HGD_PT_output_mesh,HGD_PT_final_edit,HGD_PT_cleanup_utility,HGD_PT_advanced,HGD_MT_hair_guide_pie)

def register():
    for cls in classes: bpy.utils.register_class(cls)
    try: bpy.utils.register_tool(HGD_WST_hair_guide, after={"builtin.select_box"}, group=True)
    except Exception as exc: print(f"WARNING: Hair Guide toolbar registration failed: {exc}")

def unregister():
    try: bpy.utils.unregister_tool(HGD_WST_hair_guide)
    except Exception: pass
    for cls in reversed(classes): bpy.utils.unregister_class(cls)
