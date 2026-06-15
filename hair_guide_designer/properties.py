import bpy
from bpy.props import EnumProperty, FloatProperty, IntProperty, PointerProperty

STRAND_TYPES = (
    ("FRONT", "Front", "Front bang strand"),
    ("SIDE", "Side", "Side strand"),
    ("BACK", "Back", "Back strand"),
    ("NAPE", "Nape", "Nape strand"),
)

PROPERTY_NAMES = (
    "hair_target_head_object",
    "hair_guide_scale",
    "hair_guide_offset",
    "hair_seed",
    "hair_density",
    "hair_symmetry_bias",
    "hair_height_variation",
    "hair_width_variation",
    "hair_depth_variation",
    "hair_size_variation",
    "hair_length_variation",
    "hair_strand_type",
    "hair_curve_length",
    "hair_curve_bevel_depth",
    "hair_curve_resolution",
    "hair_curve_root_radius",
    "hair_curve_tip_radius",
    "hair_curve_taper_strength",
    "hair_curve_segment_count",
    "hair_warning_count",
    "hair_root_cluster_threshold",
)


def register():
    scene = bpy.types.Scene
    scene.hair_target_head_object = PointerProperty(name="Target Head Object", type=bpy.types.Object)
    scene.hair_guide_scale = FloatProperty(name="Guide Scale", default=1.0, min=0.05, max=10.0)
    scene.hair_guide_offset = FloatProperty(name="Guide Offset", default=0.04, min=-1.0, max=1.0)

    scene.hair_seed = IntProperty(name="Seed", default=7, min=0)
    scene.hair_density = FloatProperty(name="Density", default=1.0, min=0.1, max=3.0)
    scene.hair_symmetry_bias = FloatProperty(name="Symmetry Bias", default=0.75, min=0.0, max=1.0)

    scene.hair_height_variation = FloatProperty(name="Height Variation", default=0.04, min=0.0, max=1.0)
    scene.hair_width_variation = FloatProperty(name="Width Variation", default=0.035, min=0.0, max=1.0)
    scene.hair_depth_variation = FloatProperty(name="Depth Variation", default=0.04, min=0.0, max=1.0)
    scene.hair_size_variation = FloatProperty(name="Size Variation", default=0.25, min=0.0, max=2.0)
    scene.hair_length_variation = FloatProperty(name="Length Variation", default=0.25, min=0.0, max=2.0)

    scene.hair_strand_type = EnumProperty(name="Strand Type", items=STRAND_TYPES, default="FRONT")
    scene.hair_curve_length = FloatProperty(name="Length", default=0.55, min=0.01, max=5.0)
    scene.hair_curve_bevel_depth = FloatProperty(name="Bevel Depth", default=0.012, min=0.0, precision=4)
    scene.hair_curve_resolution = IntProperty(name="Resolution", default=12, min=1, max=64)
    scene.hair_curve_root_radius = FloatProperty(name="Root Radius", default=0.035, min=0.0, precision=4)
    scene.hair_curve_tip_radius = FloatProperty(name="Tip Radius", default=0.004, min=0.0, precision=4)
    scene.hair_curve_taper_strength = FloatProperty(name="Taper Strength", default=0.75, min=0.0, max=1.0)
    scene.hair_curve_segment_count = IntProperty(name="Segment Count", default=3, min=2, max=12)

    scene.hair_warning_count = IntProperty(name="Warning Count", default=0, min=0)
    scene.hair_root_cluster_threshold = FloatProperty(name="Root Cluster Threshold", default=0.08, min=0.001, max=1.0)


def unregister():
    for name in PROPERTY_NAMES:
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
