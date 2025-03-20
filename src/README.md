# SMTH Blender Smart Tools

This version of the addon is designed for Blender 4.3.2. Some APIs have been modified compared to previous versions, and the correct functioning of the addon cannot be guaranteed in older versions of Blender.

This add-on allows you to do various things, primarily we can divide the functionalities into 3 panels: SMTH, EDUGAME, CONTROLLER.

---------------------------------
Let's talk about the SMTH one, it is divided into 6 categories:

- Mesh Optimization
- Texturing
- Modeling
- UV Checker
- GLB Preparation
- Export

Let's analyze it point by point:

---------------------------------
MESH OPTIMIZATION

- Collapse Decimate Meshes: This operator allows you to select one or more meshes that will be decimated using the collapse method. The desired ratio can be set in the interface, just like with the Decimate modifier. All decimated meshes will be duplicated and moved to a new collection. Both the meshes and the collection will have the _low suffix, ensuring that the original meshes remain untouched. The decimation process preserves seams and boundary edges, and the meshes are slightly smoothed to avoid artifacts. Additionally, UVs and Custom Normals are transferred from the original meshes to the processed ones.

- Planar Decimate Meshes: This operator allows you to select one or more meshes that will be decimated using the planar method. The desired angle limit can be set in the interface, just like with the Decimate modifier. All decimated meshes will be duplicated and moved to a new collection. Both the meshes and the collection will have the _low suffix, ensuring that the original meshes remain untouched. In addition to the decimation process, UVs and Custom Normals are transferred from the original meshes to the processed ones.

- Collapse Decimate Collection: This operator functions the same way as Collapse Decimate Meshes, with the key difference that, when selecting a collection, you can decide which meshes to process with decimation and which ones to simply copy with the _low suffix into the _low collection without applying any operations. This is useful when there are already optimized meshes that do not need processing but should still be conveniently and dynamically grouped within the _low collection.

---------------------------------
TEXTURING

- Auto UVW Unwrap: It’s a simple command already present in Blender for UV unwrapping starting from a cubic projection. This command allows you to do it on multiple selected objects by cycling the operation for each of them.

- Seams From Islands: This command is already present in Blender and allows you to create seams on a mesh starting from the division present in its UV space, or from its own islands. The perimeter of each UV island will be made a seam in the mesh. It is very useful when using the Smart UV Project or the Auto UVW Unwrap. This command allows you to do it on multiple selected objects by cycling the operation for each of them.

- Multi Project From View: Project UV from view for all selected object in active UV layer.

The settings of this operation are these:
orthographic=False,
camera_bounds=True,
correct_aspect=True,
clip_to_bounds=False,
scale_to_bounds=False

- World Scale UV: All islands of all object selected will be scaled to same world unit (Texture Size = 2048x2048, Density = 1024, Origin = center, Area Target = UV Island).

- Merge Duplicates Materials: Merge duplicate materials for all objects in blender file.

- Create UV1: It allows you to create a second UV layer if it is not already present for each selected mesh and make it active as a layer for editing in the UV editor while keeping it invisible to avoid it being considered as the first UV layer in export.

- Pack Islands: It allows you to pack UV islands for selected objects. The buttons in UI allows you to choose the margin and if the pack change scale and/or rotation for the islands.

---------------------------------
MODELING

- Purge Unused Data: This command is already present in Blender and allows you to clear all orphaned data-blocks without any users from the file.

- Auto Mirror: Auto Mirror all objects selected on X axis without flipping UVs and Normals.

- Check Z-Fight: This operator detects Z-fighting in selected mesh objects by identifying faces that are extremely close and have similar normals. It checks face alignment, distance, and 2D projection overlap to highlight problematic areas.
When executed, the script deselects all faces, analyzes face properties, and compares them across objects.
Detected faces are selected in edit mode for easy review.
This tool helps identify and fix overlapping geometry, reducing rendering issues and improving model quality.

- Select Negative Scale Objects: This operator selects objects with at least one negative scale value. It first deselects all objects, then scans the scene and selects any object with a negative scale along any axis. This helps quickly identify and correct unintended transformations.

- Fix Negative Scale Objects: This operator applies negative scale transformations while correcting UVs and normals. It ensures selected mesh objects maintain their intended shape by flipping UV coordinates along the X-axis and reversing normals when necessary. The tool also preserves object position and restores the original origin alignment, preventing unintended shifts in geometry.

- Toggle Scene Stats: This operator enable or disable Scene Statistics in your 3D Viewport.

- Toggle Random Color: This operator enable or disable Random Color for each object for your Matcap.

- Toggle Face Orientation: This operator toggles the face orientation overlay in the 3D Viewport, helping users visualize normal directions. It automatically enables or disables face orientation display and ensures backface culling is turned off. If no 3D Viewport is found, it notifies the user with an error message.

- Toggle Backface Culling: This operator enables or disables backface culling in Solid Mode, allowing users to control the visibility of back-facing polygons. It toggles the setting in the 3D Viewport and provides feedback on the current status. If no 3D Viewport is found, it notifies the user with an error message.

- Smart Join:
    - Create Vertex Group: Join all selected mesh togheter creating a vertex group for each object before the join.
    - Separate Vertex Group: Separate all selected mesh based on vertex groups division and rename them as well based on vertex groups names.

- Crease:
    - Mark Crease: For all objects in selection Mark all selected edges to Crease with 1.0 value.
    - Unmark Crease: For all objects in selection Unmark all selected edges to Crease with 0.0 value.
    - SubD Mod: Add for all selected objects a Subsurface modifier with default values. 

- Bevel Weight:
    - Mark Bevel Weight: For all objects in selection Mark all selected edges to Bevel Weight with 1.0 value.
    - Unmark Bevel Weight: For all objects in selection Unmark all selected edges to Bevel Weight with 0.0 value.
    - Bevel Wheight Mod: For all objects in selection add a Bevel modifier based on Weight.

- Auto Normal Hard Surf: adds a Weighted Normal modifier with weight set to 100 and Keep Sharp enabled for each selected mesh and Auto Smooth By Angle.

This command is useful if you want to check the shading of a hard surface object. The modifier helps fix shading issues, and if no changes are observed, then the object already has correct shading.
(CAUTION - the default values of the modifier may not be the most appropriate for every object, so consider whether to remove or keep the Keep Sharp option based on visual feedback).

In detail, this command checks for each selected object if a Weighted Normal modifier is already present. If it is present, the command does nothing. If it is not present, a new modifier is added with weight value set to 100 and Keep Sharp option enabled. The auto smooth is then enabled, and any existing Custom Normal Data is cleaned to ensure the modifier functions correctly.

---------------------------------
UV CHECKER

- Find UV Stretched: is udes to identify all the faces that have stretched UV.

- Find UV Flipped: is used to identify all the faces of an object that have flipped UVs. This operator first checks if the object is a mesh and if it has UV layers. It then switches to Edit Mode, creates a BMesh, and scans all the faces of the object. Any face found to have flipped UVs will be selected. After processing, the operator prints the number of flipped faces in the terminal. If the object does not have UVs or is not a mesh, the operator will issue a warning message.

- Fix UV Flipped: is designed to fix flipped UVs while maintaining the same position and scale. Like the second operator, it enters Edit Mode, creates a BMesh, and checks for UV layers. It then identifies the faces with flipped UVs. For each flipped face, the operator saves the original UV coordinates and calculates the original bounding box of the UVs. It then mirrors the UVs along the X-axis relative to the center of the original bounding box. After mirroring, the new bounding box for the UVs is calculated, and a scaling factor is applied to realign the mirrored UVs with the original bounding box size. Finally, the UVs are scaled to maintain the same size, and the object is updated. A message is displayed indicating how many flipped faces were fixed.

- Check World Scale UV: This operators allows you, from sleected objects, check if there is an island that is not in scaled properly for Vesta pipeline.

- Flat Material: adds a monochromatic material of faded yellow color with default values of Principled BSDF as the first material for each selected mesh.

This command is useful if you want to quickly add a simple material to all selected meshes without having to do it for each individual mesh.

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.), then it dissociates all materials linked to the mesh and adds a new material without nodes to the first material slot. Inside this material, a Principled BSDF with RGB values (0.8, 0.6, 0.2) is added and connected to a material output node.

- Reflection Checker: adds a reflective mirror-like metallic material to each selected mesh.

This command is useful if you want to quickly assign a unique material to multiple meshes to control the shading and verify that the reflections on the object are as desired.

In detail, this command checks for each selected object if it is of type MESH or not (it cannot be run on volumes, curves, etc.), then it dissociates all materials linked to the mesh and adds a new material without nodes to the first material slot. Inside this material, a white Principled BSDF with roughness value set to 0 and metalness value set to 1 is added to achieve a mirror-like reflection. Finally, it is connected to a material output node to be visible on the mesh.

- UV GRID & UV LINE: adds a material with a specific map to visually check the quality of UVs for each selected object.

This command is very useful if you want to assign a single material for UV checking to multiple meshes simultaneously. There are two available maps: GRID map for general UV deformation and cleanliness, and LINE map to verify if the UV orientation matches the desired orientation for the associated material.

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.). It then dissociates all materials linked to the mesh and adds a new material without nodes to the first material slot. Inside this material, a Principled BSDF is added and connected to a material output node. A Texture Coordinate node, Mapping node, and Image Texture node with the selected texture (GRID or LINE) are added and connected to each other so that the texture is displayed as the material's Base Color.

- UV Repeat & Apply Repeat: allow you to modify the scale of the UV Checker texture for each selected object. It can be used to modify the scale of a mapping node for the active material.

This command is useful if you want more control over the texture scale to have customized visual feedback for different scenarios and situations.

In detail, this command modifies the three Scale values of the Mapping node in the active material for each selected object. Once you set the desired value in the UV Repeat slider, you can press Apply Repeat to apply the changes. (CAUTION - this command can be run on any material that has a mapping node inside it).

- Remove Material Slots: allows you to dissociate all materials associated for all selected object, leaving no visible material inside.

This command is useful when you want to dissociate all materials from multiple meshes in a single step.

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.). It then removes all materials associated with each selected mesh.

---------------------------------
GLB PREPARATION

- Wrong Name Meshes: this operator is designed to check for objects whose names do not match the names of their associated mesh data. It scans through all the selected objects in the current scene, and if an object is a mesh, it compares its name with the name of its mesh data. If the names do not match, the object is considered mismatched and added to a list. After processing all selected objects, the operator deselects all objects and then reselects the ones with mismatched names. If mismatched objects are found, it sets the first mismatched object as the active object and reports a warning with the count of mismatched objects. If all selected objects have matching names, it reports an informational message stating that all names are correct. This operator ensures that the user is aware of objects that might need attention due to name mismatches between objects and their mesh data.

- Rename Meshes: allows you to rename the mesh or primitive data within an object with the object's name.

This command is useful if you want to rename the meshes of multiple primitives without having to do it manually for each individual mesh. It is also helpful for exporting multiple meshes into a single object, where the primitives retain the names of the meshes and can be easily identified for other uses in different programs or workflows.

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.). It then renames the associated primitive with the name of the mesh.

- 1K AO & 2K AO: creates a material ready for baking Ambient Occlusion (AO) so that it can be exported as a single GLB file while preserving AO information.

This command is useful when you want to create a material ready for export to GLB that also includes a dedicated AO map for the second UV set. The prefix 1K or 2K indicates the resolution of the image prepared for baking (1024x1024 or 2048x2048).

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.). It then creates an empty material with the same name as the primitive of the selected mesh. Inside the material, an empty group named 'gtlf settings' is created, which will be used to connect the AO map and identify it as such. A completely white empty Image Texture is then created with a resolution of 1K or 2K, depending on the chosen command, and connected to the previously created empty group. The Image Texture is renamed with the mesh name + the suffix '_AO'. The material will be displayed in blue color to indicate that it has been created correctly.

- Bake AO: initiates the baking process of Ambient Occlusion on the second UV set for the selected meshes and loads it as the image for the Image Texture node created with the 1K AO and 2K AO commands.

This command is very useful when you want to bake AO for multiple meshes without manually setting all the bake parameters. Once the bake is initiated, it will be performed one by one for each selected mesh, and the progress can be tracked through the classic progress bar in the Blender interface, allowing you to use the program during the baking process.

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.). It also checks if the mesh has more than a single UV set (if it doesn't, the command will have no effect). The AO bake is then initialized on the second UV set, with the Cycles rendering method and samples set to 256, while leaving the remaining settings at their default values. The generated image is automatically associated with the Image Texture node inside the material, if present. Otherwise, an error will occur as the system doesn't know where to save the bake.

---------------------------------
EXPORT

- GLB Export: allows you to export all selected meshes into a single GLB file, organized based on the collections they belong to and using corresponding collection names as file names.

This command is useful when you want to export multiple meshes from different collections, so that they are divided based on their collection membership and renamed accordingly. It uses default settings for Draco compression.

In detail, this command exports all selected meshes within each collection into a single GLB file. It uses the default Draco compression and renames each exported GLB file according to the collection that the meshes belong to. The default export path will be the location of the .blend file.

- OBJ Export: allows you to export all selected meshes into a single OBJ file, organized based on the collections they belong to and using corresponding collection names as file names.

This command is useful when you want to export multiple meshes from different collections, so that they are divided based on their collection membership and renamed accordingly.

---------------------------------
---------------------------------

Let's talk about the EDUGAME panel:

- Purge Unused Data: This command is already present in Blender and allows you to clear all orphaned data-blocks without any users from the file.

- NPC Anim Path: This button let you generate an anim path based on a mesh. The path is generated from a mesh object that you want to use as the path. It is then converted into a curve and resampled to optimize its shape and ensure that the points on the path are equidistant from each other. After that, a cube is instantiated for each generated point, and the individual origins are aligned. The various objects are then separated, and they are cleared of the cubes inside them. The result is a collection containing an empty object that holds the position and rotation information, which the NPC will use to simulate its movement.

- Rigid Body Anim Path: This command allows you to create an animation path for a rigid body animation. The animation will be baked, and the path will be generated based on the position and rotation of the pivot at every frame across the timeline. The path will be generated in a separate collection.

- Create Vertex Color Channels RGBA: This command allows you to create 5 attribute layer of Vertex Color (R, G, B, A, RGBA) and sets RGBA as active for export.

- Radial Vertex Color Gradient RGBA: This command allows you to create a vertical gradient in the Vertex Color R channel based on the object's minimum and maximum points, and then merge everything into a single RGBA channel where the GBA channels are set to a value of 1.0.

- Combine Vertex Color RGBA: This command allows you to merge all vertex color channles in VERTEX RGBA channel.

---------------------------------
---------------------------------

Now we can talk about the CONTROLLER panel:

This panel allowas you to access certain operators found in SMTH panel, designed for controller, without other distracting buttons.