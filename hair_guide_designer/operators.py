import math
import random
import mathutils
import bpy
from bpy.props import EnumProperty, StringProperty
from . import utils


HAIR_CURVE_NAME_PREFIXES = {
    "Top": "HAIR_TOP",
    "Front": "HAIR_FRONT",
    "Side_L": "HAIR_SIDE_L",
    "Side_R": "HAIR_SIDE_R",
    "Back_Upper": "HAIR_BACK_UPPER",
    "Back_Middle": "HAIR_BACK_MIDDLE",
    "Nape": "HAIR_NAPE",
}
TOP_POINT_OFFSET = 0.01
BACK_UPPER_TO_MIDDLE_BLEND = 0.65
BACK_MIDDLE_HEIGHT_RATIO = 0.55
BACK_UPPER_TO_TOP_BLEND = 0.35
BACK_MIDDLE_TO_NAPE_BLEND = 0.30
BACK_LAYER_OUTWARD_OFFSET_RATIO = 0.02


def cm_to_m(value):
    return float(value) * 0.01


def m_to_cm(value):
    return float(value) * 100.0




def _addon_preferences(context):
    addon = context.preferences.addons.get(__package__ or "hair_guide_designer")
    return addon.preferences if addon else None

def _variation_seed_settings(scene):
    prefs = _addon_preferences(bpy.context)
    if prefs:
        return (
            int(getattr(prefs, "hair_curve_variation_seed", getattr(scene, "hair_curve_variation_seed", 1))),
            bool(getattr(prefs, "hair_curve_variation_randomize_seed_per_generation", getattr(scene, "hair_curve_variation_randomize_seed_per_generation", False))),
        )
    return int(getattr(scene, "hair_curve_variation_seed", 1)), bool(getattr(scene, "hair_curve_variation_randomize_seed_per_generation", False))

def require_head(context, operator):
    head = context.scene.hair_target_head_object
    if not head or head.type != "MESH":
        operator.report({'WARNING'}, "頭部が未設定です。メッシュを選択して「選択メッシュを頭部として登録」を押してください。")
        return None
    return head


WORK_MODE_LOCK_EDITABLE_TYPES = {"guide", "region", "placement_point", "warning", "curve", "twist_control", "card_preview", "flat_mesh_preview", "card_control_empty"}
WORK_MODE_LOCK_PREV_KEY = "hgd_prev_hide_select"

CARD_WIDTH_PRESETS = {
    "UNIFORM": (6.0, 6.0, 6.0),
    "STANDARD": (8.0, 6.0, 2.0),
    "SHARP_TIP": (7.0, 4.0, 0.3),
    "VOLUME": (12.0, 10.0, 4.0),
}
CARD_WIDTH_PRESET_LABELS = {
    "UNIFORM": "均一カード",
    "STANDARD": "標準テーパー",
    "SHARP_TIP": "シャープ毛先",
    "VOLUME": "ボリューム毛束",
    "CUSTOM": "カスタム",
}

CARD_SELECTION_REDIRECT_TYPES = {"card_preview", "flat_mesh_preview", "card_mesh", "flat_mesh"}


def _sync_card_width_preset_to_scene(scene):
    preset = scene.hair_card_width_preset
    if preset == "CUSTOM":
        return
    values = CARD_WIDTH_PRESETS.get(preset)
    if not values:
        return
    root, mid, tip = values
    scene.hair_card_width_root_cm = root
    scene.hair_card_width_mid_cm = mid
    scene.hair_card_width_tip_cm = tip


def _is_card_control_empty(obj):
    return bool(obj is not None and obj.type == 'EMPTY' and obj.get("hair_guide_type") == "card_control_empty")


def _next_card_control_empty_index():
    current = 0
    for obj in bpy.data.objects:
        if _is_card_control_empty(obj):
            current = max(current, int(obj.get("hair_card_control_created_index", 0)))
    return current + 1


def _ensure_card_control_empty_index(empty):
    if _is_card_control_empty(empty) and "hair_card_control_created_index" not in empty:
        empty["hair_card_control_created_index"] = _next_card_control_empty_index()


def _latest_card_control_empty(context):
    scene = context.scene
    selected_empty = getattr(scene, "hair_selected_card_control_empty", None)
    if _is_card_control_empty(selected_empty):
        return selected_empty

    empties = [obj for obj in bpy.data.objects if _is_card_control_empty(obj)]
    if not empties:
        return None

    empties.sort(
        key=lambda obj: int(obj.get("hair_card_control_created_index", 0)),
        reverse=True,
    )
    return empties[0]


def _assign_latest_card_control_empty_if_available(context, curve_obj):
    if not getattr(context.scene, "hair_auto_assign_latest_card_control_empty", True):
        return False
    empty = _latest_card_control_empty(context)
    if not empty:
        return False

    curve_obj["hair_card_control_empty"] = empty.name
    return True





def _curve_first_point_world(obj):
    """Return the first Bezier point world coordinate for a Curve object."""
    if not obj or obj.type != "CURVE" or not obj.data:
        return None
    for spline in obj.data.splines:
        if spline.type == "BEZIER" and spline.bezier_points:
            return obj.matrix_world @ spline.bezier_points[0].co
    return None


def _restore_curve_root_world(obj, target_world):
    """Translate the whole Curve object so its first Bezier point matches target_world."""
    current_root_world = _curve_first_point_world(obj)
    if current_root_world is None:
        return False
    target_world = mathutils.Vector(target_world)
    delta = target_world - current_root_world
    if delta.length < 1e-8:
        return True
    matrix = obj.matrix_world.copy()
    matrix.translation = matrix.translation + delta
    obj.matrix_world = matrix
    obj.update_tag(refresh={'OBJECT', 'DATA'})
    return True

def _reference_empty_for_curve(curve_obj):
    empty_name = curve_obj.get("hair_card_control_empty", "") if curve_obj else ""
    empty = bpy.data.objects.get(empty_name) if empty_name else None
    if _is_card_control_empty(empty):
        return empty
    return None


def _move_curve_origin_to_world_position_keep_shape(curve_obj, new_origin_world):
    """Move only the Curve object origin while preserving its world-space shape."""
    if not curve_obj or curve_obj.type != "CURVE":
        return False

    old_matrix = curve_obj.matrix_world.copy()
    old_origin_world = old_matrix.translation.copy()
    new_origin_world = mathutils.Vector(new_origin_world)
    delta_world = new_origin_world - old_origin_world

    if delta_world.length < 1e-8:
        return True

    new_matrix = old_matrix.copy()
    new_matrix.translation = new_origin_world
    curve_obj.matrix_world = new_matrix

    delta_local = curve_obj.matrix_world.inverted().to_3x3() @ delta_world

    for spline in curve_obj.data.splines:
        if spline.type == "BEZIER":
            for bp in spline.bezier_points:
                bp.co -= delta_local
                bp.handle_left -= delta_local
                bp.handle_right -= delta_local
        elif spline.type in {"POLY", "NURBS"}:
            for point in spline.points:
                point.co.x -= delta_local.x
                point.co.y -= delta_local.y
                point.co.z -= delta_local.z

    curve_obj.data.update_tag()
    curve_obj.update_tag(refresh={'OBJECT', 'DATA'})
    return True


def _move_curve_origin_to_reference_empty_if_enabled(context, curve_obj):
    if not getattr(context.scene, "hair_curve_origin_to_reference_empty", True):
        return False
    empty = _reference_empty_for_curve(curve_obj)
    if not empty:
        return False
    return _move_curve_origin_to_world_position_keep_shape(curve_obj, empty.matrix_world.translation)

def _is_in_hair_guide_collection(obj):
    root = bpy.data.collections.get(utils.ROOT)
    return bool(root and obj in utils.collection_objects_recursive(root))


def _is_work_mode_lock_editable(obj):
    if not obj or not _is_in_hair_guide_collection(obj):
        return False
    return obj.get("hair_guide_type") in WORK_MODE_LOCK_EDITABLE_TYPES


def _save_prev_hide_select(obj):
    if WORK_MODE_LOCK_PREV_KEY not in obj:
        obj[WORK_MODE_LOCK_PREV_KEY] = bool(obj.hide_select)


def _apply_work_mode_lock_to_object(context, obj):
    scene = context.scene
    if not scene.hair_work_mode_lock_enabled or not obj:
        return
    _save_prev_hide_select(obj)
    obj.hide_select = not _is_work_mode_lock_editable(obj)
    if obj.get("hair_guide_type") == "twist_strand":
        obj.hide_select = True


def _apply_work_mode_lock_to_all_objects(context):
    if not context.scene.hair_work_mode_lock_enabled:
        return
    for obj in context.scene.objects:
        _apply_work_mode_lock_to_object(context, obj)


def _sync_work_mode_lock(context):
    if context.scene.hair_work_mode_lock_enabled:
        _apply_work_mode_lock_to_all_objects(context)
    else:
        _restore_work_mode_lock(context)


def _restore_work_mode_lock(context):
    for obj in context.scene.objects:
        if WORK_MODE_LOCK_PREV_KEY in obj:
            obj.hide_select = bool(obj[WORK_MODE_LOCK_PREV_KEY])
            del obj[WORK_MODE_LOCK_PREV_KEY]


class HGD_OT_apply_work_mode_lock(bpy.types.Operator):
    bl_idname = "hgd.apply_work_mode_lock"
    bl_label = "作業集中モードを反映"
    bl_description = "作業集中モードのON/OFFを現在のオブジェクト選択可否へ反映します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _sync_work_mode_lock(context)
        if context.scene.hair_work_mode_lock_enabled:
            self.report({'INFO'}, "作業集中モードを有効化し、hair_guide外のオブジェクトを選択不可にしました。")
        else:
            self.report({'INFO'}, "作業集中モードを解除し、選択可否を復元しました。")
        return {'FINISHED'}


class HGD_OT_toggle_work_mode_lock(bpy.types.Operator):
    bl_idname = "hgd.toggle_work_mode_lock"
    bl_label = "作業ロックを切り替え"
    bl_description = "Hair Guide編集対象以外を一時的に選択不可にします"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.hair_work_mode_lock_enabled = not scene.hair_work_mode_lock_enabled
        _sync_work_mode_lock(context)
        if scene.hair_work_mode_lock_enabled:
            self.report({'INFO'}, "Hair Guide作業ロックを有効化しました。他オブジェクトは選択不可です。")
        else:
            self.report({'INFO'}, "Hair Guide作業ロックを解除し、選択状態を復元しました。")
        return {'FINISHED'}



FINAL_EDIT_VISIBLE_TYPES = {"card_mesh", "flat_mesh"}
FINAL_EDIT_HIDE_TYPES = {
    "guide",
    "region",
    "placement_point",
    "curve",
    "twist_control",
    "twist_strand",
    "card_preview",
    "flat_mesh_preview",
    "card_control_empty",
    "warning",
    "taper_object",
    "profile_object",
}
FINAL_EDIT_PREV_HIDE_VIEWPORT_KEY = "hgd_prev_hide_viewport_final"
FINAL_EDIT_PREV_HIDE_SELECT_KEY = "hgd_prev_hide_select_final"


def _generated_output_meshes():
    return [
        obj for obj in bpy.data.objects
        if obj.get("hair_guide_type", "") in FINAL_EDIT_VISIBLE_TYPES
    ]


def _restore_final_edit_mode_visibility():
    for obj in bpy.data.objects:
        if FINAL_EDIT_PREV_HIDE_VIEWPORT_KEY in obj:
            obj.hide_viewport = bool(obj[FINAL_EDIT_PREV_HIDE_VIEWPORT_KEY])
            del obj[FINAL_EDIT_PREV_HIDE_VIEWPORT_KEY]
        if FINAL_EDIT_PREV_HIDE_SELECT_KEY in obj:
            obj.hide_select = bool(obj[FINAL_EDIT_PREV_HIDE_SELECT_KEY])
            del obj[FINAL_EDIT_PREV_HIDE_SELECT_KEY]


class HGD_OT_toggle_final_edit_mode(bpy.types.Operator):
    bl_idname = "hgd.toggle_final_edit_mode"
    bl_label = "最終編集モード切替"
    bl_description = "出力Meshのみ表示し、ガイド・配置点・Curve・Preview・Emptyを非表示にします"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if scene.hair_final_edit_mode_enabled:
            scene.hair_final_edit_mode_enabled = False
            _restore_final_edit_mode_visibility()
            self.report({'INFO'}, "最終編集モードを解除しました。")
            return {'FINISHED'}

        output_meshes = _generated_output_meshes()
        if not output_meshes:
            scene.hair_final_edit_mode_enabled = False
            self.report({'WARNING'}, "出力Meshがありません。先にCARD Meshまたは扁平Meshを出力してください。")
            return {'CANCELLED'}

        scene.hair_final_edit_mode_enabled = True
        for obj in bpy.data.objects:
            guide_type = obj.get("hair_guide_type", "")
            if not guide_type:
                continue
            if FINAL_EDIT_PREV_HIDE_VIEWPORT_KEY not in obj:
                obj[FINAL_EDIT_PREV_HIDE_VIEWPORT_KEY] = bool(obj.hide_viewport)
            if FINAL_EDIT_PREV_HIDE_SELECT_KEY not in obj:
                obj[FINAL_EDIT_PREV_HIDE_SELECT_KEY] = bool(obj.hide_select)

            if guide_type in FINAL_EDIT_VISIBLE_TYPES:
                obj.hide_viewport = False
                obj.hide_select = False
            elif guide_type in FINAL_EDIT_HIDE_TYPES:
                obj.hide_viewport = True
                obj.hide_select = True

        for obj in context.selected_objects:
            obj.select_set(False)
        active_obj = None
        for obj in output_meshes:
            obj.select_set(True)
            if active_obj is None:
                active_obj = obj
        if active_obj is not None:
            context.view_layer.objects.active = active_obj

        self.report({'INFO'}, "最終編集モードを有効化しました。出力Meshのみ表示します。")
        return {'FINISHED'}



FINISH_WORK_DELETE_TYPES = {
    "guide",
    "region",
    "placement_point",
    "curve",
    "twist_control",
    "twist_strand",
    "card_preview",
    "flat_mesh_preview",
    "card_control_empty",
    "warning",
    "taper_object",
    "profile_object",
    "mirror_empty",
}
FINISH_WORK_OUTPUT_TYPES = {"card_mesh", "flat_mesh"}
FINISH_WORK_CLEANUP_COLLECTIONS = {
    "00_Guides",
    "01_PlacementPoints",
    "02_Curves",
    "03_Previews",
    "05_Empties",
    "06_Warnings",
    "99_Internal",
}


def _unlink_empty_child_collection(parent, collection):
    if collection.name == utils.ROOT or collection.name == "04_Outputs":
        return False
    if collection.objects or collection.children:
        return False
    try:
        parent.children.unlink(collection)
    except RuntimeError:
        return False
    if not collection.users:
        bpy.data.collections.remove(collection)
    return True


def _remove_empty_finish_work_collections(parent):
    removed = 0
    for child in list(parent.children):
        removed += _remove_empty_finish_work_collections(child)
        if child.name in FINISH_WORK_CLEANUP_COLLECTIONS:
            removed += int(_unlink_empty_child_collection(parent, child))
    return removed


class HGD_OT_finish_hair_guide_work(bpy.types.Operator):
    bl_idname = "hgd.finish_hair_guide_work"
    bl_label = "作業終了：出力Meshのみ残す"
    bl_description = "ガイド・配置点・Curve・Preview・Empty・Warning・内部Objectを削除し、出力Meshのみ残します。"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        root = bpy.data.collections.get(utils.ROOT)
        if not root:
            self.report({'WARNING'}, "出力Meshがありません。先にCARD MeshまたはFlat Meshを出力してください。")
            return {'CANCELLED'}

        root_objects = utils.collection_objects_recursive(root)
        output_meshes = [
            obj for obj in root_objects
            if obj.get("hair_guide_type", "") in FINISH_WORK_OUTPUT_TYPES
        ]
        if not output_meshes:
            self.report({'WARNING'}, "出力Meshがありません。先にCARD MeshまたはFlat Meshを出力してください。")
            return {'CANCELLED'}

        if getattr(context.object, "mode", "OBJECT") != "OBJECT":
            bpy.ops.object.mode_set(mode='OBJECT')

        for obj in list(context.selected_objects):
            obj.select_set(False)

        deleted = 0
        for obj in list(root_objects):
            if obj.get("hair_guide_type", "") in FINISH_WORK_DELETE_TYPES:
                bpy.data.objects.remove(obj, do_unlink=True)
                deleted += 1

        removed_collections = _remove_empty_finish_work_collections(root)
        context.scene.hair_final_edit_mode_enabled = False
        if hasattr(context.scene, "hair_warning_count"):
            context.scene.hair_warning_count = 0

        active_obj = None
        for output in output_meshes:
            if output.name not in bpy.data.objects:
                continue
            output.hide_viewport = False
            output.hide_select = False
            output.select_set(True)
            if active_obj is None:
                active_obj = output
        if active_obj is not None:
            context.view_layer.objects.active = active_obj

        self.report({'INFO'}, f"作業用オブジェクトを{deleted}個削除し、出力Meshのみ残しました。空Collection削除: {removed_collections}")
        return {'FINISHED'}

class HGD_OT_set_target_head(bpy.types.Operator):
    bl_idname = "hgd.set_target_head"
    bl_label = "選択メッシュを頭部として登録"
    bl_description = "選択中のメッシュを頭部として登録します。メッシュ自体は変更しません"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != "MESH":
            self.report({'WARNING'}, "メッシュが選択されていません。頭部メッシュを選択して登録してください。")
            return {'CANCELLED'}
        context.scene.hair_target_head_object = obj
        self.report({'INFO'}, f"頭部を登録しました: {obj.name}")
        return {'FINISHED'}


BASIC_GUIDE_NAMES = {
    "HAIR_GUIDE_Hairline",
    "HAIR_GUIDE_SideBoundary_L",
    "HAIR_GUIDE_SideBoundary_R",
    "HAIR_GUIDE_BackUpper",
    "HAIR_GUIDE_BackMiddle",
    "HAIR_GUIDE_Nape",
    "HAIR_GUIDE_Center",
}

REGION_VISIBILITY_ITEMS = [
    ("Top", "頭頂部", "頭頂部の表示切替"),
    ("Front", "前髪", "前髪領域"),
    ("Side", "側頭部", "左右の側頭部をまとめた領域"),
    ("Side_L", "左側頭部", "左側頭部"),
    ("Side_R", "右側頭部", "右側頭部"),
    ("Back_Upper", "後頭部上層", "髪全体のボリューム領域"),
    ("Back_Middle", "後頭部中層", "大きな毛束を配置する領域"),
    ("Nape", "襟足", "首へ向かって落ちる短い毛束領域"),
    ("ALL", "すべて", "すべての領域"),
]


def _remove_named_generated_guides(names):
    removed = 0
    for name in names:
        removed += utils.remove_object_family_by_base_name(name)
    return removed


def _remove_detailed_guides():
    removed = 0
    for obj in list(utils.generated_objects()):
        if obj.get("hair_guide_level") == "detailed" and obj.get("hair_guide_type") in {"guide", "region"}:
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    return removed


class HGD_OT_create_hair_guides(bpy.types.Operator):
    bl_idname = "hgd.create_hair_guides"
    bl_label = "基本ガイドを生成"
    bl_description = "生え際、サイド境界、後頭部専用、襟足、正中線の基本ガイドを生成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            head = require_head(context, self)
            if not head:
                return {'CANCELLED'}
            _, collections = utils.ensure_system()
            guides = collections[utils.GUIDES]
            removed = _remove_named_generated_guides(BASIC_GUIDE_NAMES)
            scene = context.scene
            min_v, max_v, center, size = utils.head_bounds(head)
            scale = scene.hair_guide_scale
            offset = scene.hair_guide_offset
            rx = size.x * 0.5 * scale + offset
            ry = size.y * 0.5 * scale + offset
            top = max_v.z + offset
            hairline_z = min_v.z + size.z * 0.66
            side_back_z = min_v.z + size.z * 0.58
            nape_z = min_v.z + size.z * 0.18
            front_surface = min_v.y
            front_out = front_surface - max(scene.hair_guide_offset, size.y * 0.04)
            back_surface = max_v.y
            back_out = back_surface + max(scene.hair_guide_offset, size.y * 0.05)

            hairline_points = [
                mathutils.Vector((center.x - rx * 0.58, front_surface - size.y * 0.015, hairline_z - size.z * 0.015)),
                mathutils.Vector((center.x - rx * 0.28, front_out, hairline_z + size.z * 0.025)),
                mathutils.Vector((center.x, front_out - size.y * 0.015, hairline_z + size.z * 0.04)),
                mathutils.Vector((center.x + rx * 0.28, front_out, hairline_z + size.z * 0.025)),
                mathutils.Vector((center.x + rx * 0.58, front_surface - size.y * 0.015, hairline_z - size.z * 0.015)),
            ]
            nape_points = [
                mathutils.Vector((center.x - rx * 0.35, back_surface + size.y * 0.015, nape_z)),
                mathutils.Vector((center.x, back_out, nape_z - size.z * 0.03)),
                mathutils.Vector((center.x + rx * 0.35, back_surface + size.y * 0.015, nape_z)),
            ]
            back_upper_z = top * (1.0 - 0.38) + nape_z * 0.38
            back_middle_z = top * (1.0 - 0.62) + nape_z * 0.62
            back_upper_points = [
                mathutils.Vector((center.x - size.x * 0.35, back_surface + size.y * 0.02, back_upper_z - size.z * 0.01)),
                mathutils.Vector((center.x, back_out + size.y * 0.015, back_upper_z + size.z * 0.025)),
                mathutils.Vector((center.x + size.x * 0.35, back_surface + size.y * 0.02, back_upper_z - size.z * 0.01)),
            ]
            back_middle_points = [
                mathutils.Vector((center.x - size.x * 0.35, back_surface + size.y * 0.02, back_middle_z - size.z * 0.01)),
                mathutils.Vector((center.x, back_out + size.y * 0.015, back_middle_z + size.z * 0.015)),
                mathutils.Vector((center.x + size.x * 0.35, back_surface + size.y * 0.02, back_middle_z - size.z * 0.01)),
            ]

            guide_specs = [
                ("HAIR_GUIDE_Hairline", hairline_points, "Front"),
                ("HAIR_GUIDE_SideBoundary_L", [mathutils.Vector((center.x - rx * 0.92, front_out + size.y * 0.12, hairline_z - size.z * 0.02)), mathutils.Vector((center.x - rx * 0.98, center.y, hairline_z - size.z * 0.12)), mathutils.Vector((center.x - rx * 0.82, back_out - size.y * 0.16, side_back_z + size.z * 0.02))], "Side"),
                ("HAIR_GUIDE_SideBoundary_R", [mathutils.Vector((center.x + rx * 0.92, front_out + size.y * 0.12, hairline_z - size.z * 0.02)), mathutils.Vector((center.x + rx * 0.98, center.y, hairline_z - size.z * 0.12)), mathutils.Vector((center.x + rx * 0.82, back_out - size.y * 0.16, side_back_z + size.z * 0.02))], "Side"),
                ("HAIR_GUIDE_BackUpper", back_upper_points, "Back_Upper"),
                ("HAIR_GUIDE_BackMiddle", back_middle_points, "Back_Middle"),
                ("HAIR_GUIDE_Nape", nape_points, "Nape"),
                ("HAIR_GUIDE_Center", [mathutils.Vector((center.x, center.y, top)), mathutils.Vector((center.x, center.y, nape_z))], "Back_Middle"),
            ]
            for name, points, region in guide_specs:
                obj = utils.make_curve(name, points, guides, region, "guide", scene, bevel=0.004, origin_mode="CENTER")
                obj["hair_guide_level"] = "basic"
            _apply_work_mode_lock_to_all_objects(context)
            self.report({'INFO'}, f"基本ガイドを{len(guide_specs)}個生成しました（古い基本ガイド{removed}個を削除）。")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"基本ガイドの生成に失敗しました: {exc}")
            return {'CANCELLED'}


class HGD_OT_create_detailed_guides(bpy.types.Operator):
    bl_idname = "hgd.create_detailed_guides"
    bl_label = "未登録詳細ガイド"
    bl_description = "未登録の補助参照線生成オペレーターです"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            head = require_head(context, self)
            if not head:
                return {'CANCELLED'}
            _, collections = utils.ensure_system()
            guides = collections[utils.GUIDES]
            regions = collections[utils.REGIONS]
            scene = context.scene
            removed = _remove_detailed_guides()
            min_v, max_v, center, size = utils.head_bounds(head)
            scale = scene.hair_guide_scale
            offset = scene.hair_guide_offset
            rx = size.x * 0.5 * scale + offset
            ry = size.y * 0.5 * scale + offset
            top = max_v.z + offset
            hairline_z = min_v.z + size.z * 0.66
            hachi_z = min_v.z + size.z * 0.78
            ear_z = min_v.z + size.z * 0.48
            occ_z = min_v.z + size.z * 0.56
            nape_z = min_v.z + size.z * 0.18
            front_y = min_v.y - offset
            back_y = max_v.y + offset
            detailed_specs = [
                ("HAIR_GUIDE_Top", [center + mathutils.Vector((-rx * 0.45, 0, top-center.z)), center + mathutils.Vector((0, 0, top + size.z*0.04-center.z)), center + mathutils.Vector((rx * 0.45, 0, top-center.z))], "Back_Upper"),
                ("HAIR_GUIDE_Hachi", utils.make_arc_points(center, rx, ry, hachi_z, 0.0, 6.28, 9), "Back_Upper"),
                ("HAIR_GUIDE_Ear_Upper", [mathutils.Vector((center.x - rx, center.y, ear_z)), mathutils.Vector((center.x + rx, center.y, ear_z))], "Side"),
                ("HAIR_GUIDE_Ear_Back", [mathutils.Vector((center.x - rx, back_y, ear_z)), mathutils.Vector((center.x + rx, back_y, ear_z))], "Side"),
                ("HAIR_GUIDE_Occipital", utils.make_arc_points(center, rx * 0.75, ry * 0.65, occ_z, 0.15, 3.0, 5), "Back_Middle"),
            ]
            for name, points, region in detailed_specs:
                obj = utils.make_curve(name, points, guides, region, "guide", scene, bevel=0.003)
                obj["hair_guide_level"] = "detailed"
            region_guides = self._create_region_guides(context, regions, center, size, rx, ry, offset, hairline_z, ear_z, occ_z, nape_z, front_y, back_y)
            detailed_count = len(detailed_specs) + len(region_guides)
            self.report({'INFO'}, f"古い詳細ガイド{removed}個を削除し、詳細ガイド{detailed_count}個を生成しました。")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"詳細ガイドの追加に失敗しました: {exc}")
            return {'CANCELLED'}

    def _create_region_guides(self, context, regions, center, size, rx, ry, offset, hairline_z, ear_z, occ_z, nape_z, front_y, back_y):
        scene = context.scene
        top_z = center.z + size.z * 0.55
        # Front: start line, clearance, split guides, flow guides.
        created = []
        created.append(utils.make_curve("REGION_Front_Hair_Start", [mathutils.Vector((center.x - rx*0.55, front_y, hairline_z)), mathutils.Vector((center.x, front_y-offset, hairline_z+size.z*0.04)), mathutils.Vector((center.x + rx*0.55, front_y, hairline_z))], regions, "Front", "region", scene, bevel=0.003))
        created.append(utils.make_curve("REGION_Front_Forehead_Clearance", [mathutils.Vector((center.x - rx*0.5, front_y-offset*2.5, hairline_z-size.z*0.12)), mathutils.Vector((center.x, front_y-offset*3.0, hairline_z-size.z*0.17)), mathutils.Vector((center.x + rx*0.5, front_y-offset*2.5, hairline_z-size.z*0.12))], regions, "Front", "region", scene, bevel=0.002))
        for xmul, label in [(-0.35, "L"), (0.0, "Center"), (0.35, "R")]:
            root = mathutils.Vector((center.x + rx*xmul, front_y, hairline_z))
            created.append(utils.make_curve(f"REGION_Front_Flow_{label}", [root, root + mathutils.Vector((0, -offset*3, -size.z*0.18)), root + mathutils.Vector((0, -offset*4, -size.z*0.35))], regions, "Front", "region", scene, bevel=0.002))
        # Side.
        for side, sign in [("L", -1), ("R", 1)]:
            x = center.x + sign * rx
            created.append(utils.make_curve(f"REGION_Side_{side}_Ear_Upper", [mathutils.Vector((x, center.y-ry*0.35, ear_z)), mathutils.Vector((x, center.y+ry*0.15, ear_z+size.z*0.02)), mathutils.Vector((x, back_y, ear_z))], regions, "Side", "region", scene, bevel=0.003))
            created.append(utils.make_curve(f"REGION_Side_{side}_Flow_To_Back", [mathutils.Vector((x, center.y-ry*0.45, ear_z+size.z*0.12)), mathutils.Vector((center.x + (x-center.x)*0.9, center.y+ry*0.25, ear_z+size.z*0.02)), mathutils.Vector((center.x + (x-center.x)*0.65, back_y, occ_z))], regions, "Side", "region", scene, bevel=0.002))
            created.append(utils.make_curve(f"REGION_Side_{side}_Volume_Limit", [mathutils.Vector((center.x + (x-center.x)*1.08, center.y-ry*0.2, ear_z+size.z*0.08)), mathutils.Vector((center.x + (x-center.x)*1.08, center.y+ry*0.35, ear_z+size.z*0.05))], regions, "Side", "region", scene, bevel=0.002))
        # Back upper cap lines.
        for zmul in [0.35, 0.45, 0.55]:
            z = center.z + size.z * zmul
            created.append(utils.make_curve(f"REGION_Back_Upper_Cap_{int(zmul*100)}", utils.make_arc_points(center, rx*0.85, ry*0.85, z, 0.15, 3.0, 7), regions, "Back_Upper", "region", scene, bevel=0.002))
        created.append(utils.make_curve("REGION_Back_Upper_Volume_Boundary", utils.make_arc_points(center, rx*0.95, ry*0.95, top_z-size.z*0.12, 0.0, 3.14, 7), regions, "Back_Upper", "region", scene, bevel=0.003))
        # Back middle variation guides.
        for xmul, label in [(-0.45, "Left"), (0.0, "Center_Sparse"), (0.45, "Right")]:
            x = center.x + rx*xmul
            created.append(utils.make_curve(f"REGION_Back_Middle_{label}", [mathutils.Vector((x, back_y, occ_z+size.z*0.08)), mathutils.Vector((center.x + (x-center.x)*0.9, back_y+offset, occ_z-size.z*0.1)), mathutils.Vector((center.x + (x-center.x)*0.7, back_y, nape_z+size.z*0.14))], regions, "Back_Middle", "region", scene, bevel=0.002))
        # Nape.
        created.append(utils.make_curve("REGION_Nape_Lower_Edge", [mathutils.Vector((center.x - rx*0.45, back_y, nape_z)), mathutils.Vector((center.x, back_y+offset, nape_z-size.z*0.03)), mathutils.Vector((center.x + rx*0.45, back_y, nape_z))], regions, "Nape", "region", scene, bevel=0.003))
        for xmul, label in [(-0.25, "L"), (0.0, "Center"), (0.25, "R")]:
            root = mathutils.Vector((center.x + rx*xmul, back_y, nape_z))
            created.append(utils.make_curve(f"REGION_Nape_Flow_{label}", [root, root + mathutils.Vector((0, offset*1.5, -size.z*0.12)), root + mathutils.Vector((0, offset*2.5, -size.z*0.28))], regions, "Nape", "region", scene, bevel=0.002))
        for obj in created:
            obj["hair_guide_level"] = "detailed"
        return created




FRONT_BACK_SYMMETRY_GUIDES = (
    "HAIR_GUIDE_Hairline",
    "HAIR_GUIDE_BackUpper",
    "HAIR_GUIDE_BackMiddle",
    "HAIR_GUIDE_Nape",
)


def _front_back_symmetry_center_x(context, guide_objects):
    head = getattr(context.scene, "hair_target_head_object", None)
    if head and head.type == "MESH":
        _, _, center, _ = utils.head_bounds(head)
        return center.x
    world_points = []
    for obj in guide_objects:
        if not obj or obj.type != "CURVE":
            continue
        for spline in obj.data.splines:
            if spline.type == "BEZIER":
                world_points.extend(obj.matrix_world @ point.co for point in spline.bezier_points)
    if world_points:
        return sum(point.x for point in world_points) / len(world_points)
    return 0.0


class HGD_OT_symmetrize_front_back_guides(bpy.types.Operator):
    bl_idname = "hgd.symmetrize_front_back_guides"
    bl_label = "前後ガイドを左右対称化"
    bl_description = "Front/Back/Napeガイドの左右差を頭部中心X基準で整えます。手動調整後に使ってください"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        guide_objects = [utils.get_guide_object(name) for name in FRONT_BACK_SYMMETRY_GUIDES]
        guide_objects = [obj for obj in guide_objects if obj and obj.type == "CURVE"]
        if not guide_objects:
            self.report({'WARNING'}, "左右対称化できる前後ガイドが見つかりません。先に基本ガイドを生成してください。")
            return {'CANCELLED'}

        center_x = _front_back_symmetry_center_x(context, guide_objects)
        updated_guides = 0
        updated_points = 0
        for obj in guide_objects:
            obj_inv = obj.matrix_world.inverted()
            guide_updated = False
            for spline in obj.data.splines:
                if spline.type != "BEZIER" or not spline.bezier_points:
                    continue
                points = sorted(spline.bezier_points, key=lambda point: (obj.matrix_world @ point.co).x)
                pair_count = len(points) // 2
                for index in range(pair_count):
                    left = points[index]
                    right = points[-index - 1]
                    left_world = obj.matrix_world @ left.co
                    right_world = obj.matrix_world @ right.co
                    avg_abs = (abs(left_world.x - center_x) + abs(right_world.x - center_x)) * 0.5
                    avg_y = (left_world.y + right_world.y) * 0.5
                    avg_z = (left_world.z + right_world.z) * 0.5
                    left.co = obj_inv @ mathutils.Vector((center_x - avg_abs, avg_y, avg_z))
                    right.co = obj_inv @ mathutils.Vector((center_x + avg_abs, avg_y, avg_z))
                    updated_points += 2
                    guide_updated = True
                if len(points) % 2 == 1:
                    mid = points[pair_count]
                    mid_world = obj.matrix_world @ mid.co
                    mid.co = obj_inv @ mathutils.Vector((center_x, mid_world.y, mid_world.z))
                    updated_points += 1
                    guide_updated = True
                for point in spline.bezier_points:
                    point.handle_left_type = "AUTO"
                    point.handle_right_type = "AUTO"
            if guide_updated:
                updated_guides += 1
        if updated_guides == 0:
            self.report({'WARNING'}, "Bezier点を持つ前後ガイドが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"前後ガイド{updated_guides}本・制御点{updated_points}点を左右対称化しました。")
        return {'FINISHED'}


class HGD_OT_delete_hair_guides(bpy.types.Operator):
    bl_idname = "hgd.delete_hair_guides"
    bl_label = "ガイド削除"
    bl_description = "生成されたガイドと領域線だけを削除します。頭部メッシュは削除しません"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        root = bpy.data.collections.get(utils.ROOT)
        if not root:
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        count = 0
        for collection_name in (utils.GUIDES, utils.REGIONS):
            count += utils.clear_collection_objects(collection_name)
        if count == 0:
            self.report({'WARNING'}, "削除する生成ガイドがありません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"ガイドを{count}個削除しました。")
        return {'FINISHED'}


class HGD_OT_show_hide_guides(bpy.types.Operator):
    bl_idname = "hgd.show_hide_guides"
    bl_label = "ガイド表示切替"
    bl_description = "生成されたガイドと領域線を表示または非表示にします"
    bl_options = {'REGISTER', 'UNDO'}
    hide: bpy.props.BoolProperty(default=False, description="オンで非表示、オフで表示します")

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        count = 0
        for obj in utils.generated_objects():
            if obj.get("hair_guide_type") in {"guide", "region"}:
                obj.hide_viewport = self.hide
                obj.hide_render = self.hide
                count += 1
        if count == 0:
            self.report({'WARNING'}, "ガイドが見つかりません。先に基本ガイドを生成してください。")
            return {'CANCELLED'}
        self.report({'INFO'}, "ガイドを非表示にしました。" if self.hide else "ガイドを表示しました。")
        return {'FINISHED'}


class HGD_OT_region_visibility(bpy.types.Operator):
    bl_idname = "hgd.region_visibility"
    bl_label = "領域表示"
    bl_description = "髪の領域ごとに生成物を表示または非表示にします"
    bl_options = {'REGISTER', 'UNDO'}
    region: EnumProperty(items=REGION_VISIBILITY_ITEMS, default="ALL", description="表示または非表示にする髪領域")
    action: EnumProperty(items=[("SHOW", "表示", ""), ("HIDE", "非表示", "")], default="SHOW", description="適用する表示操作")

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        hide = self.action == "HIDE"
        regions = utils.REGION_NAMES if self.region == "ALL" else (self.region,)
        count = sum(utils.set_region_visibility(region, hide) for region in regions)
        if count == 0:
            self.report({'WARNING'}, "領域オブジェクトが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"領域表示を更新しました: {self.region} {self.action.lower()}。")
        return {'FINISHED'}


def _region_visibility_targets(region):
    all_regions = set(utils.REGION_NAMES) | set(utils.POINT_REGIONS)
    return [
        obj for obj in utils.generated_objects()
        if (
            region == "ALL" and obj.get("hair_region", "") in all_regions
        ) or (
            region == "Side" and obj.get("hair_region", "") in {"Side", "Side_L", "Side_R"}
        ) or obj.get("hair_region", "") == region
    ]


class HGD_OT_toggle_region_visibility(bpy.types.Operator):
    bl_idname = "hgd.toggle_region_visibility"
    bl_label = "表示切替"
    bl_description = "対象領域の生成物を1ボタンで表示/非表示に切り替えます"
    bl_options = {'REGISTER', 'UNDO'}
    region: StringProperty(default="", description="表示切替する髪領域")

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        targets = _region_visibility_targets(self.region)
        if not targets:
            self.report({'WARNING'}, "領域オブジェクトが見つかりません。")
            return {'CANCELLED'}
        visible_count = sum(not obj.hide_viewport for obj in targets)
        visible = visible_count == 0
        for obj in targets:
            obj.hide_viewport = not visible
            obj.hide_render = not visible
        self.report({'INFO'}, "領域を表示しました。" if visible else "領域を非表示にしました。")
        return {'FINISHED'}


class HGD_OT_toggle_all_region_visibility(bpy.types.Operator):
    bl_idname = "hgd.toggle_all_region_visibility"
    bl_label = "表示切替"
    bl_description = "全領域の生成物を1ボタンで表示/非表示に切り替えます"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        targets = _region_visibility_targets("ALL")
        if not targets:
            self.report({'WARNING'}, "領域オブジェクトが見つかりません。")
            return {'CANCELLED'}
        visible_count = sum(not obj.hide_viewport for obj in targets)
        visible = visible_count == 0
        for obj in targets:
            obj.hide_viewport = not visible
            obj.hide_render = not visible
        self.report({'INFO'}, "全領域を表示しました。" if visible else "全領域を非表示にしました。")
        return {'FINISHED'}


class HGD_OT_generate_placement_points(bpy.types.Operator):
    bl_idname = "hgd.generate_placement_points"
    bl_label = "配置点を生成/更新"
    bl_description = "既存の配置点と警告を削除し、現在の基本ガイド位置から配置点を再生成します。既存のカーブは削除されません"
    bl_options = {'REGISTER', 'UNDO'}

    BASE_COUNTS = {"Top": 5, "Front": 7, "Side_L": 4, "Side_R": 4, "Back_Upper": 6, "Back_Middle": 6, "Nape": 5}

    @staticmethod
    def _preference_counts():
        mapping = {
            "Top": "point_count_top",
            "Front": "point_count_front",
            "Side_L": "point_count_side_l",
            "Side_R": "point_count_side_r",
            "Back_Upper": "point_count_back_upper",
            "Back_Middle": "point_count_back_middle",
            "Nape": "point_count_nape",
        }
        prefs = bpy.context.preferences.addons.get(__package__)
        prefs = prefs.preferences if prefs else None
        return {
            region: getattr(prefs, attr, HGD_OT_generate_placement_points.BASE_COUNTS[region])
            for region, attr in mapping.items()
        }

    def execute(self, context):
        try:
            head = require_head(context, self)
            if not head:
                return {'CANCELLED'}
            _, collections = utils.ensure_system()
            collection = collections[utils.PLACEMENT_POINTS]
            removed_points = utils.clear_collection_objects(utils.PLACEMENT_POINTS, "placement_point")
            removed_points += utils.clear_generated_by_type("placement_point")
            removed_warnings = utils.clear_collection_objects(utils.WARNINGS, "warning")
            context.scene.hair_warning_count = 0
            scene = context.scene
            min_v, max_v, center, size = utils.head_bounds(head)
            guides = self._basic_guides()
            guide_count = sum(1 for obj in guides.values() if obj)
            used_fallback = False
            used_back_guide_fallback = False
            rng = random.Random(scene.hair_seed)
            count_total = 0
            for region, base_count in self._preference_counts().items():
                if base_count <= 0:
                    continue
                count = base_count if region == "Top" else max(1, round(base_count * scene.hair_density))
                positions = self._guide_positions(region, count, guides, min_v, max_v, center, size, scene.hair_guide_offset)
                if positions is None:
                    positions = self._base_positions(region, count, min_v, max_v, center, size, scene.hair_guide_offset)
                    used_fallback = True
                if region in {"Back_Upper", "Back_Middle"} and not guides["back_upper" if region == "Back_Upper" else "back_middle"]:
                    used_fallback = True
                    used_back_guide_fallback = True
                for i, base in enumerate(positions):
                    loc = self._jittered(region, base, rng, scene)
                    if region == "Top":
                        loc.z = max(loc.z, max_v.z + TOP_POINT_OFFSET)
                    radius = max(size.length * 0.008, 0.01) * (1.0 + rng.uniform(-scene.hair_size_variation, scene.hair_size_variation))
                    point_name = self._point_name(region, i)
                    obj = utils.make_marker(point_name, loc, max(radius, 0.004), collection, region, "placement_point", scene, use_unique_name=False)
                    position_type = self._position_type(region, i, loc, center, size)
                    direction = self._recommended_direction(region, position_type, loc.x - center.x)
                    size_rec = max(scene.hair_curve_root_radius * (1.0 + rng.uniform(-scene.hair_size_variation, scene.hair_size_variation)), 0.001)
                    obj["hair_root_id"] = obj.name
                    obj["recommended_size"] = size_rec
                    obj["recommended_direction"] = utils.vector_to_string(direction)
                    obj["flow_side"] = "L" if loc.x < center.x - size.x*0.05 else ("R" if loc.x > center.x + size.x*0.05 else "Center")
                    obj["position_type"] = position_type
                    count_total += 1
            if guide_count == 0:
                self.report({'WARNING'}, "基本ガイドが見つからないため、頭部Bounding Boxから配置点を生成しました。")
            elif used_back_guide_fallback:
                self.report({'WARNING'}, "後頭部専用ガイドが無いため互換フォールバックで生成しました。基本ガイドを再生成してください。")
            elif used_fallback:
                self.report({'WARNING'}, "一部の基本ガイドが見つからないため、頭部Bounding Box基準で補完しました。")
            _apply_work_mode_lock_to_all_objects(context)
            if removed_points or removed_warnings:
                self.report({'INFO'}, f"既存の配置点 {removed_points} 個、警告 {removed_warnings} 件を削除しました。配置点 {count_total} 個を再生成しました。")
            else:
                self.report({'INFO'}, f"配置点 {count_total} 個を生成しました。")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"配置点の生成に失敗しました: {exc}")
            return {'CANCELLED'}

    def _basic_guides(self):
        return {
            "hairline": utils.get_guide_object("HAIR_GUIDE_Hairline"),
            "side_l": utils.get_guide_object("HAIR_GUIDE_SideBoundary_L"),
            "side_r": utils.get_guide_object("HAIR_GUIDE_SideBoundary_R"),
            "top": utils.get_guide_object("HAIR_GUIDE_Top"),
            "back_upper": utils.get_guide_object("HAIR_GUIDE_BackUpper"),
            "back_middle": utils.get_guide_object("HAIR_GUIDE_BackMiddle"),
            "nape": utils.get_guide_object("HAIR_GUIDE_Nape"),
            "center": utils.get_guide_object("HAIR_GUIDE_Center"),
        }

    def _guide_positions(self, region, count, guides, min_v, max_v, center, size, offset):
        if region == "Top":
            return self._top_positions(count, min_v, max_v, center, size, guides)
        if region == "Front" and guides["hairline"]:
            return utils.sample_curve_world_points(guides["hairline"], count)
        if region == "Side_L" and guides["side_l"]:
            return utils.sample_curve_world_points(guides["side_l"], count)
        if region == "Side_R" and guides["side_r"]:
            return utils.sample_curve_world_points(guides["side_r"], count)
        if region == "Back_Upper":
            if guides["back_upper"]:
                return utils.sample_curve_world_points(guides["back_upper"], count)
        if region == "Back_Middle":
            if guides["back_middle"]:
                return utils.sample_curve_world_points(guides["back_middle"], count)
        if region == "Nape" and guides["nape"]:
            return utils.sample_curve_world_points(guides["nape"], count)
        return None

    def _nape_fallback_z(self, min_v, size):
        return min_v.z + size.z * 0.24


    def _sample_guide_positions_with_debug(self, guide_obj, count):
        if getattr(bpy.context.scene, "hair_ui_show_debug", False):
            print("[HGD] placement source:", guide_obj.name, guide_obj.location)
        points = utils.sample_curve_world_points(guide_obj, count)
        if getattr(bpy.context.scene, "hair_ui_show_debug", False):
            for position in points:
                print("[HGD] sampled point:", position)
        return points

    def _evaluate_guide_position_with_debug(self, guide_obj, t):
        sample_count = 33
        points = self._sample_guide_positions_with_debug(guide_obj, sample_count)
        if not points:
            return None
        index = min(max(round(t * (len(points) - 1)), 0), len(points) - 1)
        return points[index].copy()

    def _base_positions(self, region, count, min_v, max_v, center, size, offset):
        rx = size.x * 0.5 + offset
        ry = size.y * 0.5 + offset
        positions = []
        for i in range(count):
            t = i / max(count - 1, 1)
            if region == "Top":
                return self._top_positions(count, min_v, max_v, center, size, {})
            if region == "Front":
                x = center.x + (t - 0.5) * size.x * 0.7
                y = min_v.y - offset * 1.5
                z = min_v.z + size.z * (0.66 + 0.07 * (1 - abs(t - 0.5) * 2))
            elif region in {"Side_L", "Side_R"}:
                sign = -1 if region == "Side_L" else 1
                x = center.x + sign * rx * 0.9
                y = min_v.y + size.y * (0.28 + 0.45 * t)
                z = min_v.z + size.z * (0.62 - 0.22 * t)
            elif region == "Back_Upper":
                x = center.x + (t - 0.5) * size.x * 0.75
                y = self._back_out_y(max_v, size, offset)
                z = self._back_upper_z(min_v, max_v, size)
            elif region == "Back_Middle":
                pair_index = i // 2
                is_left = i % 2 == 0
                pair_count = max(count // 2, 1)
                pair_t = pair_index / max(pair_count - 1, 1)
                offset_x = size.x * (0.12 + 0.16 * pair_index)
                x = center.x + (-offset_x if is_left else offset_x)
                y = self._back_out_y(max_v, size, offset)
                z = self._back_middle_z(min_v, size)
                if count % 2 and i == count - 1:
                    x = center.x
            else:
                x = center.x + (t - 0.5) * size.x * 0.45
                y = max_v.y + offset * 1.3
                z = min_v.z + size.z * (0.24 - 0.04 * abs(t - 0.5))
            positions.append(mathutils.Vector((x, y, z)))
        return positions

    def _back_middle_z(self, min_v, size):
        return min_v.z + size.z * BACK_MIDDLE_HEIGHT_RATIO

    def _back_upper_z(self, min_v, max_v, size):
        top_z = max_v.z
        back_middle_z = self._back_middle_z(min_v, size)
        return top_z * (1.0 - BACK_UPPER_TO_MIDDLE_BLEND) + back_middle_z * BACK_UPPER_TO_MIDDLE_BLEND

    def _back_out_y(self, max_v, size, offset):
        return max_v.y + max(offset, size.y * 0.04)

    def _top_positions(self, count, min_v, max_v, center, size, guides):
        base = mathutils.Vector((center.x, center.y, max_v.z + TOP_POINT_OFFSET))
        center_guide = guides.get("center") if guides else None
        if center_guide:
            guide_center = utils.get_curve_world_center(center_guide)
            if guide_center:
                base.x = guide_center.x
                base.y = guide_center.y
        x_offset = size.x * 0.12
        y_offset = size.y * 0.12
        positions = [
            base,
            base + mathutils.Vector((0.0, -y_offset, 0.0)),
            base + mathutils.Vector((0.0, y_offset, 0.0)),
            base + mathutils.Vector((-x_offset, 0.0, 0.0)),
            base + mathutils.Vector((x_offset, 0.0, 0.0)),
        ]
        return positions[:count]

    def _point_name(self, region, index):
        if region == "Top":
            return ("POINT_Top_Center", "POINT_Top_Front", "POINT_Top_Back", "POINT_Top_Left", "POINT_Top_Right")[index]
        if region == "Back_Middle":
            pair_no = index // 2 + 1
            side = "L" if index % 2 == 0 else "R"
            return f"POINT_Back_Middle_{pair_no:02d}_{side}"
        return f"POINT_{region}_{index+1:03d}"

    def _create_back_middle_points(self, positions, rng, scene, collection, center, size, min_v, max_v):
        count = 0
        for pair_start in range(0, len(positions), 2):
            pair = positions[pair_start:pair_start + 2]
            if len(pair) < 2:
                loc = self._jittered("Back_Middle", pair[0], rng, scene)
                radius = max(size.length * 0.008, 0.01) * (1.0 + rng.uniform(-scene.hair_size_variation, scene.hair_size_variation))
                obj = utils.make_marker(f"POINT_Back_Middle_{pair_start // 2 + 1:02d}_C", loc, max(radius, 0.004), collection, "Back_Middle", "placement_point", scene, use_unique_name=False)
                self._apply_point_recommendations(obj, "Back_Middle", pair_start, loc, center, size, rng, scene)
                count += 1
                continue
            dx, dy, dz = self._jitter_values("Back_Middle", rng, scene)
            radius = max(size.length * 0.008, 0.01) * (1.0 + rng.uniform(-scene.hair_size_variation, scene.hair_size_variation))
            size_rec = max(scene.hair_curve_root_radius * (1.0 + rng.uniform(-scene.hair_size_variation, scene.hair_size_variation)), 0.001)
            shared = {"recommended_size": size_rec}
            mirror_names = [self._point_name("Back_Middle", pair_start), self._point_name("Back_Middle", pair_start + 1)]
            for index, base in enumerate(pair):
                side_sign = -1.0 if index == 0 else 1.0
                loc = base + mathutils.Vector((side_sign * dx, dy, dz))
                obj = utils.make_marker(mirror_names[index], loc, max(radius, 0.004), collection, "Back_Middle", "placement_point", scene, use_unique_name=False)
                self._apply_point_recommendations(obj, "Back_Middle", pair_start + index, loc, center, size, rng, scene, shared)
                obj["mirror_pair"] = mirror_names[1 - index]
                count += 1
        return count

    def _apply_point_recommendations(self, obj, region, index, loc, center, size, rng, scene, shared=None):
        position_type = self._position_type(region, index, loc, center, size)
        direction = self._recommended_direction(region, position_type, loc.x - center.x)
        size_rec = shared["recommended_size"] if shared else max(scene.hair_curve_root_radius * (1.0 + rng.uniform(-scene.hair_size_variation, scene.hair_size_variation)), 0.001)
        obj["hair_root_id"] = obj.name
        obj["recommended_size"] = size_rec
        obj["recommended_direction"] = utils.vector_to_string(direction)
        obj["flow_side"] = "L" if loc.x < center.x - size.x*0.05 else ("R" if loc.x > center.x + size.x*0.05 else "Center")
        obj["position_type"] = position_type

    def _position_type(self, region, index, loc, center, size):
        if region == "Top":
            return ("top_center", "top_front", "top_back", "top_left", "top_right")[index]
        return "center" if abs(loc.x - center.x) < size.x * 0.18 else "outer"

    def _recommended_direction(self, region, position_type, x_offset):
        if region != "Top":
            return utils.direction_for_region(region, x_offset)
        directions = {
            "top_center": mathutils.Vector((0.0, 0.35, -0.9)),
            "top_front": mathutils.Vector((0.0, -0.35, -0.9)),
            "top_back": mathutils.Vector((0.0, 0.45, -0.85)),
            "top_left": mathutils.Vector((-0.35, 0.0, -0.9)),
            "top_right": mathutils.Vector((0.35, 0.0, -0.9)),
        }
        vec = directions.get(position_type, mathutils.Vector((0.0, 0.35, -0.9)))
        vec.normalize()
        return vec

    def _jitter_values(self, region, rng, scene):
        variation = 0.5 if region == "Top" else 1.0
        width_var = cm_to_m(scene.hair_width_variation_cm)
        height_var = cm_to_m(scene.hair_height_variation_cm)
        depth_var = cm_to_m(scene.hair_depth_variation_cm)
        x_jit = rng.uniform(-width_var, width_var) * variation
        if region == "Side_R":
            x_jit *= 1.0 - scene.hair_symmetry_bias * 0.65
        elif region == "Side_L":
            x_jit *= 1.0 - scene.hair_symmetry_bias * 0.35
        return (x_jit, rng.uniform(-depth_var, depth_var) * variation, rng.uniform(-height_var, height_var) * variation)

    def _jittered(self, region, base, rng, scene):
        return base + mathutils.Vector(self._jitter_values(region, rng, scene))


class HGD_OT_clear_placement_points(bpy.types.Operator):
    bl_idname = "hgd.clear_placement_points"
    bl_label = "配置点を削除"
    bl_description = "生成された配置点だけを削除します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        count = utils.clear_collection_objects(utils.PLACEMENT_POINTS, "placement_point")
        if count == 0:
            self.report({'WARNING'}, "配置点が見つかりません。先に配置点を生成してください。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"配置点を{count}個削除しました。")
        return {'FINISHED'}


def _select_generated_objects(context, objects):
    bpy.ops.object.select_all(action='DESELECT')
    active = None
    for obj in objects:
        if obj and obj.name in context.view_layer.objects:
            obj.hide_viewport = False
            obj.hide_select = False
            obj.select_set(True)
            active = obj
    if active:
        context.view_layer.objects.active = active


class HGD_OT_create_curve_from_points(bpy.types.Operator):
    bl_idname = "hgd.create_curve_from_points"
    bl_label = "カーブ毛束を生成"
    bl_description = "選択した配置点から編集可能なBezierカーブ毛束を生成します。メッシュ化はしません"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            points = [obj for obj in context.selected_objects if obj.get("hair_guide_type") == "placement_point"]
            if not points:
                self.report({'WARNING'}, "配置点が選択されていません。生成された配置点を選択してください。")
                return {'CANCELLED'}
            if context.scene.hair_strand_generation_type == "TWIST_CURVE":
                made = 0
                curves_by_point = {}
                created_controls = []
                for point in points:
                    control, _strand = _make_twist_from_point(context, point)
                    curves_by_point[point.name] = control
                    if control:
                        created_controls.append(control)
                    made += 1
                _apply_work_mode_lock_to_all_objects(context)
                _select_generated_objects(context, created_controls)
                self.report({'INFO'}, f"ツイスト制御カーブ{made}本と表示用カーブを生成しました。制御カーブを編集してから更新してください。")
                return {'FINISHED'}
            utils.ensure_system()
            scene = context.scene
            taper_obj = None
            if scene.hair_auto_apply_taper_to_new_curves and scene.hair_use_shared_taper:
                taper_obj, _ = _create_or_update_default_taper(context)
            made = 0
            curves_by_point = {}
            created_curves = []
            for point in points:
                region = point.get("hair_region", "Front")
                direction = utils.string_to_vector(point.get("recommended_direction"), utils.direction_for_region(region))
                length = cm_to_m(scene.hair_curve_length_cm)
                root_world = point.matrix_world.translation.copy()
                segment_count = max(scene.hair_curve_segment_count, 2)
                world_points = []
                for i in range(segment_count):
                    t = i / max(segment_count - 1, 1)
                    sag = mathutils.Vector((0, 0, -0.12 * length * t * t))
                    world_points.append(root_world + direction * length * t + sag)
                curve_points = [p - root_world for p in world_points]
                prefix = self._prefix(region)
                curves = utils.get_curve_collection(region, "curve")
                obj = utils.make_curve(utils.unique_numbered(prefix), curve_points, curves, region, "curve", scene, bevel=cm_to_m(scene.hair_curve_bevel_depth_cm))
                obj.location = root_world
                obj["hair_root_id"] = point.name
                obj["hair_source_point"] = point.name
                obj["hair_curve_length"] = length
                obj["hair_curve_length_cm"] = scene.hair_curve_length_cm
                obj["hair_curve_bevel_depth"] = cm_to_m(scene.hair_curve_bevel_depth_cm)
                obj["hair_curve_resolution"] = scene.hair_curve_resolution
                obj["hair_card_roll_angle"] = scene.hair_card_default_roll_angle
                obj["hair_card_use_parallel_transport"] = scene.hair_card_use_parallel_transport
                obj["hair_card_mid_position"] = scene.hair_card_mid_position
                obj["hair_card_width_interpolation"] = scene.hair_card_width_interpolation
                if "hair_card_control_empty" not in obj:
                    _assign_latest_card_control_empty_if_available(context, obj)
                _move_curve_origin_to_reference_empty_if_enabled(context, obj)
                obj["strand_type"] = scene.hair_strand_type
                obj["root_radius"] = scene.hair_curve_root_radius
                obj["tip_radius"] = scene.hair_curve_tip_radius
                obj["taper_strength"] = scene.hair_curve_taper_strength
                obj["segment_count"] = scene.hair_curve_segment_count
                _apply_curve_variation(obj, scene, point.name)
                obj.data.bevel_object = None
                obj["hair_curve_profile_type"] = "ROUND"
                if scene.hair_auto_apply_taper_to_new_curves:
                    _apply_taper_to_curve_obj(context, obj, taper_obj)
                _ensure_curve_visible_geometry(context, obj)
                _restore_curve_root_world(obj, root_world)
                _apply_display_mode_to_curve(context, obj)
                curves_by_point[point.name] = obj
                created_curves.append(obj)
                made += 1
            _apply_work_mode_lock_to_all_objects(context)
            _select_generated_objects(context, created_curves)
            self.report({'INFO'}, f"カーブ毛束を{made}本生成しました。")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"カーブ毛束の生成に失敗しました: {exc}")
            return {'CANCELLED'}

    def _prefix(self, region):
        return _hair_curve_name_prefix(region)


def _hair_curve_name_prefix(region):
    return HAIR_CURVE_NAME_PREFIXES.get(region, "HAIR_CURVE")


HGD_CURVE_DUPLICATE_COPY_PROPS = (
    "hair_region",
    "hair_root_id",
    "hair_source_point",
    "hair_curve_length",
    "hair_curve_length_cm",
    "hair_curve_bevel_depth",
    "hair_curve_resolution",
    "hair_card_roll_angle",
    "hair_card_use_parallel_transport",
    "hair_card_mid_position",
    "hair_card_width_interpolation",
    "strand_type",
    "root_radius",
    "tip_radius",
    "taper_strength",
    "segment_count",
)
HGD_CURVE_DUPLICATE_PREVIEW_REF_PROPS = (
    "hair_card_preview_object",
    "hair_flat_mesh_preview_object",
    "hair_card_mesh_object",
    "hair_flat_mesh_object",
)


def _is_hgd_control_curve(obj):
    return bool(obj and obj.type == "CURVE" and obj.get("hair_guide_type") == "curve")


def _resolve_duplicate_source_curve_from_object(obj):
    if not obj:
        return None
    guide_type = obj.get("hair_guide_type", "")
    if guide_type == "curve" and obj.type == "CURVE":
        return obj
    if guide_type in {"card_preview", "flat_mesh_preview"}:
        source = bpy.data.objects.get(obj.get("hair_source_curve", ""))
        if _is_hgd_control_curve(source):
            return source
    return None


def _duplicate_hgd_curve_object(context, src):
    region = src.get("hair_region", "")
    prefix = _hair_curve_name_prefix(region)
    curves = utils.get_curve_collection(region, "curve")
    curve_data = src.data.copy()
    new_obj = bpy.data.objects.new(utils.unique_numbered(prefix), curve_data)
    curves.objects.link(new_obj)
    new_obj.matrix_world = src.matrix_world.copy()

    utils.set_common_props(new_obj, "curve", region, context.scene)
    for prop_name in HGD_CURVE_DUPLICATE_COPY_PROPS:
        if prop_name in src:
            new_obj[prop_name] = src[prop_name]
    new_obj["hair_guide_type"] = "curve"
    new_obj["hair_region"] = region
    new_obj["hair_curve_profile_type"] = "ROUND"

    if "hair_card_control_empty" in src:
        empty_name = src.get("hair_card_control_empty", "")
        if empty_name and bpy.data.objects.get(empty_name):
            new_obj["hair_card_control_empty"] = empty_name
    if "hair_card_control_empty" not in new_obj:
        _assign_latest_card_control_empty_if_available(context, new_obj)

    for prop_name in HGD_CURVE_DUPLICATE_PREVIEW_REF_PROPS:
        if prop_name in new_obj:
            del new_obj[prop_name]

    _ensure_curve_visible_geometry(context, new_obj)
    _apply_work_mode_lock_to_object(context, new_obj)
    return new_obj


def _unique_duplicate_source_curves_from_selection(context, resolver):
    sources = []
    seen = set()
    for obj in context.selected_objects:
        src = resolver(obj)
        if src and src.name not in seen:
            sources.append(src)
            seen.add(src.name)
    return sources


def _select_only_objects(context, objects):
    for obj in context.selected_objects:
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    context.view_layer.objects.active = objects[-1] if objects else None


class HGD_OT_duplicate_selected_hair_curves(bpy.types.Operator):
    bl_idname = "hgd.duplicate_selected_hair_curves"
    bl_label = "選択Curveを複製"
    bl_description = "選択中のHGD Curveを、現在の形状とワールド位置を維持した独立Curveとして複製します"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(_is_hgd_control_curve(obj) for obj in context.selected_objects)

    def execute(self, context):
        sources = _unique_duplicate_source_curves_from_selection(context, _is_hgd_control_curve)
        if not sources:
            self.report({'WARNING'}, "複製対象のHGD Curveが選択されていません。")
            return {'CANCELLED'}

        created = [_duplicate_hgd_curve_object(context, src) for src in sources]
        _select_only_objects(context, created)

        self.report({'INFO'}, f"HGD Curveを{len(created)}本複製しました。")
        return {'FINISHED'}


class HGD_OT_duplicate_selected_or_preview_source_curves(bpy.types.Operator):
    bl_idname = "hgd.duplicate_selected_or_preview_source_curves"
    bl_label = "選択Curve/Preview元Curveを複製"
    bl_description = "選択中のHGD Curve、またはCARD/Flat Mesh Previewの参照元Curveだけを複製します"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(_resolve_duplicate_source_curve_from_object(obj) for obj in context.selected_objects)

    def execute(self, context):
        sources = _unique_duplicate_source_curves_from_selection(context, _resolve_duplicate_source_curve_from_object)
        if not sources:
            self.report({'WARNING'}, "複製対象のHGD CurveまたはPreview元Curveが選択されていません。")
            return {'CANCELLED'}

        created = [_duplicate_hgd_curve_object(context, src) for src in sources]
        for new_obj in created:
            _apply_display_mode_to_curve(context, new_obj)
        _select_only_objects(context, created)

        self.report({'INFO'}, f"HGD Curve/Preview元Curveを{len(created)}本複製しました。")
        return {'FINISHED'}


def _stable_curve_variation_rng(scene, source_name):
    stable_id = sum(ord(char) for char in str(source_name))
    seed, _randomize = _variation_seed_settings(scene)
    return random.Random(seed + stable_id)


def _stable_curve_variation_rng_for_obj(scene, obj, source_name):
    stable_key = f"{source_name}|{obj.name}|{obj.get('hair_region', '')}|{obj.get('hair_guide_type', '')}"
    stable_id = sum(ord(char) for char in stable_key)
    seed, randomize = _variation_seed_settings(scene)
    if randomize:
        runtime_seed = random.SystemRandom().randint(0, 2_147_483_647)
    else:
        runtime_seed = seed + stable_id
    return random.Random(runtime_seed), runtime_seed


def _apply_curve_variation(obj, scene, source_name):
    if not scene.hair_curve_variation_enabled:
        return 1.0

    obj["hair_curve_variation_enabled"] = scene.hair_curve_variation_enabled
    seed, randomize = _variation_seed_settings(scene)
    obj["hair_curve_variation_seed"] = seed
    obj["hair_curve_root_jitter_ratio"] = scene.hair_curve_root_jitter_ratio
    obj["hair_curve_mid_jitter_ratio"] = scene.hair_curve_mid_jitter_ratio
    obj["hair_curve_tip_jitter_ratio"] = scene.hair_curve_tip_jitter_ratio
    obj["hair_curve_length_variation"] = scene.hair_curve_length_variation
    obj["hair_curve_variation_randomized"] = randomize
    length_scale = 1.0
    if obj.get("hair_guide_type") not in {"curve", "twist_control"}:
        obj["hair_curve_variation_runtime_seed"] = 0
        obj["hair_curve_length_scale"] = length_scale
        return length_scale
    spline = _first_bezier_spline(obj)
    if not spline:
        obj["hair_curve_variation_runtime_seed"] = 0
        obj["hair_curve_length_scale"] = length_scale
        return length_scale
    rng, runtime_seed = _stable_curve_variation_rng_for_obj(scene, obj, source_name)
    obj["hair_curve_variation_runtime_seed"] = runtime_seed
    side_multiplier = 1.35 if obj.get("hair_region", "") in {"Side_L", "Side_R"} else 1.0
    length_variation = max(scene.hair_curve_length_variation, 0.0)
    if length_variation <= 0.0:
        length_scale = 1.0
    else:
        length_scale = rng.uniform(max(1.0 - length_variation, 0.01), 1.0 + length_variation)
    base_length = float(obj.get("hair_curve_length", cm_to_m(scene.hair_curve_length_cm)))
    final_length = base_length * length_scale
    obj["hair_curve_base_length"] = base_length
    obj["hair_curve_base_length_cm"] = m_to_cm(base_length)
    obj["hair_curve_length"] = final_length
    obj["hair_curve_length_cm"] = m_to_cm(final_length)
    root = spline.bezier_points[0].co.copy()
    for point in spline.bezier_points:
        point.co = root + (point.co - root) * length_scale
        point.handle_left = root + (point.handle_left - root) * length_scale
        point.handle_right = root + (point.handle_right - root) * length_scale
    root_jitter = base_length * scene.hair_curve_root_jitter_ratio
    mid_jitter = base_length * scene.hair_curve_mid_jitter_ratio
    tip_jitter = base_length * scene.hair_curve_tip_jitter_ratio
    point_count = len(spline.bezier_points)
    for index, point in enumerate(spline.bezier_points):
        t = index / max(point_count - 1, 1)
        if t <= 0.5:
            local_t = t / 0.5 if t > 0.0 else 0.0
            amount = root_jitter + (mid_jitter - root_jitter) * local_t
        else:
            local_t = (t - 0.5) / 0.5
            amount = mid_jitter + (tip_jitter - mid_jitter) * local_t
        if index == 0:
            amount = 0.0
        amount *= side_multiplier
        offset = mathutils.Vector((
            rng.uniform(-amount, amount),
            rng.uniform(-amount, amount),
            rng.uniform(-amount, amount),
        ))
        point.co += offset
        point.handle_left += offset
        point.handle_right += offset
    obj["hair_curve_length_scale"] = length_scale
    return length_scale


class HGD_OT_check_root_clustering(bpy.types.Operator):
    bl_idname = "hgd.check_root_clustering"
    bl_label = "根元集中チェック"
    bl_description = "同じ領域内で近すぎる配置点ペアを検出します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            if not bpy.data.collections.get(utils.ROOT):
                self.report({'WARNING'}, "HairGuideSystemが存在しません。")
                return {'CANCELLED'}
            self._clear_warning_markers(context, reset_colors=False)
            points = utils.generated_objects("placement_point")
            if not points:
                self.report({'WARNING'}, "配置点が見つかりません。先に配置点を生成してください。")
                return {'CANCELLED'}
            _, collections = utils.ensure_system()
            warnings = collections[utils.WARNINGS]
            threshold = context.scene.hair_root_cluster_threshold
            warned = set()
            warning_count = 0
            for i, obj in enumerate(points):
                for other in points[i + 1:]:
                    if obj.get("hair_region") != other.get("hair_region"):
                        continue
                    pair_threshold = threshold * 0.75 if obj.get("hair_region") == "Top" else threshold
                    if (obj.location - other.location).length_squared >= pair_threshold * pair_threshold:
                        continue
                    height_delta = abs(obj.location.z - other.location.z)
                    size_delta = abs(float(obj.get("recommended_size", 0)) - float(other.get("recommended_size", 0)))
                    length_delta = abs(float(obj.get("recommended_length", 0)) - float(other.get("recommended_length", 0)))
                    for target in (obj, other):
                        target.color = utils.WARNING_COLOR
                        warned.add(target.name)
                    loc = (obj.location + other.location) * 0.5
                    marker = utils.make_marker("WARNING_RootCluster", loc, max(pair_threshold * 0.25, 0.01), warnings, obj.get("hair_region", ""), "warning", context.scene)
                    marker["hair_warning_type"] = "root_cluster"
                    marker["warning_objects"] = f"{obj.name},{other.name}"
                    marker["height_delta"] = height_delta
                    marker["size_delta"] = size_delta
                    marker["length_delta"] = length_delta
                    warning_count += 1
            context.scene.hair_warning_count = warning_count
            self.report({'INFO'}, f"警告を{warning_count}件検出しました。")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"根元集中チェックに失敗しました: {exc}")
            return {'CANCELLED'}

    def _clear_warning_markers(self, context, reset_colors=True):
        if reset_colors:
            for obj in utils.generated_objects("placement_point"):
                obj.color = utils.REGION_COLORS.get(obj.get("hair_region"), (0.9, 0.9, 0.9, 1.0))
        utils.clear_collection_objects(utils.WARNINGS, "warning")
        context.scene.hair_warning_count = 0


class HGD_OT_clear_warnings(bpy.types.Operator):
    bl_idname = "hgd.clear_warnings"
    bl_label = "警告を削除"
    bl_description = "警告マーカーを削除し、配置点の色を戻します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        for obj in utils.generated_objects("placement_point"):
            obj.color = utils.REGION_COLORS.get(obj.get("hair_region"), (0.9, 0.9, 0.9, 1.0))
        count = utils.clear_collection_objects(utils.WARNINGS, "warning")
        context.scene.hair_warning_count = 0
        if count == 0:
            self.report({'WARNING'}, "削除する警告がありません。")
            return {'CANCELLED'}
        self.report({'INFO'}, "警告を削除しました。")
        return {'FINISHED'}


class HGD_OT_clear_card_previews(bpy.types.Operator):
    bl_idname = "hgd.clear_card_previews"
    bl_label = "CARDプレビューを削除"
    bl_description = "CARDプレビューだけを削除します。元Curve、CARD Mesh、Flat Meshは削除しません"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        count = utils.clear_collection_objects(utils.CARD_PREVIEWS, "card_preview")
        for obj in utils.generated_objects():
            if obj.get("hair_card_preview_object"):
                obj["hair_card_preview_object"] = ""
        if count == 0:
            self.report({'WARNING'}, "削除するCARDプレビューがありません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"CARDプレビューを{count}個削除しました。")
        return {'FINISHED'}


class HGD_OT_clear_flat_mesh_previews(bpy.types.Operator):
    bl_idname = "hgd.clear_flat_mesh_previews"
    bl_label = "扁平メッシュPreviewを削除"
    bl_description = "扁平メッシュPreviewだけを削除します。元Curveと確定Flat Meshは削除しません"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        count = utils.clear_collection_objects(utils.CARD_PREVIEWS, "flat_mesh_preview")
        for obj in utils.generated_objects():
            if obj.get("hair_flat_mesh_preview_object"):
                obj["hair_flat_mesh_preview_object"] = ""
        if count == 0:
            self.report({'WARNING'}, "削除する扁平メッシュPreviewがありません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"扁平メッシュPreviewを{count}個削除しました。")
        return {'FINISHED'}


class HGD_OT_rebuild_preview_links_clean(bpy.types.Operator):
    bl_idname = "hgd.rebuild_preview_links_clean"
    bl_label = "Previewリンクをクリーン再生成"
    bl_description = "既存プロジェクト移行用にCARD/Flat Mesh Previewを全削除し、全CurveのPreview参照を空にして選択Curveだけを現在設定でCARD Preview再生成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}

        selected_curves, selected_twist_controls = _selected_card_update_targets(context)
        removed = 0
        for obj in list(utils.generated_objects()):
            if obj.get("hair_guide_type") in {"card_preview", "flat_mesh_preview"}:
                bpy.data.objects.remove(obj, do_unlink=True)
                removed += 1

        for obj in utils.generated_objects():
            if obj.type == "CURVE":
                obj["hair_card_preview_object"] = ""
                obj["hair_flat_mesh_preview_object"] = ""

        _sync_card_width_preset_to_scene(context.scene)
        rebuilt = 0
        for control in selected_twist_controls:
            _sync_scene_card_width_settings_to_curve(context.scene, control)
            strand = _create_or_replace_twist_strand(context, control)
            if strand:
                _sync_scene_card_width_settings_to_curve(context.scene, strand)
                strand["hair_curve_display_mode"] = "CARD"
                if _create_or_update_card_preview(context, strand):
                    rebuilt += 1

        for curve_obj in selected_curves:
            _sync_scene_card_width_settings_to_curve(context.scene, curve_obj)
            curve_obj["hair_curve_display_mode"] = "CARD"
            if _create_or_update_card_preview(context, curve_obj):
                rebuilt += 1

        context.view_layer.update()
        if rebuilt == 0:
            self.report({'WARNING'}, f"Previewを{removed}個削除しましたが、再生成対象Curveが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Previewを{removed}個削除し、CARD Previewを{rebuilt}個再生成しました。")
        return {'FINISHED'}


class HGD_OT_rebuild_card_previews_clean(HGD_OT_rebuild_preview_links_clean):
    bl_idname = "hgd.rebuild_card_previews_clean"
    bl_label = "CARD Previewをクリーン再生成"
    bl_description = "互換用です。hgd.rebuild_preview_links_clean と同じ処理でPreviewリンクをクリーン再生成します"


class HGD_OT_clear_all_generated(bpy.types.Operator):
    bl_idname = "hgd.clear_all_generated"
    bl_label = "生成物をすべて削除"
    bl_description = "hair_guide内の全生成物を削除します（元に戻す前提の危険操作です）"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        total = 0
        for collection_name in (utils.GUIDES, utils.REGIONS, utils.PLACEMENT_POINTS, utils.CURVES, utils.WARNINGS, utils.TAPER_OBJECTS, utils.PROFILE_OBJECTS, utils.CARD_PREVIEWS, utils.CARD_MESHES, utils.FLAT_MESHES, utils.CARD_CONTROLS):
            total += utils.clear_collection_objects(collection_name)
        context.scene.hair_warning_count = 0
        _apply_work_mode_lock_to_all_objects(context)
        if total == 0:
            self.report({'WARNING'}, "削除する生成物がありません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"生成物を{total}個削除しました。")
        return {'FINISHED'}


class HGD_OT_toggle_in_front_generated_helpers(bpy.types.Operator):
    bl_idname = "hgd.toggle_in_front_generated_helpers"
    bl_label = "最前面表示を切り替え"
    bl_description = "生成済みのガイド、配置点、警告、表示用カーブの最前面表示をON/OFFします"
    bl_options = {'REGISTER', 'UNDO'}

    TARGET_TYPES = {"guide", "region", "placement_point", "warning", "curve", "twist_strand"}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        scene = context.scene
        scene.hair_show_guides_in_front = not scene.hair_show_guides_in_front
        show = scene.hair_show_guides_in_front
        count = 0
        for obj in utils.generated_objects():
            if obj.get("hair_guide_type") in self.TARGET_TYPES:
                obj.show_in_front = show
                count += 1
        if show:
            self.report({'INFO'}, f"ガイド・配置点・表示カーブを最前面表示にしました。対象: {count} 個。")
        else:
            self.report({'INFO'}, f"ガイド・配置点・表示カーブの最前面表示を解除しました。対象: {count} 個。")
        return {'FINISHED'}


class HGD_OT_organize_curves_by_region(bpy.types.Operator):
    bl_idname = "hgd.organize_curves_by_region"
    bl_label = "カーブを部位別に整理"
    bl_description = "生成済みカーブをTop、Front、Side、Back、Nape、Twistの部位別Collectionへ移動します"
    bl_options = {'REGISTER', 'UNDO'}

    TARGET_TYPES = {"curve", "twist_control", "twist_strand"}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        utils.ensure_system()
        count = 0
        for obj in utils.generated_objects():
            if obj.get("hair_guide_type") in self.TARGET_TYPES and utils.organize_curve_object(obj):
                count += 1
        if count == 0:
            self.report({'WARNING'}, "整理対象の生成カーブが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"カーブを部位別Collectionへ整理しました: {count} 件")
        return {'FINISHED'}


class HGD_OT_apply_curve_region_colors(bpy.types.Operator):
    bl_idname = "hgd.apply_curve_region_colors"
    bl_label = "部位別カラーを反映"
    bl_description = "生成済みカーブとツイストカーブへ部位別のObject Colorを反映します"
    bl_options = {'REGISTER', 'UNDO'}

    TARGET_TYPES = {"curve", "twist_control", "twist_strand"}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        count = 0
        for obj in utils.generated_objects():
            if obj.get("hair_guide_type") in self.TARGET_TYPES and utils.apply_curve_region_color(obj):
                count += 1
        if count == 0:
            self.report({'WARNING'}, "カラー反映対象の生成カーブが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"部位別カラーを {count} 件に反映しました。")
        return {'FINISHED'}



def _replace_preview_mesh_data(preview_obj, new_mesh):
    old_mesh = preview_obj.data
    preview_obj.data = new_mesh
    preview_obj.data.update()
    preview_obj.update_tag(refresh={'DATA'})
    if old_mesh and old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    return preview_obj

def _generated_curves_from_context(context, selected_only):
    if not selected_only:
        return [
            obj for obj in utils.generated_objects()
            if obj.type == "CURVE" and obj.get("hair_guide_type") in {"curve", "twist_strand"}
        ]

    result = []
    seen = set()
    for obj in context.selected_objects:
        target = resolve_display_curve_from_object(context, obj)
        if target and target.name not in seen:
            result.append(target)
            seen.add(target.name)
    return result


def _follow_targets_from_context(context, selected_only):
    objects = context.selected_objects if selected_only else utils.generated_objects()
    return [
        obj for obj in objects
        if obj.type == "CURVE" and obj.get("hair_guide_type") in {"curve", "twist_control"}
    ]


def _first_bezier_spline(obj):
    if obj.type != "CURVE":
        return None
    for spline in obj.data.splines:
        if spline.type == "BEZIER" and spline.bezier_points:
            return spline
    return None


def _sample_curve_world_points(obj, count):
    spline = _first_bezier_spline(obj)
    if not spline:
        return []
    source = [obj.matrix_world @ point.co for point in spline.bezier_points]
    if len(source) == 1:
        return source * max(count, 1)
    lengths = []
    total = 0.0
    for start, end in zip(source, source[1:]):
        total += (end - start).length
        lengths.append(total)
    if total == 0.0:
        return [source[0].copy() for _ in range(max(count, 1))]
    samples = []
    for i in range(max(count, 2)):
        target = total * (i / max(count - 1, 1))
        segment_index = 0
        prev_length = 0.0
        for idx, end_length in enumerate(lengths):
            if target <= end_length:
                segment_index = idx
                break
            prev_length = end_length
        segment_length = max(lengths[segment_index] - prev_length, 0.000001)
        t = (target - prev_length) / segment_length
        samples.append(source[segment_index].lerp(source[segment_index + 1], t))
    return samples


def _curve_frame(tangent, previous_normal=None):
    world_up = mathutils.Vector((0.0, 0.0, 1.0))
    side = tangent.cross(world_up)
    if side.length < 0.0001:
        fallback = previous_normal if previous_normal and previous_normal.length > 0.0001 else mathutils.Vector((1.0, 0.0, 0.0))
        side = fallback.cross(tangent)
    if side.length < 0.0001:
        side = mathutils.Vector((1.0, 0.0, 0.0))
    side.normalize()
    normal = side.cross(tangent)
    if normal.length < 0.0001:
        normal = previous_normal if previous_normal and previous_normal.length > 0.0001 else world_up
    normal.normalize()
    return side, normal


def _safe_normalized(v, fallback):
    if v.length < 1e-6:
        return fallback.copy()
    return v.normalized()


def _initial_card_side(scene, curve_obj, sample, tangent):
    mode = getattr(scene, "hair_card_orientation_mode", "HEAD_OUT")
    if mode == "HEAD_OUT":
        head = getattr(scene, "hair_target_head_object", None)
        if head:
            _, _, center, _ = utils.head_bounds(head)
            base = sample - center
        else:
            base = mathutils.Vector((1.0, 0.0, 0.0))
    elif mode == "WORLD_X":
        base = mathutils.Vector((1.0, 0.0, 0.0))
    elif mode == "WORLD_Y":
        base = mathutils.Vector((0.0, 1.0, 0.0))
    else:
        base = mathutils.Vector((1.0, 0.0, 0.0))
    side = base - tangent * base.dot(tangent)
    if side.length < 1e-6:
        fallback = mathutils.Vector((1.0, 0.0, 0.0))
        if abs(fallback.dot(tangent)) > 0.95:
            fallback = mathutils.Vector((0.0, 1.0, 0.0))
        side = fallback - tangent * fallback.dot(tangent)
    return _safe_normalized(side, mathutils.Vector((1.0, 0.0, 0.0)))


def _parallel_transport_side(prev_tangent, current_tangent, prev_side):
    axis = prev_tangent.cross(current_tangent)
    dot = max(min(prev_tangent.dot(current_tangent), 1.0), -1.0)
    if axis.length < 1e-6:
        side = prev_side.copy()
    else:
        angle = math.acos(dot)
        rot = mathutils.Matrix.Rotation(angle, 4, axis.normalized())
        side = rot @ prev_side
    side = side - current_tangent * side.dot(current_tangent)
    if side.length < 1e-6:
        side = prev_side.copy()
    side.normalize()
    if side.dot(prev_side) < 0:
        side *= -1
    return side


def _apply_card_roll(side, tangent, roll_deg):
    if abs(roll_deg) < 1e-6:
        return side
    rot = mathutils.Matrix.Rotation(math.radians(roll_deg), 4, tangent)
    return (rot @ side).normalized()



def _card_or_flat_side_vector(context, curve_obj, sample, tangent, previous_side=None):
    empty_name = curve_obj.get("hair_card_control_empty", "")
    empty = bpy.data.objects.get(empty_name) if empty_name else None
    if not empty or empty.type != 'EMPTY':
        return None

    scene = context.scene
    mode = getattr(scene, "hair_card_control_empty_mode", "TARGET_POSITION")
    if mode == "AXIS":
        side = empty.matrix_world.to_3x3() @ mathutils.Vector((1.0, 0.0, 0.0))
    elif mode == "TARGET_POSITION":
        target_dir = empty.matrix_world.translation - sample
        if target_dir.length < 1e-6:
            return None
        target_dir.normalize()

        side = tangent.cross(target_dir)
        if side.length < 1e-6:
            side = target_dir.cross(tangent)
        if side.length < 1e-6:
            return None
        side.normalize()

        if getattr(scene, "hair_card_flip_side", False):
            side *= -1
    else:
        return None

    # CARD Control Empty based frames historically faced opposite to the target.
    # Invert only this Empty-derived side vector; automatic/PTF fallback frames stay unchanged.
    side *= -1.0

    side = side - tangent * side.dot(tangent)
    if side.length < 1e-6:
        return None
    side.normalize()
    if previous_side is not None and side.dot(previous_side) < 0:
        side *= -1
    return side



def _head_center_vector(scene, sample):
    head = getattr(scene, "hair_target_head_object", None)
    if head:
        _, _, center, _ = utils.head_bounds(head)
        return center - sample
    return mathutils.Vector((0.0, 0.0, -1.0))


def _twist_inner_flat_side_vector(context, curve_obj, sample, tangent, previous_side=None):
    scene = context.scene
    inward = None
    if getattr(scene, "hair_twist_flat_mesh_inner_mode", "HEAD_CENTER") == "TARGET_EMPTY":
        empty_name = curve_obj.get("hair_card_control_empty", "")
        empty = bpy.data.objects.get(empty_name) if empty_name else None
        if empty:
            inward = empty.matrix_world.translation - sample

    if inward is None:
        inward = _head_center_vector(scene, sample)

    if inward.length < 1e-6:
        return previous_side.copy() if previous_side else mathutils.Vector((1.0, 0.0, 0.0))

    inward.normalize()
    side = tangent.cross(inward)
    if side.length < 1e-6:
        side = inward.cross(tangent)
    if side.length < 1e-6:
        return previous_side.copy() if previous_side else mathutils.Vector((1.0, 0.0, 0.0))

    side.normalize()
    if previous_side is not None and side.dot(previous_side) < 0:
        side *= -1

    normal = tangent.cross(side)
    if normal.length >= 1e-6 and normal.dot(inward) < 0:
        side *= -1

    side = side - tangent * side.dot(tangent)
    if side.length < 1e-6:
        return previous_side.copy() if previous_side else mathutils.Vector((1.0, 0.0, 0.0))
    side.normalize()
    return side


def _flat_mesh_side_vector_for_curve(context, curve_obj, sample, tangent, previous_side=None):
    scene = context.scene
    if (
        curve_obj.get("hair_guide_type") == "twist_strand"
        and getattr(scene, "hair_twist_flat_mesh_force_inner_side", True)
    ):
        return _twist_inner_flat_side_vector(context, curve_obj, sample, tangent, previous_side)
    return _card_or_flat_side_vector(context, curve_obj, sample, tangent, previous_side)

def _card_control_empty_side_vector(curve_obj, sample, tangent):
    return _card_or_flat_side_vector(bpy.context, curve_obj, sample, tangent)

def _build_card_frames(context, curve_obj, samples):
    scene = context.scene
    frames = []
    if len(samples) < 2:
        return frames
    roll = float(curve_obj.get("hair_card_roll_angle", scene.hair_card_default_roll_angle))
    use_ptf = bool(curve_obj.get("hair_card_use_parallel_transport", scene.hair_card_use_parallel_transport))
    prev_tangent = None
    prev_side = None
    for index, sample in enumerate(samples):
        prev_point = samples[max(index - 1, 0)]
        next_point = samples[min(index + 1, len(samples) - 1)]
        tangent = next_point - prev_point
        if tangent.length < 1e-6:
            tangent = prev_tangent.copy() if prev_tangent else mathutils.Vector((0.0, 0.0, 1.0))
        tangent.normalize()
        side = _card_or_flat_side_vector(context, curve_obj, sample, tangent, prev_side)
        if side is not None:
            pass
        else:
            if index == 0 or prev_side is None or not use_ptf:
                side = _initial_card_side(scene, curve_obj, sample, tangent)
            else:
                side = _parallel_transport_side(prev_tangent, tangent, prev_side)
            side = _apply_card_roll(side, tangent, roll)
        frames.append((sample, tangent.copy(), side.copy()))
        prev_tangent = tangent.copy()
        prev_side = side.copy()
    return frames


def _next_twist_id():
    index = 1
    while True:
        twist_id = f"{index:03d}"
        if not bpy.data.objects.get(f"HGD_TWIST_CTRL_{twist_id}") and not bpy.data.objects.get(f"HGD_TWIST_STRAND_{twist_id}"):
            return twist_id
        index += 1


def _set_twist_control_display(control_obj):
    control_obj.data.bevel_depth = 0.0
    control_obj.data.bevel_object = None
    control_obj.data.taper_object = None
    control_obj.display_type = "WIRE"
    control_obj.show_in_front = True
    control_obj.hide_select = False
    control_obj["hair_guide_type"] = "twist_control"
    control_obj["hair_editable_control"] = True
    control_obj["hair_use_taper"] = False
    control_obj["hair_taper_object"] = ""
    control_obj["hair_curve_profile_type"] = "NONE"


def _twist_frame(tangent, previous_normal=None):
    up = previous_normal or mathutils.Vector((0.0, 0.0, 1.0))
    side = tangent.cross(up)
    if side.length < 0.0001:
        side = tangent.cross(mathutils.Vector((0.0, 1.0, 0.0)))
    if side.length < 0.0001:
        side = mathutils.Vector((1.0, 0.0, 0.0))
    side.normalize()
    normal = side.cross(tangent)
    if normal.length < 0.0001:
        normal = mathutils.Vector((0.0, 0.0, 1.0))
    normal.normalize()
    return side, normal


def _create_or_replace_twist_strand(context, control_obj):
    scene = context.scene
    utils.ensure_system()
    curves_collection = utils.get_curve_collection(control_obj.get("hair_region", ""), "twist_strand")
    twist_id = control_obj.get("hair_twist_id", _next_twist_id())
    for obj in list(utils.generated_objects()):
        if obj.get("hair_twist_id") == twist_id and obj.get("hair_guide_type") == "twist_strand":
            bpy.data.objects.remove(obj, do_unlink=True)
    sample_count = max(scene.hair_twist_segments, 4)
    samples = _sample_curve_world_points(control_obj, sample_count)
    if len(samples) < 2:
        return None
    points = []
    normal_hint = mathutils.Vector((0.0, 0.0, 1.0))
    for index, sample in enumerate(samples):
        prev_point = samples[max(index - 1, 0)]
        next_point = samples[min(index + 1, len(samples) - 1)]
        tangent = next_point - prev_point
        if tangent.length < 0.0001:
            tangent = mathutils.Vector((0.0, 0.0, -1.0))
        tangent.normalize()
        side, normal_hint = _twist_frame(tangent, normal_hint)
        t = index / max(len(samples) - 1, 1)
        angle = math.tau * scene.hair_twist_turns * t + scene.hair_twist_phase
        taper = max(1.0 - scene.hair_twist_taper_strength * t, 0.05)
        radius = cm_to_m(scene.hair_twist_radius) * taper
        points.append(sample + side * math.cos(angle) * radius + normal_hint * math.sin(angle) * radius)
    obj = utils.make_curve(
        f"HGD_TWIST_STRAND_{twist_id}",
        points,
        curves_collection,
        control_obj.get("hair_region", ""),
        "twist_strand",
        scene,
        bevel=cm_to_m(scene.hair_twist_bevel_depth_cm),
    )
    obj.data.resolution_u = scene.hair_twist_resolution
    obj.hide_select = True
    obj["hair_locked_visual"] = True
    obj["hair_source_point"] = control_obj.get("hair_source_point", "")
    obj["hair_twist_id"] = twist_id
    obj["hair_twist_control"] = control_obj.name
    obj["hair_twist_segments"] = scene.hair_twist_segments
    obj["hair_twist_radius"] = cm_to_m(scene.hair_twist_radius)
    obj["hair_twist_turns"] = scene.hair_twist_turns
    obj["hair_twist_phase"] = scene.hair_twist_phase
    obj["hair_twist_bevel_depth"] = cm_to_m(scene.hair_twist_bevel_depth_cm)
    obj["hair_twist_bevel_depth_cm"] = scene.hair_twist_bevel_depth_cm
    obj["hair_twist_resolution"] = scene.hair_twist_resolution
    obj["hair_twist_taper_strength"] = scene.hair_twist_taper_strength
    obj["hair_card_roll_angle"] = float(control_obj.get("hair_card_roll_angle", scene.hair_card_default_roll_angle))
    obj["hair_card_use_parallel_transport"] = bool(control_obj.get("hair_card_use_parallel_transport", scene.hair_card_use_parallel_transport))
    obj["hair_card_mid_position"] = float(control_obj.get("hair_card_mid_position", scene.hair_card_mid_position))
    obj["hair_card_width_interpolation"] = str(control_obj.get("hair_card_width_interpolation", scene.hair_card_width_interpolation))
    if control_obj.get("hair_card_control_empty"):
        obj["hair_card_control_empty"] = control_obj["hair_card_control_empty"]
    else:
        _assign_latest_card_control_empty_if_available(context, obj)
    taper_obj = None
    if scene.hair_auto_apply_taper_to_new_curves and scene.hair_use_shared_taper:
        taper_obj, _ = _create_or_update_default_taper(context)
    obj.data.bevel_object = None
    obj["hair_curve_profile_type"] = "ROUND"
    if scene.hair_auto_apply_taper_to_new_curves and scene.hair_use_shared_taper:
        _apply_taper_to_curve_obj(context, obj, taper_obj)
    obj.data.bevel_depth = cm_to_m(scene.hair_twist_bevel_depth_cm)
    _ensure_curve_visible_geometry(context, obj)
    _apply_display_mode_to_curve(context, obj)
    _apply_work_mode_lock_to_object(context, obj)
    return obj


def _make_twist_from_point(context, point):
    scene = context.scene
    utils.ensure_system()
    curves = utils.get_curve_collection(point.get("hair_region", "Front"), "twist_control")
    twist_id = _next_twist_id()
    region = point.get("hair_region", "Front")
    direction = utils.string_to_vector(point.get("recommended_direction"), utils.direction_for_region(region))
    length = cm_to_m(scene.hair_curve_length_cm)
    root_world = point.matrix_world.translation.copy()
    world_points = []
    for i in range(max(scene.hair_curve_segment_count, 2)):
        t = i / max(scene.hair_curve_segment_count - 1, 1)
        sag = mathutils.Vector((0.0, 0.0, -0.12 * length * t * t))
        world_points.append(root_world + direction * length * t + sag)
    control_points = [p - root_world for p in world_points]
    control = utils.make_curve(f"HGD_TWIST_CTRL_{twist_id}", control_points, curves, region, "twist_control", scene, bevel=0.0)
    control.location = root_world
    control["hair_source_point"] = point.name
    control["hair_root_id"] = point.name
    control["hair_twist_id"] = twist_id
    control["hair_curve_length"] = length
    control["hair_curve_length_cm"] = scene.hair_curve_length_cm
    control["hair_card_roll_angle"] = scene.hair_card_default_roll_angle
    control["hair_card_use_parallel_transport"] = scene.hair_card_use_parallel_transport
    control["hair_card_mid_position"] = scene.hair_card_mid_position
    control["hair_card_width_interpolation"] = scene.hair_card_width_interpolation
    _assign_latest_card_control_empty_if_available(context, control)
    _move_curve_origin_to_reference_empty_if_enabled(context, control)
    control.data.resolution_u = scene.hair_twist_resolution
    _set_twist_control_display(control)
    _apply_curve_variation(control, scene, point.name)
    strand = _create_or_replace_twist_strand(context, control)
    return control, strand


def _twist_controls_from_context(context, selected_only):
    if selected_only:
        controls = []
        seen = set()
        for obj in context.selected_objects:
            if obj.get("hair_guide_type") == "twist_control":
                control = obj
            elif obj.get("hair_guide_type") == "twist_strand":
                control = bpy.data.objects.get(obj.get("hair_twist_control", ""))
            else:
                control = None
            if control and control.get("hair_guide_type") == "twist_control" and control.name not in seen:
                controls.append(control)
                seen.add(control.name)
        return controls
    return [obj for obj in utils.generated_objects("twist_control") if obj.type == "CURVE"]


def _swap_side(value, src_side, dst_side):
    if not value:
        return value
    text = str(value)
    if src_side in text:
        return text.replace(src_side, dst_side)
    if text.endswith("_L"):
        return text[:-2] + "_R"
    if text.endswith("_R"):
        return text[:-2] + "_L"
    src_short = "_L" if src_side == "Side_L" else "_R"
    dst_short = "_R" if dst_side == "Side_R" else "_L"
    if src_short in text:
        return text.replace(src_short, dst_short)
    return f"{text}_{dst_short[-1]}"


def _is_mirror_source(obj, src_side):
    if obj.get("hair_guide_type") not in {"placement_point", "curve", "twist_control"}:
        return False
    region = obj.get("hair_region", "")
    flow_side = obj.get("flow_side", "")
    if src_side == "Side_L":
        return region == "Side_L" or flow_side == "L" or obj.name.endswith("_L")
    if src_side == "Side_R":
        return region == "Side_R" or flow_side == "R" or obj.name.endswith("_R")
    return False


def _mirrored_region(obj, dst_side):
    region = obj.get("hair_region", "")
    if region in {"Side_L", "Side_R"}:
        return dst_side
    return region


def _mirrored_flow_side(dst_side):
    return "R" if dst_side == "Side_R" else "L"


def _mirror_side_from_object(obj):
    flow_side = obj.get("flow_side", "")
    if flow_side in {"L", "R", "Center"}:
        return flow_side
    region = obj.get("hair_region", "")
    if region == "Side_L":
        return "L"
    if region == "Side_R":
        return "R"
    return ""


def _set_curve_mirror_metadata(curve_obj, point_obj):
    curve_obj["hair_mirror_pair"] = ""
    curve_obj["hair_mirror_source"] = ""
    curve_obj["hair_mirror_side"] = _mirror_side_from_object(point_obj)


def _link_created_curve_mirror_pairs(curves_by_point):
    for point_name, curve_obj in curves_by_point.items():
        point_obj = bpy.data.objects.get(point_name)
        if not point_obj:
            continue
        paired_point_name = point_obj.get("hair_mirror_pair", "")
        paired_curve = curves_by_point.get(paired_point_name)
        if not paired_curve:
            continue
        curve_obj["hair_mirror_pair"] = paired_curve.name
        paired_curve["hair_mirror_pair"] = curve_obj.name


def _copy_mirrored_bezier_shape(source, target, mirror_x):
    if source.type != "CURVE" or target.type != "CURVE":
        return False
    source_splines = [s for s in source.data.splines if s.type == "BEZIER"]
    target_splines = [s for s in target.data.splines if s.type == "BEZIER"]
    if len(source_splines) != len(target_splines):
        return False
    target_world_inv = target.matrix_world.inverted()
    for source_spline, target_spline in zip(source_splines, target_splines):
        if len(source_spline.bezier_points) != len(target_spline.bezier_points):
            return False
        for source_point, target_point in zip(source_spline.bezier_points, target_spline.bezier_points):
            for attr in ("co", "handle_left", "handle_right"):
                world_co = source.matrix_world @ getattr(source_point, attr)
                world_co.x = mirror_x - (world_co.x - mirror_x)
                setattr(target_point, attr, target_world_inv @ world_co)
            target_point.handle_left_type = source_point.handle_left_type
            target_point.handle_right_type = source_point.handle_right_type
    return True


def _copy_custom_properties(source, target):
    for key in source.keys():
        target[key] = source[key]


def _delete_generated_if_exists(name):
    existing = bpy.data.objects.get(name)
    if not existing or existing.get("hair_guide_type") not in {"placement_point", "curve", "twist_control", "twist_strand"}:
        return False
    if existing not in utils.generated_objects():
        return False
    bpy.data.objects.remove(existing, do_unlink=True)
    return True


TAPER_OBJECT_NAME = "HGD_Default_Taper"
TAPER_PRESET_VALUES = {
    "ANIME": (1.0, 0.65, 0.15),
    "SHARP": (1.0, 0.45, 0.05),
    "LONG": (1.0, 0.85, 0.20),
    "STRAIGHT": (1.0, 1.0, 1.0),
    # Legacy enum values are mapped for compatibility with files saved by older versions.
    "SHARP_ANIME": (1.0, 0.45, 0.05),
    "SOFT": (1.0, 0.85, 0.20),
    "REALISTIC": (1.0, 0.65, 0.15),
}
TAPER_PRESET_LABELS = {
    "ANIME": "アニメ標準",
    "SHARP": "鋭い",
    "LONG": "ロング向け",
    "STRAIGHT": "均一",
    "SHARP_ANIME": "鋭い",
    "SOFT": "ロング向け",
    "REALISTIC": "アニメ標準",
    "CUSTOM": "カスタム",
}


def _fallback_curve_bevel(scene, obj):
    guide_type = obj.get("hair_guide_type")
    if guide_type == "twist_strand":
        return cm_to_m(getattr(scene, "hair_twist_bevel_depth_cm", m_to_cm(getattr(scene, "hair_twist_bevel_depth", 0.02))))
    return cm_to_m(scene.hair_curve_bevel_depth_cm)


def _fallback_to_round_profile(scene, obj):
    obj.data.bevel_object = None
    obj.data.bevel_depth = _fallback_curve_bevel(scene, obj)
    obj["hair_curve_profile_type"] = "ROUND"
    obj["hair_profile_fallback_warning"] = "扁平断面Profileを作成できなかったため丸断面へ戻しました。"
    return False


def _ensure_curve_visible_geometry(context, obj):
    if obj.get("hair_guide_type") not in {"curve", "twist_strand"}:
        return False
    if obj.data.bevel_object is None and obj.data.bevel_depth <= 0.0:
        obj.data.bevel_depth = _fallback_curve_bevel(context.scene, obj)
        obj["hair_curve_profile_type"] = "ROUND"
        obj["hair_profile_fallback_warning"] = "表示ジオメトリがないため丸断面へ戻しました。"
        return True
    return False


def _create_or_update_default_taper(context):
    scene = context.scene
    _, collections = utils.ensure_system()
    collection = collections[utils.TAPER_OBJECTS]
    existing = bpy.data.objects.get(TAPER_OBJECT_NAME)
    created = existing is None
    if existing and existing.type != "CURVE":
        bpy.data.objects.remove(existing, do_unlink=True)
        existing = None
        created = True
    if existing:
        curve = existing.data
        for col in list(existing.users_collection):
            if col != collection:
                col.objects.unlink(existing)
        if not any(obj.name == existing.name for obj in collection.objects):
            collection.objects.link(existing)
    else:
        curve = bpy.data.curves.new(TAPER_OBJECT_NAME, "CURVE")
        existing = bpy.data.objects.new(TAPER_OBJECT_NAME, curve)
        collection.objects.link(existing)
    while len(curve.splines) > 0:
        curve.splines.remove(curve.splines[0])
    curve.dimensions = "2D"
    curve.resolution_u = scene.hair_taper_resolution
    curve.bevel_depth = 0.0
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(2)
    values = (
        (0.0, scene.hair_taper_root_radius),
        (0.5, scene.hair_taper_mid_radius),
        (1.0, scene.hair_taper_tip_radius),
    )
    for point, (x, y) in zip(spline.bezier_points, values):
        point.co = (x, y, 0.0)
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    existing.hide_viewport = True
    existing.hide_render = True
    utils.set_common_props(existing, "taper", "", scene)
    existing["hair_taper_root_radius"] = scene.hair_taper_root_radius
    existing["hair_taper_mid_radius"] = scene.hair_taper_mid_radius
    existing["hair_taper_tip_radius"] = scene.hair_taper_tip_radius
    existing["hair_taper_bevel_depth"] = scene.hair_taper_bevel_depth
    existing["hair_taper_resolution"] = scene.hair_taper_resolution
    return existing, created


def _apply_taper_to_curve_obj(context, obj, taper_obj=None):
    scene = context.scene
    obj.data.resolution_u = scene.hair_taper_resolution
    if scene.hair_use_shared_taper:
        taper_obj = taper_obj or _create_or_update_default_taper(context)[0]
        obj.data.taper_object = taper_obj
        obj["hair_use_taper"] = True
        obj["hair_taper_object"] = taper_obj.name
    else:
        obj.data.taper_object = None
        obj["hair_use_taper"] = False
        obj["hair_taper_object"] = ""
    obj["hair_taper_bevel_depth"] = scene.hair_taper_bevel_depth
    obj["hair_taper_resolution"] = scene.hair_taper_resolution
    obj["hair_taper_root_radius"] = scene.hair_taper_root_radius
    obj["hair_taper_mid_radius"] = scene.hair_taper_mid_radius
    obj["hair_taper_tip_radius"] = scene.hair_taper_tip_radius
    obj.data.bevel_object = None
    obj.data.bevel_depth = _fallback_curve_bevel(scene, obj)
    if obj.get("hair_curve_profile_type") == "FLAT":
        obj["hair_curve_profile_type"] = "ROUND"
    _ensure_curve_visible_geometry(context, obj)


def _apply_taper_to_curves(context, selected_only):
    curves = _generated_curves_from_context(context, selected_only)
    if not curves:
        return []
    taper_obj = _create_or_update_default_taper(context)[0] if context.scene.hair_use_shared_taper else None
    for obj in curves:
        _apply_taper_to_curve_obj(context, obj, taper_obj)
    return curves


def _clear_taper_from_curves(context, selected_only):
    curves = _generated_curves_from_context(context, selected_only)
    for obj in curves:
        obj.data.taper_object = None
        obj["hair_use_taper"] = False
        obj["hair_taper_object"] = ""
    return curves


def _create_or_update_flat_profile(context):
    scene = context.scene
    _, collections = utils.ensure_system()
    collection = collections[utils.PROFILE_OBJECTS]
    name = "HGD_Flat_Profile"
    existing = bpy.data.objects.get(name)
    created = False
    if existing and existing.type != "CURVE":
        bpy.data.objects.remove(existing, do_unlink=True)
        existing = None
    if existing is None:
        curve = bpy.data.curves.new(name, "CURVE")
        existing = bpy.data.objects.new(name, curve)
        collection.objects.link(existing)
        created = True
    else:
        for col in list(existing.users_collection):
            if col != collection:
                col.objects.unlink(existing)
        if not any(obj == existing for obj in collection.objects):
            collection.objects.link(existing)
    curve = existing.data
    curve.dimensions = "2D"
    curve.fill_mode = "FULL"
    curve.use_path = False
    curve.resolution_u = 12
    while curve.splines:
        curve.splines.remove(curve.splines[0])
    spline = curve.splines.new("POLY")
    point_count = 16
    spline.points.add(point_count - 1)
    half_width = scene.hair_curve_flat_width * 0.5
    half_thickness = scene.hair_curve_flat_thickness * 0.5
    for index, point in enumerate(spline.points):
        angle = math.tau * index / point_count
        point.co = (
            math.cos(angle) * half_width,
            math.sin(angle) * half_thickness,
            0.0,
            1.0,
        )
    spline.use_cyclic_u = True
    existing.hide_viewport = True
    existing.hide_render = True
    utils.set_common_props(existing, "profile", "", scene)
    existing["hair_curve_profile_type"] = "FLAT"
    existing["hair_curve_flat_width"] = scene.hair_curve_flat_width
    existing["hair_curve_flat_thickness"] = scene.hair_curve_flat_thickness
    return existing, created


def _apply_profile_to_curve_obj(context, obj, profile_obj=None):
    scene = context.scene
    if obj.get("hair_guide_type") not in {"curve", "twist_strand"}:
        return False
    _fallback_to_round_profile(scene, obj)
    obj["hair_profile_fallback_warning"] = "扁平断面Curve表示は廃止されました。扁平メッシュ生成を使用してください。"
    _ensure_curve_visible_geometry(context, obj)
    return False


def _apply_profile_to_curves(context, selected_only):
    curves = _generated_curves_from_context(context, selected_only)
    if not curves:
        return []
    profile_obj = None
    if context.scene.hair_curve_profile_type == "FLAT":
        try:
            profile_obj = _create_or_update_flat_profile(context)[0]
        except Exception:
            profile_obj = None
    for obj in curves:
        _apply_profile_to_curve_obj(context, obj, profile_obj)
    return curves


def _clear_profile_from_curves(context, selected_only):
    curves = _generated_curves_from_context(context, selected_only)
    for obj in curves:
        obj.data.bevel_object = None
        obj.data.bevel_depth = 0.0
        obj["hair_curve_profile_type"] = "NONE"
    return curves


def _flat_mesh_taper_scale(scene, obj, t):
    if obj.get("hair_use_taper") or getattr(obj.data, "taper_object", None):
        root = float(obj.get("hair_taper_root_radius", scene.hair_taper_root_radius))
        mid = float(obj.get("hair_taper_mid_radius", scene.hair_taper_mid_radius))
        tip = float(obj.get("hair_taper_tip_radius", scene.hair_taper_tip_radius))
    else:
        strength = float(getattr(scene, "hair_curve_taper_strength", 0.65))
        root = 1.0
        tip = max(1.0 - strength, 0.05)
        mid = (root + tip) * 0.5
    if t <= 0.5:
        local = t / 0.5
        return max(root + (mid - root) * local, 0.01)
    local = (t - 0.5) / 0.5
    return max(mid + (tip - mid) * local, 0.01)


def _flat_mesh_name_for_curve(curve_obj):
    base = f"HGD_FLAT_MESH_{_safe_preview_source_name(curve_obj)}"
    existing = bpy.data.objects.get(base)
    if existing and existing.get("hair_guide_type") == "flat_mesh":
        bpy.data.objects.remove(existing, do_unlink=True)
        return base
    if existing:
        return utils.unique_name(base)
    return base


FLAT_MESH_PREVIEW_PREFIX = "HGD_FLAT_MESH_PREVIEW_"


def _flat_mesh_preview_name_for_curve(curve_obj):
    return f"{FLAT_MESH_PREVIEW_PREFIX}{_safe_preview_source_name(curve_obj)}"


def _unlink_preview_reference_properties(curve_obj):
    curve_obj["hair_card_preview_object"] = ""
    curve_obj["hair_flat_mesh_preview_object"] = ""


def _clear_flat_mesh_preview_for_curve(curve_obj):
    removed = 0
    for obj in list(utils.generated_objects("flat_mesh_preview")):
        if obj.get("hair_source_curve") == curve_obj.name or obj.name == _flat_mesh_preview_name_for_curve(curve_obj):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    curve_obj["hair_flat_mesh_preview_object"] = ""
    return removed


def _remove_flat_mesh_preview_for_curve(curve_obj):
    return _clear_flat_mesh_preview_for_curve(curve_obj)


def _set_flat_mesh_preview_visible(curve_obj, visible):
    for obj in utils.generated_objects("flat_mesh_preview"):
        if obj.get("hair_source_curve") == curve_obj.name:
            obj.hide_viewport = not visible
            obj.hide_render = not visible


def _flat_mesh_normal_from_side(tangent, side, previous_normal=None):
    normal = tangent.cross(side)
    if normal.length < 1e-6:
        fallback = previous_normal if previous_normal and previous_normal.length > 1e-6 else mathutils.Vector((0.0, 0.0, 1.0))
        normal = fallback - tangent * fallback.dot(tangent) - side * fallback.dot(side)
    if normal.length < 1e-6:
        normal = side.cross(tangent)
    if normal.length < 1e-6:
        normal = mathutils.Vector((0.0, 0.0, 1.0))
    normal.normalize()
    return normal


def _flat_mesh_sharp_ring_indices(ring_segments):
    cardinal_angles = (0.0, math.pi * 0.5, math.pi, math.pi * 1.5)
    sharp_indices = set()
    for cardinal_angle in cardinal_angles:
        index = round(cardinal_angle / (2.0 * math.pi) * ring_segments) % ring_segments
        sharp_indices.add(index)
    return sharp_indices


def _build_flat_mesh_data(context, curve_obj):
    scene = context.scene
    if curve_obj.type != "CURVE" or curve_obj.get("hair_guide_type") not in {"curve", "twist_strand"}:
        return [], [], set()
    sample_count = max(int(scene.hair_card_samples), 2)
    samples = utils.sample_curve_world_points_evaluated(curve_obj, sample_count)
    if len(samples) < 2:
        return [], [], set()

    frames = _build_card_frames(context, curve_obj, samples)
    if not frames:
        return [], [], set()

    ring_segments = min(max(int(getattr(scene, "hair_flat_mesh_ring_segments", 8)), 4), 32)
    half_thickness = cm_to_m(scene.hair_flat_mesh_thickness_cm) * 0.5
    vertices = []
    faces = []
    sharp_edges = set()
    prev_normal = None
    for index, (sample, tangent, side) in enumerate(frames):
        normal = _flat_mesh_normal_from_side(tangent, side, prev_normal)
        t = index / max(len(frames) - 1, 1)
        half_width = max(_card_width(scene, t, curve_obj), 0.0) * 0.5
        for ring_index in range(ring_segments):
            angle = 2.0 * math.pi * ring_index / ring_segments
            vertex = sample + side * math.cos(angle) * half_width + normal * math.sin(angle) * half_thickness
            vertices.append(tuple(vertex))
        prev_normal = normal.copy()

    sharp_ring_indices = _flat_mesh_sharp_ring_indices(ring_segments) if scene.hair_flat_mesh_mark_side_sharp else set()
    for index in range(len(samples) - 1):
        base = index * ring_segments
        next_base = (index + 1) * ring_segments
        for ring_index in range(ring_segments):
            a = base + ring_index
            b = base + (ring_index + 1) % ring_segments
            c = next_base + (ring_index + 1) % ring_segments
            d = next_base + ring_index
            faces.append((a, b, c, d))
            if ring_index in sharp_ring_indices:
                sharp_edges.add(tuple(sorted((a, d))))
    faces.append(tuple(range(ring_segments)))
    last = (len(samples) - 1) * ring_segments
    faces.append(tuple(reversed(range(last, last + ring_segments))))
    return vertices, faces, sharp_edges


def _apply_flat_mesh_custom_props(obj, curve_obj, scene, guide_type):
    utils.set_common_props(obj, guide_type, curve_obj.get("hair_region", ""), scene)
    obj.color = curve_obj.color
    obj["hair_source_curve"] = curve_obj.name
    root_cm = float(curve_obj.get("hair_card_width_root_cm", scene.hair_card_width_root_cm))
    mid_cm = float(curve_obj.get("hair_card_width_mid_cm", scene.hair_card_width_mid_cm))
    tip_cm = float(curve_obj.get("hair_card_width_tip_cm", scene.hair_card_width_tip_cm))
    sync_widths = bool(curve_obj.get("hair_card_sync_widths", scene.hair_card_sync_widths))
    synced_cm = float(curve_obj.get("hair_card_synced_width_cm", scene.hair_card_synced_width_cm))
    obj["hair_card_width_root"] = cm_to_m(root_cm)
    obj["hair_card_width_root_cm"] = root_cm
    obj["hair_card_width_mid"] = cm_to_m(mid_cm)
    obj["hair_card_width_mid_cm"] = mid_cm
    obj["hair_card_width_tip"] = cm_to_m(tip_cm)
    obj["hair_card_width_tip_cm"] = tip_cm
    obj["hair_card_sync_widths"] = sync_widths
    obj["hair_card_synced_width_cm"] = synced_cm
    obj["hair_card_samples"] = max(int(scene.hair_card_samples), 2)
    obj["hair_card_mid_position"] = float(curve_obj.get("hair_card_mid_position", scene.hair_card_mid_position))
    obj["hair_card_width_interpolation"] = str(curve_obj.get("hair_card_width_interpolation", scene.hair_card_width_interpolation))
    obj["hair_flat_mesh_thickness"] = cm_to_m(scene.hair_flat_mesh_thickness_cm)
    obj["hair_flat_mesh_thickness_cm"] = scene.hair_flat_mesh_thickness_cm
    obj["hair_flat_mesh_ring_segments"] = min(max(int(getattr(scene, "hair_flat_mesh_ring_segments", 8)), 4), 32)
    obj["hair_flat_mesh_mark_side_sharp"] = scene.hair_flat_mesh_mark_side_sharp
    obj["hair_card_control_empty"] = curve_obj.get("hair_card_control_empty", "")


def _build_flat_mesh_mesh_data(context, curve_obj, name):
    vertices, faces, sharp_edges = _build_flat_mesh_data(context, curve_obj)
    if not vertices or not faces:
        return None
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for edge in mesh.edges:
        if tuple(sorted(edge.vertices)) in sharp_edges:
            edge.use_edge_sharp = True
    return mesh


def _create_flat_mesh_object(context, curve_obj, guide_type, name, collection):
    scene = context.scene
    mesh = _build_flat_mesh_mesh_data(context, curve_obj, name)
    if not mesh:
        return None
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    _apply_flat_mesh_custom_props(obj, curve_obj, scene, guide_type)
    if scene.hair_flat_mesh_add_subdivision:
        sub = obj.modifiers.new("HGD_Subdivision_Surface", "SUBSURF")
        sub.levels = 1
        sub.render_levels = 1
    _apply_work_mode_lock_to_object(context, obj)
    return obj


def _create_or_update_flat_mesh_preview(context, curve_obj):
    scene = context.scene
    _sync_card_width_preset_to_scene(scene)
    _sync_scene_card_width_settings_to_curve(scene, curve_obj)
    _clear_card_preview_for_curve(curve_obj)
    _, collections = utils.ensure_system()
    name = _flat_mesh_preview_name_for_curve(curve_obj)
    new_mesh = _build_flat_mesh_mesh_data(context, curve_obj, name)
    if not new_mesh:
        return None
    existing = bpy.data.objects.get(name)
    if existing and existing.get("hair_guide_type") == "flat_mesh_preview":
        preview = _replace_preview_mesh_data(existing, new_mesh)
        _apply_flat_mesh_custom_props(preview, curve_obj, scene, "flat_mesh_preview")
    else:
        preview = bpy.data.objects.new(name, new_mesh)
        collections[utils.CARD_PREVIEWS].objects.link(preview)
        _apply_flat_mesh_custom_props(preview, curve_obj, scene, "flat_mesh_preview")
        if scene.hair_flat_mesh_add_subdivision:
            sub = preview.modifiers.new("HGD_Subdivision_Surface", "SUBSURF")
            sub.levels = 1
            sub.render_levels = 1
    preview.hide_select = False
    preview["hair_select_redirect"] = True
    preview["hair_locked_preview"] = True
    preview["hair_editable"] = False
    curve_obj["hair_flat_mesh_preview_object"] = preview.name
    _apply_work_mode_lock_to_object(context, preview)
    return preview


def _create_or_update_flat_mesh_preview_keep_curve_width(context, curve_obj):
    scene = context.scene
    if curve_obj.type != "CURVE" or curve_obj.get("hair_guide_type") not in {"curve", "twist_strand"}:
        return None

    protected_props = _snapshot_custom_props(curve_obj, CARD_WIDTH_CURVE_PROP_KEYS)
    _clear_card_preview_for_curve(curve_obj)
    _, collections = utils.ensure_system()
    name = _flat_mesh_preview_name_for_curve(curve_obj)
    new_mesh = _build_flat_mesh_mesh_data(context, curve_obj, name)
    if not new_mesh:
        _restore_custom_props(curve_obj, protected_props)
        return None
    existing = bpy.data.objects.get(name)
    if existing and existing.get("hair_guide_type") == "flat_mesh_preview":
        preview = _replace_preview_mesh_data(existing, new_mesh)
    else:
        preview = bpy.data.objects.new(name, new_mesh)
        collections[utils.CARD_PREVIEWS].objects.link(preview)
        if scene.hair_flat_mesh_add_subdivision:
            sub = preview.modifiers.new("HGD_Subdivision_Surface", "SUBSURF")
            sub.levels = 1
            sub.render_levels = 1
    _apply_flat_mesh_custom_props(preview, curve_obj, scene, "flat_mesh_preview")
    _restore_custom_props(curve_obj, protected_props)
    preview.hide_select = False
    preview["hair_select_redirect"] = True
    preview["hair_locked_preview"] = True
    preview["hair_editable"] = False
    curve_obj["hair_flat_mesh_preview_object"] = preview.name
    _apply_work_mode_lock_to_object(context, preview)
    context.view_layer.update()
    return preview


def _create_flat_mesh_from_curve(context, curve_obj):
    if curve_obj.type != "CURVE" or curve_obj.get("hair_guide_type") not in {"curve", "twist_strand"}:
        return None
    _sync_scene_card_width_settings_to_curve(context.scene, curve_obj)
    _, collections = utils.ensure_system()
    mesh_name = _flat_mesh_name_for_curve(curve_obj)
    return _create_flat_mesh_object(context, curve_obj, "flat_mesh", mesh_name, collections[utils.FLAT_MESHES])


def _create_flat_meshes_from_curves(context, selected_only):
    created = []
    for curve_obj in _generated_curves_from_context(context, selected_only):
        mesh_obj = _create_flat_mesh_from_curve(context, curve_obj)
        if mesh_obj:
            created.append(mesh_obj)
    return created

CARD_PREVIEW_PREFIX = "HGD_CARD_PREVIEW_"


def _safe_preview_source_name(curve_obj):
    return curve_obj.name.replace(".", "_")


def _card_preview_name_for_curve(curve_obj):
    return f"{CARD_PREVIEW_PREFIX}{_safe_preview_source_name(curve_obj)}"


def _legacy_card_preview_name_for_curve(curve_obj):
    legacy_base = curve_obj.name.partition(".")[0]
    return f"{CARD_PREVIEW_PREFIX}{legacy_base}"


def _is_stale_card_preview_for_curve(obj, curve_obj):
    is_card_preview = obj.get("hair_guide_type") == "card_preview" or obj.name.startswith(CARD_PREVIEW_PREFIX)
    if not is_card_preview:
        return False
    if obj.get("hair_source_curve") == curve_obj.name:
        return True
    if obj.name == _card_preview_name_for_curve(curve_obj):
        return True
    if (
        obj.name.startswith(CARD_PREVIEW_PREFIX)
        and not obj.get("hair_source_curve", "")
        and obj.name == _legacy_card_preview_name_for_curve(curve_obj)
    ):
        return True
    return False


def _is_exact_card_preview_for_curve(obj, curve_obj):
    return (
        obj.get("hair_guide_type") == "card_preview"
        and obj.get("hair_source_curve") == curve_obj.name
        and obj.name == _card_preview_name_for_curve(curve_obj)
    )


def _find_card_preview_for_curve(curve_obj):
    for obj in _card_preview_cleanup_candidates():
        if _is_exact_card_preview_for_curve(obj, curve_obj):
            return obj
    return None


def _remove_mismatched_card_previews_for_curve(curve_obj):
    removed = 0
    for obj in list(_card_preview_cleanup_candidates()):
        if _is_stale_card_preview_for_curve(obj, curve_obj) and not _is_exact_card_preview_for_curve(obj, curve_obj):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    return removed


def _card_preview_cleanup_candidates():
    candidates = []
    seen = set()
    for obj in utils.generated_objects("card_preview"):
        candidates.append(obj)
        seen.add(obj.name)
    collection = utils.get_system_collection(utils.CARD_PREVIEWS, create=False)
    if collection:
        for obj in utils.collection_objects_recursive(collection):
            if obj.name not in seen and obj.name.startswith(CARD_PREVIEW_PREFIX):
                candidates.append(obj)
                seen.add(obj.name)
    return candidates


def _clear_card_preview_for_curve(curve_obj):
    removed = 0
    for obj in list(_card_preview_cleanup_candidates()):
        if _is_stale_card_preview_for_curve(obj, curve_obj):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    curve_obj["hair_card_preview_object"] = ""
    return removed


def _remove_card_preview_for_curve(curve_obj):
    return _clear_card_preview_for_curve(curve_obj)


def _clear_all_previews_for_curve(curve_obj):
    removed = _clear_card_preview_for_curve(curve_obj)
    removed += _clear_flat_mesh_preview_for_curve(curve_obj)
    return removed


def _set_card_preview_visible(curve_obj, visible):
    for obj in utils.generated_objects("card_preview"):
        if obj.get("hair_source_curve") == curve_obj.name:
            obj.hide_viewport = not visible
            obj.hide_render = not visible


def _card_width(scene, t, curve_obj=None):
    root = cm_to_m(scene.hair_card_width_root_cm)
    mid = cm_to_m(scene.hair_card_width_mid_cm)
    tip = cm_to_m(scene.hair_card_width_tip_cm)
    sync = bool(scene.hair_card_sync_widths)
    synced = float(scene.hair_card_synced_width_cm)
    mid_pos = scene.hair_card_mid_position
    mode = scene.hair_card_width_interpolation
    if curve_obj:
        root = cm_to_m(float(curve_obj.get("hair_card_width_root_cm", scene.hair_card_width_root_cm)))
        mid = cm_to_m(float(curve_obj.get("hair_card_width_mid_cm", scene.hair_card_width_mid_cm)))
        tip = cm_to_m(float(curve_obj.get("hair_card_width_tip_cm", scene.hair_card_width_tip_cm)))
        sync = bool(curve_obj.get("hair_card_sync_widths", scene.hair_card_sync_widths))
        synced = float(curve_obj.get("hair_card_synced_width_cm", scene.hair_card_synced_width_cm))
        mid_pos = float(curve_obj.get("hair_card_mid_position", mid_pos))
        mode = str(curve_obj.get("hair_card_width_interpolation", mode))
    if sync:
        return cm_to_m(synced)
    mid_pos = max(0.05, min(0.95, mid_pos))

    def _ease(f):
        f = max(0.0, min(1.0, f))
        if mode == "LINEAR":
            return f
        if mode == "SHARP":
            return f * f
        return f * f * (3.0 - 2.0 * f)

    if t <= mid_pos:
        f = _ease(t / mid_pos)
        return root + (mid - root) * f
    f = _ease((t - mid_pos) / (1.0 - mid_pos))
    return mid + (tip - mid) * f



CARD_WIDTH_CURVE_PROP_KEYS = (
    "hair_card_width_root_cm",
    "hair_card_width_mid_cm",
    "hair_card_width_tip_cm",
    "hair_card_sync_widths",
    "hair_card_synced_width_cm",
    "hair_card_mid_position",
    "hair_card_width_interpolation",
    "hair_card_samples",
)


def _snapshot_custom_props(obj, keys):
    return {key: (key in obj, obj.get(key)) for key in keys}


def _restore_custom_props(obj, snapshot):
    for key, (exists, value) in snapshot.items():
        if exists:
            obj[key] = value
        elif key in obj:
            del obj[key]

def _sync_scene_card_width_settings_to_curve(scene, curve_obj):
    """
    UI上のCARD幅設定を、対象CurveのCustom Propertyへ同期する。
    CARD Preview更新・表示モード適用の直前に必ず呼ぶ。
    """
    _sync_card_width_preset_to_scene(scene)
    curve_obj["hair_card_mid_position"] = scene.hair_card_mid_position
    curve_obj["hair_card_width_interpolation"] = scene.hair_card_width_interpolation
    curve_obj["hair_card_width_root_cm"] = scene.hair_card_width_root_cm
    curve_obj["hair_card_width_mid_cm"] = scene.hair_card_width_mid_cm
    curve_obj["hair_card_width_tip_cm"] = scene.hair_card_width_tip_cm
    curve_obj["hair_card_sync_widths"] = scene.hair_card_sync_widths
    curve_obj["hair_card_synced_width_cm"] = scene.hair_card_synced_width_cm
    curve_obj["hair_card_samples"] = scene.hair_card_samples


def _resolve_card_settings_source_from_selection(context):
    active = context.active_object
    candidates = []
    if active:
        candidates.append(active)
    candidates.extend([obj for obj in context.selected_objects if obj != active])

    for obj in candidates:
        if not obj:
            continue
        guide_type = obj.get("hair_guide_type", "")
        if guide_type == "card_preview":
            return obj
        if guide_type in {"curve", "twist_strand"}:
            return obj
        if guide_type in {"flat_mesh_preview", "card_mesh", "flat_mesh"}:
            source = bpy.data.objects.get(obj.get("hair_source_curve", ""))
            if source:
                return source
    return None


def _read_float_prop(obj, key, fallback):
    try:
        return float(obj.get(key, fallback))
    except Exception:
        return fallback


def _read_int_prop(obj, key, fallback):
    try:
        return int(obj.get(key, fallback))
    except Exception:
        return fallback


def _read_bool_prop(obj, key, fallback):
    try:
        return bool(obj.get(key, fallback))
    except Exception:
        return fallback


def _store_scene_card_width_shape(curve_obj, scene):
    _sync_scene_card_width_settings_to_curve(scene, curve_obj)


def _build_card_preview_mesh(context, curve_obj, name):
    scene = context.scene
    sample_count = int(curve_obj.get("hair_card_samples", scene.hair_card_samples))
    samples = utils.sample_curve_world_points_evaluated(curve_obj, max(sample_count, 2))
    if len(samples) < 2:
        return None, []
    frames = _build_card_frames(context, curve_obj, samples)
    if not frames:
        return None, samples
    vertices = []
    faces = []
    for index, (sample, _tangent, side) in enumerate(frames):
        t = index / max(len(frames) - 1, 1)
        half_width = max(_card_width(scene, t, curve_obj), 0.0) * 0.5
        vertices.append(tuple(sample - side * half_width))
        vertices.append(tuple(sample + side * half_width))
    for index in range(len(frames) - 1):
        base = index * 2
        faces.append((base, base + 1, base + 3, base + 2))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    return mesh, samples


def _apply_card_preview_props(preview, curve_obj, scene, samples):
    utils.set_common_props(preview, "card_preview", curve_obj.get("hair_region", ""), scene)
    preview.color = curve_obj.color
    preview.hide_select = False
    preview["hair_select_redirect"] = True
    preview["hair_source_curve"] = curve_obj.name
    preview["hair_locked_preview"] = True
    preview["hair_editable"] = False
    mid_pos = float(curve_obj.get("hair_card_mid_position", scene.hair_card_mid_position))
    width_interpolation = str(curve_obj.get("hair_card_width_interpolation", scene.hair_card_width_interpolation))
    curve_obj["hair_card_mid_position"] = mid_pos
    curve_obj["hair_card_width_interpolation"] = width_interpolation
    preview["hair_card_mid_position"] = mid_pos
    preview["hair_card_width_interpolation"] = width_interpolation
    root_cm = float(curve_obj.get("hair_card_width_root_cm", scene.hair_card_width_root_cm))
    mid_cm = float(curve_obj.get("hair_card_width_mid_cm", scene.hair_card_width_mid_cm))
    tip_cm = float(curve_obj.get("hair_card_width_tip_cm", scene.hair_card_width_tip_cm))
    sync_widths = bool(curve_obj.get("hair_card_sync_widths", scene.hair_card_sync_widths))
    synced_cm = float(curve_obj.get("hair_card_synced_width_cm", scene.hair_card_synced_width_cm))
    preview["hair_card_width_root"] = cm_to_m(root_cm)
    preview["hair_card_width_root_cm"] = root_cm
    preview["hair_card_width_mid"] = cm_to_m(mid_cm)
    preview["hair_card_width_mid_cm"] = mid_cm
    preview["hair_card_width_tip"] = cm_to_m(tip_cm)
    preview["hair_card_width_tip_cm"] = tip_cm
    preview["hair_card_sync_widths"] = sync_widths
    preview["hair_card_synced_width_cm"] = synced_cm
    preview["hair_card_samples"] = len(samples)
    preview["hair_card_roll_angle"] = float(curve_obj.get("hair_card_roll_angle", scene.hair_card_default_roll_angle))
    preview["hair_card_use_parallel_transport"] = bool(curve_obj.get("hair_card_use_parallel_transport", scene.hair_card_use_parallel_transport))
    preview.show_in_front = curve_obj.show_in_front


def _create_or_update_card_preview_for_scene(context, curve_obj):
    scene = context.scene
    _sync_card_width_preset_to_scene(scene)
    _sync_scene_card_width_settings_to_curve(scene, curve_obj)
    _clear_flat_mesh_preview_for_curve(curve_obj)
    if curve_obj.type != "CURVE" or curve_obj.get("hair_guide_type") not in {"curve", "twist_strand"}:
        return None
    _remove_mismatched_card_previews_for_curve(curve_obj)
    name = _card_preview_name_for_curve(curve_obj)
    mesh, samples = _build_card_preview_mesh(context, curve_obj, name)
    if not mesh:
        return None
    existing = _find_card_preview_for_curve(curve_obj)
    if existing:
        preview = _replace_preview_mesh_data(existing, mesh)
    else:
        preview = bpy.data.objects.new(name, mesh)
        _, collections = utils.ensure_system()
        collections[utils.CARD_PREVIEWS].objects.link(preview)
    _apply_card_preview_props(preview, curve_obj, scene, samples)
    preview["debug_card_width_root_cm"] = float(curve_obj.get("hair_card_width_root_cm", scene.hair_card_width_root_cm))
    preview["debug_card_width_mid_cm"] = float(curve_obj.get("hair_card_width_mid_cm", scene.hair_card_width_mid_cm))
    preview["debug_card_width_tip_cm"] = float(curve_obj.get("hair_card_width_tip_cm", scene.hair_card_width_tip_cm))
    preview["debug_card_vertex_count"] = len(preview.data.vertices)
    preview.hide_viewport = False
    preview.hide_render = False
    curve_obj["hair_card_preview_object"] = preview.name
    if scene.hair_work_mode_lock_enabled:
        preview.hide_select = False
    return preview

def _create_or_update_card_preview(context, curve_obj):
    preview = _create_or_update_card_preview_for_scene(context, curve_obj)
    if preview:
        preview.data.update()
        preview.update_tag(refresh={'DATA'})
        context.view_layer.update()
        _apply_work_mode_lock_to_object(context, preview)
    return preview


def _create_or_update_card_preview_keep_curve_width(context, curve_obj):
    scene = context.scene
    if curve_obj.type != "CURVE" or curve_obj.get("hair_guide_type") not in {"curve", "twist_strand"}:
        return None

    protected_props = _snapshot_custom_props(curve_obj, CARD_WIDTH_CURVE_PROP_KEYS)
    _clear_flat_mesh_preview_for_curve(curve_obj)
    _remove_mismatched_card_previews_for_curve(curve_obj)
    name = _card_preview_name_for_curve(curve_obj)
    mesh, samples = _build_card_preview_mesh(context, curve_obj, name)
    if not mesh:
        _restore_custom_props(curve_obj, protected_props)
        return None

    existing = _find_card_preview_for_curve(curve_obj)
    if existing:
        preview = _replace_preview_mesh_data(existing, mesh)
    else:
        preview = bpy.data.objects.new(name, mesh)
        _, collections = utils.ensure_system()
        collections[utils.CARD_PREVIEWS].objects.link(preview)

    _apply_card_preview_props(preview, curve_obj, scene, samples)
    _restore_custom_props(curve_obj, protected_props)
    preview["debug_card_width_root_cm"] = float(curve_obj.get("hair_card_width_root_cm", scene.hair_card_width_root_cm))
    preview["debug_card_width_mid_cm"] = float(curve_obj.get("hair_card_width_mid_cm", scene.hair_card_width_mid_cm))
    preview["debug_card_width_tip_cm"] = float(curve_obj.get("hair_card_width_tip_cm", scene.hair_card_width_tip_cm))
    preview["debug_card_vertex_count"] = len(preview.data.vertices)
    preview.hide_viewport = False
    preview.hide_render = False
    curve_obj["hair_card_preview_object"] = preview.name
    if scene.hair_work_mode_lock_enabled:
        preview.hide_select = False
    preview.data.update()
    preview.update_tag(refresh={'DATA'})
    _apply_work_mode_lock_to_object(context, preview)
    context.view_layer.update()
    return preview


def _card_mesh_name_for_curve(curve_obj):
    base = f"HGD_CARD_MESH_{_safe_preview_source_name(curve_obj)}"
    return utils.unique_name(base) if bpy.data.objects.get(base) else base


def _curve_has_card_preview(curve_obj):
    if curve_obj.get("hair_curve_display_mode") == "CARD":
        return True
    preview_name = curve_obj.get("hair_card_preview_object", "")
    if preview_name and bpy.data.objects.get(preview_name):
        return True
    return any(obj.get("hair_source_curve") == curve_obj.name for obj in utils.generated_objects("card_preview"))


def _create_card_mesh_from_curve(context, curve_obj):
    scene = context.scene
    _sync_scene_card_width_settings_to_curve(scene, curve_obj)
    if curve_obj.type != "CURVE" or curve_obj.get("hair_guide_type") not in {"curve", "twist_strand"}:
        return None
    sample_count = int(curve_obj.get("hair_card_samples", scene.hair_card_samples))
    samples = utils.sample_curve_world_points_evaluated(curve_obj, max(sample_count, 2))
    if len(samples) < 2:
        return None
    frames = _build_card_frames(context, curve_obj, samples)
    if not frames:
        return None
    vertices = []
    faces = []
    for index, (sample, _tangent, side) in enumerate(frames):
        t = index / max(len(frames) - 1, 1)
        half_width = max(_card_width(scene, t, curve_obj), 0.0) * 0.5
        vertices.append(tuple(sample - side * half_width))
        vertices.append(tuple(sample + side * half_width))
    for index in range(len(frames) - 1):
        base = index * 2
        faces.append((base, base + 1, base + 3, base + 2))
    _, collections = utils.ensure_system()
    name = _card_mesh_name_for_curve(curve_obj)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collections[utils.CARD_MESHES].objects.link(obj)
    utils.set_common_props(obj, "card_mesh", curve_obj.get("hair_region", ""), scene)
    obj.color = curve_obj.color
    obj["hair_source_curve"] = curve_obj.name
    obj["hair_region"] = curve_obj.get("hair_region", "")
    mid_pos = float(curve_obj.get("hair_card_mid_position", scene.hair_card_mid_position))
    width_interpolation = str(curve_obj.get("hair_card_width_interpolation", scene.hair_card_width_interpolation))
    curve_obj["hair_card_mid_position"] = mid_pos
    curve_obj["hair_card_width_interpolation"] = width_interpolation
    obj["hair_card_mid_position"] = mid_pos
    obj["hair_card_width_interpolation"] = width_interpolation
    root_cm = float(curve_obj.get("hair_card_width_root_cm", scene.hair_card_width_root_cm))
    mid_cm = float(curve_obj.get("hair_card_width_mid_cm", scene.hair_card_width_mid_cm))
    tip_cm = float(curve_obj.get("hair_card_width_tip_cm", scene.hair_card_width_tip_cm))
    sync_widths = bool(curve_obj.get("hair_card_sync_widths", scene.hair_card_sync_widths))
    synced_cm = float(curve_obj.get("hair_card_synced_width_cm", scene.hair_card_synced_width_cm))
    obj["hair_card_width_root"] = cm_to_m(root_cm)
    obj["hair_card_width_root_cm"] = root_cm
    obj["hair_card_width_mid"] = cm_to_m(mid_cm)
    obj["hair_card_width_mid_cm"] = mid_cm
    obj["hair_card_width_tip"] = cm_to_m(tip_cm)
    obj["hair_card_width_tip_cm"] = tip_cm
    obj["hair_card_sync_widths"] = sync_widths
    obj["hair_card_synced_width_cm"] = synced_cm
    obj["hair_card_samples"] = len(samples)
    obj["hair_card_roll_angle"] = float(curve_obj.get("hair_card_roll_angle", scene.hair_card_default_roll_angle))
    obj["hair_card_use_parallel_transport"] = bool(curve_obj.get("hair_card_use_parallel_transport", scene.hair_card_use_parallel_transport))
    _apply_work_mode_lock_to_object(context, obj)
    return obj


def _create_card_meshes_from_curves(context, selected_only):
    created = []
    curves = resolve_card_display_curves_from_selection(context) if selected_only else [
        obj for obj in utils.generated_objects()
        if obj.type == "CURVE" and obj.get("hair_guide_type") in {"curve", "twist_strand"}
    ]
    for curve_obj in curves:
        mesh_obj = _create_card_mesh_from_curve(context, curve_obj)
        if mesh_obj:
            created.append(mesh_obj)
    return created

def _apply_display_mode_to_curve(context, obj):
    scene = context.scene
    if obj.type != "CURVE" or obj.get("hair_guide_type") not in {"curve", "twist_strand"}:
        return False
    mode = scene.hair_curve_display_mode
    if mode == "CURVE":
        obj.data.bevel_depth = 0.0
        obj.data.bevel_object = None
        obj.data.taper_object = None
        _clear_all_previews_for_curve(obj)
    elif mode == "SOLID":
        obj.display_type = 'TEXTURED'
        obj.data.bevel_object = None
        obj.data.bevel_depth = _fallback_curve_bevel(scene, obj)
        if scene.hair_use_shared_taper:
            _apply_taper_to_curve_obj(context, obj)
        else:
            obj.data.taper_object = None
            obj["hair_use_taper"] = False
            obj["hair_taper_object"] = ""
        _clear_all_previews_for_curve(obj)
        _ensure_curve_visible_geometry(context, obj)
    elif mode == "CARD":
        _sync_card_width_preset_to_scene(scene)
        _sync_scene_card_width_settings_to_curve(scene, obj)
        obj.hide_viewport = False
        obj.display_type = 'WIRE'
        obj.data.bevel_depth = 0.0
        obj.data.bevel_object = None
        obj.data.taper_object = None
        preview = _create_or_update_card_preview(context, obj)
        if preview:
            preview.hide_viewport = False
            preview.hide_render = False
            preview["hair_source_curve"] = obj.name
            preview.hide_select = False
            preview["hair_select_redirect"] = True
            preview["hair_locked_preview"] = True
        _set_card_preview_visible(obj, True)
        _set_flat_mesh_preview_visible(obj, False)
    elif mode == "FLAT_MESH":
        _sync_card_width_preset_to_scene(scene)
        _sync_scene_card_width_settings_to_curve(scene, obj)
        obj.hide_viewport = False
        obj.display_type = 'WIRE'
        obj.data.bevel_depth = 0.0
        obj.data.bevel_object = None
        obj.data.taper_object = None
        _set_card_preview_visible(obj, False)
        preview = _create_or_update_flat_mesh_preview(context, obj)
        if preview:
            preview.hide_viewport = False
            preview.hide_render = False
            preview["hair_source_curve"] = obj.name
            preview.hide_select = False
            preview["hair_select_redirect"] = True
            preview["hair_locked_preview"] = True
        _set_flat_mesh_preview_visible(obj, True)
    obj["hair_curve_display_mode"] = mode
    if obj.get("hair_guide_type") == "twist_strand":
        obj["hair_twist_display_preview_ready"] = True
    return True


def _apply_display_mode_to_curves(context, selected_only):
    curves = _generated_curves_from_context(context, selected_only)
    for obj in curves:
        _apply_display_mode_to_curve(context, obj)
    return curves


def _apply_shape_to_curves(context, selected_only):
    curves = _generated_curves_from_context(context, selected_only)
    if not curves:
        return []
    scene = context.scene
    taper_obj = _create_or_update_default_taper(context)[0] if scene.hair_use_shared_taper else None
    for obj in curves:
        guide_type = obj.get("hair_guide_type")
        resolution = scene.hair_twist_resolution if guide_type == "twist_strand" else scene.hair_curve_resolution
        bevel_depth = _fallback_curve_bevel(scene, obj)
        obj.data.resolution_u = resolution
        obj.data.bevel_depth = bevel_depth
        obj.data.bevel_object = None
        obj["hair_curve_profile_type"] = "ROUND"
        if guide_type == "twist_strand":
            obj["hair_twist_bevel_depth"] = bevel_depth
            obj["hair_twist_bevel_depth_cm"] = scene.hair_twist_bevel_depth_cm
            obj["hair_twist_resolution"] = resolution
        else:
            obj["hair_curve_bevel_depth"] = bevel_depth
            obj["hair_curve_bevel_depth_cm"] = scene.hair_curve_bevel_depth_cm
            obj["hair_curve_resolution"] = resolution
        if scene.hair_use_shared_taper:
            _apply_taper_to_curve_obj(context, obj, taper_obj)
        else:
            obj.data.taper_object = None
            obj["hair_use_taper"] = False
            obj["hair_taper_object"] = ""
        obj.data.resolution_u = resolution
        obj.data.bevel_depth = bevel_depth
        if guide_type == "twist_strand":
            obj["hair_twist_bevel_depth"] = bevel_depth
            obj["hair_twist_bevel_depth_cm"] = scene.hair_twist_bevel_depth_cm
            obj["hair_twist_resolution"] = resolution
        else:
            obj["hair_curve_bevel_depth"] = bevel_depth
            obj["hair_curve_bevel_depth_cm"] = scene.hair_curve_bevel_depth_cm
            obj["hair_curve_resolution"] = resolution
    return curves


def _clear_shape_from_curves(context, selected_only):
    curves = _generated_curves_from_context(context, selected_only)
    for obj in curves:
        obj.data.bevel_object = None
        obj.data.taper_object = None
        obj.data.bevel_depth = 0.0
        obj["hair_curve_profile_type"] = "NONE"
        obj["hair_use_taper"] = False
        obj["hair_taper_object"] = ""
    return curves


class HGD_OT_apply_card_width_preset(bpy.types.Operator):
    bl_idname = "hgd.apply_card_width_preset"
    bl_label = "CARD幅プリセットを反映"
    bl_description = "選択中のCARD幅プリセット値をRoot/Mid/Tip幅へ反映します。同期設定や同期幅は変更しません"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        preset = scene.hair_card_width_preset
        _sync_card_width_preset_to_scene(scene)
        if preset == "CUSTOM":
            self.report({'INFO'}, "カスタム設定を使用します。")
            return {'FINISHED'}
        self.report({'INFO'}, f"CARD幅プリセット「{CARD_WIDTH_PRESET_LABELS.get(preset, preset)}」を反映しました。")
        return {'FINISHED'}


class HGD_OT_load_card_preview_settings_to_scene(bpy.types.Operator):
    bl_idname = "hgd.load_card_preview_settings_to_scene"
    bl_label = "現在のPreview設定を読み込み"
    bl_description = "選択中のCARD Previewまたは参照元CurveからRoot/Mid/Tip幅、Mid位置、幅補間、分割数を読み込み、CARD幅プリセットをCUSTOMにします。"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        source = _resolve_card_settings_source_from_selection(context)
        if not source:
            self.report({'WARNING'}, "CARD設定を読み込めるPreview、Curve、または参照元Curve付きMeshが選択されていません。")
            return {'CANCELLED'}

        width_keys = (
            "hair_card_width_root_cm",
            "hair_card_width_mid_cm",
            "hair_card_width_tip_cm",
        )
        if not any(key in source for key in width_keys):
            self.report({'WARNING'}, "選択対象にRoot/Mid/Tip幅のPreview設定がありません。")
            return {'CANCELLED'}

        scene.hair_card_width_preset = "CUSTOM"
        scene.hair_card_width_root_cm = _read_float_prop(source, "hair_card_width_root_cm", scene.hair_card_width_root_cm)
        scene.hair_card_width_mid_cm = _read_float_prop(source, "hair_card_width_mid_cm", scene.hair_card_width_mid_cm)
        scene.hair_card_width_tip_cm = _read_float_prop(source, "hair_card_width_tip_cm", scene.hair_card_width_tip_cm)
        scene.hair_card_mid_position = _read_float_prop(source, "hair_card_mid_position", scene.hair_card_mid_position)

        width_interpolation = str(source.get("hair_card_width_interpolation", scene.hair_card_width_interpolation))
        enum_items = scene.bl_rna.properties["hair_card_width_interpolation"].enum_items
        if width_interpolation in {item.identifier for item in enum_items}:
            scene.hair_card_width_interpolation = width_interpolation

        scene.hair_card_samples = _read_int_prop(source, "hair_card_samples", scene.hair_card_samples)
        scene.hair_card_sync_widths = False
        scene.hair_card_synced_width_cm = _read_float_prop(source, "hair_card_synced_width_cm", scene.hair_card_synced_width_cm)
        scene.hair_card_default_roll_angle = _read_float_prop(source, "hair_card_roll_angle", scene.hair_card_default_roll_angle)
        scene.hair_card_use_parallel_transport = _read_bool_prop(source, "hair_card_use_parallel_transport", scene.hair_card_use_parallel_transport)

        self.report({'INFO'}, f"{source.name} からCARD Preview設定を読み込み、プリセットをCUSTOMにしました。")
        return {'FINISHED'}


class HGD_OT_apply_taper_preset(bpy.types.Operator):
    bl_idname = "hgd.apply_taper_preset"
    bl_label = "プリセットを反映"
    bl_description = "選択中のテーパープリセット値をカーブ形状へ反映します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        preset = scene.hair_taper_preset
        if preset == "CUSTOM":
            self.report({'INFO'}, "カスタム設定を使用します。現在値は変更しません。")
            return {'FINISHED'}
        root, mid, tip = TAPER_PRESET_VALUES.get(preset, TAPER_PRESET_VALUES["ANIME"])
        scene.hair_taper_root_radius = root
        scene.hair_taper_mid_radius = mid
        scene.hair_taper_tip_radius = tip
        self.report({'INFO'}, f"プリセット「{TAPER_PRESET_LABELS[preset]}」を反映しました。")
        return {'FINISHED'}


class HGD_OT_create_or_update_default_taper(bpy.types.Operator):
    bl_idname = "hgd.create_or_update_default_taper"
    bl_label = "テーパー形状を作成/更新"
    bl_description = "共有テーパーオブジェクトHGD_Default_Taperを作成または現在値で更新します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            _, created = _create_or_update_default_taper(context)
            self.report({'INFO'}, "テーパー形状を作成しました。" if created else "テーパー形状を更新しました。")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"テーパー形状の作成/更新に失敗しました: {exc}")
            return {'CANCELLED'}


class HGD_OT_apply_taper_to_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.apply_taper_to_selected_curves"
    bl_label = "選択カーブへ適用"
    bl_description = "選択中の生成済み髪カーブへ共有テーパーと太さを適用します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _apply_taper_to_curves(context, True)
        if not curves:
            self.report({'WARNING'}, "生成済み髪カーブが選択されていません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"選択カーブ {len(curves)} 本へテーパーを適用しました。")
        return {'FINISHED'}


class HGD_OT_apply_taper_to_all_curves(bpy.types.Operator):
    bl_idname = "hgd.apply_taper_to_all_curves"
    bl_label = "全カーブへ適用"
    bl_description = "すべての生成済み髪カーブへ共有テーパーと太さを適用します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _apply_taper_to_curves(context, False)
        if not curves:
            self.report({'WARNING'}, "生成済み髪カーブが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"全カーブ {len(curves)} 本へテーパーを適用しました。")
        return {'FINISHED'}


class HGD_OT_clear_taper_from_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.clear_taper_from_selected_curves"
    bl_label = "選択カーブのテーパー解除"
    bl_description = "選択中の生成済み髪カーブからテーパーを解除します。太さは維持します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _clear_taper_from_curves(context, True)
        if not curves:
            self.report({'WARNING'}, "生成済み髪カーブが選択されていません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"選択カーブ {len(curves)} 本のテーパーを解除しました。")
        return {'FINISHED'}


class HGD_OT_clear_taper_from_all_curves(bpy.types.Operator):
    bl_idname = "hgd.clear_taper_from_all_curves"
    bl_label = "全カーブのテーパー解除"
    bl_description = "すべての生成済み髪カーブからテーパーを解除します。太さは維持します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _clear_taper_from_curves(context, False)
        if not curves:
            self.report({'WARNING'}, "生成済み髪カーブが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"全カーブ {len(curves)} 本のテーパーを解除しました。")
        return {'FINISHED'}


class HGD_OT_create_or_update_flat_profile(bpy.types.Operator):
    bl_idname = "hgd.create_or_update_flat_profile"
    bl_label = "扁平断面を作成/更新"
    bl_description = "廃止済みです。扁平メッシュ生成を使用してください"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'WARNING'}, "扁平断面Curve表示は廃止されました。扁平メッシュ生成を使用してください。")
        return {'CANCELLED'}


class HGD_OT_apply_profile_to_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.apply_profile_to_selected_curves"
    bl_label = "選択カーブへ断面を適用"
    bl_description = "廃止済みです。扁平メッシュ生成を使用してください"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'WARNING'}, "扁平断面Curve表示は廃止されました。扁平メッシュ生成を使用してください。")
        return {'CANCELLED'}


class HGD_OT_apply_profile_to_all_curves(bpy.types.Operator):
    bl_idname = "hgd.apply_profile_to_all_curves"
    bl_label = "全カーブへ断面を適用"
    bl_description = "廃止済みです。扁平メッシュ生成を使用してください"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'WARNING'}, "扁平断面Curve表示は廃止されました。扁平メッシュ生成を使用してください。")
        return {'CANCELLED'}


class HGD_OT_clear_profile_from_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.clear_profile_from_selected_curves"
    bl_label = "選択カーブの断面解除"
    bl_description = "廃止済みです。扁平メッシュ生成を使用してください"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'WARNING'}, "扁平断面Curve表示は廃止されました。扁平メッシュ生成を使用してください。")
        return {'CANCELLED'}


class HGD_OT_clear_profile_from_all_curves(bpy.types.Operator):
    bl_idname = "hgd.clear_profile_from_all_curves"
    bl_label = "全カーブの断面解除"
    bl_description = "廃止済みです。扁平メッシュ生成を使用してください"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'WARNING'}, "扁平断面Curve表示は廃止されました。扁平メッシュ生成を使用してください。")
        return {'CANCELLED'}


class HGD_OT_update_flat_mesh_previews_from_curves(bpy.types.Operator):
    bl_idname = "hgd.update_flat_mesh_previews_from_curves"
    bl_label = "Flat Mesh Preview更新"
    bl_description = "選択中または全Flat Mesh表示Curveから、現在のCurve形状でFlat Mesh Previewを再生成します。確定Meshは作成しません"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _sync_card_width_preset_to_scene(context.scene)
        curves = _generated_curves_from_context(context, True)
        if not curves:
            curves = [
                obj for obj in utils.generated_objects()
                if obj.type == "CURVE"
                and obj.get("hair_guide_type") in {"curve", "twist_strand"}
                and obj.get("hair_curve_display_mode") == "FLAT_MESH"
            ]
        updated = 0
        for obj in curves:
            preview = _create_or_update_flat_mesh_preview(context, obj)
            if preview:
                preview.hide_viewport = False
                preview.hide_render = False
                preview["hair_source_curve"] = obj.name
                preview.hide_select = False
                preview["hair_select_redirect"] = True
                preview["hair_locked_preview"] = True
                _set_flat_mesh_preview_visible(obj, True)
                updated += 1
        if updated == 0:
            self.report({'WARNING'}, "更新できるFlat Mesh Preview対象Curveがありません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Flat Mesh Previewを{updated}個更新しました。")
        return {'FINISHED'}


class HGD_OT_create_flat_mesh_from_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.create_flat_mesh_from_selected_curves"
    bl_label = "選択カーブから扁平メッシュ生成"
    bl_description = "選択CurveからFlat Meshを実体化します。元Curveは残りますが、Meshが新規作成されます。"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        meshes = _create_flat_meshes_from_curves(context, True)
        if not meshes:
            self.report({'WARNING'}, "扁平メッシュ化できる表示用カーブが選択されていません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"選択カーブから扁平メッシュを{len(meshes)}個生成しました。元Curveは残しています。")
        return {'FINISHED'}


class HGD_OT_create_flat_mesh_from_all_curves(bpy.types.Operator):
    bl_idname = "hgd.create_flat_mesh_from_all_curves"
    bl_label = "全カーブから扁平メッシュ生成"
    bl_description = "全CurveからFlat Meshを実体化します。大量のMeshが作成される可能性があります。"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        meshes = _create_flat_meshes_from_curves(context, False)
        if not meshes:
            self.report({'WARNING'}, "扁平メッシュ化できる表示用カーブが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"全カーブから扁平メッシュを{len(meshes)}個生成しました。元Curveは残しています。")
        return {'FINISHED'}


class HGD_OT_export_flat_mesh_from_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.export_flat_mesh_from_selected_curves"
    bl_label = "選択Curveを扁平メッシュ出力"
    bl_description = "選択CurveからFlat Meshを実体化します。元Curveは残りますが、Meshが新規作成されます。"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        meshes = _create_flat_meshes_from_curves(context, True)
        if not meshes:
            self.report({'WARNING'}, "扁平メッシュ出力できる表示用Curveが選択されていません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"選択Curve {len(meshes)} 本を扁平メッシュ出力しました。元Curveは残しています。")
        return {'FINISHED'}


class HGD_OT_convert_selected_card_preview_to_mesh(bpy.types.Operator):
    bl_idname = "hgd.convert_selected_card_preview_to_mesh"
    bl_label = "選択CurveのCARDプレビューを実体化"
    bl_description = "選択CurveからCARD Meshを実体化します。元Curveは残りますが、Meshが新規作成されます。"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        meshes = _create_card_meshes_from_curves(context, True)
        if not meshes:
            self.report({'WARNING'}, "実体化できる通常Curve/ツイスト表示Curveが選択されていません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"選択CurveをCARD Meshとして{len(meshes)}個実体化しました。")
        return {'FINISHED'}


class HGD_OT_convert_all_card_previews_to_mesh(bpy.types.Operator):
    bl_idname = "hgd.convert_all_card_previews_to_mesh"
    bl_label = "全CARDプレビューを実体化"
    bl_description = "全CurveからCARD Meshを実体化します。大量のMeshが作成される可能性があります。"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        meshes = _create_card_meshes_from_curves(context, False)
        if not meshes:
            self.report({'WARNING'}, "実体化できる通常Curve/ツイスト表示Curveが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"CurveをCARD Meshとして{len(meshes)}個実体化しました。")
        return {'FINISHED'}


def resolve_edit_curve_for_preview_redirect(obj):
    if not obj:
        return None

    guide_type = obj.get("hair_guide_type")

    if guide_type == "curve":
        return obj

    if guide_type == "twist_control":
        return obj

    if guide_type == "twist_strand":
        control_name = obj.get("hair_twist_control", "")
        control = bpy.data.objects.get(control_name)
        if control and control.get("hair_guide_type") == "twist_control":
            return control
        return None

    if guide_type == "card_preview":
        source_name = obj.get("hair_source_curve", "")
        source = bpy.data.objects.get(source_name)
        if not source:
            return None

        if source.get("hair_guide_type") == "twist_strand":
            control_name = source.get("hair_twist_control", "")
            control = bpy.data.objects.get(control_name)
            if control and control.get("hair_guide_type") == "twist_control":
                return control
            return None

        if source.get("hair_guide_type") == "curve":
            return source

    return None


def resolve_edit_curve_from_object(obj):
    return resolve_edit_curve_for_preview_redirect(obj)


def _curve_handle_twist_weight(index, count, falloff, preserve_end_handles):
    t = index / max(count - 1, 1)
    if falloff == "CENTER":
        weight = math.sin(math.pi * t)
    elif falloff == "TIP":
        weight = t * t
    else:
        weight = t
    if preserve_end_handles:
        weight *= math.sin(math.pi * t)
    return weight


def _twist_bezier_spline_handles(spline, angle_rad, strength, falloff, preserve_end_handles):
    points = spline.bezier_points
    count = len(points)
    if count < 2:
        return False

    for i, point in enumerate(points):
        if i == 0:
            tangent = points[1].co - point.co
        elif i == count - 1:
            tangent = point.co - points[count - 2].co
        else:
            tangent = points[i + 1].co - points[i - 1].co
        if tangent.length_squared == 0.0:
            continue

        weight = _curve_handle_twist_weight(i, count, falloff, preserve_end_handles)
        if weight == 0.0 and strength == 1.0:
            point.handle_left_type = "FREE"
            point.handle_right_type = "FREE"
            continue

        co = point.co.copy()
        left_vec = point.handle_left - co
        right_vec = point.handle_right - co
        rot = mathutils.Matrix.Rotation(angle_rad * weight, 4, tangent.normalized())
        point.handle_left_type = "FREE"
        point.handle_right_type = "FREE"
        point.handle_left = co + (rot @ left_vec) * strength
        point.handle_right = co + (rot @ right_vec) * strength
    return True


def _selected_point_twist_axis(obj, spline, index, axis):
    points = spline.bezier_points
    count = len(points)
    if axis == "OBJECT_Z":
        tangent = mathutils.Vector((0.0, 0.0, 1.0))
    elif axis == "WORLD_Z":
        tangent = obj.matrix_world.inverted().to_3x3() @ mathutils.Vector((0.0, 0.0, 1.0))
    else:
        if count < 2:
            return None
        if index == 0:
            tangent = points[1].co - points[0].co
        elif index == count - 1:
            tangent = points[count - 1].co - points[count - 2].co
        else:
            tangent = points[index + 1].co - points[index - 1].co
    if tangent.length < 1e-6:
        return None
    tangent.normalize()
    return tangent


def _twist_selected_bezier_points(obj, angle_rad, strength, axis):
    changed = 0
    for spline in obj.data.splines:
        if spline.type != "BEZIER":
            continue
        for i, point in enumerate(spline.bezier_points):
            if not point.select_control_point:
                continue
            tangent = _selected_point_twist_axis(obj, spline, i, axis)
            if tangent is None:
                continue
            co = point.co.copy()
            left_vec = point.handle_left - co
            right_vec = point.handle_right - co
            rot = mathutils.Matrix.Rotation(angle_rad, 4, tangent)
            point.handle_left_type = "FREE"
            point.handle_right_type = "FREE"
            point.handle_left = co + (rot @ left_vec) * strength
            point.handle_right = co + (rot @ right_vec) * strength
            changed += 1
    return changed


class HGD_OT_twist_selected_bezier_points(bpy.types.Operator):
    bl_idname = "hgd.twist_selected_bezier_points"
    bl_label = "選択点だけハンドルをねじる"
    bl_description = "Curve編集モードで選択中のBezier点の座標を維持したまま、左右ハンドルだけをねじります"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == "CURVE"
            and obj.get("hair_guide_type") in {"curve", "twist_control"}
            and context.mode == "EDIT_CURVE"
        )

    def execute(self, context):
        obj = context.active_object
        if context.mode != "EDIT_CURVE":
            self.report({'WARNING'}, "Curve編集モードで実行してください。")
            return {'CANCELLED'}
        if not obj or obj.type != "CURVE" or obj.get("hair_guide_type") not in {"curve", "twist_control"}:
            self.report({'WARNING'}, "通常Curveまたはツイスト制御Curveを編集モードで選択してください。")
            return {'CANCELLED'}

        scene = context.scene
        angle_rad = math.radians(scene.hair_curve_selected_point_twist_angle)
        strength = scene.hair_curve_selected_point_twist_strength
        axis = scene.hair_curve_selected_point_twist_axis

        bpy.ops.object.mode_set(mode='OBJECT')
        changed = _twist_selected_bezier_points(obj, angle_rad, strength, axis)
        obj.data.update_tag()
        bpy.ops.object.mode_set(mode='EDIT')

        if changed == 0:
            self.report({'WARNING'}, "選択中のBezier点がありません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"選択Bezier点 {changed}点のハンドルをねじりました。")
        return {'FINISHED'}


class HGD_OT_twist_selected_curve_handles(bpy.types.Operator):
    bl_idname = "hgd.twist_selected_curve_handles"
    bl_label = "選択Curveのハンドルをねじる"
    bl_description = "制御点座標を維持したまま、選択CurveまたはCARD参照元CurveのBezierハンドルだけをねじります"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        targets = []
        seen = set()
        for obj in context.selected_objects:
            edit_curve = resolve_edit_curve_for_preview_redirect(obj)
            if not edit_curve or edit_curve.name in seen:
                continue
            if edit_curve.type != "CURVE" or edit_curve.get("hair_guide_type") not in {"curve", "twist_control"}:
                continue
            targets.append(edit_curve)
            seen.add(edit_curve.name)

        if not targets:
            self.report({'WARNING'}, "ハンドルねじりを適用できる選択Curveがありません。")
            return {'CANCELLED'}

        angle_rad = math.radians(scene.hair_curve_twist_handle_angle)
        strength = scene.hair_curve_twist_handle_strength
        falloff = scene.hair_curve_twist_handle_falloff
        preserve = scene.hair_curve_twist_preserve_end_handles
        changed = 0
        for obj in targets:
            object_changed = False
            for spline in obj.data.splines:
                if spline.type == "BEZIER" and _twist_bezier_spline_handles(spline, angle_rad, strength, falloff, preserve):
                    object_changed = True
            if object_changed:
                obj.data.update_tag()
                changed += 1

        if changed == 0:
            self.report({'WARNING'}, "Bezierハンドルを持つ対象Curveがありません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"選択Curve {changed}本のハンドルをねじりました。")
        return {'FINISHED'}


def resolve_display_curve_from_object(context, obj):
    if not obj:
        return None

    guide_type = obj.get("hair_guide_type", "")

    if guide_type == "curve":
        return obj

    if guide_type == "twist_strand":
        return obj

    if guide_type == "twist_control":
        return _create_or_replace_twist_strand(context, obj)

    if guide_type in CARD_SELECTION_REDIRECT_TYPES:
        source_name = obj.get("hair_source_curve", "")
        source = bpy.data.objects.get(source_name)
        if not source:
            return None

        source_type = source.get("hair_guide_type", "")

        if source_type == "curve":
            return source

        if source_type == "twist_strand":
            return source

        if source_type == "twist_control":
            return _create_or_replace_twist_strand(context, source)

    return None


def _source_curve_from_redirect_object(obj):
    if not obj:
        return None
    source_name = obj.get("hair_source_curve", "")
    if not source_name:
        return None
    source = bpy.data.objects.get(source_name)
    if source and source.type == "CURVE":
        return source
    return None


def _add_unique_object(items, obj):
    if obj and obj.name not in {item.name for item in items}:
        items.append(obj)


def resolve_card_display_curve_from_object(context, obj):
    """Return the curve/twist_strand used to generate CARD display from common selections."""
    if not obj:
        return None
    guide_type = obj.get("hair_guide_type")
    if guide_type in {"curve", "twist_strand"}:
        return obj
    if guide_type == "twist_control":
        return _create_or_replace_twist_strand(context, obj)
    if guide_type in CARD_SELECTION_REDIRECT_TYPES:
        source = bpy.data.objects.get(obj.get("hair_source_curve", ""))
        if not source:
            return None
        source_type = source.get("hair_guide_type")
        if source_type in {"curve", "twist_strand"}:
            return source
        if source_type == "twist_control":
            return _create_or_replace_twist_strand(context, source)
    return None




def _resolve_origin_move_curve_from_object(obj):
    if not obj:
        return None
    guide_type = obj.get("hair_guide_type", "")
    if obj.type == "CURVE" and guide_type in {"curve", "twist_control"}:
        return obj
    if guide_type == "twist_strand":
        control = bpy.data.objects.get(obj.get("hair_twist_control", ""))
        if control and control.type == "CURVE" and control.get("hair_guide_type") == "twist_control":
            return control
        return None
    if guide_type in CARD_SELECTION_REDIRECT_TYPES:
        source = bpy.data.objects.get(obj.get("hair_source_curve", ""))
        if not source:
            return None
        source_type = source.get("hair_guide_type", "")
        if source.type == "CURVE" and source_type in {"curve", "twist_control"}:
            return source
        if source_type == "twist_strand":
            control = bpy.data.objects.get(source.get("hair_twist_control", ""))
            if control and control.type == "CURVE" and control.get("hair_guide_type") == "twist_control":
                return control
    return None


class HGD_OT_move_selected_curve_origins_to_reference_empty(bpy.types.Operator):
    bl_idname = "hgd.move_selected_curve_origins_to_reference_empty"
    bl_label = "選択Curve原点を参照Emptyへ移動"
    bl_description = "参照Emptyがある選択Curveの見た目を維持したまま、Object原点をEmpty位置へ移動します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        targets = []
        seen = set()
        for obj in context.selected_objects:
            curve = _resolve_origin_move_curve_from_object(obj)
            if curve and curve.name not in seen:
                targets.append(curve)
                seen.add(curve.name)

        moved = 0
        for curve in targets:
            empty = _reference_empty_for_curve(curve)
            if empty and _move_curve_origin_to_world_position_keep_shape(curve, empty.matrix_world.translation):
                moved += 1

        if moved == 0:
            self.report({'WARNING'}, "参照Emptyがある選択Curveが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"{moved}本のCurve原点を参照Emptyへ移動しました。")
        return {'FINISHED'}



CARD_CONTROL_SHARED_NAME = "HGD_CARD_CTRL_SHARED"


def _link_card_control_empty(empty):
    _, collections = utils.ensure_system()
    collection = collections[utils.CARD_CONTROLS]
    if not any(obj.name == empty.name for obj in collection.objects):
        try:
            collection.objects.link(empty)
        except RuntimeError:
            pass
    return collection


def _is_object_in_view_layer(context, obj):
    return bool(obj is not None and obj.name in context.view_layer.objects)


def _ensure_object_in_active_scene_collection(context, obj):
    if obj is not None and not _is_object_in_view_layer(context, obj):
        try:
            context.scene.collection.objects.link(obj)
        except RuntimeError:
            pass


def _mark_card_control_empty(empty):
    empty["hair_guide_type"] = "card_control_empty"
    empty["hair_card_control_empty"] = True
    _ensure_card_control_empty_index(empty)
    return empty


def _setup_card_control_empty(context, empty):
    empty.empty_display_type = 'SINGLE_ARROW'
    empty.empty_display_size = 0.08
    _mark_card_control_empty(empty)
    _link_card_control_empty(empty)
    _ensure_object_in_active_scene_collection(context, empty)
    context.scene.hair_selected_card_control_empty = empty
    _apply_work_mode_lock_to_object(context, empty)
    return empty


def _average_curve_world_center(curves):
    centers = []
    for curve in curves:
        samples = utils.sample_curve_world_points(curve, 3)
        if samples:
            center = mathutils.Vector((0.0, 0.0, 0.0))
            for point in samples:
                center += point
            centers.append(center / len(samples))
        else:
            centers.append(curve.matrix_world.translation.copy())
    if not centers:
        return mathutils.Vector((0.0, 0.0, 0.0))
    total = mathutils.Vector((0.0, 0.0, 0.0))
    for center in centers:
        total += center
    return total / len(centers)


def _card_control_empty_location_for_curves(context, curves):
    head = getattr(context.scene, "hair_target_head_object", None)
    if head and head.type == "MESH":
        _, _, center, _ = utils.head_bounds(head)
        return center
    return _average_curve_world_center(curves)


def _resolve_shared_card_control_empty(context, curves):
    pointer_empty = getattr(context.scene, "hair_selected_card_control_empty", None)
    if _is_card_control_empty(pointer_empty):
        return pointer_empty
    return None

def _object_is_missing_card_control_empty(curve_obj):
    empty_name = curve_obj.get("hair_card_control_empty", "")
    return bool(empty_name) and bpy.data.objects.get(empty_name) is None


def _resolve_reference_card_control_empty(context):
    """Return the selected/active CARD Control Empty used as sharing reference."""
    selected_empty = next((obj for obj in context.selected_objects if obj.type == 'EMPTY'), None)
    if selected_empty:
        return selected_empty

    active = context.view_layer.objects.active
    if active and active.get("hair_guide_type") in {"curve", "twist_strand"}:
        empty = bpy.data.objects.get(active.get("hair_card_control_empty", ""))
        if empty and empty.type == 'EMPTY':
            return empty

    if active and active.get("hair_guide_type") == "card_preview":
        source = bpy.data.objects.get(active.get("hair_source_curve", ""))
        if source:
            empty = bpy.data.objects.get(source.get("hair_card_control_empty", ""))
            if empty and empty.type == 'EMPTY':
                return empty
    return None

def resolve_card_display_curves_from_selection(context):
    curves = []
    seen = set()
    for obj in context.selected_objects:
        curve = resolve_card_display_curve_from_object(context, obj)
        if curve and curve.name not in seen and curve.get("hair_guide_type") in {"curve", "twist_strand"}:
            curves.append(curve)
            seen.add(curve.name)
    return curves


def _all_card_display_curves(context):
    curves = []
    seen = set()
    for obj in utils.generated_objects():
        if obj.type != "CURVE" or obj.get("hair_guide_type") not in {"curve", "twist_strand"}:
            continue
        if obj.get("hair_curve_display_mode") == "CARD" or _curve_has_card_preview(obj):
            if obj.name not in seen:
                curves.append(obj)
                seen.add(obj.name)
    return curves


def _add_card_update_target_from_object(context, obj, curves, twist_controls):
    target = resolve_display_curve_from_object(context, obj)
    if not target:
        return

    guide_type = target.get("hair_guide_type")
    if guide_type == "curve" and target.type == "CURVE":
        _add_unique_object(curves, target)
        return

    if guide_type == "twist_strand" and target.type == "CURVE":
        control = resolve_edit_curve_for_preview_redirect(target)
        if control and control.get("hair_guide_type") == "twist_control":
            _add_unique_object(twist_controls, control)
        else:
            _add_unique_object(curves, target)


def _selected_card_update_targets(context):
    curves = []
    twist_controls = []
    for obj in context.selected_objects:
        _add_card_update_target_from_object(context, obj, curves, twist_controls)
    return curves, twist_controls


class HGD_OT_select_edit_curve_from_preview(bpy.types.Operator):
    bl_idname = "hgd.select_edit_curve_from_preview"
    bl_label = "選択CARDの編集Curveを選択"
    bl_description = "選択中のCARDプレビュー/ツイスト表示Curveから、実際に編集する通常Curveまたはツイスト制御Curveへ選択を移します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        edit_curve = None
        for obj in context.selected_objects:
            if obj.get("hair_guide_type") in {"card_preview", "twist_strand", "curve", "twist_control"}:
                edit_curve = resolve_edit_curve_for_preview_redirect(obj)
                if edit_curve:
                    break
        if not edit_curve:
            self.report({'WARNING'}, "選択中のCARDから編集対象Curveを取得できませんでした。")
            return {'CANCELLED'}
        for obj in context.selected_objects:
            obj.select_set(False)
        edit_curve.hide_select = False
        edit_curve.select_set(True)
        context.view_layer.objects.active = edit_curve
        self.report({'INFO'}, f"編集対象Curveを選択しました: {edit_curve.name}")
        return {'FINISHED'}


class HGD_OT_edit_source_curve(bpy.types.Operator):
    bl_idname = "hgd.edit_source_curve"
    bl_label = "編集Curveを開く"
    bl_description = "選択中のCARDプレビューから、参照元の編集Curveを選択してEdit Modeに入ります。出力Meshは通常のMeshとして編集します"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            context.mode == 'OBJECT'
            and obj is not None
            and obj.get("hair_guide_type") == "card_preview"
            and resolve_edit_curve_for_preview_redirect(obj) is not None
        )

    def execute(self, context):
        active = context.active_object
        if not active or active.get("hair_guide_type") != "card_preview":
            self.report({'WARNING'}, "編集Curveへの遷移はCARDプレビュー選択時のみ使用します。出力Meshは通常のMeshとして編集してください。")
            return {'CANCELLED'}

        edit_curve = resolve_edit_curve_for_preview_redirect(active)
        if not edit_curve:
            self.report({'WARNING'}, "選択中のCARDプレビューから編集対象Curveを取得できませんでした。")
            return {'CANCELLED'}

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        for obj in context.selected_objects:
            obj.select_set(False)
        edit_curve.hide_select = False
        edit_curve.hide_set(False)
        edit_curve.select_set(True)
        context.view_layer.objects.active = edit_curve
        bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, f"編集対象CurveをEdit Modeで開きました: {edit_curve.name}")
        return {'FINISHED'}


class HGD_OT_select_source_curve_from_card_preview(bpy.types.Operator):
    bl_idname = "hgd.select_source_curve_from_card_preview"
    bl_label = "選択CARDの元Curveを選択"
    bl_description = "互換用です。選択中のCARDプレビューから編集対象Curveへ選択を移します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.hgd.select_edit_curve_from_preview()


class HGD_OT_apply_card_roll_to_selected(bpy.types.Operator):
    bl_idname = "hgd.apply_card_roll_to_selected"
    bl_label = "CARD Rollを適用"
    bl_description = "CurveごとのCARD Roll角と平行移動フレーム設定を適用し、CARDプレビューを再生成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        targets = resolve_card_display_curves_from_selection(context) if scene.hair_card_roll_apply_scope == "SELECTED" else _all_card_display_curves(context)
        applied = 0
        for curve in targets:
            curve["hair_card_roll_angle"] = scene.hair_card_default_roll_angle
            curve["hair_card_use_parallel_transport"] = scene.hair_card_use_parallel_transport
            _sync_scene_card_width_settings_to_curve(scene, curve)
            curve["hair_curve_display_mode"] = "CARD"
            if _create_or_update_card_preview(context, curve):
                applied += 1
        if not applied:
            self.report({'WARNING'}, "CARD Rollを適用できるCurveが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"CARD Rollを{applied}本へ適用しました。")
        return {'FINISHED'}


class HGD_OT_fix_card_twist(bpy.types.Operator):
    bl_idname = "hgd.fix_card_twist"
    bl_label = "CARDねじれ修正"
    bl_description = "Parallel Transport Frameを有効にして、元CurveからCARDプレビューを再生成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        targets = resolve_card_display_curves_from_selection(context) if scene.hair_card_twist_fix_scope == "SELECTED" else _all_card_display_curves(context)
        fixed = 0
        for curve in targets:
            curve["hair_card_use_parallel_transport"] = True
            if "hair_card_roll_angle" not in curve:
                curve["hair_card_roll_angle"] = scene.hair_card_default_roll_angle
            _sync_scene_card_width_settings_to_curve(scene, curve)
            curve["hair_curve_display_mode"] = "CARD"
            if _create_or_update_card_preview(context, curve):
                fixed += 1
        if not fixed:
            self.report({'WARNING'}, "CARDねじれ修正を適用できるCurveが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"CARDねじれ修正を{fixed}本へ適用しました。")
        return {'FINISHED'}


class HGD_OT_create_card_control_empty(bpy.types.Operator):
    bl_idname = "hgd.create_card_control_empty"
    bl_label = "共有CARD Control Empty作成/割り当て"
    bl_description = "既存の共有CARD Control Emptyを優先再利用し、無ければ1個だけ作成して選択Curveへ割り当てます"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = resolve_card_display_curves_from_selection(context)
        if not curves:
            self.report({'WARNING'}, "参照Emptyを割り当てるCurveがありません。")
            return {'CANCELLED'}

        empty = _resolve_shared_card_control_empty(context, curves)
        created = False
        if not empty:
            empty = bpy.data.objects.new(CARD_CONTROL_SHARED_NAME, None)
            empty.location = _card_control_empty_location_for_curves(context, curves)
            created = True

        _setup_card_control_empty(context, empty)
        empty["hair_card_shared"] = True
        empty["hair_shared_curve_count"] = len(curves)
        if created or empty.name == CARD_CONTROL_SHARED_NAME:
            empty["hair_source_curve"] = curves[-1].name

        for curve in curves:
            curve["hair_card_control_empty"] = empty.name

        action = "作成" if created else "再利用"
        self.report({'INFO'}, f"CARD Control Emptyを{action}し、{len(curves)}本のCurveへ割り当てました。")
        return {'FINISHED'}


class HGD_OT_create_card_control_empty_per_curve(bpy.types.Operator):
    bl_idname = "hgd.create_card_control_empty_per_curve"
    bl_label = "選択Curveごとに個別Empty作成"
    bl_description = "選択対象の参照元Curveごとに個別CARD Control Emptyを作成/割り当てします（詳細設定向け）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = resolve_card_display_curves_from_selection(context)
        if not curves:
            self.report({'WARNING'}, "CARD Control Emptyを作成するCurveが見つかりません。")
            return {'CANCELLED'}
        count = 0
        for curve in curves:
            name = f"HGD_CARD_CTRL_{curve.name}"
            empty = bpy.data.objects.get(name)
            if not empty:
                empty = bpy.data.objects.new(name, None)
            empty.location = _card_control_empty_location_for_curves(context, [curve])
            _setup_card_control_empty(context, empty)
            empty["hair_source_curve"] = curve.name
            curve["hair_card_control_empty"] = empty.name
            count += 1
        self.report({'INFO'}, f"個別CARD Control Emptyを{count}個作成/割り当てしました。")
        return {'FINISHED'}

class HGD_OT_assign_selected_card_control_empty(bpy.types.Operator):
    bl_idname = "hgd.assign_selected_card_control_empty"
    bl_label = "選択Emptyを割り当て"
    bl_description = "選択中のEmptyを選択Curve/CARDの参照元Curveへ割り当てします"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        empty = next((obj for obj in context.selected_objects if obj.type == 'EMPTY'), None)
        if not empty:
            self.report({'WARNING'}, "割り当てるEmptyが選択されていません。")
            return {'CANCELLED'}
        curves = [curve for curve in resolve_card_display_curves_from_selection(context) if curve != empty]
        if not curves:
            self.report({'WARNING'}, "Emptyを割り当てるCurveが見つかりません。")
            return {'CANCELLED'}
        _, collections = utils.ensure_system()
        collection = collections[utils.CARD_CONTROLS]
        if not any(obj.name == empty.name for obj in collection.objects):
            try:
                collection.objects.link(empty)
            except RuntimeError:
                pass
        for curve in curves:
            curve["hair_card_control_empty"] = empty.name
        _mark_card_control_empty(empty)
        empty["hair_source_curve"] = curves[-1].name
        _apply_work_mode_lock_to_object(context, empty)
        suffix = "（同一Emptyを複数Curveへ割り当て）" if len(curves) > 1 else ""
        self.report({'INFO'}, f"選択Emptyを{len(curves)}本のCurveへ割り当てました。{suffix}")
        return {'FINISHED'}


class HGD_OT_clear_card_control_empty(bpy.types.Operator):
    bl_idname = "hgd.clear_card_control_empty"
    bl_label = "CARD Control Empty割当解除"
    bl_description = "選択対象の参照元CurveからCARD Control Empty割り当てを解除します（Emptyは削除しません）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = resolve_card_display_curves_from_selection(context)
        cleared = 0
        for curve in curves:
            if "hair_card_control_empty" in curve:
                del curve["hair_card_control_empty"]
                cleared += 1
        if not cleared:
            self.report({'WARNING'}, "解除するCARD Control Empty割り当てが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"CARD Control Empty割当を{cleared}本解除しました。")
        return {'FINISHED'}


class HGD_OT_share_card_control_empty_to_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.share_card_control_empty_to_selected_curves"
    bl_label = "参照Emptyを選択Curveへ共有"
    bl_description = "選択Emptyまたはアクティブ対象の参照Emptyを、選択Curve/CARDの参照元Curveへ共有します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        empty = _resolve_reference_card_control_empty(context)
        if not empty:
            self.report({'WARNING'}, "共有する参照Emptyが見つかりません。")
            return {'CANCELLED'}

        curves = resolve_card_display_curves_from_selection(context)
        if not curves:
            self.report({'WARNING'}, "参照Emptyを共有するCurveが見つかりません。")
            return {'CANCELLED'}

        _, collections = utils.ensure_system()
        collection = collections[utils.CARD_CONTROLS]
        if not any(obj.name == empty.name for obj in collection.objects):
            try:
                collection.objects.link(empty)
            except RuntimeError:
                pass

        count = 0
        for curve in curves:
            curve["hair_card_control_empty"] = empty.name
            count += 1

        _mark_card_control_empty(empty)
        empty["hair_card_shared"] = True
        empty["hair_shared_curve_count"] = count
        _apply_work_mode_lock_to_object(context, empty)
        self.report({'INFO'}, f"参照Emptyを{count}本のCurveへ共有しました。")
        return {'FINISHED'}


class HGD_OT_unshare_card_control_empty_from_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.unshare_card_control_empty_from_selected_curves"
    bl_label = "選択Curveの参照Empty共有を解除"
    bl_description = "選択Curve/CARDの参照元Curveから参照Empty情報を削除します（Emptyは削除しません）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = resolve_card_display_curves_from_selection(context)
        cleared = 0
        for curve in curves:
            if "hair_card_control_empty" in curve:
                del curve["hair_card_control_empty"]
                cleared += 1
        if not cleared:
            self.report({'WARNING'}, "解除する参照Empty共有が見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"{cleared}本のCurveから参照Emptyを解除しました。")
        return {'FINISHED'}


class HGD_OT_select_shared_card_control_empty(bpy.types.Operator):
    bl_idname = "hgd.select_shared_card_control_empty"
    bl_label = "参照Emptyを選択"
    bl_description = "選択Curve/CARDの参照元Curveに保存されたCARD Control Emptyを選択します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curve = next((c for c in resolve_card_display_curves_from_selection(context)), None)
        if not curve:
            self.report({'WARNING'}, "参照Emptyを持つCurveが見つかりません。")
            return {'CANCELLED'}
        empty = bpy.data.objects.get(curve.get("hair_card_control_empty", ""))
        if not empty:
            self.report({'WARNING'}, "参照Emptyが見つかりません。")
            return {'CANCELLED'}
        _ensure_object_in_active_scene_collection(context, empty)
        context.view_layer.update()
        if not _is_object_in_view_layer(context, empty):
            self.report({'WARNING'}, "参照Emptyは現在のViewLayerに存在しないため選択できません。")
            return {'CANCELLED'}
        bpy.ops.object.select_all(action='DESELECT')
        empty.hide_viewport = False
        empty.hide_select = False
        empty.select_set(True)
        context.view_layer.objects.active = empty
        self.report({'INFO'}, "参照Emptyを選択しました。")
        return {'FINISHED'}


class HGD_OT_load_card_control_empty_from_selected(bpy.types.Operator):
    bl_idname = "hgd.load_card_control_empty_from_selected"
    bl_label = "選択対象から参照Emptyを読み込み"
    bl_description = "選択Curve/CARDの参照元Curveに保存されたCARD Control Emptyを参照Empty欄へ読み込みます"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curve = next((c for c in resolve_card_display_curves_from_selection(context)), None)
        empty = bpy.data.objects.get(curve.get("hair_card_control_empty", "")) if curve else None
        if not _is_card_control_empty(empty):
            context.scene.hair_selected_card_control_empty = None
            self.report({'WARNING'}, "参照Emptyが見つからないか、CARD Control Emptyではありません。")
            return {'CANCELLED'}
        context.scene.hair_selected_card_control_empty = empty
        self.report({'INFO'}, "参照Emptyを読み込みました。")
        return {'FINISHED'}


class HGD_OT_assign_pointer_card_control_empty(bpy.types.Operator):
    bl_idname = "hgd.assign_pointer_card_control_empty"
    bl_label = "参照Emptyを選択Curveへ割り当て"
    bl_description = "参照Empty欄のObjectを選択Curve/CARDの参照元Curveへ割り当てます"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        empty = getattr(context.scene, "hair_selected_card_control_empty", None)
        if not empty or empty.type != 'EMPTY':
            self.report({'WARNING'}, "参照Emptyが設定されていません。")
            return {'CANCELLED'}
        curves = resolve_card_display_curves_from_selection(context)
        if not curves:
            self.report({'WARNING'}, "参照Emptyを割り当てるCurveが見つかりません。")
            return {'CANCELLED'}
        _setup_card_control_empty(context, empty)
        for curve in curves:
            curve["hair_card_control_empty"] = empty.name
        empty["hair_card_shared"] = len(curves) > 1
        empty["hair_shared_curve_count"] = len(curves)
        self.report({'INFO'}, f"参照Emptyを{len(curves)}本のCurveへ割り当てました。")
        return {'FINISHED'}


class HGD_OT_cleanup_card_control_empties(bpy.types.Operator):
    bl_idname = "hgd.cleanup_card_control_empties"
    bl_label = "未使用CARD Control Emptyを削除"
    bl_description = "どのCurveからも参照されていないCARD Control Emptyを削除します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        referenced = {obj.get("hair_card_control_empty", "") for obj in bpy.data.objects if obj.type == "CURVE" and obj.get("hair_card_control_empty", "")}
        removed = 0
        for obj in list(bpy.data.objects):
            if obj.type != 'EMPTY':
                continue
            is_card_empty = obj.get("hair_guide_type") == "card_control_empty" or obj.name.startswith("HGD_CARD_CTRL")
            if is_card_empty and obj.name not in referenced:
                bpy.data.objects.remove(obj, do_unlink=True)
                removed += 1
        self.report({'INFO'}, f"未使用CARD Control Emptyを{removed}個削除しました。")
        return {'FINISHED'}


class HGD_OT_update_card_previews_from_curves(bpy.types.Operator):
    bl_idname = "hgd.update_card_previews_from_curves"
    bl_label = "CARD Previewを現在設定で更新"
    bl_description = "現在のRoot/Mid/Tip幅、Mid位置、幅補間を選択Curveへ同期してPreviewを再生成します。"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _sync_card_width_preset_to_scene(context.scene)
        curves, twist_controls = _selected_card_update_targets(context)
        if not curves and not twist_controls:
            for obj in utils.generated_objects():
                if (
                    obj.type == "CURVE"
                    and obj.get("hair_guide_type") in {"curve", "twist_strand"}
                    and obj.get("hair_curve_display_mode") == "CARD"
                ):
                    if obj.get("hair_guide_type") == "twist_strand":
                        control = resolve_edit_curve_for_preview_redirect(obj)
                        if control and control.get("hair_guide_type") == "twist_control":
                            _add_unique_object(twist_controls, control)
                    else:
                        _add_unique_object(curves, obj)

        updated = 0
        for control in twist_controls:
            _sync_scene_card_width_settings_to_curve(context.scene, control)
            strand = _create_or_replace_twist_strand(context, control)
            if strand:
                _sync_scene_card_width_settings_to_curve(context.scene, strand)
                strand["hair_curve_display_mode"] = "CARD"
                if _create_or_update_card_preview(context, strand):
                    updated += 1

        for curve_obj in curves:
            _sync_scene_card_width_settings_to_curve(context.scene, curve_obj)
            if curve_obj.get("hair_guide_type") == "twist_strand":
                curve_obj["hair_curve_display_mode"] = "CARD"
            elif curve_obj.get("hair_guide_type") == "curve":
                curve_obj["hair_curve_display_mode"] = "CARD"
            if _create_or_update_card_preview(context, curve_obj):
                updated += 1

        if not updated:
            self.report({'WARNING'}, "更新できるCurveが見つかりません。")
            return {'CANCELLED'}
        context.view_layer.update()
        missing_empty = any(_object_is_missing_card_control_empty(curve) for curve in [*curves, *twist_controls])
        if missing_empty:
            self.report({'WARNING'}, "参照Emptyが見つからないため自動フレームを使用しました。")
        self.report({'INFO'}, f"CARDプレビュー {updated} 個を更新しました。")
        return {'FINISHED'}


def _resolve_keep_width_preview_curve_from_object(context, obj):
    if not obj:
        return None
    guide_type = obj.get("hair_guide_type", "")
    if obj.type == "CURVE" and guide_type in {"curve", "twist_strand"}:
        return obj
    if guide_type in {"card_preview", "flat_mesh_preview"}:
        source = bpy.data.objects.get(obj.get("hair_source_curve", ""))
        if source and source.type == "CURVE" and source.get("hair_guide_type") in {"curve", "twist_strand"}:
            return source
    return None


def _resolve_keep_width_preview_curve_from_selection(context):
    active = context.active_object
    candidates = []
    if active:
        candidates.append(active)
    candidates.extend([obj for obj in context.selected_objects if obj != active])
    for obj in candidates:
        curve_obj = _resolve_keep_width_preview_curve_from_object(context, obj)
        if curve_obj:
            return curve_obj
    return None


class HGD_OT_refresh_preview_keep_curve_width(bpy.types.Operator):
    bl_idname = "hgd.refresh_preview_keep_curve_width"
    bl_label = "幅を維持してPreview更新"
    bl_description = "選択中のCurveまたはPreview参照元Curveについて、保存済みCARD幅を変更せずにPreviewだけ再生成します。"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curve_obj = _resolve_keep_width_preview_curve_from_selection(context)
        if not curve_obj:
            self.report({'WARNING'}, "更新対象のCurveまたはPreview参照元Curveが見つかりません。")
            return {'CANCELLED'}

        scene = context.scene
        mode = getattr(scene, "hair_curve_display_mode", "CARD")
        updated = False
        if mode == "FLAT_MESH":
            curve_obj.hide_viewport = False
            curve_obj.display_type = 'WIRE'
            curve_obj.data.bevel_depth = 0.0
            curve_obj.data.bevel_object = None
            curve_obj.data.taper_object = None
            preview = _create_or_update_flat_mesh_preview_keep_curve_width(context, curve_obj)
            if preview:
                _set_flat_mesh_preview_visible(curve_obj, True)
                updated = True
        elif mode == "SOLID":
            curve_obj.display_type = 'TEXTURED'
            curve_obj.data.bevel_object = None
            curve_obj.data.bevel_depth = _fallback_curve_bevel(scene, curve_obj)
            if scene.hair_use_shared_taper:
                _apply_taper_to_curve_obj(context, curve_obj)
            else:
                curve_obj.data.taper_object = None
                curve_obj["hair_use_taper"] = False
                curve_obj["hair_taper_object"] = ""
            _clear_all_previews_for_curve(curve_obj)
            _ensure_curve_visible_geometry(context, curve_obj)
            updated = True
        elif mode == "CURVE":
            curve_obj.data.bevel_depth = 0.0
            curve_obj.data.bevel_object = None
            curve_obj.data.taper_object = None
            _clear_all_previews_for_curve(curve_obj)
            updated = True
        else:
            curve_obj.hide_viewport = False
            curve_obj.display_type = 'WIRE'
            curve_obj.data.bevel_depth = 0.0
            curve_obj.data.bevel_object = None
            curve_obj.data.taper_object = None
            preview = _create_or_update_card_preview_keep_curve_width(context, curve_obj)
            if preview:
                _set_card_preview_visible(curve_obj, True)
                _set_flat_mesh_preview_visible(curve_obj, False)
                updated = True

        if not updated:
            self.report({'WARNING'}, "Previewを更新できませんでした。")
            return {'CANCELLED'}
        curve_obj["hair_curve_display_mode"] = mode
        context.view_layer.update()
        self.report({'INFO'}, f"{curve_obj.name} のPreviewを保存済み幅のまま更新しました。")
        return {'FINISHED'}


class HGD_OT_apply_display_mode_to_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.apply_display_mode_to_selected_curves"
    bl_label = "選択Curveへ表示モードを適用"
    bl_description = "選択中のCurve、またはCARD Preview/出力Meshの参照元Curveへ現在の表示モードを適用します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _apply_display_mode_to_curves(context, True)
        if not curves:
            self.report({'WARNING'}, "表示モードを適用できるCurve、または元Curveを持つPreview/Meshが選択されていません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"選択Curve {len(curves)} 本へ表示モード「{context.scene.hair_curve_display_mode}」を適用しました。")
        return {'FINISHED'}


class HGD_OT_apply_display_mode_to_all_curves(bpy.types.Operator):
    bl_idname = "hgd.apply_display_mode_to_all_curves"
    bl_label = "全Curveへ表示モードを適用"
    bl_description = "すべての通常Curveとツイスト表示Curveへ現在の表示モードを適用します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _apply_display_mode_to_curves(context, False)
        if not curves:
            self.report({'WARNING'}, "表示モードを適用できるCurveが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"全Curve {len(curves)} 本へ表示モード「{context.scene.hair_curve_display_mode}」を適用しました。")
        return {'FINISHED'}


class HGD_OT_load_selected_curve_settings(bpy.types.Operator):
    bl_idname = "hgd.load_selected_curve_settings"
    bl_label = "選択カーブ設定を読み込み"
    bl_description = "選択中の生成カーブから太さ、解像度、テーパー設定をScene設定へ読み込みます"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _generated_curves_from_context(context, True)
        if not curves:
            self.report({'WARNING'}, "設定読み込み対象の生成カーブが選択されていません。")
            return {'CANCELLED'}
        obj = context.object if context.object in curves else curves[0]
        scene = context.scene
        length = float(obj.get("hair_curve_length", scene.hair_curve_length))
        scene.hair_curve_length_cm = m_to_cm(length)
        scene.hair_curve_bevel_depth_cm = m_to_cm(float(obj.get("hair_curve_bevel_depth", obj.data.bevel_depth)))
        scene.hair_curve_bevel_depth = float(obj.get("hair_curve_bevel_depth", obj.data.bevel_depth))
        scene.hair_curve_resolution = int(obj.get("hair_curve_resolution", obj.data.resolution_u))
        scene.hair_curve_root_jitter_ratio = float(obj.get("hair_curve_root_jitter_ratio", scene.hair_curve_root_jitter_ratio))
        scene.hair_curve_mid_jitter_ratio = float(obj.get("hair_curve_mid_jitter_ratio", scene.hair_curve_mid_jitter_ratio))
        scene.hair_curve_tip_jitter_ratio = float(obj.get("hair_curve_tip_jitter_ratio", scene.hair_curve_tip_jitter_ratio))
        scene.hair_curve_profile_type = "ROUND"
        scene.hair_use_shared_taper = bool(obj.get("hair_use_taper", scene.hair_use_shared_taper))
        scene.hair_taper_root_radius = float(obj.get("hair_taper_root_radius", scene.hair_taper_root_radius))
        scene.hair_taper_mid_radius = float(obj.get("hair_taper_mid_radius", scene.hair_taper_mid_radius))
        scene.hair_taper_tip_radius = float(obj.get("hair_taper_tip_radius", scene.hair_taper_tip_radius))
        scene.hair_taper_resolution = int(obj.get("hair_taper_resolution", scene.hair_taper_resolution))
        self.report({'INFO'}, f"選択カーブ設定を読み込みました: {obj.name}")
        return {'FINISHED'}


class HGD_OT_apply_shape_to_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.apply_shape_to_selected_curves"
    bl_label = "選択カーブへ形状を適用"
    bl_description = "現在の太さ、解像度、断面、テーパー設定を選択中の表示用カーブへまとめて適用します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _apply_shape_to_curves(context, True)
        if not curves:
            self.report({'WARNING'}, "形状適用対象の生成カーブが選択されていません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"選択カーブ {len(curves)} 本へ形状を適用しました。")
        return {'FINISHED'}


class HGD_OT_apply_shape_to_all_curves(bpy.types.Operator):
    bl_idname = "hgd.apply_shape_to_all_curves"
    bl_label = "全カーブへ形状を適用"
    bl_description = "現在の太さ、解像度、断面、テーパー設定をすべての表示用カーブへまとめて適用します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _apply_shape_to_curves(context, False)
        if not curves:
            self.report({'WARNING'}, "形状適用対象の生成カーブが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"全カーブ {len(curves)} 本へ形状を適用しました。")
        return {'FINISHED'}


class HGD_OT_clear_shape_from_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.clear_shape_from_selected_curves"
    bl_label = "選択カーブの形状を解除"
    bl_description = "選択中の表示用カーブから断面Profileとテーパーを解除します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _clear_shape_from_curves(context, True)
        if not curves:
            self.report({'WARNING'}, "形状解除対象の生成カーブが選択されていません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"選択カーブ {len(curves)} 本の形状を解除しました。")
        return {'FINISHED'}


class HGD_OT_clear_shape_from_all_curves(bpy.types.Operator):
    bl_idname = "hgd.clear_shape_from_all_curves"
    bl_label = "全カーブの形状を解除"
    bl_description = "すべての表示用カーブから断面Profileとテーパーを解除します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _clear_shape_from_curves(context, False)
        if not curves:
            self.report({'WARNING'}, "形状解除対象の生成カーブが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"全カーブ {len(curves)} 本の形状を解除しました。")
        return {'FINISHED'}


class HGD_OT_lock_twist_visual_curves(bpy.types.Operator):
    bl_idname = "hgd.lock_twist_visual_curves"
    bl_label = "ツイスト表示Curveを選択不可にする"
    bl_description = "既存のツイスト表示Curveを選択不可にし、ツイスト制御Curveを編集可能な状態へ戻します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        locked = 0
        controls = 0
        for obj in utils.generated_objects("twist_strand"):
            obj.hide_select = True
            obj["hair_locked_visual"] = True
            locked += 1
        for obj in utils.generated_objects("twist_control"):
            obj.hide_select = False
            obj.show_in_front = True
            obj["hair_editable_control"] = True
            controls += 1
        if locked == 0 and controls == 0:
            self.report({'WARNING'}, "ツイストCurveが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"ツイスト表示Curve {locked} 本を選択不可にし、制御Curve {controls} 本を編集可能にしました。")
        return {'FINISHED'}


class HGD_OT_lock_card_previews(bpy.types.Operator):
    bl_idname = "hgd.lock_card_previews"
    bl_label = "CARDプレビューを選択可能にする"
    bl_description = "既存のCARDプレビューを選択可能なリダイレクト対象にし、編集は元Curveで行います"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        locked = 0
        for obj in utils.generated_objects("card_preview"):
            obj.hide_select = False
            obj["hair_select_redirect"] = True
            obj["hair_locked_preview"] = True
            obj["hair_editable"] = False
            locked += 1
        if locked == 0:
            self.report({'WARNING'}, "CARDプレビューが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"CARDプレビュー {locked} 個を選択可能にしました。編集は元Curveで行ってください。")
        return {'FINISHED'}


class HGD_OT_update_selected_twists(bpy.types.Operator):
    bl_idname = "hgd.update_selected_twists"
    bl_label = "選択ツイストを更新"
    bl_description = "選択中のツイスト制御カーブから表示用ツイストカーブを再生成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        controls = _twist_controls_from_context(context, True)
        if not controls:
            self.report({'WARNING'}, "ツイスト制御カーブが選択されていません。")
            return {'CANCELLED'}
        updated = 0
        for control in controls:
            if _create_or_replace_twist_strand(context, control):
                updated += 1
        self.report({'INFO'}, f"選択ツイストを{updated}本更新しました。")
        return {'FINISHED'}


class HGD_OT_update_all_twists(bpy.types.Operator):
    bl_idname = "hgd.update_all_twists"
    bl_label = "全ツイストを更新"
    bl_description = "すべてのツイスト制御カーブから表示用ツイストカーブを再生成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        controls = _twist_controls_from_context(context, False)
        if not controls:
            self.report({'WARNING'}, "ツイスト制御カーブが見つかりません。")
            return {'CANCELLED'}
        updated = 0
        for control in controls:
            if _create_or_replace_twist_strand(context, control):
                updated += 1
        self.report({'INFO'}, f"全ツイストを{updated}本更新しました。")
        return {'FINISHED'}


class HGD_OT_apply_curve_batch_settings(bpy.types.Operator):
    bl_idname = "hgd.apply_curve_batch_settings"
    bl_label = "カーブ一括設定を適用"
    bl_description = "選択または全生成カーブに長さ倍率、太さ、解像度を一括適用します"
    bl_options = {'REGISTER', 'UNDO'}

    target: EnumProperty(
        items=(("SELECTED", "選択", "選択中の生成カーブへ適用"), ("ALL", "全生成", "全生成カーブへ適用")),
        default="SELECTED",
        description="更新する生成カーブの範囲",
    )

    def execute(self, context):
        curves = _generated_curves_from_context(context, self.target == "SELECTED")
        if not curves:
            message = "生成カーブが選択されていません。" if self.target == "SELECTED" else "生成カーブが見つかりません。"
            self.report({'WARNING'}, message)
            return {'CANCELLED'}
        scale = context.scene.hair_batch_curve_length
        for obj in curves:
            spline = _first_bezier_spline(obj)
            if spline:
                root = spline.bezier_points[0].co.copy()
                for point in spline.bezier_points:
                    point.co = root + (point.co - root) * scale
                    point.handle_left = root + (point.handle_left - root) * scale
                    point.handle_right = root + (point.handle_right - root) * scale
                obj["hair_curve_length"] = float(obj.get("hair_curve_length", 1.0)) * scale
            obj.data.bevel_depth = context.scene.hair_batch_curve_bevel_depth
            obj.data.resolution_u = context.scene.hair_batch_curve_resolution
            obj["hair_curve_bevel_depth"] = context.scene.hair_batch_curve_bevel_depth
            obj["hair_curve_resolution"] = context.scene.hair_batch_curve_resolution
        self.report({'INFO'}, f"カーブ設定を{len(curves)}本に適用しました。")
        return {'FINISHED'}


class HGD_OT_update_curve_roots_from_points(bpy.types.Operator):
    bl_idname = "hgd.update_curve_roots_from_points"
    bl_label = "配置点から更新"
    bl_description = "通常カーブまたはツイスト制御カーブの根元を元の配置点へ追従させます"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _follow_targets_from_context(context, context.scene.hair_follow_update_selected_only)
        if not curves:
            self.report({'WARNING'}, "生成カーブが選択されていません。" if context.scene.hair_follow_update_selected_only else "生成カーブが見つかりません。")
            return {'CANCELLED'}
        updated = 0
        skipped = 0
        for obj in curves:
            source_name = obj.get("hair_source_point")
            source = bpy.data.objects.get(source_name) if source_name else None
            if not source or source.get("hair_guide_type") != "placement_point":
                skipped += 1
                continue
            spline = _first_bezier_spline(obj)
            if not spline:
                skipped += 1
                continue
            obj.location = source.matrix_world.translation
            if not context.scene.hair_follow_keep_tip_offset:
                root_point = spline.bezier_points[0]
                delta = -root_point.co
                root_point.co = mathutils.Vector((0.0, 0.0, 0.0))
                root_point.handle_left += delta
                root_point.handle_right += delta
            updated += 1
        if skipped:
            self.report({'WARNING'}, f"カーブ根元を{updated}本更新しました。参照元配置点が見つからないカーブ {skipped} 本をスキップしました。")
        else:
            self.report({'INFO'}, f"カーブ根元を{updated}本更新しました。参照点なしは0本です。")
        return {'FINISHED'}


class HGD_OT_clear_legacy_braid_objects(bpy.types.Operator):
    # 旧データ掃除用・通常UI非表示。classesには含めず通常運用では未登録にする。
    bl_idname = "hgd.clear_legacy_braid_objects"
    bl_label = "旧三つ編み生成物を削除"
    bl_description = "旧バージョンで生成された三つ編み制御カーブと表示用カーブだけを削除します"
    bl_options = {'REGISTER', 'UNDO'}

    TARGET_TYPES = {"braid_control", "braid_strand", "braid_visual"}

    def execute(self, context):
        count = 0
        for obj in list(utils.generated_objects()):
            if obj.get("hair_guide_type") in self.TARGET_TYPES:
                bpy.data.objects.remove(obj, do_unlink=True)
                count += 1
        if count == 0:
            self.report({'WARNING'}, "旧三つ編み生成物は見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"旧三つ編み生成物を{count}個削除しました。")
        return {'FINISHED'}



def _mirror_axis_x(context):
    axis = getattr(context.scene, "hair_mirror_axis", "HEAD_CENTER_X")
    if axis in {"WORLD_X_ZERO", "WORLD_X", "X"}:
        return 0.0
    if axis == "EMPTY" and getattr(context.scene, "hair_mirror_empty", None):
        return context.scene.hair_mirror_empty.matrix_world.translation.x
    head = getattr(context.scene, "hair_target_head_object", None)
    if head:
        _min_v, _max_v, center, _size = utils.head_bounds(head)
        return center.x
    return 0.0

def _auto_create_mirror_pairs_for_generated_curves(context, curves_by_point):
    scene = context.scene
    if not getattr(scene, "hair_mirror_modifier_enabled", False):
        return 0
    applied = 0
    for obj in curves_by_point.values():
        if _ensure_mirror_modifier(context, obj):
            applied += 1
    return applied

def _copy_mirrored_curve_data_world_x(source, target):
    new_data = source.data.copy()
    new_data.name = target.name + "Curve"
    target_world_inv = target.matrix_world.inverted()
    for spline in new_data.splines:
        if spline.type != "BEZIER":
            continue
        for point in spline.bezier_points:
            co_world = source.matrix_world @ point.co
            left_world = source.matrix_world @ point.handle_left
            right_world = source.matrix_world @ point.handle_right
            co_world.x *= -1
            left_world.x *= -1
            right_world.x *= -1
            point.co = target_world_inv @ co_world
            point.handle_left = target_world_inv @ left_world
            point.handle_right = target_world_inv @ right_world
    return new_data


MIRROR_MODIFIER_TYPES = {"curve", "twist_control", "twist_strand", "card_preview", "flat_mesh_preview"}
MIRROR_CURVE_TYPES = {"curve", "twist_control", "twist_strand"}
MIRROR_PREVIEW_TYPES = {"card_preview", "flat_mesh_preview"}


def _mirror_empty_location(context):
    scene = context.scene
    axis = getattr(scene, "hair_mirror_axis", "HEAD_CENTER_X")
    if axis == "EMPTY" and getattr(scene, "hair_mirror_empty", None):
        return scene.hair_mirror_empty.matrix_world.translation.copy()
    if axis == "HEAD_CENTER_X":
        head = getattr(scene, "hair_target_head_object", None)
        if head:
            return head.matrix_world.translation.copy()
    return mathutils.Vector((0.0, 0.0, 0.0))


def _ensure_or_get_mirror_empty(context):
    scene = context.scene
    if getattr(scene, "hair_mirror_axis", "HEAD_CENTER_X") == "EMPTY" and getattr(scene, "hair_mirror_empty", None):
        return scene.hair_mirror_empty
    empty = getattr(scene, "hair_mirror_empty", None)
    if empty and empty.type == 'EMPTY' and empty.get("hair_guide_type") == "mirror_empty":
        empty.location = _mirror_empty_location(context)
        return empty
    _, collections = utils.ensure_system()
    empty = bpy.data.objects.new(utils.unique_name("HGD_Mirror_Empty"), None)
    empty.empty_display_type = 'ARROWS'
    empty.empty_display_size = 0.25
    empty.location = _mirror_empty_location(context)
    empty["hair_guide_type"] = "mirror_empty"
    collections[utils.CARD_CONTROLS].objects.link(empty)
    scene.hair_mirror_empty = empty
    return empty


def _ensure_mirror_modifier(context, obj):
    if not obj or obj.get("hair_guide_type") not in MIRROR_MODIFIER_TYPES:
        return False
    empty = _ensure_or_get_mirror_empty(context)
    try:
        mod = obj.modifiers.get("HGD_Mirror")
        if not mod:
            mod = obj.modifiers.new("HGD_Mirror", "MIRROR")
        mod.use_axis[0] = True
        mod.use_axis[1] = False
        mod.use_axis[2] = False
        mod.use_bisect_axis[0] = False
        mod.use_clip = False
        mod.mirror_object = empty
    except Exception:
        return False
    obj["hair_mirror_modifier_enabled"] = True
    obj["hair_mirror_empty"] = empty.name
    return True


def _remove_hgd_mirror_modifier(obj):
    mod = obj.modifiers.get("HGD_Mirror") if obj else None
    if mod:
        obj.modifiers.remove(mod)
    if obj:
        obj["hair_mirror_modifier_enabled"] = False


def _mirror_world_point(point, mirror_matrix):
    local = mirror_matrix.inverted() @ point
    local.x *= -1
    return mirror_matrix @ local


def _mirror_name(name):
    if "Side_L" in name:
        return name.replace("Side_L", "Side_R")
    if "Side_R" in name:
        return name.replace("Side_R", "Side_L")
    if name.endswith("_L"):
        return name[:-2] + "_R"
    if name.endswith("_R"):
        return name[:-2] + "_L"
    return name + "_Mirror"


def _mirror_region_value(region):
    return "Side_R" if region == "Side_L" else "Side_L" if region == "Side_R" else region


def _mirror_flow_side_value(side):
    return "R" if side == "L" else "L" if side == "R" else side


def _resolve_curve_mirror_object(context, source, mirror_empty):
    if not source or source.type != "CURVE" or source.get("hair_guide_type") not in MIRROR_CURVE_TYPES:
        return None
    new_name = utils.unique_name(_mirror_name(source.name))
    new_data = source.data.copy()
    new_data.name = new_name + "Curve"
    mirrored = bpy.data.objects.new(new_name, new_data)
    mirrored.matrix_world = source.matrix_world.copy()
    target_inv = mirrored.matrix_world.inverted()
    for spline in new_data.splines:
        if spline.type != "BEZIER":
            continue
        for point in spline.bezier_points:
            for attr in ("co", "handle_left", "handle_right"):
                world_point = source.matrix_world @ getattr(point, attr)
                setattr(point, attr, target_inv @ _mirror_world_point(world_point, mirror_empty.matrix_world))
    for key in source.keys():
        mirrored[key] = source[key]
    mirrored["hair_mirror_source"] = source.name
    mirrored["hair_mirror_resolved"] = True
    mirrored["hair_mirror_pair"] = source.name
    mirrored["hair_region"] = _mirror_region_value(source.get("hair_region", ""))
    mirrored["flow_side"] = _mirror_flow_side_value(source.get("flow_side", ""))
    source["hair_mirror_pair"] = mirrored.name
    _remove_hgd_mirror_modifier(mirrored)
    utils.get_curve_collection(mirrored.get("hair_region", ""), mirrored.get("hair_guide_type", "curve")).objects.link(mirrored)
    utils.apply_curve_region_color(mirrored)
    return mirrored


class HGD_OT_create_mirror_empty(bpy.types.Operator):
    bl_idname = "hgd.create_mirror_empty"
    bl_label = "Mirror Empty作成"
    bl_description = "head centerまたはworld originにMirror Modifier用Emptyを作成します"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        empty = _ensure_or_get_mirror_empty(context)
        self.report({'INFO'}, f"Mirror Emptyを設定しました: {empty.name}")
        return {'FINISHED'}


class HGD_OT_apply_mirror_modifier_to_selected(bpy.types.Operator):
    bl_idname = "hgd.apply_mirror_modifier_to_selected"
    bl_label = "選択対象へMirror適用"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        count = sum(1 for obj in context.selected_objects if _ensure_mirror_modifier(context, obj))
        context.scene.hair_mirror_modifier_enabled = count > 0
        self.report({'INFO' if count else 'WARNING'}, f"{count}個にMirror Modifierを適用しました。")
        return {'FINISHED' if count else 'CANCELLED'}


class HGD_OT_apply_mirror_modifier_to_all(bpy.types.Operator):
    bl_idname = "hgd.apply_mirror_modifier_to_all"
    bl_label = "全Curve/PreviewへMirror適用"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        count = sum(1 for obj in utils.generated_objects() if _ensure_mirror_modifier(context, obj))
        context.scene.hair_mirror_modifier_enabled = count > 0
        self.report({'INFO' if count else 'WARNING'}, f"{count}個にMirror Modifierを適用しました。")
        return {'FINISHED' if count else 'CANCELLED'}


class HGD_OT_remove_mirror_modifier(bpy.types.Operator):
    bl_idname = "hgd.remove_mirror_modifier"
    bl_label = "Mirror Modifier削除"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        targets = context.selected_objects or [obj for obj in utils.generated_objects() if obj.modifiers.get("HGD_Mirror")]
        count = 0
        for obj in targets:
            if obj.modifiers.get("HGD_Mirror"):
                _remove_hgd_mirror_modifier(obj); count += 1
        self.report({'INFO' if count else 'WARNING'}, f"{count}個のMirror Modifierを削除しました。")
        return {'FINISHED' if count else 'CANCELLED'}


class HGD_OT_resolve_mirror_modifier(bpy.types.Operator):
    bl_idname = "hgd.resolve_mirror_modifier"
    bl_label = "Mirror解決"
    bl_description = "Mirror Modifierで表示されている反対側を、独立したCurveとPreviewとして生成します。出力Meshは対象外です。"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.get("hair_guide_type") in MIRROR_MODIFIER_TYPES]
        targets = selected or [obj for obj in utils.generated_objects() if obj.get("hair_guide_type") in MIRROR_MODIFIER_TYPES and obj.modifiers.get("HGD_Mirror")]
        if not targets:
            self.report({'WARNING'}, "Mirror解決対象がありません。")
            return {'CANCELLED'}
        empty = _ensure_or_get_mirror_empty(context)
        curve_sources = [obj for obj in targets if obj.get("hair_guide_type") in MIRROR_CURVE_TYPES]
        for obj in targets:
            if obj.get("hair_guide_type") in MIRROR_PREVIEW_TYPES:
                src = bpy.data.objects.get(obj.get("hair_source_curve", ""))
                if src and src not in curve_sources:
                    curve_sources.append(src)
        mirrored_curves = []
        for source in curve_sources:
            mirrored = _resolve_curve_mirror_object(context, source, empty)
            if mirrored:
                mirrored_curves.append(mirrored)
                if source.get("hair_guide_type") == "twist_control":
                    _create_or_replace_twist_strand(context, mirrored)
                if context.scene.hair_mirror_resolve_remove_modifier:
                    _remove_hgd_mirror_modifier(source)
        preview_count = 0
        for curve in mirrored_curves:
            if _create_or_update_card_preview(context, curve):
                preview_count += 1
            if _create_or_update_flat_mesh_preview(context, curve):
                preview_count += 1
        if context.scene.hair_mirror_resolve_remove_modifier:
            for obj in targets:
                if obj.get("hair_guide_type") in MIRROR_PREVIEW_TYPES:
                    _remove_hgd_mirror_modifier(obj)
        self.report({'INFO'}, f"{len(mirrored_curves)}本の反対側Curveと{preview_count}個のPreviewを生成しました。")
        return {'FINISHED'}


class HGD_OT_mirror_side_guide_base(bpy.types.Operator):
    bl_options = {'REGISTER', 'UNDO'}
    source_name = ""
    target_name = ""
    target_region = "Side"

    def execute(self, context):
        source = utils.get_guide_object(self.source_name)
        target = utils.get_guide_object(self.target_name)
        if not source or source.type != "CURVE":
            self.report({'WARNING'}, f"コピー元ガイドが見つかりません: {self.source_name}")
            return {'CANCELLED'}
        if not target or target.type != "CURVE":
            self.report({'WARNING'}, f"コピー先ガイドが見つかりません: {self.target_name}")
            return {'CANCELLED'}
        old_data = target.data
        target.data = _copy_mirrored_curve_data_world_x(source, target)
        if old_data and old_data.users == 0:
            bpy.data.curves.remove(old_data)
        target["hair_guide_type"] = "guide"
        target["hair_region"] = self.target_region
        target["hair_guide_level"] = target.get("hair_guide_level", source.get("hair_guide_level", "basic"))
        target.show_in_front = getattr(context.scene, "hair_show_guides_in_front", target.show_in_front)
        target.color = utils.REGION_COLORS.get(self.target_region, utils.REGION_COLORS.get("Side", (0.9, 0.9, 0.9, 1.0)))
        self.report({'INFO'}, f"{source.name} を {target.name} へミラーしました。")
        return {'FINISHED'}


class HGD_OT_mirror_side_guide_l_to_r(HGD_OT_mirror_side_guide_base):
    bl_idname = "hgd.mirror_side_guide_l_to_r"
    bl_label = "左側頭ガイド → 右へミラー"
    bl_description = "HAIR_GUIDE_SideBoundary_Lの編集済みCurveをWorld X=0基準でHAIR_GUIDE_SideBoundary_Rへ反映します"
    source_name = "HAIR_GUIDE_SideBoundary_L"
    target_name = "HAIR_GUIDE_SideBoundary_R"
    target_region = "Side"


class HGD_OT_mirror_side_guide_r_to_l(HGD_OT_mirror_side_guide_base):
    bl_idname = "hgd.mirror_side_guide_r_to_l"
    bl_label = "右側頭ガイド → 左へミラー"
    bl_description = "HAIR_GUIDE_SideBoundary_Rの編集済みCurveをWorld X=0基準でHAIR_GUIDE_SideBoundary_Lへ反映します"
    source_name = "HAIR_GUIDE_SideBoundary_R"
    target_name = "HAIR_GUIDE_SideBoundary_L"
    target_region = "Side"


class HGD_OT_mirror_side(bpy.types.Operator):
    bl_idname = "hgd.mirror_side"
    bl_label = "左右ミラー"
    bl_description = "選択したSide_LまたはSide_Rの配置点、生成カーブ、ツイスト制御カーブをX軸で反対側へ複製します"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        items=(("L2R", "左から右", "選択したSide_LオブジェクトをSide_Rへミラー"), ("R2L", "右から左", "選択したSide_RオブジェクトをSide_Lへミラー")),
        default="L2R",
        description="左右ミラー方向",
    )

    def execute(self, context):
        src_side, dst_side = ("Side_L", "Side_R") if self.direction == "L2R" else ("Side_R", "Side_L")
        selected = [obj for obj in context.selected_objects if _is_mirror_source(obj, src_side)]
        if not selected:
            self.report({'WARNING'}, f"{src_side}のオブジェクトが選択されていません。")
            return {'CANCELLED'}
        _, collections = utils.ensure_system()
        point_map = {}
        mirrored = 0
        lost_links = 0
        for obj in selected:
            if obj.get("hair_guide_type") != "placement_point":
                continue
            new_name = _swap_side(obj.name, src_side, dst_side)
            if context.scene.hair_mirror_overwrite_existing:
                _delete_generated_if_exists(new_name)
            elif bpy.data.objects.get(new_name):
                self.report({'WARNING'}, "ミラー先が既に存在し、上書きがオフです。連番名で作成します。")
                new_name = utils.unique_name(new_name)
            new_obj = obj.copy()
            new_obj.data = obj.data.copy() if obj.data else None
            new_obj.name = new_name
            if new_obj.data:
                new_obj.data.name = new_name + "Mesh"
            collections[utils.PLACEMENT_POINTS].objects.link(new_obj)
            if context.scene.hair_mirror_copy_custom_properties:
                _copy_custom_properties(obj, new_obj)
            else:
                for key in list(new_obj.keys()):
                    del new_obj[key]
            world_loc = obj.matrix_world.translation.copy()
            world_loc.x *= -1
            if new_obj.parent:
                new_obj.location = new_obj.parent.matrix_world.inverted() @ world_loc
            else:
                new_obj.location = world_loc
            new_obj["hair_guide_type"] = "placement_point"
            new_obj["hair_region"] = _mirrored_region(obj, dst_side)
            new_obj["flow_side"] = _mirrored_flow_side(dst_side)
            direction = utils.string_to_vector(obj.get("recommended_direction"), None)
            if direction:
                direction.x *= -1
                new_obj["recommended_direction"] = utils.vector_to_string(direction)
            new_obj["hair_root_id"] = new_obj.name
            new_obj["hair_mirror_source"] = obj.name
            new_obj["hair_mirror_pair"] = obj.name
            obj["hair_mirror_pair"] = new_obj.name
            point_map[obj.name] = new_obj.name
            mirrored += 1
        for obj in selected:
            if obj.get("hair_guide_type") != "curve":
                continue
            new_name = _swap_side(obj.name, src_side, dst_side)
            if context.scene.hair_mirror_overwrite_existing:
                _delete_generated_if_exists(new_name)
            elif bpy.data.objects.get(new_name):
                self.report({'WARNING'}, "ミラー先が既に存在し、上書きがオフです。連番名で作成します。")
                new_name = utils.unique_name(new_name)
            new_obj = obj.copy()
            new_obj.data = obj.data.copy()
            new_obj.name = new_name
            new_obj.data.name = new_name + "Curve"
            new_region = _mirrored_region(obj, dst_side)
            utils.get_curve_collection(new_region, "curve").objects.link(new_obj)
            if context.scene.hair_mirror_copy_custom_properties:
                _copy_custom_properties(obj, new_obj)
            else:
                for key in list(new_obj.keys()):
                    del new_obj[key]
            # 生成カーブはObject transformを保持し、ローカル座標だけをミラーします。
            for spline in new_obj.data.splines:
                if spline.type != "BEZIER":
                    continue
                for point in spline.bezier_points:
                    point.co.x *= -1
                    point.handle_left.x *= -1
                    point.handle_right.x *= -1
            new_obj["hair_guide_type"] = "curve"
            new_obj["hair_region"] = new_region
            new_obj["flow_side"] = _mirrored_flow_side(dst_side)
            utils.apply_curve_region_color(new_obj)
            new_obj["hair_mirror_source"] = obj.name
            new_obj["hair_mirror_pair"] = obj.name
            obj["hair_mirror_pair"] = new_obj.name
            source_name = obj.get("hair_source_point")
            if source_name in point_map:
                new_obj["hair_source_point"] = point_map[source_name]
                new_obj["hair_root_id"] = point_map[source_name]
            else:
                new_obj["hair_source_point"] = ""
                new_obj["hair_root_id"] = ""
                lost_links += 1
            mirrored += 1
        twist_candidates = []
        seen_twists = set()
        for obj in selected:
            if obj.get("hair_guide_type") == "twist_control" and obj.name not in seen_twists:
                twist_candidates.append(obj)
                seen_twists.add(obj.name)
        for obj in twist_candidates:
            twist_id = _next_twist_id()
            new_name = f"HGD_TWIST_CTRL_{twist_id}"
            if context.scene.hair_mirror_overwrite_existing:
                _delete_generated_if_exists(new_name)
            elif bpy.data.objects.get(new_name):
                self.report({'WARNING'}, "ミラー先が既に存在し、上書きがオフです。連番名で作成します。")
                new_name = utils.unique_name(new_name)
            new_obj = obj.copy()
            new_obj.data = obj.data.copy()
            new_obj.name = new_name
            new_obj.data.name = new_name + "Curve"
            new_region = _mirrored_region(obj, dst_side)
            utils.get_curve_collection(new_region, "twist_control").objects.link(new_obj)
            if context.scene.hair_mirror_copy_custom_properties:
                _copy_custom_properties(obj, new_obj)
            else:
                for key in list(new_obj.keys()):
                    del new_obj[key]
            for spline in new_obj.data.splines:
                if spline.type != "BEZIER":
                    continue
                for point in spline.bezier_points:
                    point.co.x *= -1
                    point.handle_left.x *= -1
                    point.handle_right.x *= -1
            new_obj["hair_guide_type"] = "twist_control"
            new_obj["hair_region"] = new_region
            new_obj["flow_side"] = _mirrored_flow_side(dst_side)
            utils.apply_curve_region_color(new_obj)
            new_obj["hair_twist_id"] = twist_id
            _set_twist_control_display(new_obj)
            new_obj["hair_mirror_source"] = obj.name
            new_obj["hair_mirror_pair"] = obj.name
            obj["hair_mirror_pair"] = new_obj.name
            source_name = obj.get("hair_source_point")
            if source_name in point_map:
                new_obj["hair_source_point"] = point_map[source_name]
                new_obj["hair_root_id"] = point_map[source_name]
            else:
                new_obj["hair_source_point"] = ""
                new_obj["hair_root_id"] = ""
                lost_links += 1
            strand = _create_or_replace_twist_strand(context, new_obj)
            mirrored += 1 + (1 if strand else 0)
        self.report({'INFO'}, f"{mirrored}個をミラーしました。参照配置点を失ったカーブは{lost_links}本です。")
        return {'FINISHED'}


class HGD_OT_mirror_selected_curves(bpy.types.Operator):
    bl_idname = "hgd.mirror_selected_curves"
    bl_label = "選択Curveを左右ミラー"
    bl_description = "選択Curveの形状をhair_mirror_pairの対応Curveへ頭部中心X軸で反転コピーします"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        head = require_head(context, self)
        if not head:
            return {'CANCELLED'}
        _min_v, _max_v, center, _size = utils.head_bounds(head)
        selected = [
            obj for obj in context.selected_objects
            if obj.type == "CURVE" and obj.get("hair_guide_type") in {"curve", "twist_control"}
        ]
        if not selected:
            self.report({'WARNING'}, "ミラー元Curveが選択されていません。")
            return {'CANCELLED'}

        mirrored = 0
        warnings = 0
        for source in selected:
            pair_name = source.get("hair_mirror_pair", "")
            target = bpy.data.objects.get(pair_name) if pair_name else None
            if not target or target.type != "CURVE" or target.get("hair_guide_type") not in {"curve", "twist_control"}:
                self.report({'WARNING'}, f"対応Curveが見つかりません: {source.name}")
                warnings += 1
                continue
            if not _copy_mirrored_bezier_shape(source, target, center.x):
                self.report({'WARNING'}, f"BezierPoint数が一致しません: {source.name} -> {target.name}")
                warnings += 1
                continue
            target["hair_mirror_pair"] = source.name
            source["hair_mirror_pair"] = target.name
            if source.get("hair_mirror_side", "") and not target.get("hair_mirror_side", ""):
                target["hair_mirror_side"] = "R" if source.get("hair_mirror_side") == "L" else "L"
            if target.get("hair_guide_type") == "twist_control":
                _create_or_replace_twist_strand(context, target)
            mirrored += 1
        if mirrored == 0:
            return {'CANCELLED'}
        self.report({'INFO' if warnings == 0 else 'WARNING'}, f"{mirrored}本のCurveを左右ミラーしました。警告: {warnings}")
        return {'FINISHED'}



class HGD_OT_mirror_mode_sync_pairs(bpy.types.Operator):
    bl_idname = "hgd.mirror_mode_sync_pairs"
    bl_label = "ミラーペア同期"
    bl_description = "hair_mirror_pairで対応付けられたCurveへ、選択Curveまたは先に見つかったCurveの形状を反映します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        mirror_x = _mirror_axis_x(context)
        selected_names = {obj.name for obj in context.selected_objects}
        sources = [
            obj for obj in utils.generated_objects()
            if obj.type == "CURVE" and obj.get("hair_guide_type") in {"curve", "twist_control"}
        ]
        sources.sort(key=lambda obj: (obj.name not in selected_names, obj.name))
        updated = 0
        seen_pairs = set()
        for source in sources:
            target = bpy.data.objects.get(source.get("hair_mirror_pair", ""))
            if not target or target.type != "CURVE" or target.get("hair_guide_type") not in {"curve", "twist_control"}:
                continue
            pair_key = frozenset((source.name, target.name))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            if _copy_mirrored_bezier_shape(source, target, mirror_x):
                target["hair_mirror_pair"] = source.name
                source["hair_mirror_pair"] = target.name
                if target.get("hair_guide_type") == "twist_control":
                    _create_or_replace_twist_strand(context, target)
                updated += 1
        if updated == 0:
            self.report({'WARNING'}, "同期対象のミラーペアが見つかりません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"ミラーペア{updated}本を同期しました。")
        return {'FINISHED'}

class HGD_OT_mirror_side_l_to_r(bpy.types.Operator):
    bl_idname = "hgd.mirror_side_l_to_r"
    bl_label = "左側→右側へミラー"
    bl_description = "選択したSide_Lの配置点、カーブ、ツイストをX軸でSide_Rへ複製します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.hgd.mirror_side(direction="L2R")


class HGD_OT_mirror_side_r_to_l(bpy.types.Operator):
    bl_idname = "hgd.mirror_side_r_to_l"
    bl_label = "右側→左側へミラー"
    bl_description = "選択したSide_Rの配置点、カーブ、ツイストをX軸でSide_Lへ複製します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.hgd.mirror_side(direction="R2L")



def _remove_obsolete_card_auto_handlers():
    handlers = bpy.app.handlers.depsgraph_update_post
    for handler in list(handlers):
        if getattr(handler, "__name__", "") == "hgd_card_preview_auto_update_handler":
            handlers.remove(handler)


class HGD_OT_reload_keymaps(bpy.types.Operator):
    bl_idname = "hgd.reload_keymaps"
    bl_label = "Keymap再登録"
    bl_description = "Addon PreferencesのPie Menu Key設定でHair Guide PieのKeyMapを再登録します"

    def execute(self, context):
        from . import keymap
        keymap.unregister_keymaps()
        keymap.register_keymaps()
        self.report({'INFO'}, "Hair Guide keymapsを再登録しました。")
        return {'FINISHED'}


classes = (
    HGD_OT_reload_keymaps,
    HGD_OT_apply_work_mode_lock,
    HGD_OT_toggle_work_mode_lock,
    HGD_OT_toggle_final_edit_mode,
    HGD_OT_finish_hair_guide_work,
    HGD_OT_set_target_head,
    HGD_OT_create_hair_guides,
    HGD_OT_symmetrize_front_back_guides,
    HGD_OT_mirror_side_guide_l_to_r,
    HGD_OT_mirror_side_guide_r_to_l,
    HGD_OT_delete_hair_guides,
    HGD_OT_show_hide_guides,
    HGD_OT_region_visibility,
    HGD_OT_toggle_region_visibility,
    HGD_OT_toggle_all_region_visibility,
    HGD_OT_generate_placement_points,
    HGD_OT_clear_placement_points,
    HGD_OT_create_curve_from_points,
    HGD_OT_duplicate_selected_hair_curves,
    HGD_OT_duplicate_selected_or_preview_source_curves,
    HGD_OT_check_root_clustering,
    HGD_OT_clear_warnings,
    HGD_OT_clear_card_previews,
    HGD_OT_clear_flat_mesh_previews,
    HGD_OT_rebuild_preview_links_clean,
    HGD_OT_rebuild_card_previews_clean,
    HGD_OT_clear_all_generated,
    HGD_OT_toggle_in_front_generated_helpers,
    HGD_OT_organize_curves_by_region,
    HGD_OT_apply_curve_region_colors,
    HGD_OT_apply_card_width_preset,
    HGD_OT_load_card_preview_settings_to_scene,
    HGD_OT_apply_taper_preset,
    HGD_OT_create_or_update_default_taper,
    HGD_OT_apply_taper_to_selected_curves,
    HGD_OT_apply_taper_to_all_curves,
    HGD_OT_clear_taper_from_selected_curves,
    HGD_OT_clear_taper_from_all_curves,
    HGD_OT_update_flat_mesh_previews_from_curves,
    HGD_OT_create_flat_mesh_from_selected_curves,
    HGD_OT_create_flat_mesh_from_all_curves,
    HGD_OT_export_flat_mesh_from_selected_curves,
    HGD_OT_convert_selected_card_preview_to_mesh,
    HGD_OT_convert_all_card_previews_to_mesh,
    HGD_OT_select_edit_curve_from_preview,
    HGD_OT_edit_source_curve,
    HGD_OT_select_source_curve_from_card_preview,
    HGD_OT_create_card_control_empty,
    HGD_OT_create_card_control_empty_per_curve,
    HGD_OT_assign_selected_card_control_empty,
    HGD_OT_clear_card_control_empty,
    HGD_OT_share_card_control_empty_to_selected_curves,
    HGD_OT_unshare_card_control_empty_from_selected_curves,
    HGD_OT_select_shared_card_control_empty,
    HGD_OT_load_card_control_empty_from_selected,
    HGD_OT_assign_pointer_card_control_empty,
    HGD_OT_move_selected_curve_origins_to_reference_empty,
    HGD_OT_cleanup_card_control_empties,
    HGD_OT_update_card_previews_from_curves,
    HGD_OT_refresh_preview_keep_curve_width,
    HGD_OT_apply_display_mode_to_selected_curves,
    HGD_OT_apply_display_mode_to_all_curves,
    HGD_OT_load_selected_curve_settings,
    HGD_OT_apply_shape_to_selected_curves,
    HGD_OT_apply_shape_to_all_curves,
    HGD_OT_clear_shape_from_selected_curves,
    HGD_OT_clear_shape_from_all_curves,
    HGD_OT_lock_twist_visual_curves,
    HGD_OT_lock_card_previews,
    HGD_OT_update_selected_twists,
    HGD_OT_update_all_twists,
    HGD_OT_apply_curve_batch_settings,
    HGD_OT_update_curve_roots_from_points,
)


def register():
    _remove_obsolete_card_auto_handlers()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    _remove_obsolete_card_auto_handlers()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
