bl_info = {
    "name": "Hair Guide Designer",
    "author": "地図ヶ原",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3Dビュー > サイドバー > ヘアガイド",
    "description": "アニメ調・VRC向け髪型設計を補助するガイド、配置点、カーブ毛束ツールです。",
    "category": "Object",
}

import bpy
from bpy.props import IntProperty

from . import properties, operators, ui

modules = (properties, operators, ui)

addon_keymaps = []


def _register_keymaps():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return
    km = kc.keymaps.new(name="Object Mode", space_type="EMPTY")
    kmi = km.keymap_items.new("hgd.edit_source_curve", type="TAB", value="PRESS")
    addon_keymaps.append((km, kmi))


def _unregister_keymaps():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


class HGD_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__ or "hair_guide_designer"

    point_count_top: IntProperty(name="Top", default=5, min=0, max=5, description="頭頂部の配置点数")
    point_count_front: IntProperty(name="Front", default=7, min=0, max=64, description="前髪領域の配置点数")
    point_count_side_l: IntProperty(name="Side_L", default=4, min=0, max=64, description="左側頭部の配置点数")
    point_count_side_r: IntProperty(name="Side_R", default=4, min=0, max=64, description="右側頭部の配置点数")
    point_count_back_upper: IntProperty(name="Back_Upper", default=6, min=0, max=64, description="後頭部上層の配置点数")
    point_count_back_middle: IntProperty(name="Back_Middle", default=6, min=0, max=64, description="後頭部中層の配置点数")
    point_count_nape: IntProperty(name="Nape", default=5, min=0, max=64, description="襟足の配置点数")

    def draw(self, context):
        layout = self.layout
        layout.label(text="配置点数")
        layout.prop(self, "point_count_top")
        layout.prop(self, "point_count_front")
        layout.prop(self, "point_count_side_l")
        layout.prop(self, "point_count_side_r")
        layout.prop(self, "point_count_back_upper")
        layout.prop(self, "point_count_back_middle")
        layout.prop(self, "point_count_nape")

def register():
    bpy.utils.register_class(HGD_AddonPreferences)
    for module in modules:
        module.register()
    _register_keymaps()

def unregister():
    _unregister_keymaps()
    for module in reversed(modules):
        module.unregister()
    bpy.utils.unregister_class(HGD_AddonPreferences)

if __name__ == "__main__":
    register()
