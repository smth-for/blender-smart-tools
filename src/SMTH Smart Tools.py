bl_info = {
    "name": "SMTH Smart Tools",
    "author": "Lorenzo Ronghi",
    "version": (0, 1),
    "blender": (2, 93, 0),
    "location": "N Panel",
    "description": "Add a tab in N panel with SMTH tools"
}


import bpy
from bpy.types import Operator, Panel
from bpy_extras.io_utils import ExportHelper
import os
from bpy.app import tempdir

addon_name = "SMTH Smart Tools"

# Operator to rename mesh data with the object name
class OBJECT_OT_RenameMeshes(Operator):
    bl_idname = "object.rename_meshes"
    bl_label = "Rename Meshes"
    bl_description = "Rename all meshes data with the same name as the object they are contained in"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects

        for obj in selection:
            if obj.type == 'MESH':
                obj.data.name = obj.name

        return {'FINISHED'}
    
class OBJECT_OT_DeleteAllMaterials(Operator):
    bl_idname = "object.delete_all_materials"
    bl_label = "Delete All Materials"
    bl_description = "Delete ALL materials present in the Blender file regardless of which objects are selected (unselected objects will keep the material slot even if there is no material inside it; to solve this issue, use the Remove Material Slots button)."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        
        selection = bpy.context.selected_objects
             
        # Get materials list of all materials in Blender File 
        materials = bpy.data.materials

        # Delete all materials in Blender File
        for material in materials:
            materials.remove(material)

        for obj in selection:
            if obj.type == 'MESH':
                obj.data.materials.clear()

        return {'FINISHED'}

class OBJECT_OT_RemoveMaterials(Operator):
    bl_idname = "object.remove_materials"
    bl_label = "Remove Materials"
    bl_description = "Disassociate all materials for selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        
        selection = bpy.context.selected_objects

        for obj in selection:
            if obj.type == 'MESH':
                obj.data.materials.clear()
                
        return {'FINISHED'}

# Operator to create a material dedicated to baking AO at 1024 resolution for export to GLB
class OBJECT_OT_CreateMaterials1024(Operator):
    bl_idname = "object.create_materials1024"
    bl_label = "Create Materials1024"
    bl_description = "Create material with blank texture 1024x1024 for selected objects ready to AO Bake and ready to GLB export"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects

        for obj in selection:
            if obj.type == 'MESH':
                    material_name = obj.data.name
                    
                    if material_name in bpy.data.materials:
                        old_material = bpy.data.materials[material_name]
                        bpy.data.materials.remove(old_material)
                        obj.data.materials.clear()
                    
                    material = bpy.data.materials.new(name=material_name)
                    obj.data.materials.append(material)
                    
                    bpy.ops.material.new()

                    material.use_nodes = True
                    node_tree = material.node_tree
                    
                    # Remove all existing nodes
                    node_tree.nodes.clear()

                    # Set Image Texture name as mesh name + AO 
                    image_name = obj.data.name + "_AO"

                    # Delete all textures with the same name
                    for image in bpy.data.images:
                        if image.name == image_name:
                            bpy.data.images.remove(image)

                    # Add image texture node
                    image_texture_node = node_tree.nodes.new('ShaderNodeTexImage')

                    # Create a White Image Texture
                    image = bpy.ops.image.new(name=image_name, width=1024, height=1024, color=(1.0, 1.0, 1.0, 1.0))
                    tex = bpy.data.images.get(image_name)

                    # Set White image texture as image for the node Image Texture
                    image_texture_node.image = tex

                    # Add Principled BSDF
                    principled_bsdf_node = node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                    principled_bsdf_node.location = (500, -500)
                    principled_bsdf_node.inputs['Base Color'].default_value = (0.0, 1.0, 1.0, 1.0)  # R, G, B, Alpha

                    # Add Material Output
                    material_output_node = node_tree.nodes.new('ShaderNodeOutputMaterial')
                    material_output_node.location = (800, -500)

                    # Connect Principled BSDF to Material Output
                    node_tree.links.new(principled_bsdf_node.outputs[0], material_output_node.inputs[0])

                    # Check if "gltf settings" group already exists
                    group_name = "gltf settings"
                    group_node = None
                    existing_group = bpy.data.node_groups.get(group_name)
                    if existing_group:
                        group_node = node_tree.nodes.new(type='ShaderNodeGroup')
                        group_node.location = (500, 0)
                        group_node.node_tree = existing_group
                    else:
                        # Create "gltf settings" group
                        group_node = node_tree.nodes.new(type='ShaderNodeGroup')
                        group_node.location = (500, 0)
                        group_node.node_tree = bpy.data.node_groups.new(name=group_name, type="ShaderNodeTree")

                        # Add Group Output
                        group_output = group_node.node_tree.nodes.new(type='NodeGroupOutput')
                        group_output.location = (group_node.location.x + 200, group_node.location.y)

                        # Add "Occlusion" as input of the group
                        occlusion_input = group_node.node_tree.nodes.new(type='NodeGroupInput')
                        occlusion_input.location = (group_node.location.x - 200, group_node.location.y)
                        occlusion_input.name = 'Occlusion'
                        group_node.node_tree.inputs.new('NodeSocketFloat', occlusion_input.name)

                    # Connect image texture to the "Occlusion" input of the group
                    node_tree.links.new(image_texture_node.outputs['Color'], group_node.inputs['Occlusion'])

        return {'FINISHED'}
    
    
# Operator to create a material dedicated to baking AO at 2048 resolution for export to GLB
class OBJECT_OT_CreateMaterials2048(Operator):
    bl_idname = "object.create_materials2048"
    bl_label = "Create Materials2048"
    bl_description = "Create material with blank texture 2048x2048 for selected objects ready to AO Bake and ready to GLB export"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects

        for obj in selection:
            if obj.type == 'MESH':
                    material_name = obj.data.name
                    
                    if material_name in bpy.data.materials:
                        old_material = bpy.data.materials[material_name]
                        bpy.data.materials.remove(old_material)
                        obj.data.materials.clear()
                        
                    material = bpy.data.materials.new(name=material_name)
                    obj.data.materials.append(material)
                    
                    bpy.ops.material.new()

                    material.use_nodes = True
                    node_tree = material.node_tree
                    
                    # Remove all existing node
                    node_tree.nodes.clear()

                    # Set Image Texture name as mesh name + AO  
                    image_name = obj.data.name + "_AO"

                    # Delete all textures with the same name
                    for image in bpy.data.images:
                        if image.name == image_name:
                            bpy.data.images.remove(image)

                    # Add image texture
                    image_texture_node = node_tree.nodes.new('ShaderNodeTexImage')

                    # Create a White Image Texture
                    image = bpy.ops.image.new(name=image_name, width=2048, height=2048, color=(1.0, 1.0, 1.0, 1.0))
                    tex = bpy.data.images.get(image_name)

                    # Set White image texture as image for the node Image Texture
                    image_texture_node.image = tex

                    # Add Principled BSDF
                    principled_bsdf_node = node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                    principled_bsdf_node.location = (500, -500)
                    principled_bsdf_node.inputs['Base Color'].default_value = (0.0, 1.0, 1.0, 1.0)  # R, G, B, Alpha

                    # Add Material Output
                    material_output_node = node_tree.nodes.new('ShaderNodeOutputMaterial')
                    material_output_node.location = (800, -500)

                    # Connect Principled BSDF to Material Output
                    node_tree.links.new(principled_bsdf_node.outputs[0], material_output_node.inputs[0])

                    # Check if "gltf settings" group already exists
                    group_name = "gltf settings"
                    group_node = None
                    existing_group = bpy.data.node_groups.get(group_name)
                    if existing_group:
                        group_node = node_tree.nodes.new(type='ShaderNodeGroup')
                        group_node.location = (500, 0)
                        group_node.node_tree = existing_group
                    else:
                        # Create "gltf settings" group
                        group_node = node_tree.nodes.new(type='ShaderNodeGroup')
                        group_node.location = (500, 0)
                        group_node.node_tree = bpy.data.node_groups.new(name=group_name, type="ShaderNodeTree")

                        # Add Group Output
                        group_output = group_node.node_tree.nodes.new(type='NodeGroupOutput')
                        group_output.location = (group_node.location.x + 200, group_node.location.y)

                        # Add "Occlusion" as input of the group
                        occlusion_input = group_node.node_tree.nodes.new(type='NodeGroupInput')
                        occlusion_input.location = (group_node.location.x - 200, group_node.location.y)
                        occlusion_input.name = 'Occlusion'
                        group_node.node_tree.inputs.new('NodeSocketFloat', occlusion_input.name)

                    # Connect image texture to the "Occlusion" input of the group
                    node_tree.links.new(image_texture_node.outputs['Color'], group_node.inputs['Occlusion'])

        return {'FINISHED'}
    
    
# Operator to export objects as GLB
class OBJECT_OT_GLBExport(Operator, ExportHelper):
    bl_idname = "export_scene.batch_glb"
    bl_label = "ciao"
    bl_description = "Export GLB from Selected Objects named as Collection limited to Collection"
    bl_options = {'PRESET', 'UNDO'}

    # ExportHelper mixin class uses this
    filename_ext = ".glb"

    def execute(self, context):

        wm = bpy.context.window_manager

        # Export to blend file location
        basedir = os.path.dirname(self.filepath)

        if not basedir:
            raise Exception("Blend file is not saved")

        view_layer = bpy.context.view_layer

        obj_active = view_layer.objects.active
        selection = bpy.context.selected_objects

        tot = len(selection)
        progress = 0
        wm.progress_begin(0, tot)

        bpy.ops.object.select_all(action='DESELECT')

        for obj in selection:
            obj.select_set(True)

        collection_objects = {}

        for obj in selection:
            for collection in obj.users_collection:
                if collection.name not in collection_objects:
                    collection_objects[collection.name] = []

                collection_objects[collection.name].append(obj)

        for collection_name, objects in collection_objects.items():
            bpy.ops.object.select_all(action='DESELECT')

            for obj in objects:
                obj.select_set(True)

                # Rename mesh with object name
                mesh = obj.data
                mesh.name = obj.name

            fn = os.path.join(basedir, collection_name + self.filename_ext)
            file_path = fn

            # Get list of all selected objects
            oggetti_selezionati = bpy.context.selected_objects

            
            for oggetto in oggetti_selezionati:

                # Export objects in the collection
                bpy.ops.export_scene.gltf(
                    filepath=file_path,
                    export_format='GLB',
                    export_copyright='Simtech Srl',
                    use_selection=True,
                    filter_glob="*.glb",
                    export_draco_mesh_compression_enable=True,
                    export_apply=True
                )

                print("Written:", fn)

        view_layer.objects.active = obj_active

        for obj in selection:
            obj.select_set(True)

        wm.progress_end()
        return {'FINISHED'}
    
def get_path():
    """Get the path of Addon"""
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


# Assing UV Checker to a Mesh removing all others materials
class OBJECT_OT_UVCheckerGRID(Operator):
    bl_idname = "object.uv_checker_grid"
    bl_label = "UV Checker GRID"
    bl_description = "Assign UV Checker GRID map for selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selection = context.selected_objects

        for obj in selection:
            if obj.type == 'MESH':
                obj.data.materials.clear()

                if not obj.data.materials:
                    material_name = 'UV_checker_grid'
                    material = bpy.data.materials.new(name=material_name)
                    obj.data.materials.append(material)

                if obj.data.materials:
                    material = obj.data.materials[0]

                    material.use_nodes = True
                    node_tree = material.node_tree

                    # Remove all existing nodes
                    node_tree.nodes.clear()

                    # Add Principled BSDF node
                    principled_bsdf_node = node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                    principled_bsdf_node.location = (500, -500)
                    principled_bsdf_node.inputs['Base Color'].default_value = (0.0, 0.0, 1.0, 1.0)  # R, G, B, Alpha

                    # Add Material Output node
                    material_output_node = node_tree.nodes.new('ShaderNodeOutputMaterial')
                    material_output_node.location = (800, -500)

                    # Connect Principled BSDF node to Material Output node
                    node_tree.links.new(principled_bsdf_node.outputs[0], material_output_node.inputs[0])

                    # Add image texture node
                    image_texture_node = node_tree.nodes.new('ShaderNodeTexImage')
                    image_texture_node.location = (200, -500)

                    # Add Texture Coordinate node
                    texture_coord_node = node_tree.nodes.new('ShaderNodeTexCoord')
                    texture_coord_node.location = (-200, -500)

                    # Create the path to the image
                    addon_dir = get_path()
                    image_path = os.path.join(addon_dir, "addons", "resources", 'UV_checker_GRID.png').replace("\\", "/")

                    # Set the newly created image as the texture for the node
                    image_texture_node.image = bpy.data.images.load(image_path)

                    # Add Mapping node
                    mapping_node = node_tree.nodes.new('ShaderNodeMapping')
                    mapping_node.location = (0, -500)

                    # Connect Texture Coordinate node to Mapping node
                    node_tree.links.new(texture_coord_node.outputs[2], mapping_node.inputs[0])

                    # Connect Mapping node to Image Texture node
                    node_tree.links.new(mapping_node.outputs[0], image_texture_node.inputs[0])

                    # Connect Image Texture node to the "Base Color" input of Principled BSDF node
                    node_tree.links.new(image_texture_node.outputs['Color'], principled_bsdf_node.inputs['Base Color'])

                    # Update the scale values of the Mapping node
                    mapping_node.inputs['Scale'].default_value = (context.scene.mapping_scale_property,) * 3

        return {'FINISHED'}


# Assing UV Checker to a Mesh removing all others materials
class OBJECT_OT_UVCheckerLINE(Operator):
    bl_idname = "object.uv_checker_line"
    bl_label = "UV Checker LINE"
    bl_description = "Assign UV Checker LINE map for selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    # Assing UV Checker to a Mesh removing all others materials
    def execute(self, context):
        
        global mapping_node
        selection = context.selected_objects
        
        for obj in selection:
            if obj.type == 'MESH':
                obj.data.materials.clear()
            
                if not obj.data.materials:
                    material_name = 'UV_checker_line'
                    material = bpy.data.materials.new(name=material_name)
                    obj.data.materials.append(material)

                if obj.data.materials:
                    material = obj.data.materials[0]

                    material.use_nodes = True
                    node_tree = material.node_tree

                    # Remove all existing nodes
                    node_tree.nodes.clear()

                    # Add Principled BSDF
                    principled_bsdf_node = node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                    principled_bsdf_node.location = (500, -500)
                    principled_bsdf_node.inputs['Base Color'].default_value = (1.0, 0.0, 0.0, 1.0)  # R, G, B, Alpha

                    # Add Material Output
                    material_output_node = node_tree.nodes.new('ShaderNodeOutputMaterial')
                    material_output_node.location = (800, -500)

                    # Connect Principled BSDF to Material Output
                    node_tree.links.new(principled_bsdf_node.outputs[0], material_output_node.inputs[0])
                    
                    # Add image texture node
                    image_texture_node = node_tree.nodes.new('ShaderNodeTexImage')
                    image_texture_node.location = (200, -500)
                    
                    # Add Texture Coordinate node
                    texture_coord_node = node_tree.nodes.new('ShaderNodeTexCoord')
                    texture_coord_node.location = (-200, -500)
                    
                    # Create path to the image
                    addon_dir = get_path()
                    image_path = os.path.join(addon_dir,"addons", "resources", 'UV_checker_LINE.png').replace("\\", "/")

                    bpy.data.images.load(image_path)

                    # Set the newly created image as the texture for the node
                    image_texture_node.image =  bpy.data.images.load(image_path)
                    
                     # Add Mapping node
                    mapping_node = node_tree.nodes.new('ShaderNodeMapping')
                    mapping_node.location = (0, -500)

                    # Connect Texture Coordinate node to Mapping node
                    node_tree.links.new(texture_coord_node.outputs[2], mapping_node.inputs[0])

                    # Connect Mapping node to Image Texture node
                    node_tree.links.new(mapping_node.outputs[0], image_texture_node.inputs[0])

                    # Connect Image Texture node to the "Base Color" input of Principled BSDF node
                    node_tree.links.new(image_texture_node.outputs['Color'], principled_bsdf_node.inputs['Base Color'])
                    
                    # Update the scale values of the Mapping node
                    mapping_node.inputs['Scale'].default_value = (context.scene.mapping_scale_property,) * 3

                    
                    
        return {'FINISHED'}
    
# Assing Reflection Checker to a Mesh removing all others materials
class OBJECT_OT_ReflectionChecker(Operator):
    bl_idname = "object.reflection_checker"
    bl_label = "Reflection Checker"
    bl_description = "Assign Reflection Checker Material for selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        
        selection = bpy.context.selected_objects

        for obj in selection:
            if obj.type == 'MESH':
                obj.data.materials.clear()
            
                if not obj.data.materials:
                    material_name = 'Reflection_Checker'
                    material = bpy.data.materials.new(name=material_name)
                    obj.data.materials.append(material)

                if obj.data.materials:
                    material = obj.data.materials[0]

                    material.use_nodes = True
                    node_tree = material.node_tree

                    # Remove all exsisting
                    node_tree.nodes.clear()

                    # Add Principled BSDF
                    principled_bsdf_node = node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                    principled_bsdf_node.location = (500, -500)
                    principled_bsdf_node.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)  # R, G, B, Alpha
                    principled_bsdf_node.inputs['Roughness'].default_value = (0.0)
                    principled_bsdf_node.inputs['Metallic'].default_value = (1.0)

                    # Add Material Output
                    material_output_node = node_tree.nodes.new('ShaderNodeOutputMaterial')
                    material_output_node.location = (800, -500)

                    # Coonect Principled BSDF to Material Output
                    node_tree.links.new(principled_bsdf_node.outputs[0], material_output_node.inputs[0])
                    
                    
        return {'FINISHED'}
    

# Define the property for the slider
bpy.types.Scene.mapping_scale_property = bpy.props.IntProperty(
    name="Mapping Scale",
    description="Scale value for the Mapping node for selected objects (min 1 - max 20)",
    default=1,
    min=1,
    max=20
)

class OBJECT_OT_ApplyMappingScale(Operator):
    bl_idname = "object.apply_mapping_scale"
    bl_label = "Apply Scale"
    bl_description = "Apply the scale value to the Mapping node to control the UV map Repeat for selected objects"

    def execute(self, context):
        selected_objects = bpy.context.selected_objects
        
        for obj in selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                material = obj.data.materials[0]
                node_tree = material.node_tree

                mapping_node = None

                # Find the Mapping node in the node tree
                for node in node_tree.nodes:
                    if node.type == 'MAPPING':
                        mapping_node = node
                        break

                if mapping_node:
                    mapping_node.inputs['Scale'].default_value = (context.scene.mapping_scale_property,) * 3

        return {'FINISHED'}
    
class OBJECT_OT_Bake(Operator):
    bl_idname = "object.bake_ao"
    bl_label = "Bake"
    bl_description = "Bake Ambient Occlusion for selected objects (128 samples)"

    def execute(self, context):
        selected_objects = bpy.context.selected_objects

        # Cycle for all selected objects
        for obj in selected_objects:
            
            # Check UV set
            if obj.type == 'MESH':
                if len(obj.data.uv_layers) > 1:
                    
                    # Set Bake Settings
                    bpy.context.scene.render.engine = 'CYCLES'
                    bpy.context.scene.cycles.samples = 128

                    # Select Active object
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)

                    # Bake AO in the second UV set
                    bpy.ops.object.bake('INVOKE_DEFAULT', type='AO', margin_type='ADJACENT_FACES', uv_layer=obj.data.uv_layers[1].name)

        return {'FINISHED'}
    
class OBJECT_OT_Normal(Operator):
    bl_idname = "object.normal"
    bl_label = "Normal"
    bl_description = "Add a Weighted Normal modifier to check normal tangents on surfaces for all selected objects (Weight = 100, Keep Sharp = True)"

    def execute(self, context):
        selection = bpy.context.selected_objects

        for obj in selection:

            # Check if modifier already exsist
            modifier_exists = False
            for modifier in obj.modifiers:
                if modifier.type == 'WEIGHTED_NORMAL':
                    modifier_exists = True
                    break

            if not modifier_exists:
                
                # Add Wegithed Normal Modifier 
                bpy.ops.object.modifier_add(type='WEIGHTED_NORMAL')
                bpy.context.object.modifiers["WeightedNormal"].weight = 100
                bpy.context.object.modifiers["WeightedNormal"].keep_sharp = True
                
            # Enable auto smooth
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = 0.523599

            # Clear custom split normal data
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        
        return {'FINISHED'}
    
    
# Assing Reflection Checker to a Mesh removing all others materials
class OBJECT_OT_ClassicMaterial(Operator):
    bl_idname = "object.classic_material"
    bl_label = "Classic Material"
    bl_description = "Assign a Monochromatic yellow material for selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        
        selection = bpy.context.selected_objects

        for obj in selection:
            if obj.type == 'MESH':
                obj.data.materials.clear()
            
                if not obj.data.materials:
                    material_name = 'Monochromatic Material'
                    material = bpy.data.materials.new(name=material_name)
                    obj.data.materials.append(material)

                if obj.data.materials:
                    material = obj.data.materials[0]

                    material.use_nodes = True
                    node_tree = material.node_tree

                    # Remove all exsisting nodes
                    node_tree.nodes.clear()

                    # Add Principled BSDF
                    principled_bsdf_node = node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                    principled_bsdf_node.location = (500, -500)
                    principled_bsdf_node.inputs['Base Color'].default_value = (0.8, 0.6, 0.2, 1.0)  # R, G, B, Alpha

                    # Add Material Output
                    material_output_node = node_tree.nodes.new('ShaderNodeOutputMaterial')
                    material_output_node.location = (800, -500)

                    # Connect Principled BSDF to Material Output
                    node_tree.links.new(principled_bsdf_node.outputs[0], material_output_node.inputs[0])
                    
                    
        return {'FINISHED'}

# Panel in the N dropdown menu in the 3D view    
class VIEW3D_PT_Panel00(Panel):
    bl_label = "UV Checker"
    bl_idname = "VIEW3D_PT_panel00"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"

    def draw(self, context):
        layout = self.layout        

        # Main Panel
        col = layout.column()
        box0 = col.box()
        
        box0.operator("object.classic_material", text='Monochromatic Material', icon='MATERIAL')
        box0.operator("object.reflection_checker", text='Reflection Checker', icon='SHADING_RENDERED')
        box0.operator("object.normal", text='Hard Surface Checker', icon='MOD_NORMALEDIT')
        
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()

        # Create first Box
        box1 = col.box()

        # First Panel in the first Box
        row = box1.row()
        row.operator("object.uv_checker_grid", text="UV GRID", icon='TEXTURE_DATA')
        row.operator("object.uv_checker_line", text="UV LINE", icon='ALIGN_JUSTIFY')

        # Add Slider UV Repeat in the first box
        box1.prop(context.scene, "mapping_scale_property", text="UV Repeat")

        # Add "Apply Repeat" button in the first box
        box1.operator("object.apply_mapping_scale", text="Apply Repeat", icon='CHECKMARK')
        
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()
        
        # Create second Box
        box2 = col.box()
        
        # Add "Remove Materials" button in the second box
        box2.operator("object.remove_materials", text="Remove Material Slots", icon='X')
        
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()
        
        # Create third box
        box5 = col.box()

        # Add "Delete All Materials" button in the third box
        box5.operator("object.delete_all_materials", text="Destroy ALL Materials", icon='TRASH')

# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel01(Panel):
    bl_label = "GLB Preparation"
    bl_idname = "VIEW3D_PT_panel01"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"

    def draw(self, context):
        layout = self.layout
        
        # Add subtitle
        layout.label(text="Create GLB Materials:")

        # Main panel
        col = layout.column()

        # Create a box
        box = col.box()

        box.operator("object.rename_meshes", text="Rename Meshes", icon='SORTALPHA')
        
        row = box.row()
        row.operator("object.create_materials1024", text="1K AO", icon='ALIASED')
        row.operator("object.create_materials2048", text="2K AO", icon='ANTIALIASED')
        
        box.operator("object.bake_ao", text='Bake AO', icon='TPAINT_HLT')
    

# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel02(Panel):
    bl_label = "GLB Export"
    bl_idname = "VIEW3D_PT_panel02"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"

    def draw(self, context):
        layout = self.layout

        # Main panel
        col = layout.column()

        # Create a box
        box = col.box()

        box.operator("export_scene.batch_glb", text="GLB Export", icon='EXPORT')
        

# Register all classes 
classes = (
    OBJECT_OT_UVCheckerGRID,
    OBJECT_OT_UVCheckerLINE,
    OBJECT_OT_DeleteAllMaterials,
    OBJECT_OT_ClassicMaterial,
    OBJECT_OT_RenameMeshes,
    OBJECT_OT_CreateMaterials1024,
    OBJECT_OT_CreateMaterials2048,
    OBJECT_OT_Bake,
    OBJECT_OT_GLBExport,
    OBJECT_OT_RemoveMaterials,
    OBJECT_OT_Normal,
    VIEW3D_PT_Panel00,
    VIEW3D_PT_Panel01,
    VIEW3D_PT_Panel02,
    OBJECT_OT_ApplyMappingScale,
    OBJECT_OT_ReflectionChecker,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
