import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty

KEY_ITEMS = tuple((chr(code), chr(code), f"Use {chr(code)} for the Hair Guide pie menu") for code in range(ord('A'), ord('Z') + 1))


class HGD_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__ or "hair_guide_designer"

    point_count_top: IntProperty(name="Top", default=5, min=0, max=5, description="頭頂部の配置点数")
    point_count_front: IntProperty(name="Front", default=7, min=0, max=64, description="前髪領域の配置点数")
    point_count_side_l: IntProperty(name="Side_L", default=4, min=0, max=64, description="左側頭部の配置点数")
    point_count_side_r: IntProperty(name="Side_R", default=4, min=0, max=64, description="右側頭部の配置点数")
    point_count_back_upper: IntProperty(name="Back_Upper", default=6, min=0, max=64, description="後頭部上層の配置点数")
    point_count_back_middle: IntProperty(name="Back_Middle", default=6, min=0, max=64, description="後頭部中層の配置点数")
    point_count_nape: IntProperty(name="Nape", default=5, min=0, max=64, description="襟足の配置点数")

    hgd_pie_key: EnumProperty(name="Pie Menu Key", items=KEY_ITEMS, default="J")
    hgd_pie_use_alt: BoolProperty(name="Alt", default=True)
    hgd_pie_use_shift: BoolProperty(name="Shift", default=False)
    hgd_pie_use_ctrl: BoolProperty(name="Ctrl", default=False)

    def draw(self, context):
        layout = self.layout
        key_box = layout.box()
        key_box.label(text="Hair Guide Pie Menu", icon='KEYINGSET')
        key_box.prop(self, "hgd_pie_key")
        row = key_box.row(align=True)
        row.prop(self, "hgd_pie_use_ctrl")
        row.prop(self, "hgd_pie_use_shift")
        row.prop(self, "hgd_pie_use_alt")
        key_box.operator("hgd.reload_keymaps", icon='FILE_REFRESH')

        layout.label(text="配置点数")
        for prop in ("point_count_top", "point_count_front", "point_count_side_l", "point_count_side_r", "point_count_back_upper", "point_count_back_middle", "point_count_nape"):
            layout.prop(self, prop)


classes = (HGD_AddonPreferences,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
