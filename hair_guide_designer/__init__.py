bl_info = {
    "name": "Hair Guide Designer",
    "author": "地図ヶ原",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3Dビュー > サイドバー > ヘアガイド",
    "description": "アニメ調・VRC向け髪型設計を補助するガイド、配置点、カーブ毛束ツールです。",
    "category": "Object",
}

from . import properties, operators, ui

modules = (properties, operators, ui)

def register():
    for module in modules:
        module.register()

def unregister():
    for module in reversed(modules):
        module.unregister()

if __name__ == "__main__":
    register()
