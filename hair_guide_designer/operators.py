import random
import mathutils
import bpy
from bpy.props import EnumProperty
from . import utils


def require_head(context, operator):
    head = context.scene.hair_target_head_object
    if not head or head.type != "MESH":
        operator.report({'WARNING'}, "No target head object set. Select a mesh and click Set Selected Mesh as Head.")
        return None
    return head


class HGD_OT_set_target_head(bpy.types.Operator):
    bl_idname = "hgd.set_target_head"
    bl_label = "Set Selected Mesh as Head"
    bl_description = "Register the selected mesh as the target head without editing it"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != "MESH":
            self.report({'WARNING'}, "No mesh selected. Select a head mesh and click Set Selected Mesh as Head.")
            return {'CANCELLED'}
        context.scene.hair_target_head_object = obj
        self.report({'INFO'}, f"Target head set: {obj.name}")
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
    bl_label = "Create Basic Hair Guides"
    bl_description = "Creates only essential guide lines: Hairline, Side Boundary, Back Volume, Nape, and Center."
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
            self.report({'INFO'}, f"Regenerated {len(guide_specs)} basic guide object(s); removed {removed} old basic guide(s).")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"Failed to create basic hair guides: {exc}")
            return {'CANCELLED'}


class HGD_OT_create_detailed_guides(bpy.types.Operator):
    bl_idname = "hgd.create_detailed_guides"
    bl_label = "Add Detailed Guide Lines"
    bl_description = "Add optional detailed references such as Top, Hachi, Ear, Occipital, and region helper lines."
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
            self.report({'INFO'}, f"Added {detailed_count} detailed guide object(s).")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"Failed to create detailed guide lines: {exc}")
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
    bl_label = "Delete Guide Lines"
    bl_description = "Delete only generated guide and region line objects; the target head is not deleted"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        root = bpy.data.collections.get(utils.ROOT)
        if not root:
            self.report({'WARNING'}, "HairGuideSystem does not exist")
            return {'CANCELLED'}
        count = 0
        for collection_name in (utils.GUIDES, utils.REGIONS):
            count += utils.clear_collection_objects(collection_name)
        if count == 0:
            self.report({'WARNING'}, "No generated hair guides to delete")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Deleted {count} guide objects")
        return {'FINISHED'}


class HGD_OT_show_hide_guides(bpy.types.Operator):
    bl_idname = "hgd.show_hide_guides"
    bl_label = "Show/Hide Guide Lines"
    bl_description = "Show or hide generated guide and region line objects"
    bl_options = {'REGISTER', 'UNDO'}
    hide: bpy.props.BoolProperty(default=False, description="Hide when enabled; show when disabled")

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystem does not exist")
            return {'CANCELLED'}
        count = 0
        for obj in utils.generated_objects():
            if obj.get("hair_guide_type") in {"guide", "region"}:
                obj.hide_viewport = self.hide
                obj.hide_render = self.hide
                count += 1
        if count == 0:
            self.report({'WARNING'}, "No guide lines found. Click Regenerate Basic Guides first.")
            return {'CANCELLED'}
        self.report({'INFO'}, "Guide lines hidden." if self.hide else "Guide lines shown.")
        return {'FINISHED'}


class HGD_OT_region_visibility(bpy.types.Operator):
    bl_idname = "hgd.region_visibility"
    bl_label = "Region Visibility"
    bl_description = "Show or hide generated objects for a hair construction region"
    bl_options = {'REGISTER', 'UNDO'}
    region: EnumProperty(items=[("Front", "Front", ""), ("Side", "Side", ""), ("Side_L", "Side L", ""), ("Side_R", "Side R", ""), ("Back_Upper", "Back Upper", ""), ("Back_Middle", "Back Middle", ""), ("Nape", "Nape", ""), ("ALL", "All", "")], default="ALL", description="Hair construction region to show or hide")
    action: EnumProperty(items=[("SHOW", "Show", ""), ("HIDE", "Hide", "")], default="SHOW", description="Visibility action to apply")

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystem does not exist")
            return {'CANCELLED'}
        hide = self.action == "HIDE"
        regions = utils.REGION_NAMES if self.region == "ALL" else (self.region,)
        count = sum(utils.set_region_visibility(region, hide) for region in regions)
        if count == 0:
            self.report({'WARNING'}, "No region objects found")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Region visibility updated: {self.region} {self.action.lower()}.")
        return {'FINISHED'}


class HGD_OT_generate_placement_points(bpy.types.Operator):
    bl_idname = "hgd.generate_placement_points"
    bl_label = "Generate Placement Points"
    bl_description = "Generate seed-based suggested hair strand root positions inside HairGuideSystem/PlacementPoints"
    bl_options = {'REGISTER', 'UNDO'}

    BASE_COUNTS = {"Front": 7, "Side_L": 4, "Side_R": 4, "Back_Upper": 6, "Back_Middle": 9, "Nape": 5}

    def execute(self, context):
        try:
            head = require_head(context, self)
            if not head:
                return {'CANCELLED'}
            _, collections = utils.ensure_system()
            collection = collections[utils.PLACEMENT_POINTS]
            scene = context.scene
            min_v, max_v, center, size = utils.head_bounds(head)
            rng = random.Random(scene.hair_seed)
            count_total = 0
            for region, base_count in self.BASE_COUNTS.items():
                count = max(1, round(base_count * scene.hair_density))
                positions = self._base_positions(region, count, min_v, max_v, center, size, scene.hair_guide_offset)
                for i, base in enumerate(positions):
                    loc = self._jittered(region, base, rng, scene)
                    radius = max(size.length * 0.008, 0.01) * (1.0 + rng.uniform(-scene.hair_size_variation, scene.hair_size_variation))
                    obj = utils.make_marker(f"POINT_{region}_{i+1:03d}", loc, max(radius, 0.004), collection, region, "placement_point", scene)
                    direction = utils.direction_for_region(region, loc.x - center.x)
                    length = scene.hair_curve_length * (1.0 + rng.uniform(-scene.hair_length_variation, scene.hair_length_variation))
                    size_rec = max(scene.hair_curve_root_radius * (1.0 + rng.uniform(-scene.hair_size_variation, scene.hair_size_variation)), 0.001)
                    obj["hair_root_id"] = obj.name
                    obj["recommended_size"] = size_rec
                    obj["recommended_direction"] = utils.vector_to_string(direction)
                    obj["recommended_length"] = max(length, 0.01)
                    obj["flow_side"] = "L" if loc.x < center.x - size.x*0.05 else ("R" if loc.x > center.x + size.x*0.05 else "Center")
                    obj["position_type"] = "center" if abs(loc.x - center.x) < size.x * 0.18 else "outer"
                    count_total += 1
            self.report({'INFO'}, f"Generated {count_total} placement points")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"Failed to generate placement points: {exc}")
            return {'CANCELLED'}

    def _base_positions(self, region, count, min_v, max_v, center, size, offset):
        rx = size.x * 0.5 + offset
        ry = size.y * 0.5 + offset
        positions = []
        for i in range(count):
            t = i / max(count - 1, 1)
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

    def _jittered(self, region, base, rng, scene):
        x_jit = rng.uniform(-scene.hair_width_variation, scene.hair_width_variation)
        if region == "Side_R":
            x_jit *= 1.0 - scene.hair_symmetry_bias * 0.65
        elif region == "Side_L":
            x_jit *= 1.0 - scene.hair_symmetry_bias * 0.35
        return base + mathutils.Vector((x_jit, rng.uniform(-scene.hair_depth_variation, scene.hair_depth_variation), rng.uniform(-scene.hair_height_variation, scene.hair_height_variation)))


class HGD_OT_clear_placement_points(bpy.types.Operator):
    bl_idname = "hgd.clear_placement_points"
    bl_label = "Clear Placement Points"
    bl_description = "Delete generated placement point objects only"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystem does not exist")
            return {'CANCELLED'}
        count = utils.clear_collection_objects(utils.PLACEMENT_POINTS, "placement_point")
        if count == 0:
            self.report({'WARNING'}, "No placement points found. Click Generate Placement Points first.")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Cleared {count} placement points")
        return {'FINISHED'}


class HGD_OT_create_curve_from_points(bpy.types.Operator):
    bl_idname = "hgd.create_curve_from_points"
    bl_label = "Create Editable Curve Strands"
    bl_description = "Create editable Bezier curve strands from selected placement points without converting them to mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            points = [obj for obj in context.selected_objects if obj.get("hair_guide_type") == "placement_point"]
            if not points:
                self.report({'WARNING'}, "No placement points selected. Select generated placement point objects first.")
                return {'CANCELLED'}
            _, collections = utils.ensure_system()
            curves = collections[utils.CURVES]
            scene = context.scene
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
                made += 1
            self.report({'INFO'}, f"Created {made} curve strands")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"Failed to create curve strands: {exc}")
            return {'CANCELLED'}

    def _prefix(self, region):
        return {
            "Front": "HAIR_FRONT",
            "Side_L": "HAIR_SIDE_L",
            "Side_R": "HAIR_SIDE_R",
            "Back_Upper": "HAIR_BACK_UPPER",
            "Back_Middle": "HAIR_BACK_MIDDLE",
            "Nape": "HAIR_NAPE",
        }.get(region, "HAIR_CURVE")


class HGD_OT_check_root_clustering(bpy.types.Operator):
    bl_idname = "hgd.check_root_clustering"
    bl_label = "Check Root Clustering"
    bl_description = "Detect placement point pairs in the same region that are closer than the root clustering threshold"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            if not bpy.data.collections.get(utils.ROOT):
                self.report({'WARNING'}, "HairGuideSystem does not exist")
                return {'CANCELLED'}
            self._clear_warning_markers(context, reset_colors=False)
            points = utils.generated_objects("placement_point")
            if not points:
                self.report({'WARNING'}, "No placement points found. Click Generate Placement Points first.")
                return {'CANCELLED'}
            _, collections = utils.ensure_system()
            warnings = collections[utils.WARNINGS]
            threshold = context.scene.hair_root_cluster_threshold
            threshold_sq = threshold * threshold
            warned = set()
            warning_count = 0
            for i, obj in enumerate(points):
                for other in points[i + 1:]:
                    if obj.get("hair_region") != other.get("hair_region"):
                        continue
                    if (obj.location - other.location).length_squared >= threshold_sq:
                        continue
                    height_delta = abs(obj.location.z - other.location.z)
                    size_delta = abs(float(obj.get("recommended_size", 0)) - float(other.get("recommended_size", 0)))
                    length_delta = abs(float(obj.get("recommended_length", 0)) - float(other.get("recommended_length", 0)))
                    for target in (obj, other):
                        target.color = utils.WARNING_COLOR
                        warned.add(target.name)
                    loc = (obj.location + other.location) * 0.5
                    marker = utils.make_marker("WARNING_RootCluster", loc, max(threshold * 0.25, 0.01), warnings, obj.get("hair_region", ""), "warning", context.scene)
                    marker["hair_warning_type"] = "root_cluster"
                    marker["warning_objects"] = f"{obj.name},{other.name}"
                    marker["height_delta"] = height_delta
                    marker["size_delta"] = size_delta
                    marker["length_delta"] = length_delta
                    warning_count += 1
            context.scene.hair_warning_count = warning_count
            self.report({'INFO'}, f"Found {warning_count} root clustering warnings.")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"Failed to check root clustering: {exc}")
            return {'CANCELLED'}

    def _clear_warning_markers(self, context, reset_colors=True):
        if reset_colors:
            for obj in utils.generated_objects("placement_point"):
                obj.color = utils.REGION_COLORS.get(obj.get("hair_region"), (0.9, 0.9, 0.9, 1.0))
        utils.clear_collection_objects(utils.WARNINGS, "warning")
        context.scene.hair_warning_count = 0


class HGD_OT_clear_warnings(bpy.types.Operator):
    bl_idname = "hgd.clear_warnings"
    bl_label = "Clear Warnings"
    bl_description = "Remove warning markers and restore placement point colors"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystem does not exist")
            return {'CANCELLED'}
        for obj in utils.generated_objects("placement_point"):
            obj.color = utils.REGION_COLORS.get(obj.get("hair_region"), (0.9, 0.9, 0.9, 1.0))
        count = utils.clear_collection_objects(utils.WARNINGS, "warning")
        context.scene.hair_warning_count = 0
        if count == 0:
            self.report({'WARNING'}, "No warnings to clear")
            return {'CANCELLED'}
        self.report({'INFO'}, "Cleared warnings.")
        return {'FINISHED'}


class HGD_OT_clear_all_generated(bpy.types.Operator):
    bl_idname = "hgd.clear_all_generated"
    bl_label = "Clear All Generated Objects"
    bl_description = "Delete generated guides, regions, placement points, curves, and warnings inside HairGuideSystem only"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystem does not exist")
            return {'CANCELLED'}
        total = 0
        for collection_name in (utils.GUIDES, utils.REGIONS, utils.PLACEMENT_POINTS, utils.CURVES, utils.WARNINGS):
            total += utils.clear_collection_objects(collection_name)
        context.scene.hair_warning_count = 0
        if total == 0:
            self.report({'WARNING'}, "No generated objects to clear")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Cleared {total} generated Hair Guide objects")
        return {'FINISHED'}


def _generated_curves_from_context(context, selected_only):
    objects = context.selected_objects if selected_only else utils.generated_objects("curve")
    return [obj for obj in objects if obj.type == "CURVE" and obj.get("hair_guide_type") == "curve"]


def _first_bezier_spline(obj):
    if obj.type != "CURVE":
        return None
    for spline in obj.data.splines:
        if spline.type == "BEZIER" and spline.bezier_points:
            return spline
    return None


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
    if not existing or existing.get("hair_guide_type") not in {"placement_point", "curve"}:
        return False
    if existing not in utils.generated_objects():
        return False
    bpy.data.objects.remove(existing, do_unlink=True)
    return True


class HGD_OT_apply_curve_batch_settings(bpy.types.Operator):
    bl_idname = "hgd.apply_curve_batch_settings"
    bl_label = "Apply Curve Batch Settings"
    bl_description = "Apply length scale, bevel depth, and resolution to selected or all generated hair curves"
    bl_options = {'REGISTER', 'UNDO'}

    target: EnumProperty(
        items=(("SELECTED", "Selected", "Apply to selected generated curves"), ("ALL", "All Generated", "Apply to all generated curves")),
        default="SELECTED",
        description="Generated curves to update",
    )

    def execute(self, context):
        curves = _generated_curves_from_context(context, self.target == "SELECTED")
        if not curves:
            message = "No generated hair curves selected." if self.target == "SELECTED" else "No generated hair curves found."
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
        self.report({'INFO'}, f"Applied curve settings to {len(curves)} curve(s).")
        return {'FINISHED'}


class HGD_OT_update_curve_roots_from_points(bpy.types.Operator):
    bl_idname = "hgd.update_curve_roots_from_points"
    bl_label = "Update Curve Roots From Points"
    bl_description = "Move generated curve roots back to their source placement points"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = _generated_curves_from_context(context, context.scene.hair_follow_update_selected_only)
        if not curves:
            self.report({'WARNING'}, "No generated hair curves selected." if context.scene.hair_follow_update_selected_only else "No generated hair curves found.")
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
            self.report({'WARNING'}, f"Updated {updated} curve root(s), skipped {skipped} missing source point(s).")
        else:
            self.report({'INFO'}, f"Updated {updated} curve root(s), skipped 0 missing source point(s).")
        return {'FINISHED'}


class HGD_OT_mirror_side(bpy.types.Operator):
    bl_idname = "hgd.mirror_side"
    bl_label = "Mirror Side Objects"
    bl_description = "Mirror selected Side_L or Side_R placement points and generated curves across the X axis"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        items=(("L2R", "Side_L to Side_R", "Mirror selected Side_L objects to Side_R"), ("R2L", "Side_R to Side_L", "Mirror selected Side_R objects to Side_L")),
        default="L2R",
        description="Side mirror direction",
    )

    def execute(self, context):
        src_side, dst_side = ("Side_L", "Side_R") if self.direction == "L2R" else ("Side_R", "Side_L")
        selected = [obj for obj in context.selected_objects if obj.get("hair_region") == src_side and obj.get("hair_guide_type") in {"placement_point", "curve"}]
        if not selected:
            self.report({'WARNING'}, f"No {src_side} objects selected.")
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
                self.report({'WARNING'}, "Mirror target already exists and overwrite is disabled; using a unique numbered name.")
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
                self.report({'WARNING'}, "Mirror target already exists and overwrite is disabled; using a unique numbered name.")
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
            # Mirror generated curve data in local coordinates only; keep object transform unchanged.
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
        self.report({'INFO'}, f"Mirrored {mirrored} object(s). {lost_links} curve(s) lost source point link.")
        return {'FINISHED'}


class HGD_OT_mirror_side_l_to_r(bpy.types.Operator):
    bl_idname = "hgd.mirror_side_l_to_r"
    bl_label = "Mirror Side_L to Side_R"
    bl_description = "Mirror selected Side_L placement points and curves to Side_R across the X axis"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.hgd.mirror_side(direction="L2R")


class HGD_OT_mirror_side_r_to_l(bpy.types.Operator):
    bl_idname = "hgd.mirror_side_r_to_l"
    bl_label = "Mirror Side_R to Side_L"
    bl_description = "Mirror selected Side_R placement points and curves to Side_L across the X axis"
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
