bl_info = {
    "name": "Scanner data importer",
    "author": "Fabien Devaux (fdev31)",
    "version": (1, 0, 0),
    "blender": (2, 79, 0),
    "location": "3D Window > Tool Shelf > Meshify slices",
    "description": "Allows conversion of image sequence from DICOM data to be imported as mesh",
    "warning": "",
    "category": "Object",
}

import os
import sys
import json
import time
import itertools
from random import random

# requires:
# scikit-image
# numpy

import numpy as np
from skimage import measure # find contours
from skimage.io import imread

import bpy
import bmesh
from bpy.types import Panel
from mathutils import Vector, geometry, kdtree


LAYERS = None
REF_SIZE = None

def get_z_from_layer(layer):
    return ((LAYERS - layer)/LAYERS)*REF_SIZE

def listing(path):
    return sorted((x for x in os.listdir(path) if x.endswith('.png') and not x.startswith('contour_')))


class SimpleOperator(bpy.types.Operator):
    bl_idname = "object.meslicify"
    bl_label = "Import slices"
    bl_options = {'REGISTER','UNDO'}

    decimation_factor = bpy.props.IntProperty(name="Decimation factor", default=2, min=1, max=100)
    face_tolerance = bpy.props.IntProperty(name="Face tolerance", default=50, min=1, max=1000)
    max_tension = bpy.props.FloatProperty(name="Max tension", default=20.0, min=0.01, max=1000)
    simplification_factor = bpy.props.FloatProperty(name="Simplify", default=0, min=0, max=2)
    scale = bpy.props.FloatProperty(name="Scale", default=1, min=0.01, max=10)

    contours_max = bpy.props.IntProperty(name="Feat. detection: max / slice", default=100, min=1, max=500)
    contours_min_size = bpy.props.IntProperty(name="Feat. detection minimum size", default=200, min=3, max=20000)
    contours_threshold = bpy.props.FloatProperty(name="Threshold", default=0.01, min=0, max=1)

    remove_doubles = bpy.props.BoolProperty(name="Remove doubles", default=True)

    def process_contours(self, layers, wm):
        global RANGE
        _c = itertools.count() # vertex count
        kdtrees = []
        real_contours = []

        for num, layer in enumerate(layers):
            wm.progress_update(num)
            real_contours.append( [] )
            tree = kdtree.KDTree(sum(contour['size'] for contour in layer))

            if RANGE:
                if num < RANGE[0] or num > RANGE[1]:
                    tree.balance()
                    kdtrees.append(tree)
                    continue

            z = get_z_from_layer(num)

            for n, contour in enumerate(layer):

                if contour['size'] < self.contours_min_size:
                    continue
                if n > self.contours_max:
                    break

                this_contour = []
                prev_vert = None
                prev_tan = None
                for rel_nr, v in enumerate(contour['coords']):
                    skipped = False
                    if prev_vert:
                        try:
                            tan = (v[1]-prev_vert[1]) / (v[0]-prev_vert[0])
                        except ZeroDivisionError:
                            skipped = True
                            tan = 0
                        else:
                            if rel_nr%self.decimation_factor or (prev_tan and self.simplification_factor and abs(prev_tan-tan) <= self.simplification_factor):
                                skipped = True
                        prev_tan = tan
                    prev_vert = v
                    if not skipped:
                        co = (v[0], v[1], z)
                        tree.insert(co, next(_c))
                        this_contour.append(co)
                real_contours[-1].append(this_contour)

            tree.balance()
            kdtrees.append(tree)

        self.kdtrees = kdtrees
        return real_contours

    def gen_mesh(self, real_contours, wm):
        verts = []
        edges = []
        faces = []
        vert_count = itertools.count()

        tot_vtx = itertools.count()
        ref_offset = -REF_SIZE/2

        for layer, contours in enumerate(real_contours): # from bottom to top
            wm.progress_update(layer)
            if RANGE:
                if layer < RANGE[0]:
                    continue
                elif layer > RANGE[1]:
                    continue
            z = get_z_from_layer(layer)

            vx_idx = 0
            for contour in contours:
                #print("C %d"%(len(contour)))

                for p_i, p in enumerate(contour):
                    # add vertex                    
                    verts.append(( # inverted X & Y for blender
                        self.scale * (p[1]+ref_offset)/REF_SIZE,
                        self.scale * (p[0]+ref_offset)/REF_SIZE,
                        self.scale * (1 - (z/REF_SIZE))) )

                    former_bottom_idx = vx_idx
                    # find the two nearest vertices & make two triangles
                    bottom_vx, vx_idx, dist = self.get_nearest(layer-1, p[0], p[1])
                    i = next(tot_vtx)

                    if  dist != None and dist < self.max_tension:
                        # add edge
                        if p_i:
                            left_idx = i-1
                        else: # if first vertex, link last
                            left_idx = i+len(contour)-1
                            #former_bottom_idx = get_nearest(layer-1, contour[-1][0], contour[-1][1])[1]

                        edges.append((left_idx, i))

                        if bottom_vx:
                            edges.append( (i, vx_idx) )

                            if former_bottom_idx == vx_idx: # tri
                               faces.append( (left_idx, vx_idx, i) )
                            else:
                                if p_i > 0:
                                    faces.append( [i, left_idx] + list(range(former_bottom_idx, vx_idx+1)) )
        return verts, edges, faces

    #cf: https://www.blender.org/api/blender_python_api_2_73_release/mathutils.kdtree.html
    def get_nearest(self, layer, x, y):
        return self.kdtrees[layer].find([x,y, get_z_from_layer(layer)])

    def execute(self, context):
        global LAYERS
        global REF_SIZE
        global RANGE
        obj = context.selected_objects[0]
        print("Reloading state...")
        REF_SIZE = obj.source_slices_size # Z dimmension will be adapted accordingly
        DIM = [REF_SIZE, REF_SIZE, obj.source_slices_nr]
        LAYERS = DIM[2]
        PATH = obj.source_slices # os.path.dirname(context.scene.render.filepath)
        if obj.partial_slices:
            RANGE = [obj.partial_slices_start, obj.partial_slices_end]

        c_cache_file = os.path.join(PATH, 'contours.js')
        if os.path.exists(c_cache_file) and not 'REREAD' in os.environ:
            c_cache = json.load(open(c_cache_file))
        else:
            c_cache = False

        all_files = tuple(listing(PATH))

        dirty = not c_cache

        wm = bpy.context.window_manager # notify progress

        if dirty:
            wm.progress_begin(0, len(all_files))
            c_cache = {
                    'contours': []
                    }

            for layer, filename in enumerate(all_files):
                wm.progress_update(layer)
                if RANGE:
                    if layer < RANGE[0]:
                        continue
                    elif layer > RANGE[1]:
                        continue

                sys.stderr.write('\rReading... %30s '%(filename))
                sys.stderr.flush()

                src = imread(os.path.join(PATH, filename))
                try:
                    width, height, depth = src.shape
                    data = np.array([ [src[y][x][0] for x in range(width)] for y in range(height) ])
                except ValueError:
                    width, height = src.shape
                    data = np.array([ [src[y][x] for x in range(width)] for y in range(height) ])

                contours = measure.find_contours(data, self.contours_threshold)
                c_cache['contours'].append([{'size': int(c.size), 'coords': [tuple(pos[:2]) for pos in c]} for c in contours])

            print("Saving...")
            wm.progress_end()
            json.dump(c_cache, open(c_cache_file, 'w'))

        print("\nGenerating K-D Trees")

        wm.progress_begin(0, len(c_cache['contours']))
        real_contours = self.process_contours(c_cache['contours'], wm)
        wm.progress_end()


        print('Generating Mesh data')

        wm.progress_begin(0, len(real_contours))
        verts, edges, faces = self.gen_mesh(real_contours, wm)
        wm.progress_end()

        mesh = bpy.data.meshes.new("Made from slices")
        new_obj = bpy.data.objects.new("FromSlices", mesh)

        scene = bpy.context.scene
        scene.objects.link(new_obj)  # put the object into the scene (link)
        scene.objects.active = new_obj  # set as the active object in the scene
        new_obj.select = True  # select object

        mesh = new_obj.data
        bm = bmesh.new()

        for i, v in enumerate(verts):
            bm.verts.new(v)  # add a new vert

        bm.verts.ensure_lookup_table() # required to iterate the edges

        for e in edges: # add edges
            bm.edges.new(tuple(bm.verts[c] for c in e))

        for f in faces: # add faces
            if len(f) > 2:
                bm.faces.new(tuple(bm.verts[c] for c in f))

        # make the bmesh the object's mesh
        bm.to_mesh(mesh)
        bm.free()  # always do this when finished

        if self.remove_doubles:
            bpy.ops.object.editmode_toggle()
            bpy.ops.mesh.select_all(action='TOGGLE')
            bpy.ops.mesh.remove_doubles()
            bpy.ops.object.editmode_toggle()

        return {'FINISHED'}

class VIEW3D_PT_tools_Meshify(Panel):
    bl_category = "Tools"
    bl_context = "objectmode"
    bl_label = "Meshify slices"
    bl_idname = "OBJECT_OT_slicify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'

    def draw(self, context):
        layout = self.layout
        obj = context.object
        if obj:
            col = layout.column(align=True)
            col.prop(obj, "source_slices", expand=True, text="")
            col.prop(obj, "source_slices_size", expand=True, text="Images size")
            col.prop(obj, "source_slices_nr", expand=True, text="Number of images")

            col.prop(obj, "partial_slices", expand=True, text="Render subrange")
            scol = col.row(align=True)
            scol.active = obj.partial_slices
            scol.prop(obj, "partial_slices_start",expand=True, text="Start")
            scol.prop(obj, "partial_slices_end", expand=True, text="End")

            col = layout.column(align=True)
            col.operator("object.meslicify", emboss=True)

def register():
    bpy.utils.register_class(SimpleOperator)
    bpy.utils.register_class(VIEW3D_PT_tools_Meshify)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_tools_Meshify)
    bpy.utils.unregister_class(SimpleOperator)

if __name__ == "__main__":

    bpy.types.Object.source_slices =  bpy.props.StringProperty(default="/tmp/", subtype="DIR_PATH")
    bpy.types.Object.source_slices_size = bpy.props.IntProperty(default=512, min=16, max=1024)
    bpy.types.Object.source_slices_nr = bpy.props.IntProperty(default=320, min=2, max=1024)
    bpy.types.Object.partial_slices_start = bpy.props.IntProperty(default=0, min=0, max=320)
    bpy.types.Object.partial_slices_end = bpy.props.IntProperty(default=0, min=0, max=320)
    bpy.types.Object.partial_slices = bpy.props.BoolProperty()
    register()

