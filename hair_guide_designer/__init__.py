bl_info = {
    "name": "Hair Guide Designer",
    "author": "地図ヶ原",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Hair Guide Designer",
    "description": "Guide-curve based helper tools for anime/VRC hair blockout and strip generation.",
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
