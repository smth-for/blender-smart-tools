schema_version = "1.0.0"

id = "SMTH_Smart_Tools"
version = "1.0.0"
name = "SMTH_Smart_Tools"
tagline = "SMTH_Smart_Tools"
maintainer = "Lorenzo Ronghi"
type = "add-on"

license = ["free"]

blender_version_min = "4.2.1"


bl_info = {
    "name": "SMTH_Smart_Tools",
    "author": "Lorenzo Ronghi",
    "version": (1, 0, 0),
    "blender": (4, 2, 1),
    "location": "N Panel",
    "description": "Add a tab in N panel with SMTH tools"
}

import bpy
from bpy.types import Operator, Panel
from bpy.props import IntProperty
from bpy_extras.io_utils import ExportHelper
import os
from bpy.app import tempdir

addon_name = "SMTH Smart Tools"

class OBJECT_OT_RigidBodyAnimPath(Operator):
    bl_idname = "object.rigidbody_anim"
    bl_label = "Genera Percorso di Animazione Corpo Rigido"
    bl_description = "Genera Percorso di Animazione Corpo Rigido"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Ottieni gli oggetti mesh selezionati
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}

        start_frame = 0
        end_frame = bpy.context.scene.frame_end

        for obj in mesh_objects:
            # Crea una nuova collezione "path_<nome_oggetto>"
            collection_name = f"path_{obj.name}"
            path_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(path_collection)

            # Itera sui frame per ottenere la posizione e la rotazione dell'oggetto
            for frame in range(start_frame, end_frame + 1):
                bpy.context.scene.frame_set(frame)
                
                # Crea un nuovo oggetto per questo frame
                bpy.ops.mesh.primitive_cube_add(size=0.01)
                frame_obj = bpy.context.active_object
                frame_obj.name = f"{obj.name}_frame_{frame}"
                
                # Imposta la posizione e la rotazione
                frame_obj.matrix_world = obj.matrix_world.copy()
                
                # Rimuovi l'oggetto dalla collezione corrente e aggiungilo alla collezione "path_<nome_oggetto>"
                bpy.context.collection.objects.unlink(frame_obj)
                path_collection.objects.link(frame_obj)
                
                # Rimuovi tutti i vertici per lasciare l'oggetto vuoto
                mesh = frame_obj.data
                mesh.clear_geometry()
                
        return {'FINISHED'}
    
class OBJECT_OT_VertexColorWind(Operator):
    bl_idname = "object.vertex_color"
    bl_label = "Generate Vertex Color RGBA Attribute"
    bl_description = "Generate Vertex Color RGBA Attribute"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Esegui le operazioni solo su oggetti selezionati di tipo 'MESH'
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}

        # Assicurati di essere in modalità oggetto
        bpy.ops.object.mode_set(mode='OBJECT')
        
        for obj in mesh_objects:
            context.view_layer.objects.active = obj

            # Crea un gruppo di vertici se non esiste
            if len(obj.vertex_groups) == 0:
                vgroup = obj.vertex_groups.new(name="Normalized Gradient")
            else:
                vgroup = obj.vertex_groups[0]   
            
            # Trova il punto più basso e più alto dell'oggetto
            z_min = min(v.co.z for v in obj.data.vertices)
            z_max = max(v.co.z for v in obj.data.vertices)
            z_range = z_max - z_min
            if z_range == 0:
                self.report({'WARNING'}, f"L'oggetto {obj.name} è piatto. Non è possibile applicare un gradiente verticale.")
                continue
            
            # Applica il gradiente normalizzato
            for v in obj.data.vertices:
                weight = (v.co.z - z_min) / z_range
                vgroup.add([v.index], weight, 'REPLACE')
            
            obj.data.update()
            # Imposta la modalità Weight Paint
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            obj.vertex_groups.active_index = vgroup.index

            # Rinomina o crea il layer "VERTEX R"
            if not obj.data.vertex_colors:
                obj.data.vertex_colors.new(name="VERTEX R")
            else:
                obj.data.vertex_colors[0].name = "VERTEX R"

            # Crea i nuovi attributi di colore se non esistono già
            color_layers = ["VERTEX G", "VERTEX B", "VERTEX A"]
            for color_layer_name in color_layers:
                if color_layer_name not in obj.data.vertex_colors:
                    obj.data.vertex_colors.new(name=color_layer_name)

        # Imposta la modalità Vertex Paint
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')
        for obj in mesh_objects:
            if "VERTEX R" in obj.data.vertex_colors:
                obj.data.vertex_colors.active = obj.data.vertex_colors["VERTEX R"]
                bpy.context.view_layer.objects.active = obj
                bpy.ops.paint.vertex_color_from_weight()
            else:
                self.report({'ERROR'}, f"L'oggetto {obj.name} non ha un layer di colore chiamato 'VERTEX R'.")

        # Unisci i canali di colore nei rispettivi componenti RGBA
        for obj in mesh_objects:
            if "VERTEX RGBA" not in obj.data.vertex_colors:
                rgba_layer = obj.data.vertex_colors.new(name="VERTEX RGBA")
            else:
                rgba_layer = obj.data.vertex_colors["VERTEX RGBA"]
            
            r_layer = obj.data.vertex_colors.get("VERTEX R")
            g_layer = obj.data.vertex_colors.get("VERTEX G")
            b_layer = obj.data.vertex_colors.get("VERTEX B")
            a_layer = obj.data.vertex_colors.get("VERTEX A")
            
            if not (r_layer and g_layer and b_layer and a_layer):
                self.report({'ERROR'}, f"Uno o più canali di colore mancanti in '{obj.name}'.")
                continue

            for poly in obj.data.polygons:
                for loop_index in poly.loop_indices:
                    r = r_layer.data[loop_index].color[0]
                    g = g_layer.data[loop_index].color[0]
                    b = b_layer.data[loop_index].color[0]
                    a = a_layer.data[loop_index].color[0]
                    rgba_layer.data[loop_index].color = (r, g, b, a)

        # Imposta la modalità Vertex Paint e attiva il layer VERTEX RGBA
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')
        for obj in mesh_objects:
            bpy.ops.geometry.color_attribute_render_set(name="VERTEX RGBA")

        return {'FINISHED'}
    
    
class OBJECT_OT_AnimPathNPC(Operator):
    bl_idname = "object.anim_path_npc"
    bl_label = "Generate NPC Animation Path"
    bl_description = "Generate NPC Animation Path"
    bl_options = {'REGISTER', 'UNDO'}

    # Add a new property for curve resample count
    curve_resample_count: IntProperty(
        name="Curve Resample Count",
        description="Number of points to resample the curve",
        default=200,
        min=1,
        max=1000
    )

    # Main function to execute the operation
    def execute(self, context):
        selection = context.selected_objects
        
        if not bpy.context.active_object:
            self.report({'ERROR'}, "NO OBJECT SELECTED")
            return {'CANCELLED'}
        
        obj = bpy.context.active_object
        
        # Aggiungi un modificatore Geometry Nodes
        geonodes = obj.modifiers.new(name="GeometryNodes", type='NODES')
        bpy.ops.node.new_geometry_node_group_assign()
        geonodes.node_group.name = 'AnimPath'
        
        # Accedi ai nodi e ai collegamenti del node group
        nodes = geonodes.node_group.nodes
        links = geonodes.node_group.links
        
        # Crea i nodi necessari
        input_node = nodes.new('NodeGroupInput')
        output_node = nodes.new('NodeGroupOutput')
        mesh_to_curve_node = nodes.new('GeometryNodeMeshToCurve')
        curve_resample = nodes.new('GeometryNodeResampleCurve')
        instance_on_points = nodes.new('GeometryNodeInstanceOnPoints')
        add_cube = nodes.new('GeometryNodeMeshCube')
        align_rotation_to_vector = nodes.new('FunctionNodeAlignRotationToVector')
        curve_tangent = nodes.new('GeometryNodeInputTangent')
        
        # Posiziona i nodi
        input_node.location = (-200, 0)
        mesh_to_curve_node.location = (0, 0)
        curve_resample.location = (200, 0)
        instance_on_points.location = (400, 0)
        add_cube.location = (200, 300)
        align_rotation_to_vector.location = (200, -200)
        curve_tangent.location = (0, -200)
        output_node.location = (600, 0)
        
        # Collega i nodi
        links.new(input_node.outputs[0], mesh_to_curve_node.inputs['Mesh'])
        links.new(mesh_to_curve_node.outputs['Curve'], curve_resample.inputs['Curve'])
        links.new(curve_resample.outputs['Curve'], instance_on_points.inputs['Points'])
        links.new(add_cube.outputs['Mesh'], instance_on_points.inputs['Instance'])
        links.new(curve_tangent.outputs['Tangent'], align_rotation_to_vector.inputs['Vector'])
        links.new(align_rotation_to_vector.outputs['Rotation'], instance_on_points.inputs['Rotation'])
        links.new(instance_on_points.outputs['Instances'], output_node.inputs[0])
        
        # Configura i parametri dei nodi
        curve_resample.inputs['Count'].default_value = self.curve_resample_count
        add_cube.inputs[1].default_value = 1
        add_cube.inputs[2].default_value = 1
        add_cube.inputs[3].default_value = 1
        align_rotation_to_vector.axis = 'Y'
        align_rotation_to_vector.pivot_axis = 'Z'
        
        # Elimina solo il primo nodo di input e output
        for node in nodes:
            if node.type == 'GROUP_INPUT':
                nodes.remove(node)
                break
        for node in nodes:
            if node.type == 'GROUP_OUTPUT':
                nodes.remove(node)
                break

        # Realizza i duplicati
        bpy.ops.object.duplicates_make_real()

        # Elimina tutti i modificatori dagli oggetti selezionati e dall'oggetto attivo
        selected_objects = bpy.context.selected_objects
        active_obj = bpy.context.active_object

        # Assicurati che l'oggetto attivo sia incluso negli oggetti selezionati
        if active_obj not in selected_objects:
            selected_objects.append(active_obj)

        # Rimuovi i modificatori da tutti gli oggetti selezionati
        for obj in selected_objects:
            for mod in obj.modifiers:
                obj.modifiers.remove(mod)

        # Entra in modalità Edit e elimina tutte le mesh all'interno degli oggetti
        for obj in selected_objects:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.delete(type='VERT')
            bpy.ops.object.mode_set(mode='OBJECT')

        # Crea una nuova collezione chiamata "NPC path"
        new_collection = bpy.data.collections.new("NPC path")
        bpy.context.scene.collection.children.link(new_collection)
        
        # Sposta gli oggetti vuoti nella nuova collezione
        for obj in selected_objects:
            if len(obj.data.vertices) == 0:  # Controlla se l'oggetto è vuoto
                # Linka l'oggetto alla nuova collezione
                new_collection.objects.link(obj)
                # Rimuovi l'oggetto dalla collezione principale (scene collection)
                bpy.context.scene.collection.objects.unlink(obj)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "curve_resample_count")

class OBJECT_OT_PurgeOrphans(Operator):
    bl_idname = "object.purge_orphans"
    bl_label = "Purge Unused Data"
    bl_description = "Delete Unused Data"
    bl_options = {'REGISTER', 'UNDO'}

    # Main function to execute the operation
    def execute(self, context):
        selection = context.selected_objects

        bpy.ops.outliner.orphans_purge()

        return {'FINISHED'}

class OBJECT_OT_MergeMaterials(Operator):
    bl_idname = "object.merge_materials"
    bl_label = "Merge Duplicate Materials"
    bl_description = "Merge duplicate materials for selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    # Function to find the base material without the suffix in the name
    def find_material_base(self, material):
        if '.' in material.name:
            base_name = material.name.split('.')[0]
            if base_name in bpy.data.materials:
                return bpy.data.materials[base_name]
        return None

    # Main function to execute the operation
    def execute(self, context):
        selection = context.selected_objects

        # Loop through all selected objects
        for obj in selection:
            for i, slot in enumerate(obj.material_slots):
                material = slot.material
                if material:
                    material_base = self.find_material_base(material)
                    
                    if material_base and material_base != material:
                        obj.material_slots[i].material = material_base

        # Remove orphaned materials
        for material in bpy.data.materials:
            if material.users == 0:
                bpy.data.materials.remove(material)

        return {'FINISHED'}

class OBJECT_OT_ExportForVesta_3_3(Operator, ExportHelper):    
    """Vesta - Batch export objects as glTF files"""
    bl_idname = "export_scene.batch_gltf_3_3"
    bl_label = "Vesta Batch export glTF's"
    bl_options = {'PRESET', 'UNDO'}
    
    # ExportHelper mixin class uses this
    filename_ext = ".gltf"

    def execute(self, context):        # execute() is called when running the operator.
        print('Vesta - Batch export objects as glTF files started!')
        
        wm = bpy.context.window_manager
        
        # export to blend file location
        # basedir = os.path.dirname(bpy.data.filepath)
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

            # some exporters only use the active object
            view_layer.objects.active = obj

            name = bpy.path.clean_name(obj.name)
            fn = os.path.join(basedir, name)
            print("obj: ", obj.name)
            bpy.ops.export_scene.gltf(
                filepath=fn,
                export_copyright='Simtech Srl',
                export_format='GLTF_SEPARATE',
                export_draco_mesh_compression_enable=True,
                use_selection=True,
                export_apply=True
            )

            # Can be used for multiple formats
            # bpy.ops.export_scene.x3d(filepath=fn + ".x3d", use_selection=True)

            obj.select_set(False)
            wm.progress_update(++progress)

            print("written:", fn)


        view_layer.objects.active = obj_active

        for obj in selection:
            obj.select_set(True)

        wm.progress_end()
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.


class OBJECT_OT_ExportForVesta_2_93(Operator, ExportHelper):    
    """Vesta - Batch export objects as glTF files"""
    bl_idname = "export_scene.batch_gltf_2_93"
    bl_label = "Vesta Batch export glTF's"
    bl_options = {'PRESET', 'UNDO'}
    
    # ExportHelper mixin class uses this
    filename_ext = ".gltf"

    def execute(self, context):        # execute() is called when running the operator.
        print('Vesta - Batch export objects as glTF files started!')
        
        wm = bpy.context.window_manager
        
        # export to blend file location
        # basedir = os.path.dirname(bpy.data.filepath)
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

            # some exporters only use the active object
            view_layer.objects.active = obj

            name = bpy.path.clean_name(obj.name)
            fn = os.path.join(basedir, name)
            print("obj: ", obj.name)
            bpy.ops.export_scene.gltf(
                filepath=fn,
                export_copyright='Simtech Srl',
                export_format='GLTF_SEPARATE',
                export_draco_mesh_compression_enable=True,
                export_selected=True,
                export_apply=True
            )

            # Can be used for multiple formats
            # bpy.ops.export_scene.x3d(filepath=fn + ".x3d", use_selection=True)

            obj.select_set(False)
            wm.progress_update(++progress)

            print("written:", fn)


        view_layer.objects.active = obj_active

        for obj in selection:
            obj.select_set(True)

        wm.progress_end()
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.

class OBJECT_OT_SeparateByVertexGroup(Operator):
    bl_idname = "object.vertex_group_separate"
    bl_label = "Separate Vertex Group"
    bl_description = "Separate mesh by Vertex Group"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects
        
        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        # Filter only mesh objects
        mesh_selection = [obj for obj in selection if obj.type == 'MESH']

        if not mesh_selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        created_objects = []  # List to keep track of all objects created
        for obj in mesh_selection:
            # Check if the object has any vertex groups
            if not obj.vertex_groups:
                self.report({'WARNING'}, f"NO VERTEX GROUPS IN OBJECT: {obj.name}")
                return {'CANCELLED'}
            
            empty_groups = []
            # Iterate over all vertex groups in the object
            for group in obj.vertex_groups:
                # Check if the vertex group is empty
                if not any(group.index in [vg.group for vg in v.groups] for v in obj.data.vertices):
                    empty_groups.append(group.name)
                    obj.vertex_groups.remove(group)
                    continue
                
                view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='DESELECT')
                
                # Set the active group to the current group
                obj.vertex_groups.active_index = group.index
                
                # Select all vertices of the active vertex group
                bpy.ops.object.vertex_group_select()
                
                # Separate the selected vertices into a new object
                bpy.ops.mesh.separate(type='SELECTED')
                bpy.ops.object.mode_set(mode='OBJECT')
                
                # Deselect all to make sure only the new object will be selected
                bpy.ops.object.select_all(action='DESELECT')
                
                # The separated object is the last in the collection
                new_obj = context.scene.objects[-1]
                new_obj.select_set(True)
                view_layer.objects.active = new_obj
                
                # Rename the newly created object to match the vertex group name
                new_obj.name = group.name
            
            # Report empty vertex groups
            if empty_groups:
                self.report({'INFO'}, "EMPTY VERTEX GROUPS SKIPPED: " + ", ".join(empty_groups))
            
            # Delete the original object
            bpy.data.objects.remove(obj, do_unlink=True)

        return {'FINISHED'}
    
# Operator to separate an Object by Vertex Group
class OBJECT_OT_VertexGroupCreate(Operator):
    bl_idname = "object.vertex_group_create"
    bl_label = "Create Vertex Group"
    bl_description = "Create a Vertex Group for each mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects

        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        # Filter only mesh objects
        mesh_selection = [obj for obj in selection if obj.type == 'MESH']

        if not mesh_selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        created_objects = []  # List to keep track of all objects created
        
        for obj in mesh_selection:
            # Ensure we are working with the correct object
            view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.object.vertex_group_add()
            
            # Assign the name of the object to the vertex group
            vertex_group = obj.vertex_groups.active
            vertex_group.name = obj.name
            bpy.ops.object.vertex_group_assign()
            
            # Check if the vertex group is empty
            if not any(vertex_group.weight(v.index) > 0 for v in obj.data.vertices):
                self.report({'INFO'}, f"Vertex group '{vertex_group.name}' not created for object '{obj.name}' because it was empty.")
                obj.vertex_groups.remove(vertex_group)
            else:
                created_objects.append(obj)
            
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Select all created objects
        for obj in created_objects:
            obj.select_set(True)
        
        # Join the selected objects
        if created_objects:
            view_layer.objects.active = created_objects[0]  # Set an active object
            bpy.ops.object.join()  # Join the selected objects

        return {'FINISHED'}
    
class OBJECT_OT_ExportMultipleOBJ(Operator, ExportHelper):
    """Export objects as OBJ files"""
    bl_idname = "export_scene.batch_obj"
    bl_label = "Multiple Export OBJ's"
    bl_options = {'PRESET', 'UNDO'}
    
    # ExportHelper mixin class uses this
    filename_ext = ".obj"

    def execute(self, context):
        print('Multiple Export objects as OBJ files started!')

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

            # ottieni la lista degli oggetti selezionati
            oggetti_selezionati = bpy.context.selected_objects

            # per ogni oggetto selezionato
            for oggetto in oggetti_selezionati:
            # ottieni il nome dell'oggetto
                nome_oggetto = oggetto.name

            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    obj.data.materials.clear()
                
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    obj.data.materials.clear()
                    material_name = obj.data.name
                    new_material = bpy.data.materials.new(name=material_name)
                    obj.data.materials.append(new_material)

                    # Assign the new material to the object
                    obj.active_material = new_material


            # crea un nuovo materiale con lo stesso nome dell'oggetto
                new_mat = bpy.data.materials.new(name=nome_oggetto)
                
            # assegna il nuovo materiale all'oggetto
                oggetto.active_material = new_mat

            # Export objects in the collection
            bpy.ops.wm.obj_export(filepath=file_path, export_selected_objects=False, filter_glob="*.obj")

            print("Written:", fn)

        view_layer.objects.active = obj_active

        for obj in selection:
            obj.select_set(True)

        wm.progress_end()
        return {'FINISHED'}

# Operator to add SubD modifier
class OBJECT_OT_SubD(Operator):
    bl_idname = "object.subd"
    bl_label = "SubD"
    bl_description = "Add SubD modifier"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects
        
        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        for obj in selection:
            bpy.ops.object.modifier_add(type='SUBSURF')

        return {'FINISHED'}

# Operator to unmark selected edges as Crease
class OBJECT_OT_CreaseEdgeUnmarker(Operator):
    bl_idname = "object.crease_edge_unmarker"
    bl_label = "Crease Edge Unmarker"
    bl_description = "Unmark selected edges as Crease"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects

        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        bpy.ops.transform.edge_crease(value=-1)


        return {'FINISHED'}

# Operator to mark selected edges as Crease
class OBJECT_OT_CreaseEdgeMarker(Operator):
    bl_idname = "object.crease_edge_marker"
    bl_label = "Crease Edge Marker"
    bl_description = "Mark selected edges as Crease"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects

        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        bpy.ops.transform.edge_crease(value=1)


        return {'FINISHED'}


# Operator to mark selected edges with Bevel Weight = 0
class OBJECT_OT_BevelEdgeUnmarker(Operator):
    bl_idname = "object.bevel_edge_unmarker"
    bl_label = "Bevel Edge Unmarker"
    bl_description = "Mark selected edges with Bevel Weight = 0"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects

        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        bpy.ops.transform.edge_bevelweight(value=-1)

        return {'FINISHED'}


# Operator to mark selected edges with Bevel Weight = 1
class OBJECT_OT_BevelEdgeMarker(Operator):
    bl_idname = "object.bevel_edge_marker"
    bl_label = "Bevel Edge Marker"
    bl_description = "Mark selected edges with Bevel Weight = 1"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects

        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        bpy.ops.transform.edge_bevelweight(value=1)

        return {'FINISHED'}


# Operator to add a Bevel modifier based on weight edges
class OBJECT_OT_AutoBevelWeight(Operator):
    bl_idname = "object.auto_bevel_weight"
    bl_label = "Auto Bevel Weight"
    bl_description = "Add a Bevel modifier based on weight edges"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects
        
        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        for obj in selection:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.modifier_add(type='BEVEL')
            bpy.context.object.modifiers["Bevel"].miter_outer = 'MITER_ARC'
            bpy.context.object.modifiers["Bevel"].limit_method = 'WEIGHT'
            bpy.context.object.modifiers["Bevel"].segments = 4
            bpy.context.object.modifiers["Bevel"].width = 0.005

        return {'FINISHED'}

# Operator to mark seams from islands
class OBJECT_OT_SeamsFromIslands(Operator):
    bl_idname = "object.seams_from_islands"
    bl_label = "Seams From Islands"
    bl_description = "Mark Seams from Islands"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects
        
        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        for obj in selection:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.seams_from_islands()
            bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

# Operator to UVW Box projection for UV unwrap
class OBJECT_OT_UVWBox(Operator):
    bl_idname = "object.uvw_box"
    bl_label = "UVW Box"
    bl_description = "UVW Box projection uv unwrap"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects
        
        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        for obj in selection:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.muv_uvw_box_map(assign_uvmap=True)
            bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

# Operator to world scale uvs
class OBJECT_OT_AutoScaleUV(Operator):
    bl_idname = "object.auto_scale_uv"
    bl_label = "World Scale UV"
    bl_description = "All islands of any object will be scaled to same world unit"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects
        
        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        for obj in selection:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.context.scene.muv_world_scale_uv_tgt_texture_size[1] = 2048
            bpy.context.scene.muv_world_scale_uv_tgt_texture_size[0] = 2048
            bpy.context.scene.muv_world_scale_uv_tgt_density = 1024
            bpy.ops.uv.muv_world_scale_uv_apply_manual(tgt_density=1024, tgt_texture_size=(2048, 2048), origin='CENTER', show_dialog=False, tgt_area_calc_method='UV ISLAND', only_selected=True)
            bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

# Operator to turn all object selected into a filetto
class OBJECT_OT_AutoFiletto(Operator):
    bl_idname = "object.auto_filetto"
    bl_label = "Auto Filetto"
    bl_description = "All object selected turn their edges into a filetto with a depth of 0.002 m"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects

        for obj in selection:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            if obj.type == 'MESH':
                bpy.ops.object.convert(target='CURVE')
                bpy.context.object.data.bevel_depth = 0.002
                bpy.context.object.data.bevel_resolution = 2
                bpy.ops.object.convert(target='MESH')
                bpy.ops.object.shade_smooth()
                  
        return {'FINISHED'}

# Operator to add mirror modifier to all active objects
class OBJECT_OT_AddMirrorModifier(Operator):
    bl_idname = "object.add_mirror_modifier"
    bl_label = "Add Mirror Modifier"
    bl_description = "Auto Mirror on X axis all objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects
        
        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
        
        # Check for non-mesh objects in the selection
        non_mesh_objects = [obj for obj in selection if obj.type != 'MESH']
        if non_mesh_objects:
            self.report({'WARNING'}, "NON-MESH OBJECT SELECTED: " + ", ".join([obj.name for obj in non_mesh_objects]))
            return {'CANCELLED'}

        for obj in selection:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            if obj.type == 'MESH':
                bpy.ops.transform.mirror(orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', constraint_axis=(True, False, False))
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.flip_normals()
                bpy.context.area.ui_type = 'UV'
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.select_all(action='SELECT')
                bpy.ops.transform.mirror(orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', constraint_axis=(True, False, False))
                bpy.context.area.ui_type = 'VIEW_3D'
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}

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
        
        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}

        for obj in selection:
            if obj.type == 'MESH':
                obj.data.materials.clear()
                
        return {'FINISHED'}

import bpy

class OBJECT_OT_CreateMaterials1024(bpy.types.Operator):
    bl_idname = "object.create_materials1024"
    bl_label = "Create Materials1024"
    bl_description = "Create material with blank texture 1024x1024 for selected objects ready to AO Bake and ready to GLB export"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects
        
        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}

        for obj in selection:
            if obj.type == 'MESH':
                material_name = obj.data.name
                
                if material_name in bpy.data.materials:
                    old_material = bpy.data.materials[material_name]
                    bpy.data.materials.remove(old_material)
                    obj.data.materials.clear()
                
                material = bpy.data.materials.new(name=material_name)
                obj.data.materials.append(material)
                
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
                image = bpy.data.images.new(name=image_name, width=1024, height=1024)
                image.generated_color = (1.0, 1.0, 1.0, 1.0)
                image.generated_type = 'BLANK'

                # Set White image texture as image for the node Image Texture
                image_texture_node.image = image

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
                    group_node.node_tree = existing_group
                else:
                    # Create "gltf settings" group
                    group_node = node_tree.nodes.new(type='ShaderNodeGroup')
                    group_tree = bpy.data.node_groups.new(name=group_name, type="ShaderNodeTree")
                    group_node.node_tree = group_tree

                    # Add Group Input
                    group_input = group_tree.nodes.new(type='NodeGroupInput')
                    group_input.location = (-200, 0)

                    # Add Group Output
                    group_output = group_tree.nodes.new(type='NodeGroupOutput')
                    group_output.location = (200, 0)

                    # Add the "Occlusion" input socket to the group
                    group_tree.interface.new_socket(name="Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
                    group_tree.interface.new_socket(name="Occlusion", in_out='OUTPUT', socket_type='NodeSocketFloat')

                    # Link Group Input to Group Output
                    group_tree.links.new(group_input.outputs["Occlusion"], group_output.inputs["Occlusion"])

                group_node.location = (500, 0)

                # Connect image texture to the "Occlusion" input of the group
                node_tree.links.new(image_texture_node.outputs['Color'], group_node.inputs['Occlusion'])

        return {'FINISHED'}
    
# Operator to create a material dedicated to baking AO at 2048 resolution for export to GLB
class OBJECT_OT_CreateMaterials2048(bpy.types.Operator):
    bl_idname = "object.create_materials2048"
    bl_label = "Create Materials2048"
    bl_description = "Create material with blank texture 2048x2048 for selected objects ready to AO Bake and ready to GLB export"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        obj_active = view_layer.objects.active
        selection = context.selected_objects
        
        if not selection:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}

        for obj in selection:
            if obj.type == 'MESH':
                material_name = obj.data.name
                
                if material_name in bpy.data.materials:
                    old_material = bpy.data.materials[material_name]
                    bpy.data.materials.remove(old_material)
                    obj.data.materials.clear()
                
                material = bpy.data.materials.new(name=material_name)
                obj.data.materials.append(material)
                
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
                image = bpy.data.images.new(name=image_name, width=2048, height=2048)
                image.generated_color = (1.0, 1.0, 1.0, 1.0)
                image.generated_type = 'BLANK'

                # Set White image texture as image for the node Image Texture
                image_texture_node.image = image

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
                    group_node.node_tree = existing_group
                else:
                    # Create "gltf settings" group
                    group_node = node_tree.nodes.new(type='ShaderNodeGroup')
                    group_tree = bpy.data.node_groups.new(name=group_name, type="ShaderNodeTree")
                    group_node.node_tree = group_tree

                    # Add Group Input
                    group_input = group_tree.nodes.new(type='NodeGroupInput')
                    group_input.location = (-200, 0)

                    # Add Group Output
                    group_output = group_tree.nodes.new(type='NodeGroupOutput')
                    group_output.location = (200, 0)

                    # Add the "Occlusion" input socket to the group
                    group_tree.interface.new_socket(name="Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
                    group_tree.interface.new_socket(name="Occlusion", in_out='OUTPUT', socket_type='NodeSocketFloat')

                    # Link Group Input to Group Output
                    group_tree.links.new(group_input.outputs["Occlusion"], group_output.inputs["Occlusion"])

                group_node.location = (500, 0)

                # Connect image texture to the "Occlusion" input of the group
                node_tree.links.new(image_texture_node.outputs['Color'], group_node.inputs['Occlusion'])

        return {'FINISHED'}

# Operator to export objects as GLB
class OBJECT_OT_GLBExport(Operator, ExportHelper):
    bl_idname = "export_scene.batch_glb"
    bl_label = "GLB Export"
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

        # Filter visible objects within visible collections with hide_select == False
        visible_objects = [obj for obj in selection 
                           if not obj.hide_viewport 
                           and any(not coll.hide_viewport and not coll.hide_select for coll in obj.users_collection)]

        # Deseselect objects belonging to hidden collections
        for obj in bpy.context.selected_objects:
            if any(coll.hide_viewport for coll in obj.users_collection):
                obj.select_set(False)

        # Group objects by collection
        collection_objects = {}

        for obj in visible_objects:
            for collection in obj.users_collection:
                if not collection.hide_viewport:
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
                    image_path = os.path.join(addon_dir, "resources", 'UV_checker_GRID.png').replace("\\", "/")

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
                    image_path = os.path.join(addon_dir, "resources", 'UV_checker_LINE.png').replace("\\", "/")

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
                    bpy.context.scene.cycles.samples = 256
                    bpy.context.scene.cycles.device = 'GPU'

                    # Select Active object
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)

                    # Bake AO in the second UV set
                    bpy.ops.object.bake('INVOKE_DEFAULT', type='AO', margin_type='ADJACENT_FACES', uv_layer=obj.data.uv_layers[1].name)

        return {'FINISHED'}
    

class OBJECT_OT_Normal(Operator):
    bl_idname = "object.normal"
    bl_label = "Normal"
    bl_description = "Add an Auto Smooth modifier to check normal tangents on surfaces for all selected objects"
    
    def execute(self, context):
        selection = context.selected_objects
        for obj in selection:
            # Set the active object
            context.view_layer.objects.active = obj
            
            # Check if Auto Smooth modifier already exists
            auto_smooth_exists = any(mod.name == "Smooth by Angle" for mod in obj.modifiers)
            
            # Check if Weighted Normal modifier already exists
            modifier_weight_exists = any(mod.type == 'WEIGHTED_NORMAL' for mod in obj.modifiers)
            
            if not modifier_weight_exists:
                # Add Weighted Normal Modifier 
                weighted_normal_modifier = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
                weighted_normal_modifier.weight = 100
                weighted_normal_modifier.keep_sharp = True
                bpy.context.object.modifiers["WeightedNormal"].use_pin_to_last = True
                
            if not auto_smooth_exists:
                bpy.ops.object.shade_auto_smooth()
                bpy.context.object.modifiers["Smooth by Angle"].use_pin_to_last = True

            # Clear custom split normal data
            if obj.type == 'MESH':
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
                bpy.ops.object.mode_set(mode='OBJECT')
        
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
    
class OBJECT_OT_CreateUV1(Operator):
    bl_idname = "uv.create_uv_1"
    bl_label = "Create UV 1"
    bl_description = "Create a UV 1 Layer for all selected object if missing and set active"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        view_layer = context.view_layer
        selection = context.selected_objects

        for obj in selection:
            if obj.type == 'MESH':
                mesh = obj.data

                # Verifica se esiste il layer UV [1], altrimenti crealo
                if len(mesh.uv_layers) < 2:
                    mesh.uv_layers.new(name="UVMap_1")

                # Rendi attivo il layer UV [1]
                mesh.uv_layers.active_index = 1

        return {'FINISHED'}
    
class OBJECT_OT_ProjectFromVieww(Operator):
    bl_idname = "uv.project_from_vieww"
    bl_label = "Multi UVs Project"
    bl_description = "Project UV from view for all selected object in active uv layer"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
            view_layer = context.view_layer
            selection = context.selected_objects

            for obj in selection:
                if obj.type == 'MESH':
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')

                    bpy.ops.uv.project_from_view(
                        orthographic=False,
                        camera_bounds=True,
                        correct_aspect=True,
                        clip_to_bounds=False,
                        scale_to_bounds=False
                    )
                    bpy.ops.object.mode_set(mode='OBJECT')
        
            return {'FINISHED'}
        
# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel66(Panel):
    bl_label = "Modeling"
    bl_idname = "VIEW3D_PT_panel66"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "EDUGAME"

    def draw(self, context):
        layout = self.layout

        # Main panel
        col = layout.column()
        
        col.label(text='Tools:')

        # Create a box
        box66 = col.box()
        
        box66.operator("object.purge_orphans", text = 'Purge Unused Data', icon = 'ORPHAN_DATA')
        box66.operator("object.anim_path_npc", text = 'NPC Anim Path', icon = 'GP_ONLY_SELECTED' )
        box66.operator("object.vertex_color", text = 'Vertex Color RGBA', icon = 'FORCE_WIND')
        box66.operator("object.rigidbody_anim", text = 'Rigid Body Anim Path', icon = 'PHYSICS')
        

# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel00(Panel):
    bl_label = "Modeling"
    bl_idname = "VIEW3D_PT_panel00"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"

    def draw(self, context):
        layout = self.layout

        # Main panel
        col = layout.column()
        
        col.label(text='Various:')

        # Create a box
        box6 = col.box()
        
        box6.operator("object.purge_orphans", text = 'Purge Unused Data', icon = 'ORPHAN_DATA')
        box6.operator("object.add_mirror_modifier", text = 'Auto Mirror', icon = 'MOD_MIRROR')
        
        col.label(text='Smart Join:')
        
        box6 = col.box()
        
        row6 = box6.row()
        row6.operator("object.vertex_group_create", text = 'Create Vertex Group', icon = 'MESH_CUBE')
        row6.operator("object.vertex_group_separate", text = 'Separate Vertex Group', icon = 'MOD_EXPLODE')
        
        col.label(text='Crease:')
        
        # Create a box
        box6 = col.box()
        
        row6 = box6.row()
        row6.operator("object.crease_edge_marker", text = 'Mark Crease', icon = 'SHARPCURVE')
        row6.operator("object.crease_edge_unmarker", text = 'Unmark Crease', icon = 'INVERSESQUARECURVE')
        box6.operator("object.subd", text = 'SubD Mod', icon = 'MOD_SUBSURF' )
         
        col.label(text='Bevel Weight:')
        
        # Create a box
        box6 = col.box()
        
        row6 = box6.row()
        row6.operator("object.bevel_edge_marker", text = 'Mark Weight Edge', icon = 'SPHERECURVE')
        row6.operator("object.bevel_edge_unmarker", text = 'Unmark Weight Edge', icon = 'LINCURVE')
        
        box6.operator("object.auto_bevel_weight", text = 'Bevel Weight Mod', icon = 'MOD_BEVEL')
        
        col.label(text='Normal:')
        
        box6 = col.box()
        
        box6.operator("object.normal", text='Auto Normal Hard Surf', icon='MOD_NORMALEDIT')
        
# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel07(Panel):
    bl_label = "Texturing"
    bl_idname = "VIEW3D_PT_panel07"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        
        # Create a box
        box7 = col.box()
        
        box7.operator("object.uvw_box", text = 'Auto UVW Unwrap', icon = 'UV')
        box7.operator("object.seams_from_islands", text = 'Seams From Islands', icon = 'UV_ISLANDSEL')
        box7.operator("uv.create_uv_1", text = 'Create UV 1', icon = 'STICKY_UVS_LOC')
        box7.operator("uv.project_from_vieww", text = 'Multi Project From View UVs', icon = 'MOD_UVPROJECT')
        box7.operator("object.auto_scale_uv", text = 'World Scale UV', icon = 'UV_DATA')
        box7.operator("object.merge_materials", text = 'Merge Duplicates Materials', icon = 'MATERIAL_DATA')
        
class VIEW3D_PT_Panel01(Panel):
    bl_label = "UV Checker"
    bl_idname = "VIEW3D_PT_panel01"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"

    def draw(self, context):
        layout = self.layout        

        # Main Panel
        col = layout.column()
        box0 = col.box()
        
        box0.operator("object.classic_material", text='Flat Material', icon='MATERIAL')
        box0.operator("object.reflection_checker", text='Reflection Checker', icon='SHADING_RENDERED')
        
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
class VIEW3D_PT_Panel02(Panel):
    bl_label = "GLB Preparation"
    bl_idname = "VIEW3D_PT_panel02"
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
class VIEW3D_PT_Panel03(Panel):
    bl_label = "GLB Export"
    bl_idname = "VIEW3D_PT_panel03"
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
        
# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel04(Panel):
    bl_label = "OBJ Export"
    bl_idname = "VIEW3D_PT_panel04"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"

    def draw(self, context):
        layout = self.layout

        # Main panel
        col = layout.column()

        # Create a box
        box = col.box()

        box.operator("export_scene.batch_obj", text="OBJ Export", icon='EXPORT')

# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel05(Panel):
    bl_label = "GLTF+BIN Export 2.93"
    bl_idname = "VIEW3D_PT_panel05"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"

    def draw(self, context):
        layout = self.layout

        # Main panel
        col = layout.column()

        # Create a box
        box = col.box()

        box.operator("export_scene.batch_gltf_2_93", text="GLTF+BIN Export", icon='EXPORT')
        
# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel06(Panel):
    bl_label = "GLTF+BIN Export 3+"
    bl_idname = "VIEW3D_PT_panel06"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"

    def draw(self, context):
        layout = self.layout

        # Main panel
        col = layout.column()

        # Create a box
        box = col.box()

        box.operator("export_scene.batch_gltf_3_3", text="GLTF+BIN Export", icon='EXPORT')
        

# Register all classes 
classes = (
    OBJECT_OT_ExportForVesta_3_3,
    OBJECT_OT_ExportForVesta_2_93,
    OBJECT_OT_SeparateByVertexGroup,
    OBJECT_OT_VertexGroupCreate,
    OBJECT_OT_ExportMultipleOBJ,
    OBJECT_OT_SubD,
    OBJECT_OT_CreaseEdgeMarker,
    OBJECT_OT_CreaseEdgeUnmarker,
    OBJECT_OT_BevelEdgeUnmarker,
    OBJECT_OT_BevelEdgeMarker,
    OBJECT_OT_AutoBevelWeight,
    OBJECT_OT_SeamsFromIslands,
    OBJECT_OT_UVWBox,
    OBJECT_OT_AutoScaleUV,
    OBJECT_OT_AddMirrorModifier,
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
    OBJECT_OT_AutoFiletto,
    VIEW3D_PT_Panel07,
    VIEW3D_PT_Panel00,
    VIEW3D_PT_Panel01,
    VIEW3D_PT_Panel02,
    VIEW3D_PT_Panel03,
    VIEW3D_PT_Panel04,
    VIEW3D_PT_Panel05,
    VIEW3D_PT_Panel06,
    VIEW3D_PT_Panel66,
    OBJECT_OT_ApplyMappingScale,
    OBJECT_OT_ReflectionChecker,
    OBJECT_OT_ProjectFromVieww,
    OBJECT_OT_CreateUV1,
    OBJECT_OT_MergeMaterials,
    OBJECT_OT_PurgeOrphans,
    OBJECT_OT_AnimPathNPC,
    OBJECT_OT_VertexColorWind,
    OBJECT_OT_RigidBodyAnimPath,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
