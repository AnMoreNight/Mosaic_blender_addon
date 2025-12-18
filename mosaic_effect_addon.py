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
    
    if "MosaicObjects" not in bpy.data.collections:
        mosaic_col = bpy.data.collections.new("MosaicObjects")
        scene.collection.children.link(mosaic_col)
    else:
        mosaic_col = bpy.data.collections["MosaicObjects"]
    
    if "SceneLights" not in bpy.data.collections:
        lights_col = bpy.data.collections.new("SceneLights")
        scene.collection.children.link(lights_col)
    else:
        lights_col = bpy.data.collections["SceneLights"]
    
    for col in bpy.data.collections:
        for obj in list(col.objects):
            if obj.type in ('LIGHT', 'CAMERA'):
                if obj.name not in lights_col.objects:
                    lights_col.objects.link(obj)
    
    for obj in list(mosaic_col.objects):
        mosaic_col.objects.unlink(obj)
    
    for item in props.selected_objects:
        obj = bpy.data.objects.get(item.obj_name)
        if obj and obj.name not in mosaic_col.objects:
            mosaic_col.objects.link(obj)
    
    if "MosaicOnly" not in scene.view_layers:
        scene.view_layers.new("MosaicOnly")
    if "WithoutMosaic" not in scene.view_layers:
        scene.view_layers.new("WithoutMosaic")
    
    vl_mosaic = scene.view_layers["MosaicOnly"]
    for lc in vl_mosaic.layer_collection.children:
        if lc.collection.name in ("MosaicObjects", "SceneLights"):
            lc.exclude = False
        else:
            lc.exclude = True
    
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
    
    scene.render.film_transparent = True
    
    setup_view_layers(context)
    
    rl_without = tree.nodes.new('CompositorNodeRLayers')
    rl_without.location = (0, 0)
    rl_without.layer = "WithoutMosaic"
    
    rl_mosaic = tree.nodes.new('CompositorNodeRLayers')
    rl_mosaic.location = (0, 200)
    rl_mosaic.layer = "MosaicOnly"
    
    pixelate = tree.nodes.new('CompositorNodePixelate')
    pixelate.location = (200, 200)
    pixelate.inputs['Size'].default_value = props.pixel_size
    
    z_combine = tree.nodes.new('CompositorNodeZcombine')
    z_combine.location = (400, 0)
    
    bg_color = tree.nodes.new('CompositorNodeRGB')
    bg_color.location = (200, -200)
    bg_color.outputs[0].default_value = (0.05, 0.05, 0.05, 1.0)
    
    alpha_over = tree.nodes.new('CompositorNodeAlphaOver')
    alpha_over.location = (600, 0)
    
    output.location = (800, 0)
    
    tree.links.new(rl_mosaic.outputs['Image'], pixelate.inputs['Color'])
    tree.links.new(rl_without.outputs['Image'], z_combine.inputs[0])
    tree.links.new(rl_without.outputs['Depth'], z_combine.inputs[1])
    tree.links.new(pixelate.outputs['Color'], z_combine.inputs[2])
    tree.links.new(rl_mosaic.outputs['Depth'], z_combine.inputs[3])
    tree.links.new(bg_color.outputs[0], alpha_over.inputs[0])
    tree.links.new(z_combine.outputs[0], alpha_over.inputs[1])
    tree.links.new(alpha_over.outputs[0], output.inputs[0])
    
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
        existing = {item.obj_name for item in props.selected_objects}
        added = 0
        
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.name not in existing:
                item = props.selected_objects.add()
                item.obj_name = obj.name
                added += 1
        
        self.report({'INFO'}, f"Added {added} object(s), total: {len(props.selected_objects)}")
        return {'FINISHED'}

class MOSAIC_OT_remove_object(Operator):
    bl_idname = "mosaic.remove_object"
    bl_label = "Remove"
    bl_description = "Remove object from list"
    
    index: IntProperty()
    
    def execute(self, context):
        context.scene.mosaic_props.selected_objects.remove(self.index)
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
        
        for i, item in enumerate(props.selected_objects):
            row = box.row()
            row.label(text=item.obj_name, icon='OBJECT_DATA')
            op = row.operator("mosaic.remove_object", text="", icon='X')
            op.index = i
        
        if len(props.selected_objects) > 0:
            box.operator("mosaic.clear_objects", icon='TRASH')
        
        layout.operator("mosaic.apply", icon='FILE_REFRESH')

def register():
    bpy.utils.register_class(MosaicObjectItem)
    bpy.utils.register_class(MosaicProperties)
    bpy.utils.register_class(MOSAIC_OT_add_selected)
    bpy.utils.register_class(MOSAIC_OT_remove_object)
    bpy.utils.register_class(MOSAIC_OT_clear_objects)
    bpy.utils.register_class(MOSAIC_OT_apply)
    bpy.utils.register_class(MOSAIC_PT_render_panel)
    bpy.types.Scene.mosaic_props = bpy.props.PointerProperty(type=MosaicProperties)

def unregister():
    del bpy.types.Scene.mosaic_props
    bpy.utils.unregister_class(MOSAIC_PT_render_panel)
    bpy.utils.unregister_class(MOSAIC_OT_apply)
    bpy.utils.unregister_class(MOSAIC_OT_clear_objects)
    bpy.utils.unregister_class(MOSAIC_OT_remove_object)
    bpy.utils.unregister_class(MOSAIC_OT_add_selected)
    bpy.utils.unregister_class(MosaicProperties)
    bpy.utils.unregister_class(MosaicObjectItem)

if __name__ == "__main__":
    register()
