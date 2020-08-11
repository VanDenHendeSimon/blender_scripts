import copy
import subprocess
import json
import re
import random
import time
import os
import datetime

try:
    import bpy
    import bmesh
    from mathutils import Vector

except ImportError:
    print("Could not import any of the Blender modules - BlenderHelperFunctions")


from .ObjHelpers import ObjHelpers
from .HelperFunctions import HelperFunctions


class BlenderHelperFunctions:
    def __init__(self):
        pass

    @staticmethod
    def import_obj_file(filepath):
        try:
            bpy.ops.import_scene.obj(filepath=filepath, use_split_objects=True, use_split_groups=True)
            print("Successfully imported '%s'" % filepath)

        except Exception:
            print("Failed to import %s" % filepath)

    @staticmethod
    def remove_all_objects():
        BlenderHelperFunctions.force_object_mode()
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False, confirm=False)

    @staticmethod
    def remove_meshes():
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)

    @staticmethod
    def export_obj(filepath):
        bpy.ops.export_scene.obj(filepath=filepath, group_by_object=True, group_by_material=True)
        # Delete mtl file (setting use_materials to False also disables writing material references)
        mtl_file = os.path.splitext(filepath)[0] + '.mtl'
        if os.path.exists(mtl_file):
            os.remove(mtl_file)

    @staticmethod
    def import_file(filepath, unit_size=100):
        extension = os.path.splitext(filepath)[1]

        if extension == '.obj':
            ObjHelpers.rename_material_slots(filepath)
            BlenderHelperFunctions.import_obj_file(filepath)
        elif extension == '.fbx':
            BlenderHelperFunctions.import_fbx_file(filepath, unit_size)

    @staticmethod
    def convert_ascii_fbx_to_binary(_file):
        # Cant just put the code here bcus the FbxCommon API only runs on Python 3.3
        python_location = "python33"
        for path in os.environ.get("Path").split(";"):
            if "prompto-python33" in path:
                python_location = os.path.join(path, "python33.exe")
                break

        return subprocess.check_output(
            [
                python_location,
                "%s\\convert_fbx_scene.py" % os.path.dirname(os.path.abspath(__file__)), _file
            ],
            shell=False
        )

    @staticmethod
    def import_fbx_file(filepath, unit_size=100):
        try:
            bpy.ops.import_scene.fbx(filepath=filepath, global_scale=unit_size)
            print("Successfully imported '%s'" % filepath)

        except Exception:
            try:
                file_drive = filepath[0]
                new_file = str(BlenderHelperFunctions.convert_ascii_fbx_to_binary(filepath))
                if ".fbx" in new_file:
                    new_file = new_file[new_file.find("%s:\\" % file_drive):]
                    new_file = new_file[:new_file.rfind(".fbx") + 4]
                    # import the binary file instead
                    import_fbx_file(new_file)
                else:
                    print("Can't import %s" % filepath)
            except Exception:
                print("Can't import %s" % filepath)
        finally:
            # Avoid multiple objects referencing the same mesh en material data
            bpy.ops.object.make_single_user(
                type="ALL", object=True, obdata=True, material=True, animation=False
            )

    @staticmethod
    def remove_current_scene_contents():
        BlenderHelperFunctions.remove_existing_material_data()
        BlenderHelperFunctions.remove_all_objects()

    @staticmethod
    def remove_existing_material_data():
        """
        This function does a bit more than what it says.
        It basically acts as a cleanup function during development.
        It cleans up all materials, node groups and images loaded in by the script.
        Making sure we can test on 'new' scenes without having to cleanup / reload everything manually.
        """

        for existing_material in bpy.data.materials:
            bpy.data.materials.remove(existing_material)

        for node_group in bpy.data.node_groups:
            bpy.data.node_groups.remove(node_group)

        for image in bpy.data.images:
            bpy.data.images.remove(image)

    @staticmethod
    def set_clipping_plane():
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.clip_end = 9999

    @staticmethod
    def assign_random_colors():
        for material in bpy.data.materials:
            bsdf = [n for n in material.node_tree.nodes if n.name == 'Principled BSDF'][0]
            bsdf.inputs[0].default_value = [random.random(), random.random(), random.random(), 1]

    @staticmethod
    def set_blend_method(material, blend_method):
        if blend_method == "BLEND_Masked":
            blend_method = "CLIP"
            material.alpha_threshold = 0.001
        elif blend_method == "BLEND_Translucent":
            blend_method = "BLEND"
        else:
            blend_method = "OPAQUE"

        material.blend_method = blend_method

    @staticmethod
    def create_named_plane(obj_name):
        # Generates a new object with a perfect square UV layout
        bpy.ops.mesh.primitive_plane_add(size=1, enter_editmode=False, align='WORLD', location=(0, 0, 0))
        obj = bpy.context.selected_objects[0]
        obj.name = obj_name

        return obj

    @staticmethod
    def create_texture_node(material, img_name):
        # Create texture node to load image into
        nodes = material.node_tree.nodes
        node = nodes.new('ShaderNodeTexImage')

        # Load image
        img = bpy.data.images[img_name]

        node.location = 300, 0
        node.label = img_name
        node.name = img_name
        node.image = img

        node.select = True
        nodes.active = node

        return img

    @staticmethod
    def get_material_by_name(material_name):
        try:
            return bpy.data.materials.get(material_name, None)
        except NameError:
            return ''

    @staticmethod
    def get_texture_resolution(texture_path):
        texture_name = os.path.basename(texture_path)
        try:
            img = next(
                img for img in bpy.data.images if
                img.filepath_raw.split('\\')[1] == texture_name
            )
            return list(img.size)

        except StopIteration:
            return [2048, 2048]

    @staticmethod
    def bake_material(material, resolution, export_dir="D:\\backed_textures_without_export_path"):
        # Create an object for each material slot in the scene
        obj = BlenderHelperFunctions.create_named_plane('%s_obj' % material.name)

        # Assign current material to the object
        obj.data.materials.append(material)

        # Create image to save bake to
        img_name = "%s_bake" % material.name[:10]
        # Get the width and height from the source texture
        bpy.data.images.new(name=img_name, width=resolution[0], height=resolution[1])

        uv_img = BlenderHelperFunctions.create_texture_node(material, img_name)

        # Select the object
        obj.select_set(True)

        try:
            output_path = HelperFunctions.ensure_path("%s\\%s_Diffuse_Bake.png" % (export_dir, material.name))
            # Bake current object's texture
            bpy.ops.object.bake(type='DIFFUSE', pass_filter={"COLOR"})
            # Render bake to disk
            uv_img.save_render(output_path)
            print("Baked %s\n\n" % output_path)

        except RuntimeError as ex:
            output_path = ''
            print("Could not bake %s" % material.name)
            print(ex)

        # Remove object
        bpy.ops.object.delete(use_global=False, confirm=False)
        # Remove texture node
        # Remove image
        bpy.data.images.remove(uv_img)

        return output_path

    @staticmethod
    def prepare_bake():
        # Store current render engine
        render_engine = bpy.context.scene.render.engine
        # Baking requires Cycles
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.ops.object.select_all(action='DESELECT')

        return render_engine

    @staticmethod
    def reset_after_baking(render_engine):
        bpy.context.scene.render.engine = render_engine

    @staticmethod
    def bake_materials():
        render_engine = BlenderHelperFunctions.prepare_bake()

        for material in bpy.data.materials:
            BlenderHelperFunctions.bake_material(material, (64, 64))

        # Reset the render engine
        BlenderHelperFunctions.reset_after_baking(render_engine)

    @staticmethod
    def get_light_type(light):
        try:
            if type(light) is bpy.types.SpotLight:
                return 'spot'
            elif type(light) is bpy.types.SunLight:
                return 'sun'
            elif type(light) is bpy.types.AreaLight:
                return 'area'
            else:
                return 'point'
        except Exception as ex:
            print("Could not determine light type! Defaulting to 'point'")
            print(ex)
            return 'point'

    @staticmethod
    def get_light_name(light):
        try:
            return light.name
        except Exception:
            return 'Unkown Light Name'

    @staticmethod
    def get_light_color(light):
        try:
            return list(light.color)
        except Exception:
            # mimic defaults from shapespark
            if type(light) is bpy.types.SunLight:
                return [1, 0.8, 0.638]
            else:
                return [1.0, 0.88, 0.799]

    @staticmethod
    def get_light_properties(light, unit_size=100):
        # Universal properties
        light_properties = {
            'type': BlenderHelperFunctions.get_light_type(light),
            'name': BlenderHelperFunctions.get_light_name(light),
            'color': BlenderHelperFunctions.get_light_color(light),
        }

        # Transform data
        light_properties.update(BlenderHelperFunctions.get_light_transforms(light, unit_size))

        # Specific properties
        try:
            # angle is for spot lights only
            light_properties.update({
                'angle': HelperFunctions.rad_to_deg(light.spot_size)
            })
        except AttributeError:
            pass

        try:
            # width / height is for area lights only
            light_properties.update({
                'width': light.size,
                'height': light.size,
            })
        except AttributeError:
            pass

        return light_properties

    @staticmethod
    def get_light_rotation(light_obj):
        # yaw and pitch
        try:
            light_rotations = list(light_obj.matrix_world.to_euler())
            return [
                light_rotations[0],
                light_rotations[1] - 90,
            ]

        except Exception as ex:
            print("Could not get light rotation")
            print(ex)
            return [0, 0]

    @staticmethod
    def get_light_position(light_obj, unit_size=100):
        try:
            return [
                (axis_position / unit_size)
                for axis_position in list(light_obj.matrix_world.to_translation())
            ]

        except AttributeError:
            return [0, 0, 0]

    @staticmethod
    def get_light_transforms(light, unit_size=100):
        light_obj = bpy.data.objects.get(light.name, None)
        return {
            'instances': [{
                'rotation': BlenderHelperFunctions.get_light_rotation(light_obj),
                'position': BlenderHelperFunctions.get_light_position(light_obj, unit_size),
            }]
        }

    @staticmethod
    def get_lights():
        return bpy.data.lights

    @staticmethod
    def print_material_links(material):
        for link in material.node_tree.links:
            print("%s - %s (%s - %s)" % (
                link.from_node.name, link.to_node.name, link.from_socket.name, link.to_socket.name
            ))

    @staticmethod
    def force_object_mode():
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass

    @staticmethod
    def create_text(text="Some text", width=3.5):
        BlenderHelperFunctions.force_object_mode()

        bpy.ops.object.text_add(enter_editmode=True, location=(0, 0, 0))
        bpy.ops.font.delete(type="PREVIOUS_WORD")
        bpy.ops.font.text_insert(text=text)
        bpy.ops.object.editmode_toggle()

        # Style the text
        bpy.context.object.data.bevel_depth = 0.01
        # Extrude
        bpy.ops.transform.resize(value=(1, 1, width))
        # Rotate to put the text up
        bpy.ops.transform.rotate(value=1.5708, orient_axis='X', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)))

    @staticmethod
    def reset_transforms():
        bpy.ops.object.select_all(action='DESELECT')

        for obj in bpy.data.objects:
            obj.select_set(True)
            bpy.ops.object.location_clear(clear_delta=False)
            bpy.ops.object.rotation_clear(clear_delta=False)
            bpy.ops.object.scale_clear(clear_delta=False)
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            obj.select_set(False)


