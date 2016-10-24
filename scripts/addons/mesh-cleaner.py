bl_info = {
    "name": "Mesh cleaner",
    "author": "Fabien Devaux (fdev31)",
    "version": (0, 1, 0),
    "blender": (2, 78, 0),
    "location": "3D Window > Tool Shelf > Mesh cleaner",
    "description": "Allows cleaning of points cloud",
    "warning": "",
    "category": "Object",
}

import os
import sys
import json
import time

import bpy
from bpy.types import Panel
from mathutils import kdtree


class PointCloudCleaningOperator(bpy.types.Operator):
    bl_idname = "object.pc_clean"
    bl_label = "Clean point cloud"
    bl_options = {"REGISTER", "UNDO"}

    distance = bpy.props.FloatProperty(name="Max distance", default=0.1, min=0, max=1000)
    neighbors = bpy.props.IntProperty(name="Min neighbor count", default=10, min=0, max=1000)
    recursion = bpy.props.IntProperty(name="Iterations", default=1, min=1, max=10)

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.selected_objects[0]
        for _ in range(self.recursion):
            verts = bpy.context.selected_objects[0].data.vertices #[0].co
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode="OBJECT")
            tree = kdtree.KDTree(len(verts))
            for i, v in enumerate(verts):
                tree.insert(v.co, i)
            tree.balance()
            for idx, vert in enumerate(verts):
                r = tree.find_range(vert.co, self.distance)
                if len(r) < self.neighbors:
                    verts[idx].select = True

            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.delete(type='VERT')
            bpy.ops.object.mode_set(mode = 'OBJECT')
        return {'FINISHED'}


class VIEW3D_PT_tools_Meshify(Panel):
    bl_category = "Tools"
    bl_context = "objectmode"
    bl_label = "Point cloud"
    bl_idname = "OBJECT_OT_pc_clean"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'

    def draw(self, context):
        layout = self.layout
        obj = context.object
        layout.row().operator("object.pc_clean", emboss=True)

def register():
    bpy.utils.register_class(PointCloudCleaningOperator)
    bpy.utils.register_class(VIEW3D_PT_tools_Meshify)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_tools_Meshify)
    bpy.utils.unregister_class(PointCloudCleaningOperator)

if __name__ == "__main__":

    register()
    bpy

