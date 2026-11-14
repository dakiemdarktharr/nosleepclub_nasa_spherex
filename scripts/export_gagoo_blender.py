"""Run with Blender --background --factory-startup --python THIS -- [options].

Imports the geometry exported from the actual browser factory, keeping named
parts editable. This is a conversion handoff, not hand sculpting or rigging.
"""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector


def render_poster_only(output, resolution):
    """Render the saved, verified asset without altering its .blend or GLB."""
    report_path = output / 'blender-handoff.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    blend = output / 'gagoo.blend'
    if sha256(blend.read_bytes()).hexdigest() != report['artifacts']['gagoo.blend']['sha256']:
        raise ValueError('The editable asset differs from the verified handoff')
    for path, expected in report['source_hashes'].items():
        if sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Runtime source changed since export: {path}')
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    scene.camera = bpy.data.objects['CAM_front']
    scene.compositing_node_group = None
    bpy.data.objects['Studio_Ground_Excluded_From_Asset'].hide_render = True
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_mode = 'RGBA'
    poster = output / 'gagoo-poster.png'
    scene.render.filepath = str(poster)
    bpy.ops.render.render(write_still=True)
    report['artifacts'][poster.name] = {'bytes': poster.stat().st_size, 'sha256': sha256(poster.read_bytes()).hexdigest()}
    report['studio']['poster_resolution'] = resolution
    report['studio']['poster_transparent'] = True
    report['studio']['poster_source_blend_sha256'] = report['artifacts']['gagoo.blend']['sha256']
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'poster': str(poster), 'resolution': resolution, **report['artifacts'][poster.name]}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/raw/gagoo-assets/gagoo-geometry.json')
    parser.add_argument('--output', default='data/raw/gagoo-assets')
    parser.add_argument('--render', action='store_true', help='Render front and three-quarter studio PNGs.')
    parser.add_argument('--resolution', type=int, choices=[900, 1200], default=1200)
    parser.add_argument('--samples', type=int, default=32)
    parser.add_argument('--poster-only', action='store_true', help='Render a transparent poster from the saved verified .blend only.')
    parser.add_argument('--poster-resolution', type=int, choices=[600, 900, 1200], default=600)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.poster_only:
        render_poster_only(output, args.poster_resolution)
        return
    raw = source.read_bytes()
    data = json.loads(raw)
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported geometry handoff')
    # Called in a separate factory-startup process; no user's open scene is used.
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    geometry_collection = bpy.data.collections.new('COL_Gagoo_RuntimeGeometry')
    bpy.context.scene.collection.children.link(geometry_collection)
    review_collection = bpy.data.collections.new('COL_Review_Cameras_Lights')
    bpy.context.scene.collection.children.link(review_collection)
    root = bpy.data.objects.new('Gagoo_Runtime_Export_Yup_to_Zup', None)
    geometry_collection.objects.link(root)
    root.rotation_euler.x = math.pi / 2
    root['source_kind'] = data['source_kind']
    root['source_geometry_sha256'] = sha256(raw).hexdigest()
    root['limits'] = 'Static editable runtime parts; no armature, no hand-sculpt claim.'
    materials = {}
    for item in data['materials']:
        material = bpy.data.materials.new(f"MAT_{item['id']:02d}_{item['name']}")
        material.use_nodes = True
        shader = material.node_tree.nodes.get('Principled BSDF')
        rgba = tuple(item['color_linear']) + (item['opacity'],)
        shader.inputs['Base Color'].default_value = rgba
        shader.inputs['Metallic'].default_value = item['metalness']
        shader.inputs['Roughness'].default_value = item['roughness']
        shader.inputs['Alpha'].default_value = item['opacity']
        if 'Coat Weight' in shader.inputs:
            shader.inputs['Coat Weight'].default_value = item['clearcoat']
        emission = item['color_linear'] if item['unlit'] else item['emissive_linear']
        if 'Emission Color' in shader.inputs:
            shader.inputs['Emission Color'].default_value = tuple(emission) + (1,)
            shader.inputs['Emission Strength'].default_value = 1 if item['unlit'] else item['emissive_intensity']
        material.diffuse_color = rgba
        material.use_backface_culling = not item['double_sided']
        if item['transparent'] and hasattr(material, 'surface_render_method'):
            material.surface_render_method = 'DITHERED'
        materials[item['id']] = material
    objects = {}
    triangle_count = 0
    for item in data['nodes']:
        if 'positions' in item:
            positions = item['positions']
            vertices = [positions[index:index + 3] for index in range(0, len(positions), 3)]
            indices = item['indices']
            if len(indices) % 3 or not all(math.isfinite(v) for v in positions):
                raise ValueError(f"Invalid geometry: {item['name']}")
            faces = [indices[index:index + 3] for index in range(0, len(indices), 3)]
            mesh = bpy.data.meshes.new('MESH_' + item['name'])
            mesh.from_pydata(vertices, [], faces)
            mesh.update()
            obj = bpy.data.objects.new('SM_' + item['name'], mesh)
            mat = data['materials'][item['material_id']]
            mesh.materials.append(materials[item['material_id']])
            for face in mesh.polygons:
                face.use_smooth = not mat['flat_shading']
            if item.get('uv'):
                uv = mesh.uv_layers.new(name='RuntimeUV')
                for loop in mesh.loops:
                    index = loop.vertex_index * 2
                    uv.data[loop.index].uv = item['uv'][index:index + 2]
            triangle_count += len(faces)
        else:
            obj = bpy.data.objects.new('GROUP_' + item['name'], None)
        geometry_collection.objects.link(obj)
        obj['runtime_node_id'] = item['id']
        obj.parent = objects.get(item['parent'], root)
        elements = item['matrix']
        obj.matrix_basis = Matrix([[elements[col * 4 + row] for col in range(4)] for row in range(4)])
        objects[item['id']] = obj
    lower, upper = data['bounds']['min'], data['bounds']['max']
    center = Vector(((lower[0] + upper[0]) / 2, -(lower[2] + upper[2]) / 2, (lower[1] + upper[1]) / 2))
    height = upper[1] - lower[1]
    width = upper[0] - lower[0]
    frame_size = max(height, width) * 1.22
    floor_z = lower[1] - .004
    # Front has zero yaw, with a slight studio elevation to expose the physical
    # contact shadow below both boots. Geometry is never cropped for the portrait.
    cameras = {'front': (0, -8, .22), 'back': (0, 8, .22), 'left': (-8, 0, .22), 'right': (8, 0, .22), 'three_quarter': (4.8, -7, 1.7)}
    camera_objects = {}
    for name, position in cameras.items():
        camera = bpy.data.cameras.new('CAM_' + name)
        camera.type = 'ORTHO'
        camera.ortho_scale = frame_size
        obj = bpy.data.objects.new('CAM_' + name, camera)
        review_collection.objects.link(obj)
        obj.location = center + Vector(position)
        obj.rotation_euler = (center - obj.location).to_track_quat('-Z', 'Y').to_euler()
        camera_objects[name] = obj
        if name == 'front':
            bpy.context.scene.camera = obj
    for name, position, energy, color in [('key', (-3.5, -4.5, 5), 430, (1, .96, .9)), ('fill', (4, -3, 2.5), 290, (.9, .95, 1)), ('rim', (0, 3, 4.5), 280, (.94, .97, 1))]:
        light = bpy.data.lights.new('LIGHT_' + name, 'AREA')
        light.energy = energy
        light.color = color
        light.shape = 'DISK'
        light.size = 5
        obj = bpy.data.objects.new('LIGHT_' + name, light)
        review_collection.objects.link(obj)
        obj.location = position
        obj.rotation_euler = (center - obj.location).to_track_quat('-Z', 'Y').to_euler()
    floor_mesh = bpy.data.meshes.new('MESH_Studio_Ground')
    floor_mesh.from_pydata([(-200, -200, floor_z), (200, -200, floor_z), (200, 200, floor_z), (-200, 200, floor_z)], [], [(0, 1, 2, 3)])
    floor_mesh.update()
    floor = bpy.data.objects.new('Studio_Ground_Excluded_From_Asset', floor_mesh)
    review_collection.objects.link(floor)
    floor.is_shadow_catcher = True
    floor_material = bpy.data.materials.new('MAT_Studio_LightGray')
    floor_material.use_nodes = True
    floor_shader = floor_material.node_tree.nodes.get('Principled BSDF')
    floor_shader.inputs['Base Color'].default_value = (.68, .7, .72, 1)
    floor_shader.inputs['Roughness'].default_value = 1
    floor_mesh.materials.append(floor_material)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = max(8, min(args.samples, 128))
    scene.cycles.use_denoising = True
    scene.cycles.transparent_max_bounces = 12
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    # Composite the physically rendered contact shadow onto a uniform gray card,
    # avoiding a horizon line in the almost level frontal product camera.
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.72, .74, .76, 1)
    background.inputs['Strength'].default_value = .7
    scene.view_settings.view_transform = 'AgX'
    compositor = bpy.data.node_groups.new('Gagoo_Studio_LightGray_Background', 'CompositorNodeTree')
    compositor.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    rendered = compositor.nodes.new('CompositorNodeRLayers')
    gray = compositor.nodes.new('CompositorNodeRGB')
    gray.outputs[0].default_value = (1.2, 1.2, 1.2, 1)
    over = compositor.nodes.new('CompositorNodeAlphaOver')
    over.inputs['Factor'].default_value = 1
    destination = compositor.nodes.new('NodeGroupOutput')
    compositor.links.new(gray.outputs[0], over.inputs['Background'])
    compositor.links.new(rendered.outputs['Image'], over.inputs['Foreground'])
    compositor.links.new(over.outputs[0], destination.inputs['Image'])
    scene.compositing_node_group = compositor
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in geometry_collection.objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    blend = output / 'gagoo.blend'
    glb = output / 'gagoo-lowpoly.glb'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True, export_yup=True, export_extras=True)
    artifacts = [blend, glb]
    render_checks = {}
    if args.render:
        from bpy_extras.object_utils import world_to_camera_view
        for name in ['front', 'three_quarter']:
            scene.camera = camera_objects[name]
            bpy.context.view_layer.update()
            points = [world_to_camera_view(scene, scene.camera, obj.matrix_world @ Vector(corner)) for obj in objects.values() if obj.type == 'MESH' for corner in obj.bound_box]
            bounds = {'min_x': min(point.x for point in points), 'max_x': max(point.x for point in points), 'min_y': min(point.y for point in points), 'max_y': max(point.y for point in points)}
            if min(bounds['min_x'], bounds['min_y']) < .025 or max(bounds['max_x'], bounds['max_y']) > .975:
                raise ValueError(f'Framing would clip the complete model: {name} {bounds}')
            render_checks[name] = {'whole_model_inside_frame': True, 'projected_bounds': bounds, 'camera_location': list(scene.camera.location), 'orthographic_scale': frame_size}
            path = output / f'gagoo-studio-{name}.png'
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            artifacts.append(path)
        scene.camera = camera_objects['front']
        # The web fallback is rendered from this exact mesh, not concept art.
        scene.compositing_node_group = None
        floor.hide_render = True
        scene.render.image_settings.color_mode = 'RGBA'
        poster = output / 'gagoo-poster.png'
        scene.render.filepath = str(poster)
        bpy.ops.render.render(write_still=True)
        artifacts.append(poster)
        floor.hide_render = False
        scene.compositing_node_group = compositor
        scene.render.image_settings.color_mode = 'RGB'
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report = {
        'source_kind': data['source_kind'], 'source_geometry_sha256': sha256(raw).hexdigest(),
        'source_hashes': data['source_hashes'], 'blender_version': bpy.app.version_string,
        'mesh_objects': sum(obj.type == 'MESH' for obj in objects.values()),
        'triangles': triangle_count, 'materials': len(materials), 'review_cameras': list(cameras),
        'source_bounds': data['bounds'], 'blender_axes': 'Z up, face -Y; GLB exported Y up',
        'studio': {'background': 'plain light gray', 'ground_z': floor_z, 'engine': 'Cycles CPU', 'samples': scene.cycles.samples, 'resolution': args.resolution, 'render_checks': render_checks, 'ground_and_cameras_excluded_from_glb': True},
        'artifacts': {path.name: {'bytes': path.stat().st_size, 'sha256': sha256(path.read_bytes()).hexdigest()} for path in artifacts},
        'limits': data['limits'] + ['Geometry conversion; no rig, baked motion, LOD or production-asset certification.']
    }
    (output / 'blender-handoff.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
