schema_version = "1.0.0"

id = "SMTH_Smart_Tools"
version = "1.0.1"
name = "SMTH_Smart_Tools"
tagline = "SMTH_Smart_Tools"
maintainer = "Lorenzo Ronghi"
type = "add-on"

license = ["free"]

blender_version_min = "4.3.2"


bl_info = {
    "name": "SMTH_Smart_Tools",
    "author": "Lorenzo Ronghi",
    "version": (1, 0, 1),
    "blender": (4, 3, 2),
    "location": "N Panel",
    "description": "Add a tab in N panel with SMTH tools"
}

import bpy
import bmesh
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty, PointerProperty, CollectionProperty, BoolProperty, StringProperty, IntProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper
from mathutils import Vector, Matrix, geometry
import mathutils
import os
from bpy.app import tempdir
from statistics import mean, stdev
from collections import defaultdict
from math import sqrt, pi, isclose
from mathutils.geometry import area_tri
import mathutils
import math

addon_name = "SMTH Smart Tools"

class MarkAssetOperator(Operator):
    bl_idname = "object.asset_mark"
    bl_label = "Mark As Asset"
    bl_description = "Mark As Asset selected objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.object
        
        if obj.asset_data:
            self.report({'INFO'}, f"'{obj.name}' is already marked as an asset.")
        else:
            bpy.ops.asset.mark()
            self.report({'INFO'}, f"'{obj.name}' has been marked as an asset.")
        
        return {'FINISHED'}

class RandomColorToggleOperator(Operator):
    bl_idname = "view3d.toggle_random_color"
    bl_label = "Toggle Random Color"
    bl_description = "Toggle Shading Random Color"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        shading = context.space_data.shading
        if shading.color_type == 'RANDOM':
            shading.color_type = 'OBJECT'
        else:
            shading.color_type = 'RANDOM'
        return {'FINISHED'}

class StatsToggleOperator(Operator):
    bl_idname = "view3d.toggle_stats"
    bl_label = "Toggle Stats"
    bl_description = "Toggle Scene Statistics"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.space_data.overlay.show_stats = not context.space_data.overlay.show_stats
        return {'FINISHED'}

class UV_OT_PackIslands(Operator):
    """Pack UV Islands for selected meshes"""
    bl_idname = "uv.pack_islands_custom"
    bl_label = "Pack UV Islands"
    bl_description = "Pack UV Islands for selected objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    rotate: bpy.props.BoolProperty(name="Rotate", default=True)
    scale: bpy.props.BoolProperty(name="Scale", default=True)
    margin: bpy.props.FloatProperty(name="Margin", default=0.05, min=0.0, max=1.0)

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                bpy.context.view_layer.objects.active = obj
                if obj.data.uv_layers.active:
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.uv.select_all(action='SELECT')
                    bpy.ops.uv.pack_islands(rotate=self.rotate, scale=self.scale, margin=self.margin)
        
        return {'FINISHED'}

class OBJECT_OT_CreateVertexColorLayers(Operator):
    bl_idname = "object.create_vertex_colors"
    bl_label = "Create Vertex Color Layers"
    bl_description = "Create RGBA Vertex Color Layers if they don't exist"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'WARNING'}, "Nessun oggetto mesh selezionato")
            return {'CANCELLED'}
        
        for obj in mesh_objects:
            # Rendi l'oggetto corrente attivo
            context.view_layer.objects.active = obj
            
            # Crea i singoli canali RGBA se non esistono
            color_layers = ["vertex_R", "vertex_G", "vertex_B", "vertex_A"]
            for color_layer_name in color_layers:
                if color_layer_name not in obj.data.vertex_colors:
                    obj.data.vertex_colors.new(name=color_layer_name)
            
            # Crea il layer RGBA combinato se non esiste
            if "vertex_RGBA" not in obj.data.vertex_colors:
                obj.data.vertex_colors.new(name="vertex_RGBA")
            
            # Imposta vertex_RGBA come layer di rendering attivo per l'oggetto corrente
            bpy.ops.geometry.color_attribute_render_set(name="vertex_RGBA")
        
        # Passa alla modalità Vertex Paint
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')
        
        self.report({'INFO'}, "Vertex color layers creati con successo")
        return {'FINISHED'}

class OBJECT_OT_CombineVertexColors(Operator):
    bl_idname = "object.combine_vertex_colors"
    bl_label = "Combine RGBA Vertex Colors"
    bl_description = "Combine existing R,G,B,A vertex color layers into RGBA layer"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'WARNING'}, "Nessun oggetto mesh selezionato")
            return {'CANCELLED'}
            
        bpy.ops.object.mode_set(mode='OBJECT')
        
        for obj in mesh_objects:
            # Verifica la presenza dei layer necessari
            required_layers = ["vertex_R", "vertex_G", "vertex_B", "vertex_A"]
            missing_layers = [layer for layer in required_layers if layer not in obj.data.vertex_colors]
            
            if missing_layers:
                self.report({'WARNING'}, 
                    f"L'oggetto {obj.name} non ha i seguenti layer di colore: {', '.join(missing_layers)}")
                continue
            
            # Crea o ottiene il layer RGBA
            if "vertex_RGBA" not in obj.data.vertex_colors:
                rgba_layer = obj.data.vertex_colors.new(name="vertex_RGBA")
            else:
                rgba_layer = obj.data.vertex_colors["vertex_RGBA"]
            
            # Ottiene i riferimenti ai layer esistenti
            r_layer = obj.data.vertex_colors["vertex_R"]
            g_layer = obj.data.vertex_colors["vertex_G"]
            b_layer = obj.data.vertex_colors["vertex_B"]
            a_layer = obj.data.vertex_colors["vertex_A"]
            
            # Combina i colori
            for poly in obj.data.polygons:
                for loop_index in poly.loop_indices:
                    r = r_layer.data[loop_index].color[0]
                    g = g_layer.data[loop_index].color[0]
                    b = b_layer.data[loop_index].color[0]
                    a = a_layer.data[loop_index].color[0]
                    rgba_layer.data[loop_index].color = (r, g, b, a)
            
            # Imposta il layer RGBA come quello di rendering
            bpy.context.view_layer.objects.active = obj
            bpy.ops.geometry.color_attribute_render_set(name="vertex_RGBA")
        
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')
        return {'FINISHED'}

def get_edge_lengths_3d(face):
    """Restituisce la lunghezza dei bordi della faccia nello spazio 3D."""
    return [edge.calc_length() for edge in face.edges]

def get_edge_lengths_uv(face, uv_layer):
    """Restituisce la lunghezza dei bordi della faccia nello spazio UV."""
    uvs = [loop[uv_layer].uv for loop in face.loops]
    
    if len(uvs) < 3:
        return []  # Evita calcoli inutili per poligoni non validi
    
    return [(uvs[i] - uvs[(i + 1) % len(uvs)]).length for i in range(len(uvs))]

def analyze_uv_stretch(threshold=0.1):
    # Salva la modalità corrente
    original_mode = bpy.context.object.mode if bpy.context.object else 'OBJECT'
    
    # Assicurati di essere in Object Mode per processare gli oggetti
    if original_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not selected_objects:
        print("Nessun oggetto mesh selezionato!")
        return
    
    # Deseleziona tutte le facce in tutti gli oggetti
    for obj in selected_objects:
        for polygon in obj.data.polygons:
            polygon.select = False
    
    for obj in selected_objects:
        print(f"\nAnalisi UV stretch per l'oggetto: {obj.name}")
        
        # Rendi l'oggetto corrente attivo
        bpy.context.view_layer.objects.active = obj
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        uv_layer = bm.loops.layers.uv.verify()
        if not uv_layer:
            print(f"L'oggetto {obj.name} non ha UV maps!")
            bm.free()
            continue
        
        stretched_faces = []
        for face in bm.faces:
            edge_lengths_3d = get_edge_lengths_3d(face)
            edge_lengths_uv = get_edge_lengths_uv(face, uv_layer)
            
            if not edge_lengths_3d or not edge_lengths_uv or len(edge_lengths_3d) != len(edge_lengths_uv):
                continue
            
            stretch_ratios = [(uv / max(1e-6, length_3d)) for uv, length_3d in zip(edge_lengths_uv, edge_lengths_3d)]
            avg_stretch = sum(stretch_ratios) / len(stretch_ratios)
            deviation = max(abs(r - avg_stretch) for r in stretch_ratios)
            
            if deviation > threshold:
                stretched_faces.append(face)
        
        for face in bm.faces:
            face.select = face in stretched_faces
        
        bm.to_mesh(obj.data)
        bm.free()
        
        obj.data.update()
    
    # Passa in Edit Mode alla fine dell'analisi
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='FACE')

class UV_OT_AnalyzeStretch(bpy.types.Operator):
    bl_idname = "uv.analyze_stretch"
    bl_label = "Analizza UV Stretch"
    bl_description = "Analizza lo stretching delle UV e seleziona le facce interessate"
    
    threshold: bpy.props.FloatProperty(
        name="Threshold",
        description="Soglia per la rilevazione dello stretch delle UV",
        default=0.05,
        min=0.0,
        max=1.0
    )
    
    def execute(self, context):
        analyze_uv_stretch(self.threshold)
        return {'FINISHED'}

class ToggleFaceOrientation(bpy.types.Operator):
    bl_idname = "view3d.enable_face_orientation"
    bl_label = "Enable or Disable Face Orientation"
    bl_description = "Enable or Disable Face Orientation"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':  
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_face_orientation = not space.overlay.show_face_orientation
                        space.shading.show_backface_culling = False                        
                        status = "ENABLED" if space.overlay.show_face_orientation else "DISABLED"
                        self.report({'INFO'}, f"Face Orientation {status}")
                        return {'FINISHED'}

        self.report({'ERROR'}, "No 3D View found")   
        return {'CANCELLED'}

class ToggleBackfaceCullingOperator(bpy.types.Operator):
    bl_idname = "view3d.toggle_backface_culling"
    bl_label = "Enable or Disable Backface Culling"
    bl_description = "Enable or Disable Backface Culling in Solid Mode"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.show_backface_culling = not space.shading.show_backface_culling
                        status = "ENABLED" if space.shading.show_backface_culling else "DISABLED"
                        self.report({'INFO'}, f"Backface Culling {status}")
                        return {'FINISHED'}

        self.report({'ERROR'}, "No 3D View found")
        return {'CANCELLED'}
    
class ZFightDetector(bpy.types.Operator):
    bl_idname = "object.zfight_detector"
    bl_label = "Check Z-Fight"
    bl_description = "Check Z-Fight on selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    threshold = 0.0001
    distance_threshold = 0.1

    def execute(self, context):
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

        for obj in selected_objects:
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
        
        problematic_faces, zfight_count = self.detect_zfights(selected_objects)

        for obj, faces in problematic_faces.items():
            for face in faces:
                face.select = True

        if selected_objects:
            context.view_layer.objects.active = selected_objects[0]
            bpy.ops.object.mode_set(mode='EDIT')
        
        print(f"Total number of faces with z-fighting: {zfight_count}")
        return {'FINISHED'}

    @staticmethod
    def get_face_vertices_world(obj, face):
        # Cache matrix multiplication
        matrix_world = obj.matrix_world
        mesh_vertices = obj.data.vertices
        return [matrix_world @ mesh_vertices[i].co for i in face.vertices]

    @staticmethod
    def get_face_props(vertices):
        # Compute the center as the average of the vertices
        num_vertices = len(vertices)
        center = sum(vertices, mathutils.Vector()) / num_vertices
        
        # Compute the normal using the first three vertices
        v1, v2, v3 = vertices[:3]
        edge1 = v2 - v1
        edge2 = v3 - v1
        normal = edge1.cross(edge2)
        normal_length = normal.length
        
        if normal_length > 0:
            normal /= normal_length  # Normalize only if the length is not zero
        
        # Compute the area using the cross product method
        area = 0
        for i in range(1, num_vertices - 1):
            edge1 = vertices[i] - vertices[0]
            edge2 = vertices[i + 1] - vertices[0]
            area += edge1.cross(edge2).length
        area *= 0.5  # The total area is half of the sum
        
        return center, normal, area

    def check_face_overlap(self, verts1, verts2, normal1, normal2):
        # First, check the alignment of the normals
        dot_product = abs(normal1.dot(normal2))
        if not isclose(dot_product, 1, rel_tol=self.threshold):
            return False

        # Choose the projection plane based on the dominant normal
        normal_components = (abs(normal1.x), abs(normal1.y), abs(normal1.z))
        max_component = max(normal_components)
        
        # Project the vertices onto the appropriate plane
        if normal_components[2] == max_component:  # z is dominant
            verts1_2d = [(v.x, v.y) for v in verts1]
            verts2_2d = [(v.x, v.y) for v in verts2]
        else:  # x or y are dominants
            verts1_2d = [(v.y, v.z) for v in verts1]
            verts2_2d = [(v.y, v.z) for v in verts2]

        # Calculate the 2D bounding boxes using list comprehension
        x_coords1, y_coords1 = zip(*verts1_2d)
        x_coords2, y_coords2 = zip(*verts2_2d)
        
        # Check overlap using min/max
        return not (max(x_coords1) < min(x_coords2) or 
                   min(x_coords1) > max(x_coords2) or 
                   max(y_coords1) < min(y_coords2) or 
                   min(y_coords1) > max(y_coords2))

    def detect_zfights(self, selected_objects):
        problematic_faces = {obj: set() for obj in selected_objects}
        zfight_count = 0

        # Precompute the face properties for all objects
        object_face_props = {}
        for obj in selected_objects:
            face_props = []
            matrix_world = obj.matrix_world  # Cache matrix
            mesh_vertices = obj.data.vertices  # Cache vertices
            
            for face in obj.data.polygons:
                verts = [matrix_world @ mesh_vertices[i].co for i in face.vertices]
                props = self.get_face_props(verts)
                face_props.append((face, verts, *props))
            object_face_props[obj] = face_props

        # Compare the faces between the objects
        for i, obj1 in enumerate(selected_objects):
            faces1_props = object_face_props[obj1]

            for obj2 in selected_objects[i + 1:]:
                faces2_props = object_face_props[obj2]

                for face1, verts1, center1, normal1, area1 in faces1_props:
                    for face2, verts2, center2, normal2, area2 in faces2_props:
                        # First, check the distance between the centers
                        if (center1 - center2).length > self.distance_threshold:
                            continue

                        # Check overlap and the distance along the normal
                        if self.check_face_overlap(verts1, verts2, normal1, normal2):
                            dist = abs(normal1.dot(center1 - center2))
                            if dist < self.threshold:
                                problematic_faces[obj1].add(face1)
                                problematic_faces[obj2].add(face2)
                                zfight_count += 2

        return problematic_faces, zfight_count

class UVTextureScaleCheckerOperator(Operator):
    bl_idname = "object.uv_texture_scale_checker"
    bl_label = "Check UV Texel Density"
    bl_description = "Check if UV islands match target texel density (1024) for 2048x2048 texture"
    bl_options = {'REGISTER', 'UNDO'}

    # Fixed values as class constants
    TARGET_TEXTURE_SIZE = 2048
    TARGET_DENSITY = 1024
    THRESHOLD = 1.0

    def calc_face_uv_area(self, face, uv_layer):
        """Calculate accurate UV area for a face"""
        uvs = [loop[uv_layer].uv for loop in face.loops]
        if len(uvs) < 3:
            return 0.0
        
        area = 0.0
        for i in range(len(uvs)):
            j = (i + 1) % len(uvs)
            area += uvs[i].x * uvs[j].y - uvs[j].x * uvs[i].y
        return abs(area) * 0.5

    def calc_texel_density(self, face, uv_layer):
        """Calculate texel density for a single face"""
        world_area = face.calc_area()
        if world_area == 0:
            return 0
            
        uv_area = self.calc_face_uv_area(face, uv_layer)
        if uv_area == 0:
            return 0
            
        texel_density = math.sqrt((uv_area * self.TARGET_TEXTURE_SIZE * self.TARGET_TEXTURE_SIZE) / world_area)
        return texel_density

    def find_connected_faces(self, start_face, uv_layer, threshold=0.0001):
        """Find UV connected faces with improved precision"""
        island = {start_face}
        to_process = {start_face}
        
        while to_process:
            face = to_process.pop()
            for edge in face.edges:
                for connected_face in edge.link_faces:
                    if connected_face not in island:
                        face_uvs = {tuple(loop[uv_layer].uv) for loop in face.loops}
                        connected_uvs = {tuple(loop[uv_layer].uv) for loop in connected_face.loops}
                        
                        for uv1 in face_uvs:
                            for uv2 in connected_uvs:
                                if (abs(uv1[0] - uv2[0]) < threshold and 
                                    abs(uv1[1] - uv2[1]) < threshold):
                                    island.add(connected_face)
                                    to_process.add(connected_face)
                                    break
        return island

    def get_uv_islands(self, bm, uv_layer):
        """Get all UV islands"""
        islands = []
        processed = set()
        
        for face in bm.faces:
            if face not in processed:
                island = self.find_connected_faces(face, uv_layer)
                islands.append(island)
                processed.update(island)
        
        return islands

    def calculate_island_density(self, island, uv_layer):
        """Calculate average density for an island"""
        total_density = 0
        total_area = 0
        
        for face in island:
            world_area = face.calc_area()
            density = self.calc_texel_density(face, uv_layer)
            
            if density > 0:
                total_density += density * world_area
                total_area += world_area
        
        if total_area == 0:
            return 0
            
        return total_density / total_area

    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_objects:
            self.report({'WARNING'}, "No selected mesh objects")
            return {'CANCELLED'}

        found_issues = False

        for obj in selected_objects:
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            
            uv_layer = bm.loops.layers.uv.active
            if not uv_layer:
                self.report({'WARNING'}, f"Object {obj.name} has no active UV layer")
                continue

            # Deselect all faces initially
            for face in bm.faces:
                face.select = False

            islands = self.get_uv_islands(bm, uv_layer)
            
            for island in islands:
                density = self.calculate_island_density(island, uv_layer)
                density_diff = abs((density - self.TARGET_DENSITY) / self.TARGET_DENSITY) * 100
                
                if density_diff > self.THRESHOLD:
                    found_issues = True
                    for face in island:
                        face.select = True
                    self.report({'INFO'}, 
                        f"Island in {obj.name}: "
                        f"Current density: {density:.0f}, "
                        f"Target: {self.TARGET_DENSITY}, "
                        f"Diff: {density_diff:.1f}%")

            bmesh.update_edit_mesh(obj.data)
            
            if not found_issues:
                self.report({'INFO'}, f"All UV islands in {obj.name} are within threshold")
                bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

class MeshNameChecker(bpy.types.Operator):
    bl_idname = "object.name_checker"
    bl_label = "Name Checker"
    bl_description = "Select only the objects that are selected and have a different name from their mesh data"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        mismatched_objects = []
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                if obj.name != obj.data.name:
                    mismatched_objects.append(obj)
                obj.select_set(False)  # Deselect All
                
        if mismatched_objects:
            for obj in mismatched_objects:
                obj.select_set(True) # Select Mismatched Objects
            context.view_layer.objects.active = mismatched_objects[0]
            self.report({"WARNING"}, f"{len(mismatched_objects)} selected objects with non-matching names.")
        else:
            self.report({"INFO"}, "All selected objects have correct names.")
            
        return {'FINISHED'}

class OBJECT_OT_fix_negative_scale(bpy.types.Operator):
    bl_idname = "object.fix_negative_scale"
    bl_label = "Fix Negative Scale"
    bl_description = "Apply negative scale, fix uvs and normals"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            self.report({'WARNING'}, "No Mesh selected")
            return {'CANCELLED'}
        
        for obj in selected_objects:
            context.view_layer.objects.active = obj
            
            # Save the original world matrix
            original_matrix_world = obj.matrix_world.copy()
            original_location = original_matrix_world.to_translation()
            
            # Save the origin position in the world coordinate system
            original_origin = obj.matrix_world @ mathutils.Vector((0, 0, 0))
            
            # Apply scale
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            
            # Enter Edit Mode
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            
            # Get Mesh datas in BMesh
            mesh = bmesh.from_edit_mesh(obj.data)
            
            # Check if UV Map existing
            if obj.data.uv_layers:
                uv_layer = mesh.loops.layers.uv.active
                for face in mesh.faces:
                    for loop in face.loops:
                        loop[uv_layer].uv.x = -loop[uv_layer].uv.x # Flip on X axis
            
            # Update mesh
            bmesh.update_edit_mesh(obj.data)
            
            # Flip Normals
            bpy.ops.mesh.flip_normals()
            
            # Enter Object Mode
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Restore the original position
            obj.location = original_location
            
            # Calculate and apply the necessary offset to restore the origin
            current_origin = obj.matrix_world @ mathutils.Vector((0, 0, 0))
            origin_offset = original_origin - current_origin
            
            # Move the origin while keeping the mesh position
            obj.data.transform(mathutils.Matrix.Translation(-origin_offset))
            obj.matrix_world.translation += origin_offset
            
        self.report({'INFO'}, "Flip normals and UVs for all selected objects")
        return {'FINISHED'}
    
class MeshToProcess(PropertyGroup):
    process: BoolProperty(
        name="Process Mesh",
        description="Decimate this mesh",
        default=True
    )
    name: StringProperty(default="")
    triangle_count: IntProperty(default=0)
    display_name: StringProperty(default="")

def get_triangle_count(obj):
    """Get triangle count for a mesh object."""
    try:
        mesh = obj.data
        count = sum(len(poly.vertices) - 2 for poly in mesh.polygons)
        return count
    except:
        return 0

def create_high_collection(original_collection):
    """Create or get _high collection for original meshes."""
    high_name = f"{original_collection.name}_high"
    high_collection = bpy.data.collections.get(high_name)

    if not high_collection:
        high_collection = bpy.data.collections.new(high_name)
        original_collection.children.link(high_collection)

    return high_collection

def move_original_to_high_collection(obj, high_collection):
    """Move the original object to the high collection and rename it."""
    original_name = obj.name
    obj.name = f"{original_name}_high"
    original_collection = obj.users_collection[0]
    original_collection.objects.unlink(obj)
    high_collection.objects.link(obj)
    return original_name

def create_object_copy(obj_high, original_collection, original_name):
    """Create a copy of the high object in the original collection."""
    obj_low = obj_high.copy()
    obj_low.data = obj_high.data.copy()
    obj_low.name = original_name  # Use the original name without suffix
    original_collection.objects.link(obj_low)
    return obj_low

def process_mesh(obj_high, obj_low):
    """Apply decimation and processing to a mesh."""
    try:
        batch_decimate_ratio = bpy.context.scene.batch_decimate_ratio

        bpy.context.view_layer.objects.active = obj_low
        obj_low.select_set(True)

        # Create edge protection
        vg = obj_low.vertex_groups.new(name="EdgeProtection")
        bm = bmesh.new()
        bm.from_mesh(obj_low.data)
        bm.edges.ensure_lookup_table()

        edge_verts = {v.index for e in bm.edges if e.is_boundary or e.seam for v in e.verts}
        if edge_verts:
            vg.add(list(edge_verts), 1.0, 'REPLACE')

        bm.free()

        # Add decimate modifier
        mod = obj_low.modifiers.new(name="Decimate", type='DECIMATE')
        mod.ratio = batch_decimate_ratio

        if "EdgeProtection" in obj_low.vertex_groups:
            mod.vertex_group = "EdgeProtection"
            mod.invert_vertex_group = True

        bpy.ops.object.modifier_apply(modifier=mod.name)

        # Add smooth modifier with edge protection
        if "EdgeProtection" in obj_low.vertex_groups:
            mod = obj_low.modifiers.new(name="Smooth", type='SMOOTH')
            mod.factor = 0.5
            mod.iterations = 4
            mod.vertex_group = "EdgeProtection"
            mod.invert_vertex_group = True
            bpy.ops.object.modifier_apply(modifier=mod.name)

        # Transfer data
        mod = obj_low.modifiers.new(name="NormalTransfer", type='DATA_TRANSFER')
        mod.object = obj_high
        mod.use_loop_data = True
        mod.data_types_loops = {'CUSTOM_NORMAL'}
        mod.loop_mapping = 'POLYINTERP_NEAREST'
        bpy.ops.object.modifier_apply(modifier=mod.name)

        if obj_high.data.uv_layers:
            if not obj_low.data.uv_layers:
                obj_low.data.uv_layers.new()
            mod = obj_low.modifiers.new(name="UVTransfer", type='DATA_TRANSFER')
            mod.object = obj_high
            mod.use_loop_data = True
            mod.data_types_loops = {'UV'}
            mod.loop_mapping = 'POLYINTERP_NEAREST'
            bpy.ops.object.modifier_apply(modifier=mod.name)

        obj_low.select_set(False)
        return True

    except Exception as e:
        print(f"Error during processing: {str(e)}")
        obj_low.select_set(False)
        return False

class MESH_OT_collection_batch_decimate(Operator):
    bl_idname = "mesh.collection_batch_decimate"
    bl_label = "Process Selected"
    bl_description = "Decimate collapse selected objects from collection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        collection = scene.collection_to_process

        if not collection:
            self.report({'WARNING'}, "No collection selected")
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')

        mesh_process_map = {obj: item.process
                          for obj in collection.objects
                          if obj.type == 'MESH'
                          for item in scene.meshes_to_process
                          if item.name == obj.name}

        high_collection = create_high_collection(collection)

        for obj, should_process in mesh_process_map.items():
            try:
                if should_process:
                    # Only move and process objects that are selected for processing
                    original_name = move_original_to_high_collection(obj, high_collection)
                    obj_low = create_object_copy(obj, collection, original_name)
                    
                    success = process_mesh(obj, obj_low)
                    if success:
                        reduction = (1 - len(obj_low.data.vertices)/len(obj.data.vertices))*100
                        self.report({'INFO'}, f"Processed: {original_name} - Reduction: {reduction:.1f}%")
                    else:
                        self.report({'WARNING'}, f"Error processing {original_name}, copied without changes")
                else:
                    # Skip objects that are not selected for processing
                    self.report({'INFO'}, f"Skipped: {obj.name}")

            except Exception as e:
                self.report({'WARNING'}, f"Error handling {obj.name}: {str(e)}")
                continue

        return {'FINISHED'}

def find_common_prefix(names):
    """Find the longest common prefix in a list of names"""
    if not names or len(names) == 1:
        return names if names else ""

    names.sort(key=len)
    first, second, *rest = names

    for i, char in enumerate(first):
        if char != second[i]:
            return first[:i]

    return find_common_prefix([first] + rest)

def get_display_name(full_name, common_prefix):
    if common_prefix and full_name.startswith(common_prefix):
        return full_name[len(common_prefix):]
    return full_name

def update_meshes_to_process(self, context):
    scene = context.scene
    if scene.collection_to_process:
        mesh_data = []
        mesh_names = []

        for obj in scene.collection_to_process.objects:
            if obj.type == 'MESH':
                tri_count = get_triangle_count(obj)
                mesh_data.append((obj.name, tri_count))
                mesh_names.append(obj.name)

        common_prefix = find_common_prefix(mesh_names)
        VIEW3D_PT_Panel69._common_prefix = common_prefix

        mesh_data.sort(key=lambda x: x[1], reverse=True)

        scene.meshes_to_process.clear()
        for i, (mesh_name, tri_count) in enumerate(mesh_data): # Added index i
            item = scene.meshes_to_process.add()
            item.name = mesh_name
            item.triangle_count = tri_count
            item.display_name = get_display_name(mesh_name, common_prefix)

            # Logic for automatic selection
            if i < 2:  # Select the first two
                item.process = True
            else:      # Deselect the rest
                item.process = False

class OBJECT_OT_select_objects_with_negative_scale(Operator):
    bl_idname = "object.select_objects_with_negative_scale"
    bl_label = "Find Object with negative scale"
    bl_description = "Select objects with negative scale"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
    
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        
        # Loop through all objects in the scene
        for obj in bpy.context.scene.objects:
            # Get the scale values of the object
            sx, sy, sz = obj.scale
            
            # Check if at least one of the scale values is negative
            if sx < 0 or sy < 0 or sz < 0:
                # Select object
                obj.select_set(True)
        return {'FINISHED'}
    
def is_face_flipped(face, uv_layer, epsilon=1e-6):
    """Determine if a face has mirrored UVs compared to the 3D space by comparing the sign of the area in 3D and in the UV space."""
    # Extract the first three vertices of the face
    v1, v2, v3 = (vert.co for vert in face.verts[:3])
    
    # Extract the first three UV vertices
    uv1, uv2, uv3 = (loop[uv_layer].uv for loop in face.loops[:3])
    
    # Calculate the 3D area using the cross product
    normal_3d = (v2 - v1).cross(v3 - v1)
    area_3d = normal_3d.length  # # Magnitude of the normal vector
    
    # Calculate the UV area using the determinant
    area_uv = (uv2.x - uv1.x) * (uv3.y - uv1.y) - (uv2.y - uv1.y) * (uv3.x - uv1.x)
    
    # Check if the face is degenerate
    if abs(area_3d) < epsilon or abs(area_uv) < epsilon:
        return False  # Almost flat face or collapsed UVs, consider it as not flipped
    
    # The face is flipped if the sign of the two areas is opposite
    return (area_3d < 0) != (area_uv < 0)

class MESH_OT_find_flip_UV(Operator):
    bl_idname = "mesh.find_flip_uv"
    bl_label = "Find Flipped UV"
    bl_description = "Find Flipped UV"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        # Get selected objects
        selected_objects = bpy.context.selected_objects

        for obj in selected_objects:
            # Ensure that the object is a mesh
            if obj.type != 'MESH':
                continue

            # Switch to Edit mode for the current object
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')

            # Create a BMesh from the object
            me = obj.data
            bm = bmesh.from_edit_mesh(me)
            bm.faces.ensure_lookup_table()

            # Check if the object has UV layers
            if not bm.loops.layers.uv:
                print(f"L'oggetto {obj.name} non ha layer UV")
                continue

            # Get the active UV layer
            uv_layer = bm.loops.layers.uv.verify()

            # Deselect all faces of the current object
            for f in bm.faces:
                f.select = False

            # Select the flipped faces of the current object
            flipped_count = 0
            for f in bm.faces:
                if is_face_flipped(f, uv_layer):
                    f.select = True
                    flipped_count += 1

            # Update the mesh of the current object
            bmesh.update_edit_mesh(me)
            bm.free()  # Free the BMesh

            print(f"Found {flipped_count} faces flipped in {obj.name}")

        return {'FINISHED'}

def get_uv_bounds(uv_coords):
    """Return the min/max bounding box of the UV coordinates"""
    min_uv = mathutils.Vector((min(uv.x for uv in uv_coords), min(uv.y for uv in uv_coords)))
    max_uv = mathutils.Vector((max(uv.x for uv in uv_coords), max(uv.y for uv in uv_coords)))
    return min_uv, max_uv

class MESH_OT_fix_flipped_uv_faces(bpy.types.Operator):
    bl_idname = "mesh.fix_uv_flipped"
    bl_label = "Fix Flipped UV"
    bl_description = "Fixes flipped UVs while maintaining the same position and scale"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        bpy.ops.object.mode_set(mode='EDIT')  # Enter in Edit Mode
        
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.faces.ensure_lookup_table()

        if not bm.loops.layers.uv:
            self.report({'WARNING'}, "The object does not have UV layers")
            return {'CANCELLED'}
        
        uv_layer = bm.loops.layers.uv.verify()
        flipped_faces = [f for f in bm.faces if is_face_flipped(f, uv_layer)]

        for f in flipped_faces:
            original_uvs = [loop[uv_layer].uv.copy() for loop in f.loops]
            min_orig, max_orig = get_uv_bounds(original_uvs)

            # Mirrors the UVs on the X axis relative to the center of the original bounding box
            center_x = (min_orig.x + max_orig.x) / 2
            for loop in f.loops:
                loop[uv_layer].uv.x = center_x - (loop[uv_layer].uv.x - center_x)

            # After the flip, calculate the new bounding box
            mirrored_uvs = [loop[uv_layer].uv.copy() for loop in f.loops]
            min_mirrored, max_mirrored = get_uv_bounds(mirrored_uvs)

            # Calculate the scale factor to maintain the same size
            scale_x = (max_orig.x - min_orig.x) / (max_mirrored.x - min_mirrored.x) if max_mirrored.x != min_mirrored.x else 1.0
            scale_y = (max_orig.y - min_orig.y) / (max_mirrored.y - min_mirrored.y) if max_mirrored.y != min_mirrored.y else 1.0

            # Scale the UVs to realign them with the original bounding box
            for loop in f.loops:
                loop[uv_layer].uv.x = min_orig.x + (loop[uv_layer].uv.x - min_mirrored.x) * scale_x
                loop[uv_layer].uv.y = min_orig.y + (loop[uv_layer].uv.y - min_mirrored.y) * scale_y
                    
        bmesh.update_edit_mesh(me)  # Update Mesh
        bpy.ops.object.mode_set(mode='OBJECT')  # Return in Object Mode
        self.report({'INFO'}, f"Fixed {len(flipped_faces)} flipped UV faces.")
        return {'FINISHED'}
    
def create_high_collection(original_collection):
    """Create or get _high collection for original meshes."""
    high_name = f"{original_collection.name}_high"
    high_collection = bpy.data.collections.get(high_name)
    
    if not high_collection:
        high_collection = bpy.data.collections.new(high_name)
        original_collection.children.link(high_collection)
    
    return high_collection

def create_edge_vertex_group(obj):
    """Create vertex group for boundary edges and seams."""
    vg = obj.vertex_groups.new(name="EdgeProtection")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    
    edge_verts = {v.index for e in bm.edges if e.is_boundary or e.seam for v in e.verts}
    if edge_verts:
        vg.add(list(edge_verts), 1.0, 'REPLACE')
    
    bm.free()
    return vg

def apply_decimation(obj, ratio=0.5):
    """Apply single-step decimation with given ratio."""
    mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
    mod.ratio = ratio
    
    if "EdgeProtection" in obj.vertex_groups:
        mod.vertex_group = "EdgeProtection"
        mod.invert_vertex_group = True
    
    bpy.ops.object.modifier_apply(modifier=mod.name)

def transfer_data(source, target):
    """Transfer normals and UVs from source to target."""
    # Transfer normals
    mod = target.modifiers.new(name="NormalTransfer", type='DATA_TRANSFER')
    mod.object = source
    mod.use_loop_data = True
    mod.data_types_loops = {'CUSTOM_NORMAL'}
    mod.loop_mapping = 'POLYINTERP_NEAREST'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    
    # Transfer UVs
    if source.data.uv_layers:
        if not target.data.uv_layers:
            target.data.uv_layers.new()
        
        mod = target.modifiers.new(name="UVTransfer", type='DATA_TRANSFER')
        mod.object = source
        mod.use_loop_data = True
        mod.data_types_loops = {'UV'}
        mod.loop_mapping = 'POLYINTERP_NEAREST'
        bpy.ops.object.modifier_apply(modifier=mod.name)

def move_original_to_high_collection(obj, high_collection):
    """Move the original object to the high collection and rename it."""
    original_name = obj.name
    obj.name = f"{original_name}_high"
    original_collection = obj.users_collection[0]
    original_collection.objects.unlink(obj)
    high_collection.objects.link(obj)
    return original_name

def decimate_mesh(obj_high, original_collection, original_name, batch_decimate_ratio=0.5):
    """Process a single mesh with decimation and data transfer."""
    # Create processed version in original collection
    obj_low = obj_high.copy()
    obj_low.data = obj_high.data.copy()
    obj_low.name = original_name
    original_collection.objects.link(obj_low)
    
    # Set as active object
    bpy.context.view_layer.objects.active = obj_low
    obj_low.select_set(True)
    
    # Create edge protection group
    create_edge_vertex_group(obj_low)
    
    # Apply single-step decimation
    apply_decimation(obj_low, batch_decimate_ratio)
    
    # Apply smooth modifier with edge protection
    if "EdgeProtection" in obj_low.vertex_groups:
        mod = obj_low.modifiers.new(name="Smooth", type='SMOOTH')
        mod.factor = 0.5
        mod.iterations = 4
        mod.vertex_group = "EdgeProtection"
        mod.invert_vertex_group = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    
    # Transfer data from original
    transfer_data(obj_high, obj_low)
    
    obj_low.select_set(False)
    return obj_low

class MESH_OT_batch_decimate(Operator):
    """Batch process selected meshes with decimation"""
    bl_idname = "mesh.batch_decimate"
    bl_label = "Decimate Collapse Meshes"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_meshes:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        
        # Process each mesh
        for obj in selected_meshes:
            try:
                # Get or create high collection
                original_collection = obj.users_collection[0]
                high_collection = create_high_collection(original_collection)
                
                # Move and rename original to high collection
                original_name = move_original_to_high_collection(obj, high_collection)
                
                # Process mesh
                obj_low = decimate_mesh(obj, original_collection, original_name, context.scene.decimate_ratio)
                
                self.report({'INFO'}, f"Processed: {original_name} - Reduction: {(1 - len(obj_low.data.vertices)/len(obj.data.vertices))*100:.1f}%")
                
            except Exception as e:
                self.report({'ERROR'}, f"Error processing {obj.name}: {str(e)}")
                return {'CANCELLED'}
        
        return {'FINISHED'}

class MESH_OT_batch_decimate_planar(Operator):
    """Batch process selected meshes with planar decimation"""
    bl_idname = "mesh.batch_decimate_planar"
    bl_label = "Decimate Planar Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not selected_meshes:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}

        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        # Process each mesh
        for obj in selected_meshes:
            try:
                # Get or create high collection
                original_collection = obj.users_collection[0]
                high_collection = create_high_collection(original_collection)
                
                # Move and rename original to high collection
                original_name = move_original_to_high_collection(obj, high_collection)
                
                # Create processed version
                obj_low = obj.copy()
                obj_low.data = obj.data.copy()
                obj_low.name = original_name
                original_collection.objects.link(obj_low)
                
                # Process the mesh with planar decimation
                bpy.context.view_layer.objects.active = obj_low
                obj_low.select_set(True)
                
                # Add planar decimation modifier
                mod = obj_low.modifiers.new(name="Decimate", type='DECIMATE')
                mod.decimate_type = 'DISSOLVE'
                mod.angle_limit = context.scene.planar_angle
                bpy.ops.object.modifier_apply(modifier=mod.name)
                
                # Transfer data from original to decimated mesh
                transfer_data(obj, obj_low)
                
                self.report({'INFO'}, f"Processed: {original_name} - Final faces: {len(obj_low.data.polygons)}")

            except Exception as e:
                self.report({'ERROR'}, f"Error processing {obj.name}: {str(e)}")
                return {'CANCELLED'}

        return {'FINISHED'}

class OBJECT_OT_RigidBodyAnimPath(Operator):
    bl_idname = "object.rigidbody_anim"
    bl_label = "Generate Rigid Body Animation Path"
    bl_description = "Generate Rigid Body Animation Path"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get all selected objects
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}

        start_frame = 0
        end_frame = bpy.context.scene.frame_end

        for obj in mesh_objects:
            # Create a new collection "path_<object_name>"
            collection_name = f"path_{obj.name}"
            path_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(path_collection)

            # Iterate over frames to get the object's position and rotation
            for frame in range(start_frame, end_frame + 1):
                bpy.context.scene.frame_set(frame)
                
                # Create a new object for this frame
                bpy.ops.mesh.primitive_cube_add(size=0.01)
                frame_obj = bpy.context.active_object
                frame_obj.name = f"{obj.name}_frame_{frame}"
                
                # Set the position and rotation
                frame_obj.matrix_world = obj.matrix_world.copy()
                
                # Remove the object from the current collection and add it to the "path_<object_name>" collection
                bpy.context.collection.objects.unlink(frame_obj)
                path_collection.objects.link(frame_obj)
                
                # Remove all vertices to leave the object empty
                mesh = frame_obj.data
                mesh.clear_geometry()
                
        return {'FINISHED'}
    
class OBJECT_OT_VertexColorWind(Operator):
    bl_idname = "object.vertex_color"
    bl_label = "Generate Spherical Vertex Color RGBA Attribute"
    bl_description = "Generate Spherical Vertex Color RGBA Attribute"
    bl_options = {'REGISTER', 'UNDO'}
    
    min_weight: bpy.props.FloatProperty(
        name="Minimum Weight",
        description="Minimum weight value for the gradient",
        default=0.0,
        min=-10.0,
        max=10.0
    )
    
    max_weight: bpy.props.FloatProperty(
        name="Maximum Weight",
        description="Maximum weight value for the gradient",
        default=1.0,
        min=-10.0,
        max=10.0
    )
    
    falloff_power: bpy.props.FloatProperty(
        name="Falloff Power",
        description="Power of the falloff curve (1.0 = linear, >1.0 = sharper, <1.0 = smoother)",
        default=1.0,
        min=0.1,
        max=10.0
    )
    
    def execute(self, context):
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'WARNING'}, "NO MESH SELECTED")
            return {'CANCELLED'}
            
        if self.max_weight <= self.min_weight:
            self.report({'ERROR'}, "Maximum weight must be greater than minimum weight")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')
        
        for obj in mesh_objects:
            context.view_layer.objects.active = obj

            if len(obj.vertex_groups) == 0:
                vgroup = obj.vertex_groups.new(name="Spherical Gradient")
            else:
                vgroup = obj.vertex_groups[0]   
            
            # Calculate the effective center of the mesh on the XY plane
            mesh = obj.data
            center_xy = mathutils.Vector((0, 0, 0))
            min_z = float('inf')
            max_z = float('-inf')
            
            # First pass: find the XY center and the Z limits
            for v in mesh.vertices:
                center_xy.x += v.co.x
                center_xy.y += v.co.y
                min_z = min(min_z, v.co.z)
                max_z = max(max_z, v.co.z)
            
            num_vertices = len(mesh.vertices)
            center_xy.x /= num_vertices
            center_xy.y /= num_vertices
            
            # The origin point of the gradient will be centered at XY and at the lowest point in Z
            gradient_origin = mathutils.Vector((center_xy.x, center_xy.y, min_z))
            
            # Calculate the maximum distance from the origin point to normalize the gradient
            max_distance = 0
            for v in mesh.vertices:
                # Calculate distance from origin point
                distance = (v.co - gradient_origin).length
                max_distance = max(max_distance, distance)
            
            if max_distance == 0:
                self.report({'WARNING'}, f"The object {obj.name} has all vertices in the center. A spherical gradient cannot be applied.")
                continue
            
            # Calculate the total height of the object
            height = max_z - min_z
            
            # Apply the normalized spherical gradient with custom parameters
            for v in mesh.vertices:
                # Calculate the distance from the origin point
                distance = (v.co - gradient_origin).length
                
                # Normalize distance (0-1)
                normalized_distance = distance / max_distance
                
                # Apply power falloff
                if self.falloff_power != 1.0:
                    normalized_distance = normalized_distance ** self.falloff_power
                
                # Reverse the normalized value (1-0 instead of 0-1)
                normalized_distance = normalized_distance
                
                # Calculate the final weight
                weight = normalized_distance
                weight = self.min_weight + (self.max_weight - self.min_weight) * weight
                
                # Make sure the weight is within the correct range
                weight = max(min(weight, self.max_weight), self.min_weight)

                vgroup.add([v.index], weight, 'REPLACE')
            
            obj.data.update()
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            obj.vertex_groups.active_index = vgroup.index

            if not obj.data.vertex_colors:
                obj.data.vertex_colors.new(name="vertex_R")
            else:
                obj.data.vertex_colors[0].name = "vertex_R"

            color_layers = ["vertex_G", "vertex_B", "vertex_A"]
            for color_layer_name in color_layers:
                if color_layer_name not in obj.data.vertex_colors:
                    obj.data.vertex_colors.new(name=color_layer_name)

        bpy.ops.object.mode_set(mode='VERTEX_PAINT')
        for obj in mesh_objects:
            if "vertex_R" in obj.data.vertex_colors:
                obj.data.vertex_colors.active = obj.data.vertex_colors["vertex_R"]
                bpy.context.view_layer.objects.active = obj
                bpy.ops.paint.vertex_color_from_weight()
            else:
                self.report({'ERROR'}, f"The object {obj.name} does not have a color layer called 'vertex_R'.")

        for obj in mesh_objects:
            if "vertex_RGBA" not in obj.data.vertex_colors:
                rgba_layer = obj.data.vertex_colors.new(name="vertex_RGBA")
            else:
                rgba_layer = obj.data.vertex_colors["vertex_RGBA"]
            
            r_layer = obj.data.vertex_colors.get("vertex_R")
            g_layer = obj.data.vertex_colors.get("vertex_G")
            b_layer = obj.data.vertex_colors.get("vertex_B")
            a_layer = obj.data.vertex_colors.get("vertex_A")
            
            if not (r_layer and g_layer and b_layer and a_layer):
                self.report({'ERROR'}, f"One or more color channels are missing in '{obj.name}'.")
                continue

            for poly in obj.data.polygons:
                for loop_index in poly.loop_indices:
                    r = r_layer.data[loop_index].color[0]
                    g = g_layer.data[loop_index].color[0]
                    b = b_layer.data[loop_index].color[0]
                    a = a_layer.data[loop_index].color[0]
                    rgba_layer.data[loop_index].color = (r, g, b, a)

        bpy.ops.object.mode_set(mode='VERTEX_PAINT')
        for obj in mesh_objects:
            bpy.ops.geometry.color_attribute_render_set(name="vertex_RGBA")

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
        
        # Add Geometry Nodes modifier
        geonodes = obj.modifiers.new(name="GeometryNodes", type='NODES')
        bpy.ops.node.new_geometry_node_group_assign()
        geonodes.node_group.name = 'AnimPath'
        
        # Access the nodes and connections of the node group
        nodes = geonodes.node_group.nodes
        links = geonodes.node_group.links
        
        # Create the necessary nodes
        input_node = nodes.new('NodeGroupInput')
        output_node = nodes.new('NodeGroupOutput')
        mesh_to_curve_node = nodes.new('GeometryNodeMeshToCurve')
        curve_resample = nodes.new('GeometryNodeResampleCurve')
        instance_on_points = nodes.new('GeometryNodeInstanceOnPoints')
        add_cube = nodes.new('GeometryNodeMeshCube')
        align_rotation_to_vector = nodes.new('FunctionNodeAlignRotationToVector')
        curve_tangent = nodes.new('GeometryNodeInputTangent')
        
        # Place the nodes
        input_node.location = (-200, 0)
        mesh_to_curve_node.location = (0, 0)
        curve_resample.location = (200, 0)
        instance_on_points.location = (400, 0)
        add_cube.location = (200, 300)
        align_rotation_to_vector.location = (200, -200)
        curve_tangent.location = (0, -200)
        output_node.location = (600, 0)
        
        # Connect the nodes
        links.new(input_node.outputs[0], mesh_to_curve_node.inputs['Mesh'])
        links.new(mesh_to_curve_node.outputs['Curve'], curve_resample.inputs['Curve'])
        links.new(curve_resample.outputs['Curve'], instance_on_points.inputs['Points'])
        links.new(add_cube.outputs['Mesh'], instance_on_points.inputs['Instance'])
        links.new(curve_tangent.outputs['Tangent'], align_rotation_to_vector.inputs['Vector'])
        links.new(align_rotation_to_vector.outputs['Rotation'], instance_on_points.inputs['Rotation'])
        links.new(instance_on_points.outputs['Instances'], output_node.inputs[0])
        
        # Set up node parameters
        curve_resample.inputs['Count'].default_value = self.curve_resample_count
        add_cube.inputs[1].default_value = 1
        add_cube.inputs[2].default_value = 1
        add_cube.inputs[3].default_value = 1
        align_rotation_to_vector.axis = 'Y'
        align_rotation_to_vector.pivot_axis = 'Z'
        
        # Remove only the first input and output node
        for node in nodes:
            if node.type == 'GROUP_INPUT':
                nodes.remove(node)
                break
        for node in nodes:
            if node.type == 'GROUP_OUTPUT':
                nodes.remove(node)
                break

        # Realize duplicates
        bpy.ops.object.duplicates_make_real()

        # Remove all modifiers from selected objects and the active object
        selected_objects = bpy.context.selected_objects
        active_obj = bpy.context.active_object

        # Make sure the active object is included in the selected objects
        if active_obj not in selected_objects:
            selected_objects.append(active_obj)

        # Remove modifiers from all selected objects
        for obj in selected_objects:
            for mod in obj.modifiers:
                obj.modifiers.remove(mod)

        # Enter Edit mode and delete all the meshes inside the objects
        for obj in selected_objects:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.delete(type='VERT')
            bpy.ops.object.mode_set(mode='OBJECT')

        # Create a new collection called "NPC path"
        new_collection = bpy.data.collections.new("NPC path")
        bpy.context.scene.collection.children.link(new_collection)
        
        # Move empty objects to the new collection
        for obj in selected_objects:
            if len(obj.data.vertices) == 0:  # Check if the object is empty
                # Link the item to the new collection
                new_collection.objects.link(obj)
                # Remove the object from the main collection (scene collection)
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
    bl_description = "Merge duplicate materials across the entire file"
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
        # Dictionary to track material replacements
        material_map = {}
        
        # Iterate over all materials in the file
        for material in bpy.data.materials:
            material_base = self.find_material_base(material)
            if material_base and material_base != material:
                material_map[material] = material_base
        
        # Apply material replacements
        for obj in bpy.data.objects:
            for slot in obj.material_slots:
                if slot.material in material_map:
                    slot.material = material_map[slot.material]
        
        # Remove orphaned materials
        for material in list(bpy.data.materials):
            if material.users == 0:
                bpy.data.materials.remove(material)

        return {'FINISHED'}
    
def copy_modifiers(source_obj, target_obj):
    """Copia i modificatori da un oggetto all'altro."""
    for mod in source_obj.modifiers:
        new_mod = target_obj.modifiers.new(name=mod.name, type=mod.type)
        for attr in dir(mod):
            if attr.startswith("__") or attr in {'name', 'type', 'bl_rna'}:
                continue
            try:
                setattr(new_mod, attr, getattr(mod, attr))
            except AttributeError:
                pass  # Ignora gli attributi che non possono essere copiati

class OBJECT_OT_SeparateByVertexGroup(Operator):
    bl_idname = "object.vertex_group_separate"
    bl_label = "Separate Vertex Group"
    bl_description = "Separate mesh by Vertex Group"
    bl_options = {'REGISTER', 'UNDO'}
    
    def clean_empty_vertex_groups(self, obj):
        # Remove empty vertex groups
        empty_groups = []
        for group in obj.vertex_groups:
            if not any(group.index in [vg.group for vg in v.groups] for v in obj.data.vertices):
                empty_groups.append(group.name)
        
        for group_name in empty_groups:
            group = obj.vertex_groups.get(group_name)
            if group:
                obj.vertex_groups.remove(group)
                
        return empty_groups
    
    def rename_mesh_data(self, obj):
        # Rename the mesh data to match the object name
        if obj.data:
            obj.data.name = obj.name

    def execute(self, context):
        view_layer = context.view_layer
        
        # Filter only visible mesh objects from selection
        selection = [obj for obj in context.selected_objects 
                    if obj.type == 'MESH' and 
                    not obj.hide_viewport and 
                    not obj.hide_get()]
        
        if not selection:
            self.report({'WARNING'}, "NO VISIBLE MESH OBJECTS SELECTED")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Keep track of all created objects
        processed_objects = []
        
        for obj in selection:
            if not obj.vertex_groups:
                self.report({'WARNING'}, f"NO VERTEX GROUPS IN OBJECT: {obj.name}")
                continue
            
            original_name = obj.name
            
            # Clean empty groups from original object
            empty_groups = self.clean_empty_vertex_groups(obj)
            
            if empty_groups:
                self.report({'INFO'}, f"EMPTY GROUPS SKIPPED IN {obj.name}: {', '.join(empty_groups)}")
            
            if len(obj.vertex_groups) <= 1:
                self.rename_mesh_data(obj)
                processed_objects.append(obj)
                continue
            
            # Find if there's a vertex group with the same name as the object
            matching_group = None
            for group in obj.vertex_groups:
                if group.name == original_name:
                    matching_group = group
                    break
            
            # Process vertex groups
            while len(obj.vertex_groups) > 1:
                view_layer.objects.active = obj
                
                # Choose which group to process
                if matching_group and len(obj.vertex_groups) == 2:
                    group = obj.vertex_groups[0] if obj.vertex_groups[0] != matching_group else obj.vertex_groups[1]
                else:
                    group = next(g for g in obj.vertex_groups if g != matching_group)
                
                group_name = group.name
                
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='DESELECT')
                
                # Select vertices in current group
                obj.vertex_groups.active_index = group.index
                bpy.ops.object.vertex_group_select()
                
                # Separate selected vertices
                bpy.ops.mesh.separate(type='SELECTED')
                bpy.ops.object.mode_set(mode='OBJECT')
                
                # Find the new object (it will be the last selected)
                new_obj = context.selected_objects[-1]
                
                # Remove the processed vertex group from original object
                obj.vertex_groups.remove(group)
                
                # Rename the new object
                new_obj.name = group_name
                
                # Clean empty vertex groups from new object
                self.clean_empty_vertex_groups(new_obj)
                
                # Rename mesh data
                self.rename_mesh_data(new_obj)
                
                processed_objects.append(new_obj)
                
                # Deselect all objects except the original
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                view_layer.objects.active = obj
            
            # Clean and rename the original object's mesh data
            self.clean_empty_vertex_groups(obj)
            self.rename_mesh_data(obj)
            processed_objects.append(obj)
        
        # Final cleanup and rename for all processed objects
        for obj in processed_objects:
            if obj.type == 'MESH':
                self.clean_empty_vertex_groups(obj)
                self.rename_mesh_data(obj)
        
        return {'FINISHED'}
    
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
    """Export selected objects as separate OBJ files per collection"""
    bl_idname = "export_scene.batch_obj"
    bl_label = "Multiple Export OBJ's"
    bl_options = {'PRESET', 'UNDO'}
    
    filename_ext = ".obj"

    def execute(self, context):
        print('Multiple Export objects as OBJ files started!')

        wm = bpy.context.window_manager
        basedir = os.path.dirname(self.filepath)

        if not basedir:
            self.report({'ERROR'}, "Blend file is not saved")
            return {'CANCELLED'}

        view_layer = bpy.context.view_layer
        obj_active = view_layer.objects.active
        selection = bpy.context.selected_objects
        
        collection_objects = {}
        
        for obj in selection:
            for collection in obj.users_collection:
                if collection.name not in collection_objects:
                    collection_objects[collection.name] = []
                collection_objects[collection.name].append(obj)
        
        tot = len(collection_objects)
        wm.progress_begin(0, tot)
        progress = 0
        
        for collection_name, objects in collection_objects.items():
            bpy.ops.object.select_all(action='DESELECT')
            
            for obj in objects:
                obj.select_set(True)
                obj.data.name = obj.name  # Ensure mesh name matches object name
            
            file_path = os.path.join(basedir, collection_name + self.filename_ext)
            
            bpy.ops.wm.obj_export(filepath=file_path, export_selected_objects=True, export_materials=False, filter_glob="*.obj")
            print("Written:", file_path)
            
            progress += 1
            wm.progress_update(progress)
        
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
            modifier = obj.modifiers.new(name="Subdivision", type='SUBSURF')
            modifier.levels = 1  # Livelli di suddivisione in viewport
            modifier.render_levels = 2  # Livelli di suddivisione in rendering

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
            bpy.context.view_layer.objects.active = obj  # Assicura che l'oggetto sia attivo
            bpy.ops.object.mode_set(mode='OBJECT')  # Assicurati di essere in Object Mode
            modifier = obj.modifiers.new(name="Bevel", type='BEVEL')
            modifier.miter_outer = 'MITER_ARC'
            modifier.limit_method = 'WEIGHT'
            modifier.segments = 2
            modifier.width = 0.02

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
                bpy.ops.mesh.reveal()
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

class OBJECT_OT_GLBExport(Operator, ExportHelper):
    bl_idname = "export_scene.batch_glb"
    bl_label = "GLB Export"
    bl_description = "Export GLB from selected objects or entire collection of active object"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".glb"

    def execute(self, context):
        wm = bpy.context.window_manager
        scene = context.scene
        basedir = os.path.dirname(self.filepath)

        if not basedir:
            raise Exception("Blend file is not saved")

        view_layer = bpy.context.view_layer
        obj_active = view_layer.objects.active
        selection = bpy.context.selected_objects[:]
        
        if scene.export_entire_collection and obj_active:
            collection = obj_active.users_collection[0] if obj_active.users_collection else None
            if collection:
                objects_to_export = list(collection.objects)
            else:
                self.report({'WARNING'}, "Active object has no collection, exporting selection instead.")
                objects_to_export = selection
        else:
            objects_to_export = selection

        tot = len(objects_to_export)
        progress = 0
        wm.progress_begin(0, tot)

        bpy.ops.object.select_all(action='DESELECT')

        # Group objects by collection for export
        collection_objects = {}
        for obj in objects_to_export:
            for collection in obj.users_collection:
                if not collection.hide_viewport:
                    # Escludi le collezioni che terminano con "_high"
                    if scene.exclude_high_collections and collection.name.endswith("_high"):
                        continue
                    if collection.name not in collection_objects:
                        collection_objects[collection.name] = []
                    collection_objects[collection.name].append(obj)

        for collection_name, objects in collection_objects.items():
            bpy.ops.object.select_all(action='DESELECT')
            
            for obj in objects:
                obj.select_set(True)
                mesh = obj.data
                mesh.name = obj.name
            
            fn = os.path.join(basedir, collection_name + self.filename_ext)
            
            bpy.ops.export_scene.gltf(
                filepath=fn,
                export_format='GLB',
                export_apply=scene.export_apply,
                export_draco_mesh_compression_enable=scene.export_draco_mesh_compression_enable,
                export_draco_mesh_compression_level=scene.export_draco_mesh_compression_level,
                export_draco_position_quantization=scene.export_draco_position_quantization,
                export_draco_normal_quantization=scene.export_draco_normal_quantization,
                export_draco_texcoord_quantization=scene.export_draco_texcoord_quantization,
                export_draco_color_quantization=scene.export_draco_color_quantization,
                export_draco_generic_quantization=scene.export_draco_generic_quantization,
                export_materials=scene.export_materials,
                export_animations=scene.export_animations,
                export_skins=scene.export_skins,
                use_selection=True,
                use_active_scene=True
            )
            
            print("Written:", fn)

        view_layer.objects.active = obj_active
        
        # Restore previous selection if entire collection was exported
        bpy.ops.object.select_all(action='DESELECT')
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
                    image_path = os.path.join(addon_dir,"SMTH_Smart_Tools", "resources", 'UV_checker_GRID.png').replace("\\", "/")

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
                    image_path = os.path.join(addon_dir,"SMTH_Smart_Tools", "resources", 'UV_checker_LINE.png').replace("\\", "/")

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
    bl_description = "Bake Ambient Occlusion for selected objects (1024 samples)"

    def execute(self, context):
        selected_objects = bpy.context.selected_objects

        # Cycle for all selected objects
        for obj in selected_objects:
            
            # Check UV set
            if obj.type == 'MESH':
                if len(obj.data.uv_layers) > 1:
                    
                    # Set Bake Settings
                    bpy.context.scene.render.engine = 'CYCLES'
                    bpy.context.scene.cycles.samples = 1024
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
            
            # Check if Auto Smooth modifier exists and get its name
            smooth_modifier = None
            for mod in obj.modifiers:
                if mod.name == "Smooth by Angle" or (mod.name.startswith("Smooth by Angle.") and mod.name[-3:].isdigit()):
                    smooth_modifier = mod
                    break
            
            # Check if Weighted Normal modifier already exists
            modifier_weight_exists = any(mod.type == 'WEIGHTED_NORMAL' for mod in obj.modifiers)
            
            if not modifier_weight_exists:
                # Add Weighted Normal Modifier 
                weighted_normal_modifier = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
                weighted_normal_modifier.weight = 100
                weighted_normal_modifier.keep_sharp = True
                bpy.context.object.modifiers["WeightedNormal"].use_pin_to_last = True
            else:
                bpy.context.object.modifiers["WeightedNormal"].weight = 100
                bpy.context.object.modifiers["WeightedNormal"].keep_sharp = True 
                bpy.context.object.modifiers["WeightedNormal"].thresh = 0.01
                bpy.context.object.modifiers["WeightedNormal"].mode = 'FACE_AREA' 
                bpy.context.object.modifiers["WeightedNormal"].use_face_influence = False
                
            if not smooth_modifier:
                bpy.ops.object.shade_auto_smooth()
                # Get the newly created modifier
                for mod in obj.modifiers:
                    if mod.name == "Smooth by Angle" or (mod.name.startswith("Smooth by Angle.") and mod.name[-3:].isdigit()):
                        smooth_modifier = mod
                        break

            # Set use_pin_to_last for the smooth modifier
            if smooth_modifier:
                smooth_modifier.use_pin_to_last = True

            # Clear custom split normal data
            if obj.type == 'MESH':
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
                bpy.ops.object.mode_set(mode='OBJECT')
                
                # Set use_pin_to_last to False for the smooth modifier
                if smooth_modifier:
                    smooth_modifier.use_pin_to_last = False
        
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

                # Check if the UV layer [1] exists, otherwise create it
                if len(mesh.uv_layers) < 2:
                    mesh.uv_layers.new(name="UVMap_1")

                # Enable the UV layer [1]
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
        
class VIEW3D_PT_Panel69(Panel):
    bl_label = "Mesh Optimization"
    bl_idname = "VIEW3D_PT_Panel69"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SMTH'
    bl_options = {'DEFAULT_CLOSED'}
    
    _common_prefix = ""
    _mesh_items = []
    
    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def draw(self, context):        
        layout = self.layout
        
        col = layout.column()
        col.label(text='Collapse Decimate Meshes:')
        
        box69 = col.box()
        
        scene = context.scene        

        box69.prop(scene, "decimate_ratio", text="Decimate Ratio", slider=True)
        box69.operator("mesh.batch_decimate", icon = 'MOD_DECIM')
        
        col = layout.column()
        col.label(text='Planar Decimate Meshes:')
        
        box = col.box()
        
        scene = context.scene    
        
        box.prop(scene, "planar_angle", text="Angle Threshold (degrees)", slider=True)
        box.operator("mesh.batch_decimate_planar", icon = 'MOD_DECIM')

        col.label(text='Collapse Decimate Collection:')
        
        scene = context.scene
        
        box70 = col.box()
        
        box70.prop(scene, "collection_to_process", text='', icon='COLLECTION_COLOR_05')
        box70.prop(scene, "batch_decimate_ratio", slider=True)
        box70.separator()
        
        if scene.collection_to_process:
            if self._common_prefix:
                box70.label(text=f"Common Prefix: {self._common_prefix}")
                box70.separator()
            
            for item in scene.meshes_to_process:
                row = box70.row()
                row.scale_x = 1.0
                
                row.prop(item, "process", text="")
                
                split = row.split(factor=0.4)
                split.label(text=f"{item.triangle_count:,}")
                split.label(text=item.display_name)
        
        box70.operator("mesh.collection_batch_decimate", text="Decimate", icon = 'MOD_DECIM')

# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel_Controller(Panel):
    bl_label = "Controller"
    bl_idname = "VIEW3D_PT_panel_controller"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CONTROLLER"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout

        # Main panel
        col = layout.column()
        
        col.label(text='Helper:')
        
        # Create a box
        box = col.box()
        
        box.operator("object.classic_material", text='Flat Material', icon='MATERIAL')
        box.operator("object.reflection_checker", text='Reflection Checker', icon='SHADING_RENDERED')
        
        # First Panel in the first Box
        row = box.row()
        row.operator("object.uv_checker_grid", text="UV GRID", icon='TEXTURE_DATA')
        row.operator("object.uv_checker_line", text="UV LINE", icon='ALIGN_JUSTIFY')

        # Add Slider UV Repeat in the first box
        box.prop(context.scene, "mapping_scale_property", text="UV Repeat")

        # Add "Apply Repeat" button in the first box
        box.operator("object.apply_mapping_scale", text="Apply Repeat", icon='CHECKMARK')
        
        col.label(text='Various:')

        # Create a box
        box = col.box()
        
        icon = 'CHECKBOX_HLT' if context.space_data.overlay.show_stats else 'CHECKBOX_DEHLT'
        box.operator("view3d.toggle_stats", text = 'Toggle Scene Stats', icon = icon)
        
        icon7 = 'CHECKBOX_HLT' if context.space_data.shading.color_type == 'RANDOM' else 'CHECKBOX_DEHLT'
        box.operator("view3d.toggle_random_color", text='Toggle Random Color', icon=icon7)
        
        face_orientation_active = any(
            space.overlay.show_face_orientation 
            for area in bpy.context.screen.areas if area.type == 'VIEW_3D'
            for space in area.spaces if space.type == 'VIEW_3D'
        )
        icon = 'RECORD_ON' if face_orientation_active else 'RECORD_OFF'
        
        box.operator("view3d.enable_face_orientation", text = 'Toggle Face Orientation', icon=icon)
        
        space = context.space_data
        
        # Check if Backface Culling is enabled
        is_backface_culling_enabled = space.shading.show_backface_culling

        # Display a dynamic icon based on the status
        icon01 = 'RADIOBUT_ON' if is_backface_culling_enabled else 'RADIOBUT_OFF'
        
        box.operator("view3d.toggle_backface_culling", text = 'Toggle Backface Culling', icon=icon01)
               
        col.label(text='UV Check:')

        box = col.box()
        
        box.operator("uv.analyze_stretch", text = 'Find UV Stretched', icon = 'VIEW_PERSPECTIVE')
        
        box = col.box()
        
        box.operator("mesh.find_flip_uv", text = 'Find UV Flipped', icon = 'STICKY_UVS_LOC')
        box.operator("mesh.fix_uv_flipped", text = 'Fix UV Flipped', icon = 'UV_SYNC_SELECT')
        
        col.label(text='World Scale UV Check:')
        
        box = col.box()
        
        box.operator("object.uv_texture_scale_checker", text = 'Check World Scale UV', icon = 'STICKY_UVS_VERT')
        box.operator("object.auto_scale_uv", text = 'World Scale UV', icon = 'UV_DATA')
        
        col.label(text='Name Check:')
        
        box = col.box()
        
        box.operator("object.name_checker", text="Wrong Name Meshes", icon='FONTPREVIEW')
        box.operator("object.rename_meshes", text="Rename Meshes", icon='SORTALPHA')
        
        col.label(text='Z-Fight Check:')
        
        box = col.box()
        
        box.operator("object.zfight_detector", text = 'Check Z-Fight', icon = 'AREA_SWAP')
        
# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel66(Panel):
    bl_label = "Edugame"
    bl_idname = "VIEW3D_PT_panel66"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "EDUGAME"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Main panel
        col = layout.column()
        
        col.label(text='Various:')

        # Create a box
        box66 = col.box()
        
        box66.operator("object.purge_orphans", text = 'Purge Unused Data', icon = 'ORPHAN_DATA')
        
        box66.operator("object.asset_mark", text = 'Mark As Asset', icon = 'ASSET_MANAGER')
        
        col = layout.column()
        
        col.label(text='Path:')

        # Create a box
        box66 = col.box()
        
        box66.operator("object.anim_path_npc", text = 'NPC Anim Path', icon = 'GP_ONLY_SELECTED')
        box66.operator("object.rigidbody_anim", text = 'Rigid Body Anim Path', icon = 'ONIONSKIN_ON')
        
        col = layout.column()
        
        col.label(text='Vertex Colors:')

        # Create a box
        box66 = col.box()
        
        box66.operator("object.create_vertex_colors", text = 'Create Vertex Color Channels RGBA', icon = 'COLOR')
        box66.operator("object.vertex_color", text = 'Radial Vertex Color Gradient RGBA', icon = 'FORCE_WIND')
        box66.operator("object.combine_vertex_colors", text = 'Combine Vertex Color RGBA', icon = 'GROUP_VERTEX')
        

# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel00(Panel):
    bl_label = "Modeling"
    bl_idname = "VIEW3D_PT_panel00"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Main panel
        col = layout.column()
        
        col.label(text='Various:')

        # Create a box
        box6 = col.box()
        
        box6.operator("object.purge_orphans", text = 'Purge Unused Data', icon = 'ORPHAN_DATA')
        box6.operator("object.add_mirror_modifier", text = 'Auto Mirror', icon = 'MOD_MIRROR')
        box6.operator("object.zfight_detector", text = 'Check Z-Fight', icon = 'AREA_SWAP')
               
        col.label(text='Negative Scale:')
        
        # Create a box
        box6 = col.box()
        
        box6.operator("object.select_objects_with_negative_scale", text = 'Select Negative Scale Objects', icon = 'GROUP_BONE')
        box6.operator("object.fix_negative_scale", text = 'Fix Negative Scale Objects', icon = 'BONE_DATA')
        
        col.label(text='Helper:')
        
        # Create a box
        box6 = col.box()
        
        icon = 'CHECKBOX_HLT' if context.space_data.overlay.show_stats else 'CHECKBOX_DEHLT'
        box6.operator("view3d.toggle_stats", text = 'Toggle Scene Stats', icon = icon)
        
        icon7 = 'CHECKBOX_HLT' if context.space_data.shading.color_type == 'RANDOM' else 'CHECKBOX_DEHLT'
        box6.operator("view3d.toggle_random_color", text='Toggle Random Color', icon=icon7)
        
        face_orientation_active = any(
            space.overlay.show_face_orientation 
            for area in bpy.context.screen.areas if area.type == 'VIEW_3D'
            for space in area.spaces if space.type == 'VIEW_3D'
        )
        icon = 'RECORD_ON' if face_orientation_active else 'RECORD_OFF'
        box6.operator("view3d.enable_face_orientation", text = 'Toggle Face Orientation', icon=icon)
        
        space = context.space_data
        
        # Check if Backface Culling is enabled
        is_backface_culling_enabled = space.shading.show_backface_culling

        # Display a dynamic icon based on the state
        icon01 = 'RADIOBUT_ON' if is_backface_culling_enabled else 'RADIOBUT_OFF'
        
        box6.operator("view3d.toggle_backface_culling", text = 'Toggle Backface Culling', icon=icon01)
               
        col.label(text='Smart Join:')
        
        box6 = col.box()
        
        box6.operator("object.vertex_group_create", text = 'Join with Vertex Group', icon = 'MESH_CUBE')
        box6.operator("object.vertex_group_separate", text = 'Separate with Vertex Group', icon = 'MOD_EXPLODE')
        
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
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        
        col.label(text='Various:')
        
        # Create a box
        box7 = col.box()
        
        box7.operator("object.uvw_box", text = 'Auto UVW Unwrap', icon = 'UV')
        box7.operator("object.seams_from_islands", text = 'Seams From Islands', icon = 'UV_ISLANDSEL')
        box7.operator("uv.project_from_vieww", text = 'Multi Project From View UVs', icon = 'MOD_UVPROJECT')
        box7.operator("object.uv_world_scale_checker", text = 'Check World Scale UV', icon = 'STICKY_UVS_VERT')
        box7.operator("object.auto_scale_uv", text = 'World Scale UV', icon = 'UV_DATA')
        box7.operator("object.merge_materials", text = 'Merge Duplicates Materials', icon = 'MATERIAL_DATA')
        
        col = layout.column()
        
        col.label(text='AO:')
        
        box7 = col.box()
        
        box7.operator("uv.create_uv_1", text = 'Create UV 1', icon = 'GROUP_UVS')
        box7.operator("uv.pack_islands_custom", text = 'Pack Islands', icon = 'PACKAGE')
        box7.prop(context.scene, "pack_islands_rotate")
        box7.prop(context.scene, "pack_islands_scale")
        box7.prop(context.scene, "pack_islands_margin")
        
class VIEW3D_PT_Panel01(Panel):
    bl_label = "UV Checker"
    bl_idname = "VIEW3D_PT_panel01"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout        

        # Main Panel
        col = layout.column()
        
        box2 = col.box()
        
        box2.operator("uv.analyze_stretch", text = 'Find UV Stretched', icon = 'VIEW_PERSPECTIVE')
        box2.operator("mesh.find_flip_uv", text = 'Find UV Flipped', icon = 'STICKY_UVS_LOC')
        box2.operator("mesh.fix_uv_flipped", text = 'Fix UV Flipped', icon = 'UV_SYNC_SELECT')
        
        box2.operator("object.uv_texture_scale_checker", text = 'Check World Scale UV', icon = 'STICKY_UVS_VERT')
        
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()
        col.split()
        
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

# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel02(Panel):
    bl_label = "GLB Preparation"
    bl_idname = "VIEW3D_PT_panel02"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        
        # Add subtitle
        layout.label(text="Create GLB Materials:")
        
        # Main panel
        col = layout.column()

        # Create a box
        box = col.box()
        
        box.operator("object.name_checker", text="Wrong Name Meshes", icon='FONTPREVIEW')

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
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "export_entire_collection")
        layout.prop(scene, "exclude_high_collections")
        layout.prop(scene, "export_apply")
        layout.prop(scene, "export_materials")
        layout.prop(scene, "export_animations")
        layout.prop(scene, "export_skins")
        layout.prop(scene, "export_draco_mesh_compression_enable")
        
        if scene.export_draco_mesh_compression_enable:
        
            layout.prop(scene, "export_draco_mesh_compression_level")
            layout.prop(scene, "export_draco_position_quantization")
            layout.prop(scene, "export_draco_normal_quantization")
            layout.prop(scene, "export_draco_texcoord_quantization")
            layout.prop(scene, "export_draco_color_quantization")
            layout.prop(scene, "export_draco_generic_quantization")
        
        col = layout.column()
        
        box = col.box()
        
        box.operator("export_scene.batch_glb", text="Export GLB", icon='EXPORT')
        
# Panel in the N dropdown menu in the 3D view
class VIEW3D_PT_Panel04(Panel):
    bl_label = "OBJ Export"
    bl_idname = "VIEW3D_PT_panel04"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SMTH"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Main panel
        col = layout.column()

        # Create a box
        box = col.box()

        box.operator("export_scene.batch_obj", text="OBJ Export", icon='EXPORT')    

# Register all classes 
classes = (
    MarkAssetOperator,
    RandomColorToggleOperator,
    StatsToggleOperator,
    UV_OT_PackIslands,
    OBJECT_OT_CreateVertexColorLayers,
    OBJECT_OT_CombineVertexColors,
    UV_OT_AnalyzeStretch,
    ToggleBackfaceCullingOperator,
    ZFightDetector,
    UVTextureScaleCheckerOperator,
    MeshNameChecker,
    VIEW3D_PT_Panel_Controller,
    ToggleFaceOrientation,
    OBJECT_OT_fix_negative_scale,
    MeshToProcess,
    MESH_OT_collection_batch_decimate,
    OBJECT_OT_select_objects_with_negative_scale,
    MESH_OT_find_flip_UV,
    MESH_OT_fix_flipped_uv_faces,
    MESH_OT_batch_decimate,
    MESH_OT_batch_decimate_planar,
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
    OBJECT_OT_ClassicMaterial,
    OBJECT_OT_RenameMeshes,
    OBJECT_OT_CreateMaterials1024,
    OBJECT_OT_CreateMaterials2048,
    OBJECT_OT_Bake,
    OBJECT_OT_GLBExport,
    OBJECT_OT_RemoveMaterials,
    OBJECT_OT_Normal,
    VIEW3D_PT_Panel69,
    VIEW3D_PT_Panel07,
    VIEW3D_PT_Panel00,
    VIEW3D_PT_Panel01,
    VIEW3D_PT_Panel02,
    VIEW3D_PT_Panel03,
    VIEW3D_PT_Panel04,
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
    
    bpy.types.Scene.decimate_ratio = FloatProperty(
    name="Decimate Ratio",
    description="Ratio for decimation (0.0 to 1.0)",
    min=0.1,
    max=1.0,
    default=0.5,
    )
    
    bpy.types.Scene.planar_angle = FloatProperty(
    name="Planar Angle",
    description="Angle threshold for planar decimation (degrees)",
    min=0.0,
    max=180.0,
    default=5.0,
    )
    
    bpy.types.Scene.meshes_to_process = CollectionProperty(type=MeshToProcess)
    bpy.types.Scene.batch_decimate_ratio = FloatProperty(
        name="Decimate Ratio",
        description="Ratio of decimation (lower values result in more aggressive decimation)",
        default=0.5,
        min=0.1,
        max=1.0,
    )
    bpy.types.Scene.collection_to_process = PointerProperty(
        name="Collection to Process",
        description="Select the collection containing the meshes to process",
        type=bpy.types.Collection,
        update=update_meshes_to_process
    )
    
    bpy.types.Scene.export_apply = BoolProperty(name="Apply Modifiers", default=True)
    bpy.types.Scene.export_draco_mesh_compression_enable = BoolProperty(name="Draco Compression", default=False)
    bpy.types.Scene.export_draco_mesh_compression_level = IntProperty(name="Compression Level", default=6, min=0, max=10)   
    bpy.types.Scene.export_draco_position_quantization= IntProperty(name="Position", default=14, min=0, max=30)
    bpy.types.Scene.export_draco_normal_quantization= IntProperty(name="Normal", default=10, min=0, max=30)
    bpy.types.Scene.export_draco_texcoord_quantization= IntProperty(name="Texture Coordinate", default=12, min=0, max=30)
    bpy.types.Scene.export_draco_color_quantization= IntProperty(name="Texture Coordinate", default=10, min=0, max=30)
    bpy.types.Scene.export_draco_generic_quantization= IntProperty(name="Texture Coordinate", default=12, min=0, max=30)
    bpy.types.Scene.export_materials = EnumProperty(name="Materials", items=[('EXPORT', "Export Materials", ""), ('PLACEHOLDER', "Placeholder", "")], default='PLACEHOLDER')
    bpy.types.Scene.export_animations = BoolProperty(name="Animations", default=False)    
    bpy.types.Scene.export_skins = BoolProperty(name="Skins", default=False)
    bpy.types.Scene.use_selection = BoolProperty(name="Selected Only", default=True)   
    bpy.types.Scene.export_entire_collection = bpy.props.BoolProperty(
    name="Export Entire Collection",
    description="Export the entire collection of the active object instead of only selected objects",
    default=True)
    
    bpy.types.Scene.exclude_high_collections = bpy.props.BoolProperty(name="Exclude _high Collections", description="Exclude collections ending with '_high' from export", default=True)

    bpy.types.Scene.pack_islands_rotate = bpy.props.BoolProperty(name="Rotate", default=True)
    bpy.types.Scene.pack_islands_scale = bpy.props.BoolProperty(name="Scale", default=True)
    bpy.types.Scene.pack_islands_margin = bpy.props.FloatProperty(name="Margin", default=0.05, min=0.0, max=1.0)

def unregister():
    bpy.types.Scene.decimate_ratio = FloatProperty(
    name="Decimate Ratio",
    description="Ratio for decimation (0.0 to 1.0)",
    min=0.1,
    max=1.0,
    default=0.5,
    )
    bpy.types.Scene.planar_angle = FloatProperty(
    name="Planar Angle",
    description="Angle threshold for planar decimation (degrees)",
    min=0.0,
    max=180.0,
    default=5.0,
    )
    bpy.types.Scene.meshes_to_process = CollectionProperty(type=MeshToProcess)
    bpy.types.Scene.batch_decimate_ratio = FloatProperty(
        name="Decimate Ratio",
        description="Ratio of decimation (lower values result in more aggressive decimation)",
        default=0.5,
        min=0.1,
        max=1.0,
    )
    bpy.types.Scene.collection_to_process = PointerProperty(
        name="Collection to Process",
        description="Select the collection containing the meshes to process",
        type=bpy.types.Collection,
        update=update_meshes_to_process
    )
    
    bpy.types.Scene.export_apply = BoolProperty(name="Apply Modifiers", default=True)
    bpy.types.Scene.export_draco_mesh_compression_enable = BoolProperty(name="Draco Compression", default=False)
    bpy.types.Scene.export_draco_mesh_compression_level = IntProperty(name="Compression Level", default=6, min=0, max=10)   
    bpy.types.Scene.export_draco_position_quantization= IntProperty(name="Position", default=14, min=0, max=30)
    bpy.types.Scene.export_draco_normal_quantization= IntProperty(name="Normal", default=10, min=0, max=30)
    bpy.types.Scene.export_draco_texcoord_quantization= IntProperty(name="Texture Coordinate", default=12, min=0, max=30)
    bpy.types.Scene.export_draco_color_quantization= IntProperty(name="Texture Coordinate", default=10, min=0, max=30)
    bpy.types.Scene.export_draco_generic_quantization= IntProperty(name="Texture Coordinate", default=12, min=0, max=30)
    bpy.types.Scene.export_materials = EnumProperty(name="Materials", items=[('EXPORT', "Export Materials", ""), ('PLACEHOLDER', "Placeholder", "")], default='PLACEHOLDER')
    bpy.types.Scene.export_animations = BoolProperty(name="Animations", default=False)    
    bpy.types.Scene.export_skins = BoolProperty(name="Skins", default=True)
    bpy.types.Scene.use_selection = BoolProperty(name="Selected Only", default=True)   
    bpy.types.Scene.export_entire_collection = bpy.props.BoolProperty(
    name="Export Entire Collection",
    description="Export the entire collection of the active object instead of only selected objects",
    default=True
)
    
    bpy.types.Scene.exclude_high_collections = bpy.props.BoolProperty(name="Exclude _high Collections", description="Exclude collections ending with '_high' from export", default=True)
    
    bpy.types.Scene.pack_islands_rotate = bpy.props.BoolProperty(name="Allow Rotation", default=True)
    bpy.types.Scene.pack_islands_scale = bpy.props.BoolProperty(name="Allow Scaling", default=True)
    bpy.types.Scene.pack_islands_margin = bpy.props.FloatProperty(name="Margin", default=0.05, min=0.0, max=1.0)
    
    del bpy.types.Scene.decimate_ratio
    del bpy.types.Scene.collection_to_process
    del bpy.types.Scene.meshes_to_process
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()