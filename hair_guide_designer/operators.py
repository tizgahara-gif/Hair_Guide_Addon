import random
import mathutils
import bpy
from bpy.props import EnumProperty
from . import utils


def require_head(context, operator):
    head = context.scene.hair_target_head_object
    if not head or head.type != "MESH":
        operator.report({'WARNING'}, "Target Head Object is not set to a Mesh")
        return None
    return head


class HGD_OT_set_target_head(bpy.types.Operator):
    bl_idname = "hgd.set_target_head"
    bl_label = "Set Selected As Target Head"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != "MESH":
            self.report({'WARNING'}, "Select a Mesh object to set as Target Head")
            return {'CANCELLED'}
        context.scene.hair_target_head_object = obj
        self.report({'INFO'}, f"Target Head Object set to {obj.name}")
        return {'FINISHED'}


class HGD_OT_create_hair_guides(bpy.types.Operator):
    bl_idname = "hgd.create_hair_guides"
    bl_label = "Create Hair Guides"
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

            guide_specs = [
                ("HAIR_GUIDE_Top", [center + mathutils.Vector((-rx * 0.45, 0, top-center.z)), center + mathutils.Vector((0, 0, top + size.z*0.04-center.z)), center + mathutils.Vector((rx * 0.45, 0, top-center.z))], "Back_Upper"),
                ("HAIR_GUIDE_Hairline", utils.make_arc_points(center, rx * 0.72, ry * 0.55, hairline_z, 3.6, 5.8, 5), "Front"),
                ("HAIR_GUIDE_Hachi", utils.make_arc_points(center, rx, ry, hachi_z, 0.0, 6.28, 9), "Back_Upper"),
                ("HAIR_GUIDE_Ear_Upper", [mathutils.Vector((center.x - rx, center.y, ear_z)), mathutils.Vector((center.x + rx, center.y, ear_z))], "Side"),
                ("HAIR_GUIDE_Ear_Back", [mathutils.Vector((center.x - rx, back_y, ear_z)), mathutils.Vector((center.x + rx, back_y, ear_z))], "Side"),
                ("HAIR_GUIDE_Occipital", utils.make_arc_points(center, rx * 0.75, ry * 0.65, occ_z, 0.15, 3.0, 5), "Back_Middle"),
                ("HAIR_GUIDE_Nape", [mathutils.Vector((center.x - rx * 0.45, back_y, nape_z)), mathutils.Vector((center.x, back_y + offset, nape_z - size.z*0.03)), mathutils.Vector((center.x + rx * 0.45, back_y, nape_z))], "Nape"),
                ("HAIR_GUIDE_Center", [mathutils.Vector((center.x, center.y, top)), mathutils.Vector((center.x, center.y, nape_z))], "Back_Middle"),
                ("HAIR_GUIDE_Side_Boundary_L", [mathutils.Vector((center.x - rx, front_y, hairline_z)), mathutils.Vector((center.x - rx, center.y, ear_z)), mathutils.Vector((center.x - rx * 0.7, back_y, occ_z))], "Side"),
                ("HAIR_GUIDE_Side_Boundary_R", [mathutils.Vector((center.x + rx, front_y, hairline_z)), mathutils.Vector((center.x + rx, center.y, ear_z)), mathutils.Vector((center.x + rx * 0.7, back_y, occ_z))], "Side"),
            ]
            for name, points, region in guide_specs:
                utils.make_curve(name, points, guides, region, "guide", scene, bevel=0.004)
            self._create_region_guides(context, regions, center, size, rx, ry, offset, hairline_z, ear_z, occ_z, nape_z, front_y, back_y)
            self.report({'INFO'}, "Hair guides and region guides created")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f"Failed to create hair guides: {exc}")
            return {'CANCELLED'}

    def _create_region_guides(self, context, regions, center, size, rx, ry, offset, hairline_z, ear_z, occ_z, nape_z, front_y, back_y):
        scene = context.scene
        top_z = center.z + size.z * 0.55
        # Front: start line, clearance, split guides, flow guides.
        utils.make_curve("REGION_Front_Hair_Start", [mathutils.Vector((center.x - rx*0.55, front_y, hairline_z)), mathutils.Vector((center.x, front_y-offset, hairline_z+size.z*0.04)), mathutils.Vector((center.x + rx*0.55, front_y, hairline_z))], regions, "Front", "region", scene, bevel=0.003)
        utils.make_curve("REGION_Front_Forehead_Clearance", [mathutils.Vector((center.x - rx*0.5, front_y-offset*2.5, hairline_z-size.z*0.12)), mathutils.Vector((center.x, front_y-offset*3.0, hairline_z-size.z*0.17)), mathutils.Vector((center.x + rx*0.5, front_y-offset*2.5, hairline_z-size.z*0.12))], regions, "Front", "region", scene, bevel=0.002)
        for xmul, label in [(-0.35, "L"), (0.0, "Center"), (0.35, "R")]:
            root = mathutils.Vector((center.x + rx*xmul, front_y, hairline_z))
            utils.make_curve(f"REGION_Front_Flow_{label}", [root, root + mathutils.Vector((0, -offset*3, -size.z*0.18)), root + mathutils.Vector((0, -offset*4, -size.z*0.35))], regions, "Front", "region", scene, bevel=0.002)
        # Side.
        for side, sign in [("L", -1), ("R", 1)]:
            x = center.x + sign * rx
            utils.make_curve(f"REGION_Side_{side}_Ear_Upper", [mathutils.Vector((x, center.y-ry*0.35, ear_z)), mathutils.Vector((x, center.y+ry*0.15, ear_z+size.z*0.02)), mathutils.Vector((x, back_y, ear_z))], regions, "Side", "region", scene, bevel=0.003)
            utils.make_curve(f"REGION_Side_{side}_Flow_To_Back", [mathutils.Vector((x, center.y-ry*0.45, ear_z+size.z*0.12)), mathutils.Vector((center.x + (x-center.x)*0.9, center.y+ry*0.25, ear_z+size.z*0.02)), mathutils.Vector((center.x + (x-center.x)*0.65, back_y, occ_z))], regions, "Side", "region", scene, bevel=0.002)
            utils.make_curve(f"REGION_Side_{side}_Volume_Limit", [mathutils.Vector((center.x + (x-center.x)*1.08, center.y-ry*0.2, ear_z+size.z*0.08)), mathutils.Vector((center.x + (x-center.x)*1.08, center.y+ry*0.35, ear_z+size.z*0.05))], regions, "Side", "region", scene, bevel=0.002)
        # Back upper cap lines.
        for zmul in [0.35, 0.45, 0.55]:
            z = center.z + size.z * zmul
            utils.make_curve(f"REGION_Back_Upper_Cap_{int(zmul*100)}", utils.make_arc_points(center, rx*0.85, ry*0.85, z, 0.15, 3.0, 7), regions, "Back_Upper", "region", scene, bevel=0.002)
        utils.make_curve("REGION_Back_Upper_Volume_Boundary", utils.make_arc_points(center, rx*0.95, ry*0.95, top_z-size.z*0.12, 0.0, 3.14, 7), regions, "Back_Upper", "region", scene, bevel=0.003)
        # Back middle variation guides.
        for xmul, label in [(-0.45, "Left"), (0.0, "Center_Sparse"), (0.45, "Right")]:
            x = center.x + rx*xmul
            utils.make_curve(f"REGION_Back_Middle_{label}", [mathutils.Vector((x, back_y, occ_z+size.z*0.08)), mathutils.Vector((center.x + (x-center.x)*0.9, back_y+offset, occ_z-size.z*0.1)), mathutils.Vector((center.x + (x-center.x)*0.7, back_y, nape_z+size.z*0.14))], regions, "Back_Middle", "region", scene, bevel=0.002)
        # Nape.
        utils.make_curve("REGION_Nape_Lower_Edge", [mathutils.Vector((center.x - rx*0.45, back_y, nape_z)), mathutils.Vector((center.x, back_y+offset, nape_z-size.z*0.03)), mathutils.Vector((center.x + rx*0.45, back_y, nape_z))], regions, "Nape", "region", scene, bevel=0.003)
        for xmul, label in [(-0.25, "L"), (0.0, "Center"), (0.25, "R")]:
            root = mathutils.Vector((center.x + rx*xmul, back_y, nape_z))
            utils.make_curve(f"REGION_Nape_Flow_{label}", [root, root + mathutils.Vector((0, offset*1.5, -size.z*0.12)), root + mathutils.Vector((0, offset*2.5, -size.z*0.28))], regions, "Nape", "region", scene, bevel=0.002)


class HGD_OT_delete_hair_guides(bpy.types.Operator):
    bl_idname = "hgd.delete_hair_guides"
    bl_label = "Delete Hair Guides"
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
    bl_label = "Show/Hide Guides"
    bl_options = {'REGISTER', 'UNDO'}
    hide: bpy.props.BoolProperty(default=False)

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
            self.report({'WARNING'}, "No guides found")
            return {'CANCELLED'}
        return {'FINISHED'}


class HGD_OT_region_visibility(bpy.types.Operator):
    bl_idname = "hgd.region_visibility"
    bl_label = "Region Visibility"
    bl_options = {'REGISTER', 'UNDO'}
    region: EnumProperty(items=[("Front", "Front", ""), ("Side", "Side", ""), ("Back_Upper", "Back Upper", ""), ("Back_Middle", "Back Middle", ""), ("Nape", "Nape", ""), ("ALL", "All", "")], default="ALL")
    action: EnumProperty(items=[("SHOW", "Show", ""), ("HIDE", "Hide", "")], default="SHOW")

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
        return {'FINISHED'}


class HGD_OT_generate_placement_points(bpy.types.Operator):
    bl_idname = "hgd.generate_placement_points"
    bl_label = "Generate Placement Points"
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
                    obj["hair_root_id"] = f"{region}_{i+1:03d}"
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
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.collections.get(utils.ROOT):
            self.report({'WARNING'}, "HairGuideSystem does not exist")
            return {'CANCELLED'}
        count = utils.clear_collection_objects(utils.PLACEMENT_POINTS, "placement_point")
        if count == 0:
            self.report({'WARNING'}, "No placement points to clear")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Cleared {count} placement points")
        return {'FINISHED'}


class HGD_OT_create_curve_from_points(bpy.types.Operator):
    bl_idname = "hgd.create_curve_from_points"
    bl_label = "Create Curve From Selected Points"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            points = [obj for obj in context.selected_objects if obj.get("hair_guide_type") == "placement_point"]
            if not points:
                self.report({'WARNING'}, "Placement Point is not selected")
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
                obj["hair_root_id"] = point.get("hair_root_id", "")
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
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            if not bpy.data.collections.get(utils.ROOT):
                self.report({'WARNING'}, "HairGuideSystem does not exist")
                return {'CANCELLED'}
            self._clear_warning_markers(context, reset_colors=False)
            points = utils.generated_objects("placement_point")
            if not points:
                self.report({'WARNING'}, "No placement points found")
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
                    # Strengthen warning for similar height, size, and length when available.
                    height_close = abs(obj.location.z - other.location.z) < threshold * 0.5
                    size_close = abs(float(obj.get("recommended_size", 0)) - float(other.get("recommended_size", 0))) < threshold * 0.25
                    length_close = abs(float(obj.get("recommended_length", 0)) - float(other.get("recommended_length", 0))) < threshold * 2.0
                    if not (height_close or size_close or length_close):
                        continue
                    for target in (obj, other):
                        target.color = utils.WARNING_COLOR
                        warned.add(target.name)
                    loc = (obj.location + other.location) * 0.5
                    marker = utils.make_marker("WARNING_RootCluster", loc, max(threshold * 0.25, 0.01), warnings, obj.get("hair_region", ""), "warning", context.scene)
                    marker["hair_warning_type"] = "root_cluster"
                    marker["warning_objects"] = f"{obj.name},{other.name}"
                    warning_count += 1
            context.scene.hair_warning_count = warning_count
            self.report({'INFO'}, f"Root clustering warnings: {warning_count}")
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
        self.report({'INFO'}, f"Cleared {count} warning markers")
        return {'FINISHED'}


classes = (
    HGD_OT_set_target_head,
    HGD_OT_create_hair_guides,
    HGD_OT_delete_hair_guides,
    HGD_OT_show_hide_guides,
    HGD_OT_region_visibility,
    HGD_OT_generate_placement_points,
    HGD_OT_clear_placement_points,
    HGD_OT_create_curve_from_points,
    HGD_OT_check_root_clustering,
    HGD_OT_clear_warnings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
