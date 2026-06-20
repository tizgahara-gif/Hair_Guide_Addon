import bpy

addon_keymaps = []


def _addon_preferences():
    addon = bpy.context.preferences.addons.get(__package__ or "hair_guide_designer")
    return addon.preferences if addon else None


def _warn_conflicts(km, key, ctrl, shift, alt):
    for item in km.keymap_items:
        if item.type == key and item.value == 'PRESS' and item.ctrl == ctrl and item.shift == shift and item.alt == alt:
            print(f"WARNING: Hair Guide Pie shortcut {key} ctrl={ctrl} shift={shift} alt={alt} may conflict with {item.idname}")


def register_keymaps():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return
    prefs = _addon_preferences()
    key = getattr(prefs, "hgd_pie_key", "J")
    ctrl = getattr(prefs, "hgd_pie_use_ctrl", False)
    shift = getattr(prefs, "hgd_pie_use_shift", False)
    alt = getattr(prefs, "hgd_pie_use_alt", True)
    for name in ("3D View", "Object Mode", "Curve"):
        km = kc.keymaps.new(name=name, space_type='VIEW_3D' if name == "3D View" else 'EMPTY')
        _warn_conflicts(km, key, ctrl, shift, alt)
        kmi = km.keymap_items.new("wm.call_menu_pie", type=key, value='PRESS', ctrl=ctrl, shift=shift, alt=alt)
        kmi.properties.name = "HGD_MT_hair_guide_pie"
        addon_keymaps.append((km, kmi))
    km = kc.keymaps.new(name="Object Mode", space_type="EMPTY")
    kmi = km.keymap_items.new("hgd.edit_source_curve", type="TAB", value="PRESS")
    addon_keymaps.append((km, kmi))


def unregister_keymaps():
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except ReferenceError:
            pass
    addon_keymaps.clear()
