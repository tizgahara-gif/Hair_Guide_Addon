import math
import bpy
import mathutils

ROOT = "HairGuideSystem"
GUIDES = "Guides"
REGIONS = "Regions"
PLACEMENT_POINTS = "PlacementPoints"
CURVES = "Curves"
WARNINGS = "Warnings"
TAPER_OBJECTS = "TaperObjects"
PROFILE_OBJECTS = "ProfileObjects"
FLAT_MESHES = "FlatMeshes"
SYSTEM_COLLECTIONS = (GUIDES, REGIONS, PLACEMENT_POINTS, CURVES, WARNINGS, TAPER_OBJECTS, FLAT_MESHES)
CURVE_REGION_COLLECTIONS = ("Top", "Front", "Side_L", "Side_R", "Back_Upper", "Back_Middle", "Nape", "Braid", "Twist")
REGION_NAMES = ("Top", "Front", "Side", "Back_Upper", "Back_Middle", "Nape")
POINT_REGIONS = ("Top", "Front", "Side_L", "Side_R", "Back_Upper", "Back_Middle", "Nape")
REGION_COLORS = {
    "Top": (1.0, 0.95, 0.35, 1.0),
    "Front": (1.0, 0.45, 0.25, 1.0),
    "Side": (0.25, 0.7, 1.0, 1.0),
    "Side_L": (0.25, 0.55, 1.0, 1.0),
    "Side_R": (0.25, 1.0, 0.55, 1.0),
    "Back_Upper": (0.65, 0.35, 1.0, 1.0),
    "Back_Middle": (1.0, 0.75, 0.2, 1.0),
    "Nape": (0.2, 1.0, 0.85, 1.0),
}
CURVE_REGION_COLORS = {
    "Top": (0.1, 0.9, 0.2, 1.0),
    "Front": (0.1, 0.35, 1.0, 1.0),
    "Side_L": (1.0, 0.85, 0.1, 1.0),
    "Side_R": (1.0, 0.85, 0.1, 1.0),
    "Back_Upper": (1.0, 0.1, 0.1, 1.0),
    "Back_Middle": (1.0, 0.45, 0.1, 1.0),
    "Nape": (0.6, 0.2, 1.0, 1.0),
    "Braid": (1.0, 0.25, 0.65, 1.0),
    "Twist": (0.2, 1.0, 1.0, 1.0),
}
WARNING_COLOR = (1.0, 0.05, 0.02, 1.0)
IN_FRONT_GENERATED_TYPES = {"guide", "region", "placement_point", "warning", "curve", "braid_strand", "twist_strand"}
CONTROL_CURVE_TYPES = {"braid_control", "twist_control"}


def ensure_collection(name, parent=None):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
    parent_collection = parent or bpy.context.scene.collection
    if not any(child.name == collection.name for child in parent_collection.children):
        parent_collection.children.link(collection)
    return collection


def ensure_system():
    root = ensure_collection(ROOT)
    children = {name: ensure_collection(name, root) for name in SYSTEM_COLLECTIONS}
    ensure_curve_region_collections(children[CURVES])
    return root, children


def ensure_curve_region_collections(curves_collection=None):
    if curves_collection is None:
        root = ensure_collection(ROOT)
        curves_collection = ensure_collection(CURVES, root)
    return {name: ensure_collection(name, curves_collection) for name in CURVE_REGION_COLLECTIONS}


def get_system_collection(name, create=True):
    if create:
        _, children = ensure_system()
        return children[name]
    root = bpy.data.collections.get(ROOT)
    if not root:
        return None
    return bpy.data.collections.get(name)


def collection_objects_recursive(collection):
    objects = list(collection.objects)
    for child in collection.children:
        objects.extend(collection_objects_recursive(child))
    return objects


def collections_recursive(collection):
    collections = [collection]
    for child in collection.children:
        collections.extend(collections_recursive(child))
    return collections


def generated_objects(type_filter=None):
    root = bpy.data.collections.get(ROOT)
    if not root:
        return []
    objects = [obj for obj in collection_objects_recursive(root) if obj.get("hair_guide_type")]
    if type_filter:
        objects = [obj for obj in objects if obj.get("hair_guide_type") == type_filter]
    return objects


def get_guide_object(name):
    for obj in generated_objects("guide"):
        if obj.name == name or obj.name.split(".")[0] == name:
            return obj
    return None


def _spline_control_points_world(obj):
    if not obj or obj.type != "CURVE":
        return []
    points = []
    for spline in obj.data.splines:
        if spline.type == "BEZIER":
            points.extend(obj.matrix_world @ point.co for point in spline.bezier_points)
        else:
            for point in spline.points:
                co = point.co
                points.append(obj.matrix_world @ mathutils.Vector((co.x, co.y, co.z)))
        if points:
            break
    return points


def sample_curve_world_points(obj, count):
    source = _spline_control_points_world(obj)
    if not source:
        return []
    if len(source) == 1:
        return [source[0].copy() for _ in range(max(count, 1))]
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
        previous = 0.0
        for idx, end_length in enumerate(lengths):
            if target <= end_length:
                segment_index = idx
                break
            previous = end_length
        segment_length = max(lengths[segment_index] - previous, 0.000001)
        t = (target - previous) / segment_length
        samples.append(source[segment_index].lerp(source[segment_index + 1], t))
    return samples


def _cubic_bezier(p0, p1, p2, p3, t):
    inv = 1.0 - t
    return (
        p0 * (inv ** 3)
        + p1 * (3.0 * inv * inv * t)
        + p2 * (3.0 * inv * t * t)
        + p3 * (t ** 3)
    )


def sample_curve_world_points_evaluated(obj, count):
    """Sample the first spline in world space, including Bezier handles for Bezier curves."""
    if not obj or obj.type != "CURVE":
        return []
    spline = next((item for item in obj.data.splines if item.type == "BEZIER" and item.bezier_points), None)
    if spline is None:
        return sample_curve_world_points(obj, count)
    bezier_points = spline.bezier_points
    if len(bezier_points) == 1:
        point = obj.matrix_world @ bezier_points[0].co
        return [point.copy() for _ in range(max(count, 1))]

    dense = []
    segment_samples = 12
    for index in range(len(bezier_points) - 1):
        current = bezier_points[index]
        next_point = bezier_points[index + 1]
        p0 = obj.matrix_world @ current.co
        p1 = obj.matrix_world @ current.handle_right
        p2 = obj.matrix_world @ next_point.handle_left
        p3 = obj.matrix_world @ next_point.co
        for sample_index in range(segment_samples):
            if index > 0 and sample_index == 0:
                continue
            dense.append(_cubic_bezier(p0, p1, p2, p3, sample_index / segment_samples))
    dense.append(obj.matrix_world @ bezier_points[-1].co)
    if len(dense) < 2:
        return dense
    lengths = []
    total = 0.0
    for start, end in zip(dense, dense[1:]):
        total += (end - start).length
        lengths.append(total)
    if total == 0.0:
        return [dense[0].copy() for _ in range(max(count, 1))]
    samples = []
    for index in range(max(count, 2)):
        target = total * (index / max(count - 1, 1))
        segment_index = 0
        previous = 0.0
        for idx, end_length in enumerate(lengths):
            if target <= end_length:
                segment_index = idx
                break
            previous = end_length
        segment_length = max(lengths[segment_index] - previous, 0.000001)
        factor = (target - previous) / segment_length
        samples.append(dense[segment_index].lerp(dense[segment_index + 1], factor))
    return samples


def get_curve_world_center(obj):
    points = _spline_control_points_world(obj)
    if not points:
        return None
    center = mathutils.Vector((0.0, 0.0, 0.0))
    for point in points:
        center += point
    return center / len(points)


def get_curve_world_endpoints(obj):
    points = _spline_control_points_world(obj)
    if not points:
        return None
    return points[0], points[-1]


def clear_collection_objects(collection_name, type_filter=None):
    collection = get_system_collection(collection_name, create=False)
    if not collection:
        return 0
    objects = []
    seen = set()
    for obj in collection_objects_recursive(collection):
        if obj.name not in seen:
            objects.append(obj)
            seen.add(obj.name)
    count = 0
    for obj in objects:
        if type_filter and obj.get("hair_guide_type") != type_filter:
            continue
        if not obj.get("hair_guide_type"):
            continue
        bpy.data.objects.remove(obj, do_unlink=True)
        count += 1
    return count


def set_common_props(obj, guide_type, region="", scene=None):
    obj["hair_guide_type"] = guide_type
    obj["hair_region"] = region
    obj["hair_root_id"] = obj.get("hair_root_id", "")
    obj["hair_warning_type"] = obj.get("hair_warning_type", "")
    obj["hair_seed"] = getattr(scene, "hair_seed", 0) if scene else 0
    obj.color = REGION_COLORS.get(region, (0.9, 0.9, 0.9, 1.0))
    if guide_type in {"curve", "braid_control", "braid_strand", "twist_control", "twist_strand"}:
        apply_curve_region_color(obj)
    if guide_type in IN_FRONT_GENERATED_TYPES and scene:
        obj.show_in_front = getattr(scene, "hair_show_guides_in_front", True)
    if guide_type in CONTROL_CURVE_TYPES:
        obj.show_in_front = True


def curve_region_key(obj_or_region, guide_type=None):
    if hasattr(obj_or_region, "get"):
        guide_type = obj_or_region.get("hair_guide_type", guide_type)
        region = obj_or_region.get("hair_region", "")
    else:
        region = obj_or_region
    if guide_type in {"braid_control", "braid_strand"}:
        return "Braid"
    if guide_type in {"twist_control", "twist_strand"}:
        return "Twist"
    return region if region in CURVE_REGION_COLLECTIONS else ""


def get_curve_collection(region="", guide_type="curve"):
    _, children = ensure_system()
    curves = children[CURVES]
    key = curve_region_key(region, guide_type)
    if not key:
        return curves
    return ensure_curve_region_collections(curves)[key]


def move_object_to_collection(obj, target_collection):
    if not obj or not target_collection:
        return False
    curves_root = get_system_collection(CURVES)
    if curves_root:
        for collection in collections_recursive(curves_root):
            if any(existing == obj for existing in collection.objects):
                collection.objects.unlink(obj)
    if not any(existing == obj for existing in target_collection.objects):
        target_collection.objects.link(obj)
    return True


def organize_curve_object(obj):
    if not obj or obj.get("hair_guide_type") not in {"curve", "braid_control", "braid_strand", "twist_control", "twist_strand"}:
        return False
    target = get_curve_collection(obj.get("hair_region", ""), obj.get("hair_guide_type"))
    return move_object_to_collection(obj, target)


def apply_curve_region_color(obj):
    if not obj or obj.get("hair_guide_type") not in {"curve", "braid_control", "braid_strand", "twist_control", "twist_strand"}:
        return False
    key = curve_region_key(obj)
    obj.color = CURVE_REGION_COLORS.get(key, (0.9, 0.9, 0.9, 1.0))
    return True


def head_bounds(obj):
    points = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    min_v = mathutils.Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    max_v = mathutils.Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    center = (min_v + max_v) * 0.5
    size = max_v - min_v
    return min_v, max_v, center, size


def make_curve(name, points, collection, region, guide_type, scene, bevel=None):
    curve = bpy.data.curves.new(unique_name(name), "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = getattr(scene, "hair_curve_resolution", 12)
    curve.bevel_depth = getattr(scene, "hair_curve_bevel_depth", 0.012) if bevel is None else bevel
    spl = curve.splines.new("BEZIER")
    spl.bezier_points.add(len(points) - 1)
    for point, co in zip(spl.bezier_points, points):
        point.co = co
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(curve.name, curve)
    collection.objects.link(obj)
    set_common_props(obj, guide_type, region, scene)
    return obj


def unique_name(prefix):
    if prefix not in bpy.data.objects and prefix not in bpy.data.curves and prefix not in bpy.data.meshes:
        return prefix
    index = 1
    while True:
        name = f"{prefix}_{index:03d}"
        if name not in bpy.data.objects and name not in bpy.data.curves and name not in bpy.data.meshes:
            return name
        index += 1


def unique_numbered(prefix):
    index = 1
    while True:
        name = f"{prefix}_{index:03d}"
        if name not in bpy.data.objects and name not in bpy.data.curves and name not in bpy.data.meshes:
            return name
        index += 1


def make_marker(name, location, radius, collection, region, guide_type, scene):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = unique_name(name)
    obj.data.name = obj.name + "Mesh"
    for col in list(obj.users_collection):
        if col != collection:
            col.objects.unlink(obj)
    if not any(existing.name == obj.name for existing in collection.objects):
        collection.objects.link(obj)
    set_common_props(obj, guide_type, region, scene)
    return obj


def direction_for_region(region, x=0.0):
    if region == "Top":
        vec = mathutils.Vector((0.0, 0.35, -0.9))
    elif region == "Front":
        vec = mathutils.Vector((0.0, -0.45, -0.9))
    elif region == "Side_L":
        vec = mathutils.Vector((-0.45, 0.35, -0.75))
    elif region == "Side_R":
        vec = mathutils.Vector((0.45, 0.35, -0.75))
    elif region == "Back_Upper":
        vec = mathutils.Vector((0.0, 0.45, -0.85))
    elif region == "Back_Middle":
        vec = mathutils.Vector((0.25 if x >= 0 else -0.25, 0.15, -0.95))
    else:
        vec = mathutils.Vector((0.0, 0.25, -1.0))
    vec.normalize()
    return vec


def vector_to_string(vec):
    return f"{vec.x:.4f},{vec.y:.4f},{vec.z:.4f}"


def string_to_vector(value, fallback=None):
    fallback = fallback or mathutils.Vector((0, 0, -1))
    try:
        x, y, z = (float(part) for part in str(value).split(","))
        vec = mathutils.Vector((x, y, z))
        if vec.length == 0:
            return fallback
        vec.normalize()
        return vec
    except Exception:
        return fallback


def set_region_visibility(region, hide):
    count = 0
    for obj in generated_objects():
        obj_region = obj.get("hair_region", "")
        match = obj_region == region or (region == "Side" and obj_region in {"Side", "Side_L", "Side_R"})
        if match:
            obj.hide_viewport = hide
            obj.hide_render = hide
            count += 1
    return count


def _matches_region(obj_region, region):
    if region == "ALL":
        return any(_matches_region(obj_region, item) for item in REGION_NAMES)
    if region == "Side":
        return obj_region in {"Side", "Side_L", "Side_R"}
    return obj_region == region


def get_region_visibility_state(region):
    """Return VISIBLE, HIDDEN, MIXED, or EMPTY for generated objects in a hair region."""
    targets = [obj for obj in generated_objects() if _matches_region(obj.get("hair_region", ""), region)]
    if not targets:
        return "EMPTY"
    hidden_count = sum(1 for obj in targets if obj.hide_viewport)
    if hidden_count == 0:
        return "VISIBLE"
    if hidden_count == len(targets):
        return "HIDDEN"
    return "MIXED"


def make_arc_points(center, radius_x, radius_y, z, start_angle, end_angle, count):
    points = []
    for i in range(count):
        t = i / max(count - 1, 1)
        angle = start_angle + (end_angle - start_angle) * t
        points.append(mathutils.Vector((center.x + math.cos(angle) * radius_x, center.y + math.sin(angle) * radius_y, z)))
    return points
