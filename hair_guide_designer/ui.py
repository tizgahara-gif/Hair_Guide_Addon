import bpy
from . import utils


def _count_generated(guide_type=None):
    return len(utils.generated_objects(guide_type))


def _draw_status(layout, scene):
    box = layout.box()
    box.label(text="Current Status:", icon='INFO')
    head = scene.hair_target_head_object
    if head and head.type == 'MESH':
        box.label(text=f"Target Head: {head.name}", icon='CHECKMARK')
    else:
        box.label(text="Target Head: Not Set", icon='ERROR')
        box.label(text="Select a head mesh first.")
    guide_objects = [obj for obj in utils.generated_objects() if obj.get("hair_guide_type") in {"guide", "region"}]
    basic_count = len([obj for obj in guide_objects if obj.get("hair_guide_level") == "basic"])
    detailed_count = len([obj for obj in guide_objects if obj.get("hair_guide_level") == "detailed"])
    point_count = _count_generated("placement_point")
    curve_count = _count_generated("curve")
    warning_count = _count_generated("warning")
    box.label(text=f"Basic Guides: {basic_count}", icon='OUTLINER_OB_CURVE')
    box.label(text=f"Detailed Guides: {detailed_count}", icon='OUTLINER_OB_CURVE')
    box.label(text=f"Placement Points: {point_count}", icon='MESH_UVSPHERE')
    box.label(text=f"Curves: {curve_count}", icon='OUTLINER_OB_CURVE')
    box.label(text=f"Warnings: {scene.hair_warning_count or warning_count}", icon='ERROR' if (scene.hair_warning_count or warning_count) else 'CHECKMARK')


def _region_buttons(layout, label, region, note):
    row = layout.row(align=True)
    op = row.operator('hgd.region_visibility', text=f"Show {label}", icon='HIDE_OFF')
    op.region = region
    op.action = 'SHOW'
    op = row.operator('hgd.region_visibility', text=f"Hide {label}", icon='HIDE_ON')
    op.region = region
    op.action = 'HIDE'
    layout.label(text=note, icon='INFO')


class HGD_PT_base(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Hair Guide'


class HGD_PT_quick_start(HGD_PT_base):
    bl_label = 'Hair Guide: Quick Start'
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Workflow:", icon='INFO')
        box.label(text="1. Select head mesh")
        box.label(text="2. Set Target Head")
        box.label(text="3. Create Basic Hair Guides")
        box.label(text="4. Adjust guides if needed")
        box.label(text="5. Generate Placement Points")
        box.label(text="6. Select points")
        box.label(text="7. Create Curve Strands")
        box.label(text="8. Check Root Clustering")
        _draw_status(layout, context.scene)


class HGD_PT_setup(HGD_PT_base):
    bl_label = 'Setup'
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Register the selected head mesh.", icon='INFO')
        layout.label(text="This add-on does not edit the mesh.")
        if not scene.hair_target_head_object:
            layout.label(text="No target head set.", icon='ERROR')
            layout.label(text="Select a head mesh first.")
        col = layout.column(align=True)
        col.prop(scene, 'hair_target_head_object')
        col.operator('hgd.set_target_head', text='Set Selected Mesh as Head', icon='CHECKMARK')
        layout.separator()
        layout.prop(scene, 'hair_guide_scale')
        layout.prop(scene, 'hair_guide_offset')


class HGD_PT_guide_lines(HGD_PT_base):
    bl_label = 'Guide Lines'
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        layout.label(text="Basic guides are intentionally minimal.", icon='INFO')
        layout.label(text="Hairline, side boundaries, back volume, nape, center.")
        row = layout.row(align=True)
        op = row.operator('hgd.show_hide_guides', text='Show Guide Lines', icon='HIDE_OFF')
        op.hide = False
        op = row.operator('hgd.show_hide_guides', text='Hide Guide Lines', icon='HIDE_ON')
        op.hide = True
        layout.operator('hgd.create_hair_guides', text='Regenerate Basic Guides', icon='OUTLINER_OB_CURVE')
        layout.operator('hgd.create_detailed_guides', text='Add Detailed Guide Lines', icon='OUTLINER_OB_CURVE')
        layout.label(text="Basic guides only; details are optional.")
        layout.operator('hgd.delete_hair_guides', text='Delete Guide Lines', icon='TRASH')
        layout.label(text="Deletes only generated guide objects.")
        layout.label(text="Head mesh is not deleted.")


class HGD_PT_regions(HGD_PT_base):
    bl_label = 'Regions'
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        layout.label(text="Toggle hair construction regions.", icon='INFO')
        _region_buttons(layout, "Front", "Front", "Bangs start from hairline, not forehead.")
        _region_buttons(layout, "Side", "Side", "Avoid excessive volume above ears.")
        _region_buttons(layout, "Side L", "Side_L", "Left side-only visibility.")
        _region_buttons(layout, "Side R", "Side_R", "Right side-only visibility.")
        _region_buttons(layout, "Back Upper", "Back_Upper", "Defines hair cap volume.")
        _region_buttons(layout, "Back Middle", "Back_Middle", "Main large strand roots.")
        _region_buttons(layout, "Nape", "Nape", "Avoid strands growing from neck.")
        row = layout.row(align=True)
        op = row.operator('hgd.region_visibility', text='Show All Regions', icon='HIDE_OFF')
        op.region = 'ALL'
        op.action = 'SHOW'
        op = row.operator('hgd.region_visibility', text='Hide All Regions', icon='HIDE_ON')
        op.region = 'ALL'
        op.action = 'HIDE'


class HGD_PT_placement(HGD_PT_base):
    bl_label = 'Placement Points'
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Suggested hair strand root positions.", icon='MESH_UVSPHERE')
        layout.label(text="Use them to avoid uniform roots.")
        if not scene.hair_target_head_object:
            layout.label(text="No target head set. Do Setup first.", icon='ERROR')
        if _count_generated("placement_point") == 0:
            layout.label(text="No placement points found.", icon='ERROR')
            layout.label(text="Click Generate Placement Points.")
        layout.operator('hgd.generate_placement_points', icon='MESH_UVSPHERE')
        layout.operator('hgd.clear_placement_points', icon='TRASH')
        layout.separator()
        layout.label(text="Seed: same value reproduces layout.", icon='INFO')
        layout.label(text="Symmetry Bias: high = balanced L/R.")
        layout.prop(scene, 'hair_seed')
        layout.prop(scene, 'hair_density')
        layout.prop(scene, 'hair_symmetry_bias')
        layout.prop(scene, 'hair_height_variation')
        layout.prop(scene, 'hair_width_variation')
        layout.prop(scene, 'hair_depth_variation')
        layout.prop(scene, 'hair_size_variation')
        layout.prop(scene, 'hair_length_variation')


class HGD_PT_curve_strand(HGD_PT_base):
    bl_label = 'Curve Strand'
    bl_order = 5

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Creates editable Bezier curve strands", icon='OUTLINER_OB_CURVE')
        layout.label(text="from selected placement points.")
        layout.label(text="Curves are not converted to mesh.")
        if _count_generated("placement_point") == 0:
            layout.label(text="No placement points found.", icon='ERROR')
        if _count_generated("curve") == 0:
            layout.label(text="No curve strands created yet.", icon='INFO')
        layout.operator('hgd.create_curve_from_points', text='Create Editable Curve Strands', icon='OUTLINER_OB_CURVE')
        layout.prop(scene, 'hair_strand_type')
        layout.prop(scene, 'hair_curve_length')
        layout.prop(scene, 'hair_curve_bevel_depth')
        layout.prop(scene, 'hair_curve_resolution')
        layout.prop(scene, 'hair_curve_segment_count')
        layout.label(text="Root/Tip Radius and Taper are stored", icon='INFO')
        layout.label(text="for future versions.")
        layout.prop(scene, 'hair_curve_root_radius')
        layout.prop(scene, 'hair_curve_tip_radius')
        layout.prop(scene, 'hair_curve_taper_strength')


class HGD_PT_curve_batch_adjust(HGD_PT_base):
    bl_label = 'Curve Batch Adjust'
    bl_order = 6

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Adjust selected generated curves", icon='OUTLINER_OB_CURVE')
        layout.label(text="after creating curve strands.")
        layout.label(text="Length Scale changes from root.", icon='INFO')
        layout.prop(scene, 'hair_batch_curve_length', text='Length Scale')
        layout.prop(scene, 'hair_batch_curve_bevel_depth')
        layout.prop(scene, 'hair_batch_curve_resolution')
        row = layout.row(align=True)
        op = row.operator('hgd.apply_curve_batch_settings', text='Apply To Selected Curves')
        op.target = 'SELECTED'
        op = row.operator('hgd.apply_curve_batch_settings', text='Apply To All Generated Curves')
        op.target = 'ALL'


class HGD_PT_curve_follow(HGD_PT_base):
    bl_label = 'Curve Follow'
    bl_order = 7

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Move curve roots back to source points.", icon='INFO')
        layout.label(text="Use after moving placement points.")
        layout.prop(scene, 'hair_follow_update_selected_only')
        layout.prop(scene, 'hair_follow_keep_tip_offset')
        if not scene.hair_follow_keep_tip_offset:
            layout.label(text="Keep Tip Offset OFF may deform the strand.", icon='ERROR')
        layout.operator('hgd.update_curve_roots_from_points', icon='OUTLINER_OB_CURVE')


class HGD_PT_side_mirror(HGD_PT_base):
    bl_label = 'Side Mirror'
    bl_order = 8

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Mirror selected Side_L or Side_R", icon='INFO')
        layout.label(text="points and curves across X axis.")
        layout.label(text="Selected side objects only.", icon='ERROR')
        layout.prop(scene, 'hair_mirror_axis')
        layout.label(text="MVP mirror axis is X only.")
        layout.prop(scene, 'hair_mirror_overwrite_existing')
        layout.prop(scene, 'hair_mirror_copy_custom_properties')
        row = layout.row(align=True)
        row.operator('hgd.mirror_side_l_to_r', text='Mirror Side_L to Side_R')
        row.operator('hgd.mirror_side_r_to_l', text='Mirror Side_R to Side_L')


class HGD_PT_validation(HGD_PT_base):
    bl_label = 'Validation'
    bl_order = 9

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Checks roots that are too close.", icon='INFO')
        layout.label(text="They may look like same-origin hair.")
        if _count_generated("placement_point") == 0:
            layout.label(text="No placement points found.", icon='ERROR')
            layout.label(text="Generate points before validation.")
        layout.operator('hgd.check_root_clustering', icon='ERROR')
        layout.operator('hgd.clear_warnings', icon='TRASH')
        layout.prop(scene, 'hair_root_cluster_threshold')
        layout.prop(scene, 'hair_warning_count')
        layout.label(text="Warning Count = too-close point pairs.", icon='INFO')
        layout.label(text="Red = roots too close.")
        layout.label(text="Set Viewport Color to Object.")


class HGD_PT_display_cleanup(HGD_PT_base):
    bl_label = 'Display / Cleanup'
    bl_order = 10

    def draw(self, context):
        layout = self.layout
        layout.label(text="Display and cleanup generated objects.", icon='INFO')
        row = layout.row(align=True)
        op = row.operator('hgd.show_hide_guides', text='Show Guide Lines', icon='HIDE_OFF')
        op.hide = False
        op = row.operator('hgd.show_hide_guides', text='Hide Guide Lines', icon='HIDE_ON')
        op.hide = True
        row = layout.row(align=True)
        op = row.operator('hgd.region_visibility', text='Show All Regions', icon='HIDE_OFF')
        op.region = 'ALL'
        op.action = 'SHOW'
        op = row.operator('hgd.region_visibility', text='Hide All Regions', icon='HIDE_ON')
        op.region = 'ALL'
        op.action = 'HIDE'
        layout.separator()
        layout.label(text="Cleanup affects only HairGuideSystem.", icon='INFO')
        layout.operator('hgd.clear_warnings', icon='TRASH')
        layout.operator('hgd.clear_placement_points', icon='TRASH')
        layout.operator('hgd.delete_hair_guides', text='Delete Guide Lines', icon='TRASH')
        layout.label(text="Clear All deletes generated guides,")
        layout.label(text="points, curves, and warnings only.")
        layout.label(text="Target head is not deleted.")
        layout.operator('hgd.clear_all_generated', icon='TRASH')


class HGD_PT_help(HGD_PT_base):
    bl_label = 'Help'
    bl_order = 11
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="What this add-on does:", icon='INFO')
        box.label(text="- Shows stylized hair guide lines.")
        box.label(text="- Suggests strand root points.")
        box.label(text="- Creates editable curve strands.")
        box.label(text="- Checks root clustering.")
        box = layout.box()
        box.label(text="What this add-on does NOT do:", icon='ERROR')
        box.label(text="- No automatic final hair generation.")
        box.label(text="- Does not edit the head mesh.")
        box.label(text="- Does not convert curves to mesh.")
        box.label(text="- No Unity or PhysBone setup.")
        box = layout.box()
        box.label(text="Recommended workflow:", icon='CHECKMARK')
        box.label(text="1. Use guides as visual references.")
        box.label(text="2. Adjust points manually if needed.")
        box.label(text="3. Generate curve strands.")
        box.label(text="4. Edit curves by hand.")
        box.label(text="5. Treat warnings as hints.")


classes = (
    HGD_PT_quick_start,
    HGD_PT_setup,
    HGD_PT_guide_lines,
    HGD_PT_regions,
    HGD_PT_placement,
    HGD_PT_curve_strand,
    HGD_PT_curve_batch_adjust,
    HGD_PT_curve_follow,
    HGD_PT_side_mirror,
    HGD_PT_validation,
    HGD_PT_display_cleanup,
    HGD_PT_help,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
