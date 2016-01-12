# Default brushes:
# BLOB CLAY CLAY_STRIPS CREASE DRAW FILL FLATTEN GRAB INFLATE LAYER
# MASK NUDGE PINCH ROTATE SCRAPE SIMPLIFY SMOOTH SNAKE_HOOK THUMB

BRUSH_SET = [
        ["CLAY_STRIPS", "CREASE", "DRAW", "CLAY"],
        ["INFLATE", "BLOB", "PINCH", "LAYER"],
        ["FLATTEN", "FILL", "SCRAPE",  "SIMPLIFY"],
        ["GRAB", "SNAKE_HOOK", "THUMB", "NUDGE", "ROTATE"],
    ]

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
    bl_idname = "shortbrush.toggle_type"
    bl_label = "Toggle brush"
    bl_options = {'REGISTER', 'UNDO'}

    b_row = bpy.props.IntProperty("row")
    b_col = bpy.props.IntProperty("col")

    change_row = bpy.props.BoolProperty("vertical")
    invert_sense = bpy.props.BoolProperty("invert sense")

    def execute(self, context):
        if self.change_row:
            if self.invert_sense:
                self.b_row = self.b_row - 1 if self.b_row > 0 else len(BRUSH_SET)-1
            else:
                self.b_row = (self.b_row + 1) % len(BRUSH_SET)
            self.b_col = 0

        else:
            if self.invert_sense:
                self.b_col = (self.b_col - 1) if self.b_col > 0 else len(BRUSH_SET[self.b_row]) - 1
            else:
                self.b_col = (self.b_col + 1) % len(BRUSH_SET[self.b_row])
        bpy.ops.paint.brush_select(paint_mode="SCULPT", sculpt_tool=BRUSH_SET[self.b_row][self.b_col])
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
        sculpt = toolsettings.sculpt
        settings = self.paint_settings(context)
        brush = settings.brush
        capabilities = brush.sculpt_capabilities

        box = layout.box()

        rr = box.row()
        if context.sculpt_object.use_dynamic_topology_sculpting:
            rr.operator("sculpt.dynamic_topology_toggle", icon='SOLO_ON', text="")
        else:
            rr.operator("sculpt.dynamic_topology_toggle", icon='SOLO_OFF', text="")
        rr.prop(sculpt, "use_smooth_shading", text="Smooth")
        col = box.column()
        col.active = context.sculpt_object.use_dynamic_topology_sculpting
        sub = col.column(align=True)
        sub.active = (brush and brush.sculpt_tool != 'MASK')
        if (sculpt.detail_type_method == 'CONSTANT'):
            row = sub.row(align=True)
            row.prop(sculpt, "constant_detail")
            row.operator("sculpt.sample_detail_size", text="", icon='EYEDROPPER')
        elif (sculpt.detail_type_method == 'BRUSH'):
            sub.prop(sculpt, "detail_percent")
        else:
            sub.prop(sculpt, "detail_size")
        sub.prop(sculpt, "detail_type_method", text="")
       
        row = box.row()
        row.prop(brush, "use_frontface", text="Face")
        if capabilities.has_accumulate:
            row.prop(brush, "use_accumulate", text="Spray")

        col = box.column(align=True)

        x = col.operator("shortbrush.toggle_type", icon="TRIA_UP", text="")
        x.change_row = True
        x.invert_sense = True

        row = col.row(align=True)

        x = row.operator("shortbrush.toggle_type", icon="TRIA_LEFT", text="Prev")
        x.change_row = False
        x.invert_sense = True
        
        x = row.operator("shortbrush.toggle_type", icon="TRIA_RIGHT", text="Next")
        x.change_row = False
        x.invert_sense = False

        x = col.operator("shortbrush.toggle_type", icon="TRIA_DOWN", text="")
        x.change_row = True
        x.invert_sense = False


#        col.separator()
#        col.operator("sculpt.optimize")
#        if (sculpt.detail_type_method == 'CONSTANT'):
#            col.operator("sculpt.detail_flood_fill")
        

        box = layout.box()
        box.label(text="Mask mode")
        col = box.column(align=True)
        x = col.operator("paint.brush_select", text="Toggle")
        x.paint_mode="SCULPT"
        x.sculpt_tool="MASK"
        x.toggle=True
        x.create_missing=True

        r = col.row(align=True)
        x = r.operator("paint.mask_flood_fill", text="Fill")
        x.mode = 'VALUE'
        x.value = 1

        x = r.operator("paint.mask_flood_fill", text="Invert")
        x.mode = 'INVERT'

plug_keymap = []

def register():
    bpy.utils.register_module(__name__)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new('Sculpt', space_type='EMPTY', region_type='WINDOW', modal=False)

    kmi = km.keymap_items.new(ToggleSculpt.bl_idname, 'X', 'PRESS')
    kmi.properties.invert_sense = False
    kmi.properties.change_row = False    
    kmi = km.keymap_items.new(ToggleSculpt.bl_idname, 'X', 'PRESS', ctrl=True)
    kmi.properties.invert_sense = True
    kmi.properties.change_row = False    
    kmi = km.keymap_items.new(ToggleSculpt.bl_idname, 'X', 'PRESS', shift=True)
    kmi.properties.change_row = True
    kmi.properties.invert_sense = False
    kmi = km.keymap_items.new(ToggleSculpt.bl_idname, 'X', 'PRESS', shift=True, ctrl=True)
    kmi.properties.change_row = True
    kmi.properties.invert_sense = True


def unregister():
    # handle the keymap
    wm = bpy.context.window_manager
    for km in plug_keymap:
        wm.keyconfigs.addon.keymaps.remove(km)
    plug_keymap.clear()

if __name__ == "__main__":
    register()
