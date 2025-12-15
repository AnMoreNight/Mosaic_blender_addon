bl_info = {
    "name": "Mosaic Effect",
    "author": "Custom",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Mosaic",
    "description": "Apply mosaic/pixelation effect to selected objects during rendering",
    "category": "Render",
}

import bpy
from bpy.props import IntProperty, BoolProperty, CollectionProperty, StringProperty
from bpy.types import Panel, Operator, PropertyGroup

# Property to store mosaic targets
class MosaicTarget(PropertyGroup):
    obj_name: StringProperty()

# Scene properties
class MosaicProperties(PropertyGroup):
    mosaic_size: IntProperty(
        name="Mosaic Size",
        description="Size of mosaic blocks (higher = more pixelated)",
        default=20,
        min=2,
        max=200
    )
    enabled: BoolProperty(
        name="Enable Effect",
        description="Enable/disable mosaic effect",
        default=True
    )
    targets: CollectionProperty(type=MosaicTarget)

# Create mosaic shader nodes
def create_mosaic_material(obj, mosaic_size):
    mat_name = f"Mosaic_{obj.name}"
    
    # Remove existing mosaic material if present
    if mat_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[mat_name])
    
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    nodes.clear()
    
    # Create nodes
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (600, 0)
    
    emission = nodes.new('ShaderNodeEmission')
    emission.location = (400, 0)
    
    # Texture coordinate
    tex_coord = nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (-600, 0)
    
    # Vector math for pixelation
    multiply = nodes.new('ShaderNodeVectorMath')
    multiply.operation = 'MULTIPLY'
    multiply.location = (-400, 0)
    multiply.inputs[1].default_value = (mosaic_size, mosaic_size, mosaic_size)
    
    floor_node = nodes.new('ShaderNodeVectorMath')
    floor_node.operation = 'FLOOR'
    floor_node.location = (-200, 0)
    
    divide = nodes.new('ShaderNodeVectorMath')
    divide.operation = 'DIVIDE'
    divide.location = (0, 0)
    divide.inputs[1].default_value = (mosaic_size, mosaic_size, mosaic_size)
    
    # Color based on position
    color_ramp = nodes.new('ShaderNodeValToRGB')
    color_ramp.location = (200, 0)
    
    separate = nodes.new('ShaderNodeSeparateXYZ')
    separate.location = (0, -200)
    
    combine = nodes.new('ShaderNodeCombineXYZ')
    combine.location = (200, -200)
    
    # Link nodes
    links.new(tex_coord.outputs['Object'], multiply.inputs[0])
    links.new(multiply.outputs[0], floor_node.inputs[0])
    links.new(floor_node.outputs[0], divide.inputs[0])
    links.new(divide.outputs[0], separate.inputs[0])
    links.new(separate.outputs[0], combine.inputs[0])
    links.new(separate.outputs[1], combine.inputs[1])
    links.new(separate.outputs[2], combine.inputs[2])
    links.new(combine.outputs[0], emission.inputs[0])
    links.new(emission.outputs[0], output.inputs[0])
    
    return mat

# Operator: Add selected objects as mosaic targets
class MOSAIC_OT_add_targets(Operator):
    bl_idname = "mosaic.add_targets"
    bl_label = "Add Selected Objects"
    bl_description = "Add selected objects as mosaic targets"
    
    def execute(self, context):
        props = context.scene.mosaic_props
        
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                # Check if already in targets
                if not any(t.obj_name == obj.name for t in props.targets):
                    target = props.targets.add()
                    target.obj_name = obj.name
                    
                    # Apply mosaic material
                    mat = create_mosaic_material(obj, props.mosaic_size)
                    if obj.data.materials:
                        obj.data.materials[0] = mat
                    else:
                        obj.data.materials.append(mat)
        
        self.report({'INFO'}, f"Added {len(context.selected_objects)} object(s)")
        return {'FINISHED'}

# Operator: Remove selected objects from mosaic targets
class MOSAIC_OT_remove_targets(Operator):
    bl_idname = "mosaic.remove_targets"
    bl_label = "Remove Selected Objects"
    bl_description = "Remove selected objects from mosaic targets"
    
    def execute(self, context):
        props = context.scene.mosaic_props
        
        for obj in context.selected_objects:
            for i, target in enumerate(props.targets):
                if target.obj_name == obj.name:
                    props.targets.remove(i)
                    
                    # Remove mosaic material
                    mat_name = f"Mosaic_{obj.name}"
                    if mat_name in bpy.data.materials:
                        mat = bpy.data.materials[mat_name]
                        if obj.data.materials:
                            for j, m in enumerate(obj.data.materials):
                                if m == mat:
                                    obj.data.materials.pop(index=j)
                                    break
                    break
        
        self.report({'INFO'}, "Removed selected object(s)")
        return {'FINISHED'}

# Operator: Clear all mosaic targets
class MOSAIC_OT_clear_targets(Operator):
    bl_idname = "mosaic.clear_targets"
    bl_label = "Clear All"
    bl_description = "Remove all mosaic targets"
    
    def execute(self, context):
        props = context.scene.mosaic_props
        
        for target in props.targets:
            obj = bpy.data.objects.get(target.obj_name)
            if obj:
                mat_name = f"Mosaic_{obj.name}"
                if mat_name in bpy.data.materials:
                    mat = bpy.data.materials[mat_name]
                    if obj.data.materials:
                        for i, m in enumerate(obj.data.materials):
                            if m == mat:
                                obj.data.materials.pop(index=i)
                                break
        
        props.targets.clear()
        self.report({'INFO'}, "Cleared all targets")
        return {'FINISHED'}

# Operator: Update mosaic size
class MOSAIC_OT_update_size(Operator):
    bl_idname = "mosaic.update_size"
    bl_label = "Update Mosaic Size"
    bl_description = "Update mosaic size for all targets"
    
    def execute(self, context):
        props = context.scene.mosaic_props
        
        for target in props.targets:
            obj = bpy.data.objects.get(target.obj_name)
            if obj:
                mat = create_mosaic_material(obj, props.mosaic_size)
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)
        
        self.report({'INFO'}, f"Updated mosaic size to {props.mosaic_size}")
        return {'FINISHED'}

# UI Panel
class MOSAIC_PT_panel(Panel):
    bl_label = "Mosaic Effect"
    bl_idname = "MOSAIC_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Mosaic'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.mosaic_props
        
        # Enable/Disable
        layout.prop(props, "enabled")
        
        layout.separator()
        
        # Mosaic size
        row = layout.row()
        row.prop(props, "mosaic_size")
        row.operator("mosaic.update_size", text="", icon='FILE_REFRESH')
        
        layout.separator()
        
        # Add/Remove buttons
        layout.operator("mosaic.add_targets", icon='ADD')
        layout.operator("mosaic.remove_targets", icon='REMOVE')
        layout.operator("mosaic.clear_targets", icon='X')
        
        layout.separator()
        
        # List of targets
        box = layout.box()
        box.label(text=f"Targets ({len(props.targets)}):")
        for target in props.targets:
            box.label(text=f"  • {target.obj_name}")

# Registration
classes = (
    MosaicTarget,
    MosaicProperties,
    MOSAIC_OT_add_targets,
    MOSAIC_OT_remove_targets,
    MOSAIC_OT_clear_targets,
    MOSAIC_OT_update_size,
    MOSAIC_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mosaic_props = bpy.props.PointerProperty(type=MosaicProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.mosaic_props

if __name__ == "__main__":
    register()
