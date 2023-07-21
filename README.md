# SMTH Blender Smart Tools

This add-on allows you to do various things, primarily we can divide the functionalities into 3 categories:

- UV Checking and Shading Checking
- Preparation for exporting meshes to GLB with integrated ambient occlusion on a dedicated UV set
- Exporting multiple meshes into a single GLB file divided based on the reference collection

Let's analyze it point by point:

- Monochromatic Material: adds a monochromatic material of faded yellow color with default values of Principled BSDF as the first material for each selected mesh.

This command is useful if you want to quickly add a simple material to all selected meshes without having to do it for each individual mesh.

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.), then it dissociates all materials linked to the mesh and adds a new material without nodes to the first material slot. Inside this material, a Principled BSDF with RGB values (0.8, 0.6, 0.2) is added and connected to a material output node.

- Reflection Checker: adds a reflective mirror-like metallic material to each selected mesh.

This command is useful if you want to quickly assign a unique material to multiple meshes to control the shading and verify that the reflections on the object are as desired.

In detail, this command checks for each selected object if it is of type MESH or not (it cannot be run on volumes, curves, etc.), then it dissociates all materials linked to the mesh and adds a new material without nodes to the first material slot. Inside this material, a white Principled BSDF with roughness value set to 0 and metalness value set to 1 is added to achieve a mirror-like reflection. Finally, it is connected to a material output node to be visible on the mesh.

- Hard Surface Checker: adds a Weighted Normal modifier with weight set to 100 and Keep Sharp enabled for each selected mesh.

This command is useful if you want to check the shading of a hard surface object. The modifier helps fix shading issues, and if no changes are observed, then the object already has correct shading.
(CAUTION - the default values of the modifier may not be the most appropriate for every object, so consider whether to remove or keep the Keep Sharp option based on visual feedback).

In detail, this command checks for each selected object if a Weighted Normal modifier is already present. If it is present, the command does nothing. If it is not present, a new modifier is added with weight value set to 100 and Keep Sharp option enabled. The auto smooth is then enabled, and any existing Custom Normal Data is cleaned to ensure the modifier functions correctly.

- UV GRID & UV LINE: adds a material with a specific map to visually check the quality of UVs for each selected object.

This command is very useful if you want to assign a single material for UV checking to multiple meshes simultaneously. There are two available maps: GRID map for general UV deformation and cleanliness, and LINE map to verify if the UV orientation matches the desired orientation for the associated material.

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.). It then dissociates all materials linked to the mesh and adds a new material without nodes to the first material slot. Inside this material, a Principled BSDF is added and connected to a material output node. A Texture Coordinate node, Mapping node, and Image Texture node with the selected texture (GRID or LINE) are added and connected to each other so that the texture is displayed as the material's Base Color.

- UV Repeat & Apply Repeat: allow you to modify the scale of the UV Checker texture for each selected object.

This command is useful if you want more control over the texture scale to have customized visual feedback for different scenarios and situations.

In detail, this command modifies the three Scale values of the Mapping node in the active material for each selected object. Once you set the desired value in the UV Repeat slider, you can press Apply Repeat to apply the changes. (CAUTION - this command can be run on any material that has a mapping node inside it).

- Remove Material Slots: allows you to dissociate all materials associated with each selected object, leaving no visible material inside.

This command is useful when you want to dissociate all materials from multiple meshes in a single step.

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.). It then removes all materials associated with each selected mesh.

- Destroy ALL Materials: allows you to permanently delete any materials from the current Blender file, regardless of which mesh is selected.

This command is useful when you want to clean up all existing materials and remove them not only from the meshes but directly from the Blender file itself (e.g., UV Checker or other previously created materials).
(CAUTION - This command will delete all materials from the Blender file but will only remove the empty material slots of the selected meshes before running the command. To clean all material slots from all meshes, it is recommended to select all meshes beforehand or do it separately and then run the Remove Material Slot command.)

In detail, this command deletes all materials present in the .blend file and, only for the objects in the selection, it also cleans all material slots.

- Rename Meshes: allows you to rename the mesh or primitive data within an object with the object's name.

This command is useful if you want to rename the meshes of multiple primitives without having to do it manually for each individual mesh. It is also helpful for exporting multiple meshes into a single object, where the primitives retain the names of the meshes and can be easily identified for other uses in different programs or workflows.

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.). It then renames the associated primitive with the name of the mesh.

- 1K AO & 2K AO: creates a material ready for baking Ambient Occlusion (AO) so that it can be exported as a single GLB file while preserving AO information.

This command is useful when you want to create a material ready for export to GLB that also includes a dedicated AO map for the second UV set. The prefix 1K or 2K indicates the resolution of the image prepared for baking (1024x1024 or 2048x2048).

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.). It then creates an empty material with the same name as the primitive of the selected mesh. Inside the material, an empty group named 'gtlf settings' is created, which will be used to connect the AO map and identify it as such. A completely white empty Image Texture is then created with a resolution of 1K or 2K, depending on the chosen command, and connected to the previously created empty group. The Image Texture is renamed with the mesh name + the suffix '_AO'. The material will be displayed in blue color to indicate that it has been created correctly.

- Bake AO: initiates the baking process of Ambient Occlusion on the second UV set for the selected meshes and loads it as the image for the Image Texture node created with the 1K AO and 2K AO commands.

This command is very useful when you want to bake AO for multiple meshes without manually setting all the bake parameters. Once the bake is initiated, it will be performed one by one for each selected mesh, and the progress can be tracked through the classic progress bar in the Blender interface, allowing you to use the program during the baking process.

In detail, this command checks, for each selected object, if it is of type MESH or not (it cannot be run on volumes, curves, etc.). It also checks if the mesh has more than a single UV set (if it doesn't, the command will have no effect). The AO bake is then initialized on the second UV set, with the Cycles rendering method and samples set to 128, while leaving the remaining settings at their default values. The generated image is automatically associated with the Image Texture node inside the material, if present. Otherwise, an error will occur as the system doesn't know where to save the bake.

- GLB Export: allows you to export all selected meshes into a single GLB file, organized based on the collections they belong to and using corresponding collection names as file names.

This command is useful when you want to export multiple meshes from different collections, so that they are divided based on their collection membership and renamed accordingly. It uses default settings for Draco compression.

In detail, this command exports all selected meshes within each collection into a single GLB file. It uses the default Draco compression and renames each exported GLB file according to the collection that the meshes belong to. The default export path will be the location of the .blend file.

