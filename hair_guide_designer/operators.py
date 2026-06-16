import random
import mathutils
import bpy
from bpy.props import EnumProperty
from . import utils


def require_head(context, operator):
    head = context.scene.hair_target_head_object
    if not head or head.type != "MESH":
        operator.report({'WARNING'}, "頭部が未設定です。メッシュを選択して「選択メッシュを頭部として登録」を押してください。")
        return None
    return head


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
    "HAIR_GUIDE_BackVolume",
    "HAIR_GUIDE_Nape",
    "HAIR_GUIDE_Center",
}


def _remove_named_generated_guides(names):
    removed = 0
    for obj in list(utils.generated_objects("guide")):
        if obj.name.split(".")[0] in names or obj.name in names:
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    return removed


class HGD_OT_create_hair_guides(bpy.types.Operator):
    bl_idname = "hgd.create_hair_guides"
    bl_label = "基本ガイドを生成"
    bl_description = "生え際、サイド境界、後頭部ボリューム、襟足、正中線だけの基本ガイドを生成します"
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
            back_volume_z = min_v.z + size.z * 0.58
            nape_z = min_v.z + size.z * 0.18
            front_y = min_v.y - offset
            back_y = max_v.y + offset

            guide_specs = [
                ("HAIR_GUIDE_Hairline", utils.make_arc_points(center, rx * 0.72, ry * 0.55, hairline_z, 3.6, 5.8, 5), "Front"),
                ("HAIR_GUIDE_SideBoundary_L", [mathutils.Vector((center.x - rx, front_y, hairline_z)), mathutils.Vector((center.x - rx, center.y, hairline_z - size.z * 0.12)), mathutils.Vector((center.x - rx * 0.7, back_y, back_volume_z))], "Side"),
                ("HAIR_GUIDE_SideBoundary_R", [mathutils.Vector((center.x + rx, front_y, hairline_z)), mathutils.Vector((center.x + rx, center.y, hairline_z - size.z * 0.12)), mathutils.Vector((center.x + rx * 0.7, back_y, back_volume_z))], "Side"),
                ("HAIR_GUIDE_BackVolume", utils.make_arc_points(center, rx * 0.78, ry * 0.72, back_volume_z, 0.15, 3.0, 5), "Back_Middle"),
                ("HAIR_GUIDE_Nape", [mathutils.Vector((center.x - rx * 0.45, back_y, nape_z)), mathutils.Vector((center.x, back_y + offset, nape_z - size.z * 0.03)), mathutils.Vector((center.x + rx * 0.45, back_y, nape_z))], "Nape"),
                ("HAIR_GUIDE_Center", [mathutils.Vector((center.x, center.y, top)), mathutils.Vector((center.x, center.y, nape_z))], "Back_Middle"),
            ]
            for name, points, region in guide_specs:
                obj = utils.make_curve(name, points, guides, region, "guide", scene, bevel=0.004)
                obj["hair_guide_level"] = "basic"
            self.report({'INFO'}, f"基本ガイドを{len(guide_specs)}個生成しました（古い基本ガイド{removed}個を削除）。")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"基本ガイドの生成に失敗しました: {exc}")
            return {'CANCELLED'}


class HGD_OT_create_detailed_guides(bpy.types.Operator):
    bl_idname = "hgd.create_detailed_guides"
    bl_label = "詳細ガイドを追加"
    bl_description = "頭頂、ハチ、耳周り、後頭部などの詳細参照線を追加します"
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
            self._create_region_guides(context, regions, center, size, rx, ry, offset, hairline_z, ear_z, occ_z, nape_z, front_y, back_y)
            detailed_count = len(detailed_specs) + len([obj for obj in regions.objects if obj.get("hair_guide_type") == "region"])
            self.report({'INFO'}, f"詳細ガイドを{detailed_count}個追加しました。")
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
    region: EnumProperty(items=[("Front", "前髪", "前髪領域"), ("Side", "側頭部", "左右の側頭部をまとめた領域"), ("Side_L", "左側", "左側頭部"), ("Side_R", "右側", "右側頭部"), ("Back_Upper", "後頭部上層", "髪全体のボリューム領域"), ("Back_Middle", "後頭部中層", "大きな毛束を配置する領域"), ("Nape", "襟足", "首へ向かって落ちる短い毛束領域"), ("ALL", "すべて", "すべての領域")], default="ALL", description="表示または非表示にする髪領域")
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


class HGD_OT_generate_placement_points(bpy.types.Operator):
    bl_idname = "hgd.generate_placement_points"
    bl_label = "配置点を生成/更新"
    bl_description = "既存の配置点と警告を削除し、現在の基本ガイド位置から配置点を再生成します。既存のカーブは削除されません"
    bl_options = {'REGISTER', 'UNDO'}

    BASE_COUNTS = {"Top": 5, "Front": 7, "Side_L": 4, "Side_R": 4, "Back_Upper": 6, "Back_Middle": 9, "Nape": 5}

    def execute(self, context):
        try:
            head = require_head(context, self)
            if not head:
                return {'CANCELLED'}
            _, collections = utils.ensure_system()
            collection = collections[utils.PLACEMENT_POINTS]
            removed_points = utils.clear_collection_objects(utils.PLACEMENT_POINTS, "placement_point")
            removed_warnings = utils.clear_collection_objects(utils.WARNINGS, "warning")
            context.scene.hair_warning_count = 0
            scene = context.scene
            min_v, max_v, center, size = utils.head_bounds(head)
            guides = self._basic_guides()
            guide_count = sum(1 for obj in guides.values() if obj)
            used_fallback = False
            rng = random.Random(scene.hair_seed)
            count_total = 0
            for region, base_count in self.BASE_COUNTS.items():
                count = base_count if region == "Top" else max(1, round(base_count * scene.hair_density))
                positions = self._guide_positions(region, count, guides, min_v, max_v, center, size, scene.hair_guide_offset)
                if positions is None:
                    positions = self._base_positions(region, count, min_v, max_v, center, size, scene.hair_guide_offset)
                    used_fallback = True
                for i, base in enumerate(positions):
                    loc = self._jittered(region, base, rng, scene)
                    radius = max(size.length * 0.008, 0.01) * (1.0 + rng.uniform(-scene.hair_size_variation, scene.hair_size_variation))
                    point_name = self._point_name(region, i)
                    obj = utils.make_marker(point_name, loc, max(radius, 0.004), collection, region, "placement_point", scene)
                    position_type = self._position_type(region, i, loc, center, size)
                    direction = self._recommended_direction(region, position_type, loc.x - center.x)
                    length = scene.hair_curve_length * (1.0 + rng.uniform(-scene.hair_length_variation, scene.hair_length_variation))
                    size_rec = max(scene.hair_curve_root_radius * (1.0 + rng.uniform(-scene.hair_size_variation, scene.hair_size_variation)), 0.001)
                    obj["hair_root_id"] = obj.name
                    obj["recommended_size"] = size_rec
                    obj["recommended_direction"] = utils.vector_to_string(direction)
                    obj["recommended_length"] = max(length, 0.01)
                    obj["flow_side"] = "L" if loc.x < center.x - size.x*0.05 else ("R" if loc.x > center.x + size.x*0.05 else "Center")
                    obj["position_type"] = position_type
                    count_total += 1
            if guide_count == 0:
                self.report({'WARNING'}, "基本ガイドが見つからないため、頭部Bounding Boxから配置点を生成しました。")
            elif used_fallback or guide_count < 6:
                self.report({'WARNING'}, "一部の基本ガイドが見つからないため、頭部Bounding Box基準で補完しました。")
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
            "back": utils.get_guide_object("HAIR_GUIDE_BackVolume"),
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
        if region == "Back_Upper" and guides["back"]:
            points = utils.sample_curve_world_points(guides["back"], count)
            return [point + mathutils.Vector((0.0, 0.0, size.z * 0.12)) for point in points]
        if region == "Back_Middle" and guides["back"] and guides["nape"]:
            back_points = utils.sample_curve_world_points(guides["back"], count)
            nape_points = utils.sample_curve_world_points(guides["nape"], count)
            positions = []
            for i, (back_point, nape_point) in enumerate(zip(back_points, nape_points)):
                t = i / max(count - 1, 1)
                blend = 0.35 + 0.3 * t
                point = back_point.lerp(nape_point, blend)
                side = -1.0 if i % 3 == 0 else (1.0 if i % 3 == 2 else 0.0)
                point.x += side * size.x * 0.12
                positions.append(point)
            return positions
        if region == "Nape" and guides["nape"]:
            return utils.sample_curve_world_points(guides["nape"], count)
        return None

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
                y = max_v.y + offset
                z = min_v.z + size.z * (0.78 - 0.12 * abs(t - 0.5))
            elif region == "Back_Middle":
                # Avoid a uniform center column by spreading rows and lowering center density.
                row = i // 3
                col = i % 3
                x_options = (-0.38, 0.0, 0.38) if row % 2 == 0 else (-0.5, -0.12, 0.5)
                x = center.x + x_options[col] * size.x
                y = max_v.y + offset * (1.0 + 0.5 * row)
                z = min_v.z + size.z * (0.58 - row * 0.08 - 0.02 * col)
            else:
                x = center.x + (t - 0.5) * size.x * 0.45
                y = max_v.y + offset * 1.3
                z = min_v.z + size.z * (0.24 - 0.04 * abs(t - 0.5))
            positions.append(mathutils.Vector((x, y, z)))
        return positions

    def _top_positions(self, count, min_v, max_v, center, size, guides):
        base = mathutils.Vector((center.x, center.y, max_v.z - size.z * 0.08))
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
        return f"POINT_{region}_{index+1:03d}"

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

    def _jittered(self, region, base, rng, scene):
        variation = 0.5 if region == "Top" else 1.0
        x_jit = rng.uniform(-scene.hair_width_variation, scene.hair_width_variation) * variation
        if region == "Side_R":
            x_jit *= 1.0 - scene.hair_symmetry_bias * 0.65
        elif region == "Side_L":
            x_jit *= 1.0 - scene.hair_symmetry_bias * 0.35
        return base + mathutils.Vector((x_jit, rng.uniform(-scene.hair_depth_variation, scene.hair_depth_variation) * variation, rng.uniform(-scene.hair_height_variation, scene.hair_height_variation) * variation))


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
            if context.scene.hair_strand_generation_type == "BRAID_CURVE":
                made = 0
                for point in points:
                    _make_braid_from_point(context, point)
                    made += 1
                self.report({'INFO'}, f"三つ編みカーブを{made}本生成しました。制御カーブを編集してから更新してください。")
                return {'FINISHED'}
            _, collections = utils.ensure_system()
            curves = collections[utils.CURVES]
            scene = context.scene
            taper_obj = None
            if scene.hair_auto_apply_taper_to_new_curves and scene.hair_use_shared_taper:
                taper_obj, _ = _create_or_update_default_taper(context)
            made = 0
            for point in points:
                region = point.get("hair_region", "Front")
                direction = utils.string_to_vector(point.get("recommended_direction"), utils.direction_for_region(region))
                length = float(point.get("recommended_length", scene.hair_curve_length))
                root = point.location.copy()
                segment_count = max(scene.hair_curve_segment_count, 2)
                curve_points = []
                for i in range(segment_count):
                    t = i / max(segment_count - 1, 1)
                    sag = mathutils.Vector((0, 0, -0.12 * length * t * t))
                    curve_points.append(root + direction * length * t + sag)
                prefix = self._prefix(region)
                obj = utils.make_curve(utils.unique_numbered(prefix), curve_points, curves, region, "curve", scene, bevel=scene.hair_curve_bevel_depth)
                obj["hair_root_id"] = point.name
                obj["hair_source_point"] = point.name
                obj["hair_curve_length"] = scene.hair_curve_length
                obj["hair_curve_bevel_depth"] = scene.hair_curve_bevel_depth
                obj["hair_curve_resolution"] = scene.hair_curve_resolution
                obj["hair_mirror_pair"] = ""
                obj["hair_mirror_source"] = ""
                obj["strand_type"] = scene.hair_strand_type
                obj["root_radius"] = scene.hair_curve_root_radius
                obj["tip_radius"] = scene.hair_curve_tip_radius
                obj["taper_strength"] = scene.hair_curve_taper_strength
                obj["segment_count"] = scene.hair_curve_segment_count
                if scene.hair_auto_apply_taper_to_new_curves:
                    _apply_taper_to_curve_obj(context, obj, taper_obj)
                made += 1
            self.report({'INFO'}, f"カーブ毛束を{made}本生成しました。")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"カーブ毛束の生成に失敗しました: {exc}")
            return {'CANCELLED'}

    def _prefix(self, region):
        return {
            "Top": "HAIR_TOP",
            "Front": "HAIR_FRONT",
            "Side_L": "HAIR_SIDE_L",
            "Side_R": "HAIR_SIDE_R",
            "Back_Upper": "HAIR_BACK_UPPER",
            "Back_Middle": "HAIR_BACK_MIDDLE",
            "Nape": "HAIR_NAPE",
        }.get(region, "HAIR_CURVE")


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


class HGD_OT_clear_all_generated(bpy.types.Operator):
    bl_idname = "hgd.clear_all_generated"
    bl_label = "生成物をすべて削除"
    bl_description = "HairGuideSystem内のガイド、領域線、配置点、カーブ、警告、テーパーを削除します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystemが存在しません。")
            return {'CANCELLED'}
        total = 0
        for collection_name in (utils.GUIDES, utils.REGIONS, utils.PLACEMENT_POINTS, utils.CURVES, utils.WARNINGS, utils.TAPER_OBJECTS):
            total += utils.clear_collection_objects(collection_name)
        context.scene.hair_warning_count = 0
        if total == 0:
            self.report({'WARNING'}, "削除する生成物がありません。")
            return {'CANCELLED'}
        self.report({'INFO'}, f"生成物を{total}個削除しました。")
        return {'FINISHED'}


def _generated_curves_from_context(context, selected_only):
    objects = context.selected_objects if selected_only else utils.generated_objects("curve")
    return [obj for obj in objects if obj.type == "CURVE" and obj.get("hair_guide_type") == "curve"]


def _follow_targets_from_context(context, selected_only):
    objects = context.selected_objects if selected_only else utils.generated_objects()
    return [
        obj for obj in objects
        if obj.type == "CURVE" and obj.get("hair_guide_type") in {"curve", "braid_control"}
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


def _next_braid_id():
    index = 1
    while True:
        braid_id = f"{index:03d}"
        if not bpy.data.objects.get(f"HGD_BRAID_CTRL_{braid_id}") and not bpy.data.objects.get(f"HGD_BRAID_VIS_{braid_id}"):
            return braid_id
        index += 1


def _braid_side_vector(tangent):
    up = mathutils.Vector((0.0, 0.0, 1.0))
    side = tangent.cross(up)
    if side.length < 0.0001:
        side = mathutils.Vector((1.0, 0.0, 0.0))
    side.normalize()
    return side


def _create_or_replace_braid_visual(context, control_obj):
    scene = context.scene
    _, collections = utils.ensure_system()
    curves_collection = collections[utils.CURVES]
    braid_id = control_obj.get("hair_braid_id", _next_braid_id())
    visual_name = f"HGD_BRAID_VIS_{braid_id}"
    for obj in list(utils.generated_objects("braid_visual")):
        if obj.get("hair_braid_id") == braid_id or obj.name == visual_name:
            bpy.data.objects.remove(obj, do_unlink=True)
    segment_count = max(scene.hair_braid_segments, 2)
    samples = _sample_curve_world_points(control_obj, segment_count + 1)
    if len(samples) < 2:
        return None
    verts = []
    faces = []
    normal_hint = mathutils.Vector((0.0, 0.0, 1.0))
    for index in range(segment_count):
        start = samples[index]
        end = samples[index + 1]
        tangent = end - start
        if tangent.length < 0.0001:
            tangent = mathutils.Vector((0.0, 0.0, -1.0))
        tangent.normalize()
        side = _braid_side_vector(tangent)
        normal = side.cross(tangent)
        if normal.length < 0.0001:
            normal = normal_hint
        normal.normalize()
        normal_hint = normal
        t = index / max(segment_count - 1, 1)
        taper_scale = max(1.0 - scene.hair_braid_taper * t, 0.05)
        width = scene.hair_braid_width * taper_scale
        radius = scene.hair_braid_radius * taper_scale
        twist = scene.hair_braid_twist
        sign = -1.0 if index % 2 else 1.0
        mid = (start + end) * 0.5
        left = mid + side * sign * width * twist + normal * radius
        right = mid - side * sign * width * 0.75 * twist - normal * radius * 0.35
        base_index = len(verts)
        verts.extend([start, left, end, right])
        faces.append((base_index, base_index + 1, base_index + 2, base_index + 3))
    mesh = bpy.data.meshes.new(visual_name + "Mesh")
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.update()
    visual = bpy.data.objects.new(visual_name, mesh)
    curves_collection.objects.link(visual)
    utils.set_common_props(visual, "braid_visual", control_obj.get("hair_region", ""), scene)
    visual["hair_source_point"] = control_obj.get("hair_source_point", "")
    visual["hair_braid_id"] = braid_id
    visual["hair_braid_control"] = control_obj.name
    visual["hair_braid_segments"] = scene.hair_braid_segments
    visual["hair_braid_radius"] = scene.hair_braid_radius
    visual["hair_braid_width"] = scene.hair_braid_width
    visual["hair_braid_taper"] = scene.hair_braid_taper
    visual["hair_braid_twist"] = scene.hair_braid_twist
    return visual


def _make_braid_from_point(context, point):
    scene = context.scene
    _, collections = utils.ensure_system()
    curves = collections[utils.CURVES]
    braid_id = _next_braid_id()
    region = point.get("hair_region", "Front")
    direction = utils.string_to_vector(point.get("recommended_direction"), utils.direction_for_region(region))
    length = float(point.get("recommended_length", scene.hair_curve_length))
    root = point.location.copy()
    control_points = []
    for i in range(max(scene.hair_curve_segment_count, 2)):
        t = i / max(scene.hair_curve_segment_count - 1, 1)
        sag = mathutils.Vector((0.0, 0.0, -0.12 * length * t * t))
        control_points.append(root + direction * length * t + sag)
    control = utils.make_curve(f"HGD_BRAID_CTRL_{braid_id}", control_points, curves, region, "braid_control", scene, bevel=scene.hair_braid_bevel_depth)
    control["hair_source_point"] = point.name
    control["hair_root_id"] = point.name
    control["hair_braid_id"] = braid_id
    control["hair_use_taper"] = False
    control.data.resolution_u = scene.hair_braid_resolution
    visual = _create_or_replace_braid_visual(context, control)
    return control, visual


def _braid_controls_from_context(context, selected_only):
    if selected_only:
        controls = []
        seen = set()
        for obj in context.selected_objects:
            if obj.get("hair_guide_type") == "braid_control":
                control = obj
            elif obj.get("hair_guide_type") == "braid_visual":
                control = bpy.data.objects.get(obj.get("hair_braid_control", ""))
            else:
                control = None
            if control and control.get("hair_guide_type") == "braid_control" and control.name not in seen:
                controls.append(control)
                seen.add(control.name)
        return controls
    return [obj for obj in utils.generated_objects("braid_control") if obj.type == "CURVE"]


def _swap_side(value, src_side, dst_side):
    if not value:
        return value
    text = str(value)
    if src_side in text:
        return text.replace(src_side, dst_side)
    src_short = "_L" if src_side == "Side_L" else "_R"
    dst_short = "_R" if dst_side == "Side_R" else "_L"
    if src_short in text:
        return text.replace(src_short, dst_short)
    return f"{text}_{dst_short[-1]}"


def _copy_custom_properties(source, target):
    for key in source.keys():
        target[key] = source[key]


def _delete_generated_if_exists(name):
    existing = bpy.data.objects.get(name)
    if not existing or existing.get("hair_guide_type") not in {"placement_point", "curve", "braid_control", "braid_visual"}:
        return False
    if existing not in utils.generated_objects():
        return False
    bpy.data.objects.remove(existing, do_unlink=True)
    return True


TAPER_OBJECT_NAME = "HGD_Default_Taper"
TAPER_PRESET_VALUES = {
    "ANIME": (1.0, 0.65, 0.0, 0.035),
    "SHARP_ANIME": (1.1, 0.45, 0.0, 0.03),
    "SOFT": (1.0, 0.8, 0.15, 0.035),
    "REALISTIC": (0.8, 0.55, 0.2, 0.02),
}
TAPER_PRESET_LABELS = {
    "ANIME": "アニメ標準",
    "SHARP_ANIME": "鋭いアニメ髪",
    "SOFT": "柔らかめ",
    "REALISTIC": "自然寄り",
    "CUSTOM": "カスタム",
}


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
    obj.data.bevel_depth = scene.hair_taper_bevel_depth
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


class HGD_OT_apply_taper_preset(bpy.types.Operator):
    bl_idname = "hgd.apply_taper_preset"
    bl_label = "プリセットを反映"
    bl_description = "選択中のテーパープリセット値をカーブ形状設定へ反映します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        preset = scene.hair_taper_preset
        if preset == "CUSTOM":
            self.report({'INFO'}, "カスタム設定を使用します。現在値は変更しません。")
            return {'FINISHED'}
        root, mid, tip, bevel = TAPER_PRESET_VALUES[preset]
        scene.hair_taper_root_radius = root
        scene.hair_taper_mid_radius = mid
        scene.hair_taper_tip_radius = tip
        scene.hair_taper_bevel_depth = bevel
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


class HGD_OT_update_selected_braids(bpy.types.Operator):
    bl_idname = "hgd.update_selected_braids"
    bl_label = "選択三つ編みを更新"
    bl_description = "選択中の三つ編み制御カーブから表示用三つ編みを再生成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        controls = _braid_controls_from_context(context, True)
        if not controls:
            self.report({'WARNING'}, "三つ編み制御カーブが選択されていません。")
            return {'CANCELLED'}
        updated = 0
        for control in controls:
            if _create_or_replace_braid_visual(context, control):
                updated += 1
        self.report({'INFO'}, f"選択三つ編みを{updated}本更新しました。")
        return {'FINISHED'}


class HGD_OT_update_all_braids(bpy.types.Operator):
    bl_idname = "hgd.update_all_braids"
    bl_label = "全三つ編みを更新"
    bl_description = "すべての三つ編み制御カーブから表示用三つ編みを再生成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        controls = _braid_controls_from_context(context, False)
        if not controls:
            self.report({'WARNING'}, "三つ編み制御カーブが見つかりません。")
            return {'CANCELLED'}
        updated = 0
        for control in controls:
            if _create_or_replace_braid_visual(context, control):
                updated += 1
        self.report({'INFO'}, f"全三つ編みを{updated}本更新しました。")
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
    bl_description = "通常カーブまたは三つ編み制御カーブの根元を元の配置点へ追従させます"
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
            new_root_local = obj.matrix_world.inverted() @ source.matrix_world.translation
            root_point = spline.bezier_points[0]
            old_root_local = root_point.co.copy()
            delta = new_root_local - old_root_local
            if context.scene.hair_follow_keep_tip_offset:
                for point in spline.bezier_points:
                    point.co += delta
                    point.handle_left += delta
                    point.handle_right += delta
            else:
                root_point.co = new_root_local
                root_point.handle_left += delta
                root_point.handle_right += delta
            updated += 1
        if skipped:
            self.report({'WARNING'}, f"カーブ根元を{updated}本更新しました。参照元配置点が見つからないカーブ {skipped} 本をスキップしました。")
        else:
            self.report({'INFO'}, f"カーブ根元を{updated}本更新しました。参照点なしは0本です。")
        return {'FINISHED'}


class HGD_OT_mirror_side(bpy.types.Operator):
    bl_idname = "hgd.mirror_side"
    bl_label = "左右ミラー"
    bl_description = "選択したSide_LまたはSide_Rの配置点、生成カーブ、三つ編み制御カーブをX軸で反対側へ複製します"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        items=(("L2R", "左から右", "選択したSide_LオブジェクトをSide_Rへミラー"), ("R2L", "右から左", "選択したSide_RオブジェクトをSide_Lへミラー")),
        default="L2R",
        description="左右ミラー方向",
    )

    def execute(self, context):
        src_side, dst_side = ("Side_L", "Side_R") if self.direction == "L2R" else ("Side_R", "Side_L")
        selected = [obj for obj in context.selected_objects if obj.get("hair_region") == src_side and obj.get("hair_guide_type") in {"placement_point", "curve", "braid_control", "braid_visual"}]
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
            new_obj.location.x *= -1
            new_obj["hair_guide_type"] = "placement_point"
            new_obj["hair_region"] = dst_side
            new_obj["flow_side"] = "R" if dst_side == "Side_R" else "L"
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
            collections[utils.CURVES].objects.link(new_obj)
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
            new_obj["hair_region"] = dst_side
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
        control_candidates = []
        seen_controls = set()
        for obj in selected:
            if obj.get("hair_guide_type") == "braid_control":
                control = obj
            elif obj.get("hair_guide_type") == "braid_visual":
                control = bpy.data.objects.get(obj.get("hair_braid_control", ""))
            else:
                control = None
            if control and control.get("hair_guide_type") == "braid_control" and control.name not in seen_controls:
                control_candidates.append(control)
                seen_controls.add(control.name)
        for obj in control_candidates:
            braid_id = _next_braid_id()
            new_name = f"HGD_BRAID_CTRL_{braid_id}"
            if context.scene.hair_mirror_overwrite_existing:
                _delete_generated_if_exists(new_name)
            elif bpy.data.objects.get(new_name):
                self.report({'WARNING'}, "ミラー先が既に存在し、上書きがオフです。連番名で作成します。")
                new_name = utils.unique_name(new_name)
            new_obj = obj.copy()
            new_obj.data = obj.data.copy()
            new_obj.name = new_name
            new_obj.data.name = new_name + "Curve"
            collections[utils.CURVES].objects.link(new_obj)
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
            new_obj["hair_guide_type"] = "braid_control"
            new_obj["hair_region"] = dst_side
            new_obj["hair_braid_id"] = braid_id
            new_obj["hair_use_taper"] = False
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
            _create_or_replace_braid_visual(context, new_obj)
            mirrored += 2
        self.report({'INFO'}, f"{mirrored}個をミラーしました。参照配置点を失ったカーブは{lost_links}本です。")
        return {'FINISHED'}


class HGD_OT_mirror_side_l_to_r(bpy.types.Operator):
    bl_idname = "hgd.mirror_side_l_to_r"
    bl_label = "左側→右側へミラー"
    bl_description = "選択したSide_Lの配置点、カーブ、三つ編みをX軸でSide_Rへ複製します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.hgd.mirror_side(direction="L2R")


class HGD_OT_mirror_side_r_to_l(bpy.types.Operator):
    bl_idname = "hgd.mirror_side_r_to_l"
    bl_label = "右側→左側へミラー"
    bl_description = "選択したSide_Rの配置点、カーブ、三つ編みをX軸でSide_Lへ複製します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.hgd.mirror_side(direction="R2L")


classes = (
    HGD_OT_set_target_head,
    HGD_OT_create_hair_guides,
    HGD_OT_create_detailed_guides,
    HGD_OT_delete_hair_guides,
    HGD_OT_show_hide_guides,
    HGD_OT_region_visibility,
    HGD_OT_generate_placement_points,
    HGD_OT_clear_placement_points,
    HGD_OT_create_curve_from_points,
    HGD_OT_check_root_clustering,
    HGD_OT_clear_warnings,
    HGD_OT_clear_all_generated,
    HGD_OT_apply_taper_preset,
    HGD_OT_create_or_update_default_taper,
    HGD_OT_apply_taper_to_selected_curves,
    HGD_OT_apply_taper_to_all_curves,
    HGD_OT_clear_taper_from_selected_curves,
    HGD_OT_clear_taper_from_all_curves,
    HGD_OT_update_selected_braids,
    HGD_OT_update_all_braids,
    HGD_OT_apply_curve_batch_settings,
    HGD_OT_update_curve_roots_from_points,
    HGD_OT_mirror_side,
    HGD_OT_mirror_side_l_to_r,
    HGD_OT_mirror_side_r_to_l,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
