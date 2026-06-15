import bpy


class HGD_PT_base(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Hair Guide'


class HGD_PT_setup(HGD_PT_base):
    bl_label = 'Setup'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column(align=True)
        col.prop(scene, 'hair_target_head_object')
        col.operator('hgd.set_target_head')
        col.operator('hgd.create_hair_guides')
        col.operator('hgd.delete_hair_guides')
        row = col.row(align=True)
        op = row.operator('hgd.show_hide_guides', text='Show Guides')
        op.hide = False
        op = row.operator('hgd.show_hide_guides', text='Hide Guides')
        op.hide = True
        col.prop(scene, 'hair_guide_scale')
        col.prop(scene, 'hair_guide_offset')


class HGD_PT_regions(HGD_PT_base):
    bl_label = 'Regions'

    def draw(self, context):
        col = self.layout.column(align=True)
        for text, region in (
            ('Show Front', 'Front'),
            ('Show Side', 'Side'),
            ('Show Back Upper', 'Back_Upper'),
            ('Show Back Middle', 'Back_Middle'),
            ('Show Nape', 'Nape'),
        ):
            op = col.operator('hgd.region_visibility', text=text)
            op.region = region
            op.action = 'SHOW'
        op = col.operator('hgd.region_visibility', text='Hide All Regions')
        op.region = 'ALL'
        op.action = 'HIDE'
        op = col.operator('hgd.region_visibility', text='Show All Regions')
        op.region = 'ALL'
        op.action = 'SHOW'


class HGD_PT_placement(HGD_PT_base):
    bl_label = 'Placement Points'

    def draw(self, context):
        scene = context.scene
        col = self.layout.column(align=True)
        col.operator('hgd.generate_placement_points')
        col.operator('hgd.clear_placement_points')
        col.prop(scene, 'hair_seed')
        col.prop(scene, 'hair_density')
        col.prop(scene, 'hair_symmetry_bias')
        col.prop(scene, 'hair_height_variation')
        col.prop(scene, 'hair_width_variation')
        col.prop(scene, 'hair_depth_variation')
        col.prop(scene, 'hair_size_variation')
        col.prop(scene, 'hair_length_variation')


class HGD_PT_curve_strand(HGD_PT_base):
    bl_label = 'Curve Strand'

    def draw(self, context):
        scene = context.scene
        col = self.layout.column(align=True)
        col.operator('hgd.create_curve_from_points')
        col.prop(scene, 'hair_strand_type')
        col.prop(scene, 'hair_curve_length')
        col.prop(scene, 'hair_curve_root_radius')
        col.prop(scene, 'hair_curve_tip_radius')
        col.prop(scene, 'hair_curve_bevel_depth')
        col.prop(scene, 'hair_curve_resolution')
        col.prop(scene, 'hair_curve_taper_strength')
        col.prop(scene, 'hair_curve_segment_count')


class HGD_PT_validation(HGD_PT_base):
    bl_label = 'Validation'

    def draw(self, context):
        scene = context.scene
        col = self.layout.column(align=True)
        col.operator('hgd.check_root_clustering')
        col.operator('hgd.clear_warnings')
        col.prop(scene, 'hair_root_cluster_threshold')
        col.prop(scene, 'hair_warning_count')


classes = (
    HGD_PT_setup,
    HGD_PT_regions,
    HGD_PT_placement,
    HGD_PT_curve_strand,
    HGD_PT_validation,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
