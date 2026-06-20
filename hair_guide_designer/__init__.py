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

from . import properties, operators, ui, preferences, keymap

modules = (properties, operators, ui, preferences)


def register():
    for module in modules:
        module.register()
    keymap.register_keymaps()

def unregister():
    keymap.unregister_keymaps()
    for module in reversed(modules):
        module.unregister()

if __name__ == "__main__":
    register()
