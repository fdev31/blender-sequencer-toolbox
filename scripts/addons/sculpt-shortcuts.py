FAVOURITE_BRUSHES = ['DRAW', 'CLAY', 'CREASE', 'PINCH', 'GRAB', 'SNAKE_HOOK', 'FLATTEN']

bl_info = {
    'name': 'Sculpt shortcuts',
    'author': 'fdev31, fab31',
    'version': (1, 0, 0),
    'blender': (2, 6, 9),
    'api': 32738,
    'location': 'Sequencer > Properties',
    'warning': '',
    'description': 'Add a couple of simple but useful buttons to sequencer.',
    'wiki_url': '',
    'tracker_url': '',
    'category': 'System'}

import bpy
from bpy.types import Menu, Panel, UIList
from bl_ui.properties_paint_common import UnifiedPaintPanel
import itertools

class ToggleSculpt(bpy.types.Operator):
    " Toggle between brushes "
    bl_idname = "brush.toggle_type"
    bl_label = "Toggle brush"
    bl_options = {'REGISTER', 'UNDO'}

    BRUSHES = itertools.cycle(FAVOURITE_BRUSHES)

    def execute(self, context):
        bpy.ops.paint.brush_select(paint_mode="SCULPT", sculpt_tool=next(self.BRUSHES))
        return {'FINISHED'}

class VIEW3D_PT_tools_test(Panel, UnifiedPaintPanel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "Tools"
    bl_label = "Shortcuts"

    @classmethod
    def poll(cls, context):
        return cls.paint_settings(context)

    def draw(self, context):
        layout = self.layout

        toolsettings = context.tool_settings
        settings = self.paint_settings(context)
        brush = settings.brush

        col = layout.column()
        col.operator("brush.toggle_type")

        col = layout.column(align=True)
        x = col.operator("paint.brush_select", text="Toggle mask")
        x.paint_mode="SCULPT"
        x.sculpt_tool="MASK"
        x.toggle=True
        x.create_missing=True

        x = col.operator("paint.mask_flood_fill", text="Fill mask")
        x.mode = 'VALUE'
        x.value = 1

        x = col.operator("paint.mask_flood_fill", text="Invert mask")
        x.mode = 'INVERT'

plug_keymap = []

def register():
    bpy.utils.register_module(__name__)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new('Sculpt', space_type='EMPTY', region_type='WINDOW', modal=False)
    km.keymap_items.new(ToggleSculpt.bl_idname, 'X', 'PRESS')

def unregister():
    # handle the keymap
    wm = bpy.context.window_manager
    for km in plug_keymap:
        wm.keyconfigs.addon.keymaps.remove(km)
    plug_keymap.clear()

if __name__ == "__main__":
    register()
