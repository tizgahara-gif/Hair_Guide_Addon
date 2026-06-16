import bpy
import mathutils
from . import utils

def generate_strip_from_curve(obj, scene, collection):
    samples = utils.sample_polyline(utils.curve_points_world(obj), scene.hair_strip_segments + 1)
    if len(samples) < 2:
        return None
    verts, faces, uvs = [], [], []
    x_axis = mathutils.Vector((1, 0, 0))
    for i, p in enumerate(samples):
        v = i / (len(samples) - 1)
        width = scene.hair_strip_width * (1.0 - scene.hair_strip_taper * v)
        off = x_axis * width * 0.5
        verts.extend([p - off, p + off])
        uvs.extend([(0.0, v), (1.0, v)])
        if i < len(samples) - 1:
            j = i * 2
            faces.append((j, j + 1, j + 3, j + 2))
    mesh = bpy.data.meshes.new(obj.name + "_StripMesh")
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            uv_layer.data[li].uv = uvs[mesh.loops[li].vertex_index]
    out = bpy.data.objects.new(obj.name + "_Strip", mesh)
    collection.objects.link(out)
    out["source_hair_guide"] = obj.name
    return out
