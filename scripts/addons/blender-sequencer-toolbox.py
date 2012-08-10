import bpy
import os
from bpy import context as ctx
from bpy import ops
from time import sleep
from itertools import count

'''
class INFO_MT_actor(bpy.types.Operator):
    bl_idname = "select_actor"
    bl_label = "Select Actor"
    bl_options = {'REGISTER', 'UNDO'}                              # Options for this panel type
    mystring = bpy.props.StringProperty(name="MyString", description="...", maxlen=1024, default="my string")

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        bpy.data.objects[self.mystring].select = True
        return {'FINISHED'}

class INFO_MT_actors(bpy.types.Menu):
    bl_label = "Actors"
    bl_description = "Chose an actor ;)"

    def draw(self, context):
        layout = self.layout
        op = layout.operator("select_actor")
        op.mystring = 'coin'
        layout.separator()
'''

def act_strip(context):
    try:
        return context.scene.sequence_editor.active_strip
    except AttributeError:
        return None

class CenterStrip(bpy.types.Operator):
    bl_idname = "bpt.centerstrip"
    bl_label = "Center"
    bl_description = "Center selected strip at current frame"

    def execute(self, context):
        cur_frame = context.scene.frame_current
        sel = bpy.context.selected_editable_sequences[0]

        length = (sel.frame_final_end-sel.frame_final_start)
        offset = cur_frame - (length/2) - sel.frame_final_start
        ops.transform.seq_slide(value=(offset, 0))
        return {'FINISHED'}


class _Fader(bpy.types.Operator):
    from_start = None

    def set_vol(self, seq, vol, offset):
        bpy.context.scene.frame_current = \
                (seq.frame_final_start if self.from_start else seq.frame_final_end) \
                + offset

        seq.volume = vol
        seq.keyframe_insert('volume')

    def execute(self, context):

        all_seqs = list(bpy.context.selected_editable_sequences)

        if all_seqs:
            bpy.ops.sequencer.select_all(action='DESELECT')

            for seq in all_seqs:
                seq.name = seq.name
                if seq.type == 'SOUND':
                    self.set_fade(seq)
                elif seq.type == 'META':
                    all_seqs.extend(seq.sequences)

        return {'FINISHED'}

class FadeIn(_Fader):
    bl_idname = "bpt.audio_fade_in"
    bl_label = "Fade Audio in"
    bl_description = "Fade in selected strip"
    from_start = True

    def set_fade(self, seq):
        self.set_vol(seq, 0.0, 0)
        self.set_vol(seq, 1.0, bpy.context.scene.fancy_nb_frames)


class FadeOut(_Fader):
    bl_idname = "bpt.audio_fade_out"
    bl_label = "Fade Audio out"
    bl_description = "Fade out selected strip"
    from_start = False

    def set_fade(self, seq):
        self.set_vol(seq, 1.0, -bpy.context.scene.fancy_nb_frames)
        self.set_vol(seq, 0.0, 0)


class StripGaps(bpy.types.Operator):
    bl_idname = "bpt.stripgaps"
    bl_label = "Pack strips"
    bl_description = "Make selected strips consecutive"

    def execute(self, context):
        prev = None
        seq = context.selected_editable_sequences

        
        seqs = {}
        for s in seq:
            if s.channel not in seqs:
                seqs[s.channel] = []
            seqs[s.channel].append(s)
        
        for seq in seqs.values():
            prev = None
            seq.sort(key=lambda i: i.frame_final_start)
            for x in seq:
                if None is not prev:
                    x.frame_start = prev.frame_final_start \
                            + (prev.frame_final_end - prev.frame_final_start) \
                            - x.frame_offset_start
                prev = x
        return {'FINISHED'}

class SetProxies(bpy.types.Operator):
    bl_idname = "bpt.setproxies"
    bl_label = "Quick proxies!"
    bl_description = "Set 25% and 50% proxies use active strip properties if set"

    def execute(self, context):
        active = act_strip(bpy.context)
        if active.use_proxy:
            custom_dir = active.use_proxy_custom_directory
            dflt = { prop:getattr(active.proxy, prop)
                    for prop in 'directory build_25 build_50 timecode quality'.split()}
            dflt['directory'] = dflt['directory'].rsplit(os.path.sep, 1)[0]
        else:
            custom_dir = False
            dflt = {
                    'build_25': True,
                    'build_50': True,
                    'timecode': "FREE_RUN"
                    }
        for s in context.selected_editable_sequences:
            if s.type == 'MOVIE':
                s.use_proxy = True
                s.use_proxy_custom_directory = custom_dir
                for k, v in dflt.items():
                    if k == 'directory':
                        v = os.path.join(v, s.name)
                    setattr(s.proxy, k, v)

        bpy.ops.sequencer.rebuild_proxy()
        return {'FINISHED'}

class GoToStart(bpy.types.Operator):
    bl_idname = "bpt.gotostart"
    bl_label = "strip"
    bl_description = "Jump to start of current strip"

    def execute(self, context):
        context.scene.frame_current = context.selected_editable_sequences[0].frame_final_start
        return {'FINISHED'}


class GoToEnd(bpy.types.Operator):
    bl_idname = "bpt.gotoend"
    bl_label = "strip"
    bl_description = "Jump to end of current strip"

    def execute(self, context):
        context.scene.frame_current = context.selected_editable_sequences[0].frame_final_end
        return {'FINISHED'}


class NextMark(bpy.types.Operator):
    bl_idname = "bpt.marker_next"
    bl_label = "mark"
    bl_description = "Jump to next marker"

    def execute(self, context):
        mark = list(bpy.context.scene.timeline_markers)
        mark.sort(key=lambda x: x.frame)
        for n in mark:
            if n.frame > context.scene.frame_current:
                context.scene.frame_current = n.frame
                break
        return {'FINISHED'}


class PrevMark(bpy.types.Operator):
    bl_idname = "bpt.marker_prev"
    bl_label = "mark"
    bl_description = "Jump to previous marker"

    def execute(self, context):
        mark = list(bpy.context.scene.timeline_markers)
        mark.sort(reverse=True, key=lambda x: x.frame)
        print([(x.name, x.frame) for x in mark])
        for n in mark:
            if n.frame < context.scene.frame_current:
                context.scene.frame_current = n.frame
                break
        return {'FINISHED'}


class BiduleOnAll(bpy.types.Operator):
    bl_idname = "bpt.bidule_all"
    bl_label = "Adapt video file paths"
    bl_description = """Update file path according
to the chosen folder"""

    def execute(self, context):
        MY_PREFIX = bpy.context.scene.bidule_name
        PIVOT = next(x for x in reversed(MY_PREFIX.split('/')) if x)
        all_strips = list(context.selected_editable_sequences)

        for seq in all_strips:
            print (seq)
            if seq.type == 'META':
                all_strips.extend(seq.sequences)
            elif seq.type in ('MOVIE', 'SOUND'):

                try:
                    garbage, suffix = seq.filepath.split('DVD plan')
                except:
                    continue
                else:
                    seq.filepath = MY_PREFIX+suffix
                    if seq.filepath.endswith('.mpg'):
                        seq.filepath += '.avi'

                        if seq.type == 'movie':
                            seq.use_deinterlace = False

        return {'FINISHED'}

#        sel.frame_final_start = cur_frame - (length/2)
#        sel.frame_final_end = sel.frame_final_start + length
#
#        w = bpy.data.scenes["Samedi_rodas"].sequence_editor.sequences_all["WhiteTimeGradient"]
#        self.report( "INFO", "Biduling with %s strip"%w )
#        seq = ctx.selected_editable_sequences
#        return {'FINISHED'}


class NovelasEffect(bpy.types.Operator):

    bl_idname = "bpt.effect_novelas"
    bl_label = "Effect novelas"
    bl_description = "Apply the effect on selected strip"

    def execute(self, context):
        #cityName = bpy.context.scene.city_name
        #self.report( "INFO", "BOOOOOM!  You just destroyed the city of "
        #      + cityName )
        for x in ctx.selected_editable_sequences:
            self._apply_effect([x])
        #self._apply_effect(ctx.selected_editable_sequences)            
        return {'FINISHED'}

    def _apply_effect(self, strips):

        try:
            orig_max = max(x.channel for x in strips)
        except ValueError:
            orig_max = strips[0].channel

        strips.sort(key=lambda x: x.frame_final_start)

#        print("Bluring: %s"%(', '.join(x.name for x in strips)))

        base_chan = orig_max
        cnt = count()

        for strip in strips:

            bpy.ops.sequencer.select_all(action='DESELECT')

            strip.select = True
            speed_factor = 2.0

            # double the length
            length = ctx.selected_editable_sequences[0].frame_final_duration
            ctx.selected_editable_sequences[0].frame_final_end += length*(speed_factor-1.0)

            ops.sequencer.effect_strip_add(channel=base_chan+next(cnt), replace_sel=True, type="SPEED")
            x = ctx.selected_editable_sequences[0]
            x.multiply_speed = 1/speed_factor
            x.speed_factor = 1.0
            x.scale_to_length = False
            x.channel = base_chan+next(cnt)
            x.use_default_fade = False
            x.use_as_speed = True
            x.color_saturation = 0.2
            ops.sequencer.effect_strip_add(filepath="", relative_path=False, channel=base_chan+3, replace_sel=True, type="GLOW")
            x = ctx.selected_editable_sequences[0]
            x.channel = base_chan+next(cnt)
            #x.select = False

class Sequencer_effects_edit(bpy.types.Panel):
    bl_label = "Toolbox"
    bl_description = "A collection of useful or fancy effects"
    bl_region_type = "UI"
    bl_space_type = 'SEQUENCE_EDITOR'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        frame_current = scene.frame_current

#        try:            n = int(open('/tmp/count.txt').read())
#        except Exception:
#            n = 0
#        icons = [x.strip() for x in open('/tmp/icons.txt').read().split()]
#        print("coin {} : {}".format(n, icons[n]))

        # My custom row
        row = layout.row()
        row.operator( "bpt.effect_novelas", icon='PARTICLES' )
        layout.separator()
        row = layout.row(align=True)
        row.prop(scene, 'fancy_nb_frames')
        row.operator("bpt.audio_fade_in", icon='OUTLINER_DATA_SPEAKER')
        row.operator("bpt.audio_fade_out", icon='OUTLINER_DATA_SPEAKER')
        row = layout.row(align=False)
        row.operator( "bpt.centerstrip" , icon='MOD_WARP')
        row = layout.row(align=True)
        row.operator( "bpt.stripgaps" , icon='GO_LEFT')
        row = layout.row()
        row.label(text="Jump to")
        row.alignment = "RIGHT"
        row.operator( "bpt.gotostart" , icon='FRAME_PREV')
        row.operator( "bpt.gotoend" , icon='FRAME_NEXT')
        row.operator('bpt.marker_prev', icon='PLAY_REVERSE')
        row.operator('bpt.marker_next', icon='PLAY')
        row = layout.row()
        row.operator( "bpt.setproxies" , icon='GHOST_ENABLED')
        '''
        row = layout.row(align=False)
        col = row.column()
        col.prop( scene, "bidule_name" ) # the text field
        row.operator( "bpt.bidule_all", icon='MODIFIER')
        row = layout.row()
        sub = row.row(align=True)
        sub.menu('INFO_MT_actors')
        '''
#        open('/tmp/count.txt', 'w').write("{}".format(n+1))

    @staticmethod
    def has_sequencer(context):
        return (context.space_data.view_type == 'SEQUENCER') or (context.space_data.view_type == 'SEQUENCER_PREVIEW')

    @classmethod
    def poll(cls, context):
        return cls.has_sequencer(context) and (act_strip(context) is not None)

def register():
    bpy.types.Scene.bidule_name = bpy.props.StringProperty(
                    name="DVD plan folder",
                    description = "Bidule's name",
                    default='//Bureau/Bapteme/DVD plan',
                    subtype="DIR_PATH",
                    )
    bpy.types.Scene.fancy_nb_frames = bpy.props.IntProperty(
                    name="nb. frames",
                    description = "Number of frames to fade",
                    default=30,
                    )


    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)

bl_info = {
    'name': 'Sequencer toolbox',
    'author': 'fdev31, fab31',
    'version': (1, 0, 0),
    'blender': (2, 6, 2),
    'api': 32738,
    'location': 'Sequencer > Properties',
    'warning': '',
    'description': 'Add a couple of simple but useful buttons to sequencer.',
    'wiki_url': '',
    'tracker_url': '',
    'category': 'Sequencer'}

if __name__ == '__main__':
    register()

