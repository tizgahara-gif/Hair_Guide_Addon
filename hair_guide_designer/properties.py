import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty

STRAND_TYPES = (
    ("FRONT", "Front", "Front bang strand"),
    ("SIDE", "Side", "Side strand"),
    ("BACK", "Back", "Back strand"),
    ("NAPE", "Nape", "Nape strand"),
)

PROPERTY_NAMES = (
    "hair_target_head_object", "hair_guide_scale", "hair_guide_offset",
    "hair_seed", "hair_density", "hair_symmetry_bias",
    "hair_height_variation", "hair_width_variation", "hair_depth_variation",
    "hair_size_variation", "hair_length_variation", "hair_strand_type",
    "hair_curve_length", "hair_curve_bevel_depth", "hair_curve_resolution",
    "hair_curve_root_radius", "hair_curve_tip_radius", "hair_curve_taper_strength",
    "hair_curve_segment_count", "hair_warning_count", "hair_root_cluster_threshold",
    "hair_batch_curve_length", "hair_batch_curve_bevel_depth", "hair_batch_curve_resolution",
    "hair_follow_keep_tip_offset", "hair_follow_update_selected_only",
    "hair_mirror_axis", "hair_mirror_overwrite_existing", "hair_mirror_copy_custom_properties",
)


def register():
    scene = bpy.types.Scene
    scene.hair_target_head_object = PointerProperty(
        name="Target Head Object",
        type=bpy.types.Object,
        description="Mesh object used as the bounding-box reference for generating hair guides",
    )
    scene.hair_guide_scale = FloatProperty(
        name="Guide Scale",
        default=1.0,
        min=0.05,
        max=10.0,
        description="Scale multiplier for visual guide lines generated from the target head bounding box",
    )
    scene.hair_guide_offset = FloatProperty(
        name="Guide Offset",
        default=0.04,
        min=-1.0,
        max=1.0,
        description="Offset distance used to place guide lines slightly away from the head bounding box",
    )

    scene.hair_seed = IntProperty(
        name="Seed",
        default=7,
        min=0,
        description="Random seed. Same seed generates the same point variation.",
    )
    scene.hair_density = FloatProperty(
        name="Density",
        default=1.0,
        min=0.1,
        max=3.0,
        description="Controls the number or spacing of placement points.",
    )
    scene.hair_symmetry_bias = FloatProperty(
        name="Symmetry Bias",
        default=0.75,
        min=0.0,
        max=1.0,
        description="Controls how strongly left and right points remain symmetrical. 1.0 = more symmetrical, 0.0 = more random.",
    )

    scene.hair_height_variation = FloatProperty(
        name="Height Variation",
        default=0.04,
        min=0.0,
        max=1.0,
        description="Random vertical offset for placement points.",
    )
    scene.hair_width_variation = FloatProperty(
        name="Width Variation",
        default=0.035,
        min=0.0,
        max=1.0,
        description="Random left-right offset for placement points.",
    )
    scene.hair_depth_variation = FloatProperty(
        name="Depth Variation",
        default=0.04,
        min=0.0,
        max=1.0,
        description="Random front-back offset for placement points.",
    )
    scene.hair_size_variation = FloatProperty(
        name="Size Variation",
        default=0.25,
        min=0.0,
        max=2.0,
        description="Random size variation for point display and recommended strand size.",
    )
    scene.hair_length_variation = FloatProperty(
        name="Length Variation",
        default=0.25,
        min=0.0,
        max=2.0,
        description="Random recommended strand length variation.",
    )

    scene.hair_strand_type = EnumProperty(
        name="Strand Type",
        items=STRAND_TYPES,
        default="FRONT",
        description="Metadata category stored on generated curve strands",
    )
    scene.hair_curve_length = FloatProperty(
        name="Length",
        default=0.55,
        min=0.01,
        max=5.0,
        description="Base length of generated curve strands.",
    )
    scene.hair_curve_bevel_depth = FloatProperty(
        name="Bevel Depth",
        default=0.012,
        min=0.0,
        precision=4,
        description="Viewport thickness of generated curve strands.",
    )
    scene.hair_curve_resolution = IntProperty(
        name="Resolution",
        default=12,
        min=1,
        max=64,
        description="Curve smoothing resolution.",
    )
    scene.hair_curve_root_radius = FloatProperty(
        name="Root Radius",
        default=0.035,
        min=0.0,
        precision=4,
        description="Stored root radius value for future taper support.",
    )
    scene.hair_curve_tip_radius = FloatProperty(
        name="Tip Radius",
        default=0.004,
        min=0.0,
        precision=4,
        description="Stored tip radius value for future taper support.",
    )
    scene.hair_curve_taper_strength = FloatProperty(
        name="Taper Strength",
        default=0.75,
        min=0.0,
        max=1.0,
        description="Stored taper strength value for future taper support.",
    )
    scene.hair_curve_segment_count = IntProperty(
        name="Segment Count",
        default=3,
        min=2,
        max=12,
        description="Number of points used when creating strand guide curves.",
    )

    scene.hair_warning_count = IntProperty(
        name="Warning Count",
        default=0,
        min=0,
        description="Number of too-close placement point pairs found by root clustering validation",
    )
    scene.hair_root_cluster_threshold = FloatProperty(
        name="Root Cluster Threshold",
        default=0.08,
        min=0.001,
        max=1.0,
        description="Distance threshold for detecting placement points that are too close.",
    )

    scene.hair_batch_curve_length = FloatProperty(
        name="Length Scale",
        default=1.0,
        min=0.01,
        max=5.0,
        description="Scale selected or generated curve strand length from the root. 1.0 keeps current length.",
    )
    scene.hair_batch_curve_bevel_depth = FloatProperty(
        name="Bevel Depth",
        default=0.02,
        min=0.0,
        precision=4,
        description="Batch viewport thickness applied to generated hair curves.",
    )
    scene.hair_batch_curve_resolution = IntProperty(
        name="Resolution",
        default=3,
        min=1,
        max=64,
        description="Batch smoothing resolution applied to generated hair curves.",
    )

    scene.hair_follow_keep_tip_offset = BoolProperty(
        name="Keep Tip Offset",
        default=True,
        description="Move the whole curve by the root delta so strand shape and tip offset are preserved.",
    )
    scene.hair_follow_update_selected_only = BoolProperty(
        name="Selected Curves Only",
        default=True,
        description="Update only selected generated curves instead of all generated curves.",
    )

    scene.hair_mirror_axis = EnumProperty(
        name="Axis",
        items=(("X", "X", "Mirror across the X axis"),),
        default="X",
        description="Mirror axis. MVP supports X axis only.",
    )
    scene.hair_mirror_overwrite_existing = BoolProperty(
        name="Overwrite Existing",
        default=True,
        description="Delete generated mirror target objects with the same name before creating mirrored objects.",
    )
    scene.hair_mirror_copy_custom_properties = BoolProperty(
        name="Copy Custom Properties",
        default=True,
        description="Copy custom properties from source objects when mirroring, then update side and mirror metadata.",
    )


def unregister():
    for name in PROPERTY_NAMES:
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
