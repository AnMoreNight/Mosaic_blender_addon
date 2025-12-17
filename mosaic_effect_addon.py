bl_info = {
    "name": "Mosaic Effect",
    "author": "Custom",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "Render Properties",
    "description": "Apply mosaic/pixelation effect to selected objects",
    "category": "Render",
}

import bpy
from bpy.props import IntProperty, BoolProperty, CollectionProperty, StringProperty
from bpy.types import Panel, PropertyGroup, Operator

class MosaicObjectItem(PropertyGroup):
    obj_name: StringProperty()

class MosaicProperties(PropertyGroup):
    enabled: BoolProperty(
        name="Enable Mosaic Effect",
        description="Apply mosaic effect to renders",
        default=False
    )
    pixel_size: IntProperty(
        name="Pixel Size",
        description="Size of mosaic blocks",
        default=8,
        min=2,
        max=50
    )
    selected_objects: CollectionProperty(type=MosaicObjectItem)

def setup_view_layers(context):
    scene = context.scene
    props = scene.mosaic_props
    
    # Create collection for selected objects
    if "MosaicObjects" not in bpy.data.collections:
        mosaic_col = bpy.data.collections.new("MosaicObjects")
        scene.collection.children.link(mosaic_col)
    else:
        mosaic_col = bpy.data.collections["MosaicObjects"]
    
    # Create collection for lights/camera
    if "SceneLights" not in bpy.data.collections:
        lights_col = bpy.data.collections.new("SceneLights")
        scene.collection.children.link(lights_col)
    else:
        lights_col = bpy.data.collections["SceneLights"]
    
    # Move lights and cameras to SceneLights collection (keep in original too)
    for col in bpy.data.collections:
        for obj in list(col.objects):
            if obj.type in ('LIGHT', 'CAMERA'):
                if obj.name not in lights_col.objects:
                    lights_col.objects.link(obj)
    
    # Clear mosaic collection
    for obj in list(mosaic_col.objects):
        mosaic_col.objects.unlink(obj)
    
    # Add selected objects to mosaic collection (keep in original collections too)
    for item in props.selected_objects:
        obj = bpy.data.objects.get(item.obj_name)
        if obj and obj.name not in mosaic_col.objects:
            mosaic_col.objects.link(obj)
    
    # Create view layers
    if "MosaicOnly" not in scene.view_layers:
        scene.view_layers.new("MosaicOnly")
    if "WithoutMosaic" not in scene.view_layers:
        scene.view_layers.new("WithoutMosaic")
    
    # Configure MosaicOnly layer (show ONLY MosaicObjects + SceneLights)
    vl_mosaic = scene.view_layers["MosaicOnly"]
    for lc in vl_mosaic.layer_collection.children:
        if lc.collection.name in ("MosaicObjects", "SceneLights"):
            lc.exclude = False
        else:
            lc.exclude = True
    
    # Configure WithoutMosaic layer (show everything EXCEPT MosaicObjects)
    vl_without = scene.view_layers["WithoutMosaic"]
    for lc in vl_without.layer_collection.children:
        if lc.collection.name == "MosaicObjects":
            lc.exclude = True
        else:
            lc.exclude = False

def update_compositor(context):
    scene = context.scene
    props = scene.mosaic_props
    
    scene.render.use_compositing = True
    
    if not scene.compositing_node_group:
        tree = bpy.data.node_groups.new(name="MosaicCompositor", type='CompositorNodeTree')
        scene.compositing_node_group = tree
    else:
        tree = scene.compositing_node_group
    
    tree.nodes.clear()
    tree.interface.clear()
    
    output = tree.nodes.new('NodeGroupOutput')
    tree.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    
    if not props.enabled or len(props.selected_objects) == 0:
        scene.render.film_transparent = False
        render_layers = tree.nodes.new('CompositorNodeRLayers')
        render_layers.location = (0, 0)
        output.location = (200, 0)
        tree.links.new(render_layers.outputs['Image'], output.inputs[0])
        return
    
    # Enable transparent background for proper compositing
    scene.render.film_transparent = True
    
    # Setup view layers
    setup_view_layers(context)
    
    # Render layer for objects WITHOUT mosaic
    rl_without = tree.nodes.new('CompositorNodeRLayers')
    rl_without.location = (0, 0)
    rl_without.layer = "WithoutMosaic"
    
    # Render layer for objects WITH mosaic
    rl_mosaic = tree.nodes.new('CompositorNodeRLayers')
    rl_mosaic.location = (0, 200)
    rl_mosaic.layer = "MosaicOnly"
    
    # Pixelate the mosaic layer
    pixelate = tree.nodes.new('CompositorNodePixelate')
    pixelate.location = (200, 200)
    pixelate.inputs['Size'].default_value = props.pixel_size
    
    # Composite pixelated over non-pixelated
    alpha_over = tree.nodes.new('CompositorNodeAlphaOver')
    alpha_over.location = (400, 0)
    
    # Add background color (world color)
    bg_color = tree.nodes.new('CompositorNodeRGB')
    bg_color.location = (200, -200)
    if scene.world and scene.world.use_nodes:
        # Try to get world color
        bg_color.outputs[0].default_value = (0.05, 0.05, 0.05, 1.0)  # Dark gray default
    else:
        bg_color.outputs[0].default_value = (0.05, 0.05, 0.05, 1.0)
    
    # Composite result over background
    alpha_over2 = tree.nodes.new('CompositorNodeAlphaOver')
    alpha_over2.location = (600, 0)
    
    output.location = (800, 0)
    
    # Links
    tree.links.new(rl_mosaic.outputs['Image'], pixelate.inputs['Color'])
    tree.links.new(rl_without.outputs['Image'], alpha_over.inputs[0])  # Background
    tree.links.new(pixelate.outputs['Color'], alpha_over.inputs[1])  # Foreground
    tree.links.new(bg_color.outputs[0], alpha_over2.inputs[0])  # Solid background
    tree.links.new(alpha_over.outputs['Image'], alpha_over2.inputs[1])  # Composited result
    tree.links.new(alpha_over2.outputs['Image'], output.inputs[0])
    
    for area in context.screen.areas:
        if area.type == 'NODE_EDITOR':
            area.spaces.active.tree_type = 'CompositorNodeTree'
            area.spaces.active.node_tree = tree
            break

class MOSAIC_OT_add_selected(Operator):
    bl_idname = "mosaic.add_selected"
    bl_label = "Add Selected Objects"
    bl_description = "Add selected objects to mosaic list"
    
    def execute(self, context):
        props = context.scene.mosaic_props
        props.selected_objects.clear()
        
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                item = props.selected_objects.add()
                item.obj_name = obj.name
        
        self.report({'INFO'}, f"Added {len(props.selected_objects)} object(s)")
        return {'FINISHED'}

class MOSAIC_OT_clear_objects(Operator):
    bl_idname = "mosaic.clear_objects"
    bl_label = "Clear"
    bl_description = "Clear object list"
    
    def execute(self, context):
        context.scene.mosaic_props.selected_objects.clear()
        return {'FINISHED'}

class MOSAIC_OT_apply(Operator):
    bl_idname = "mosaic.apply"
    bl_label = "Apply Mosaic"
    bl_description = "Apply mosaic effect to compositor"
    
    def execute(self, context):
        update_compositor(context)
        props = context.scene.mosaic_props
        if props.enabled and len(props.selected_objects) > 0:
            self.report({'INFO'}, f"Mosaic applied to {len(props.selected_objects)} object(s)")
        else:
            self.report({'INFO'}, "Mosaic disabled")
        return {'FINISHED'}

class MOSAIC_PT_render_panel(Panel):
    bl_label = "Mosaic Effect"
    bl_idname = "MOSAIC_PT_render_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    
    def draw_header(self, context):
        self.layout.prop(context.scene.mosaic_props, "enabled", text="")
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.mosaic_props
        
        layout.enabled = props.enabled
        layout.prop(props, "pixel_size")
        
        box = layout.box()
        box.label(text="Objects:")
        box.operator("mosaic.add_selected", icon='ADD')
        
        for item in props.selected_objects:
            row = box.row()
            row.label(text=item.obj_name, icon='OBJECT_DATA')
        
        if len(props.selected_objects) > 0:
            box.operator("mosaic.clear_objects", icon='X')
        
        layout.operator("mosaic.apply", icon='FILE_REFRESH')

def register():
    bpy.utils.register_class(MosaicObjectItem)
    bpy.utils.register_class(MosaicProperties)
    bpy.utils.register_class(MOSAIC_OT_add_selected)
    bpy.utils.register_class(MOSAIC_OT_clear_objects)
    bpy.utils.register_class(MOSAIC_OT_apply)
    bpy.utils.register_class(MOSAIC_PT_render_panel)
    bpy.types.Scene.mosaic_props = bpy.props.PointerProperty(type=MosaicProperties)

def unregister():
    del bpy.types.Scene.mosaic_props
    bpy.utils.unregister_class(MOSAIC_PT_render_panel)
    bpy.utils.unregister_class(MOSAIC_OT_apply)
    bpy.utils.unregister_class(MOSAIC_OT_clear_objects)
    bpy.utils.unregister_class(MOSAIC_OT_add_selected)
    bpy.utils.unregister_class(MosaicProperties)
    bpy.utils.unregister_class(MosaicObjectItem)

if __name__ == "__main__":
    register()
