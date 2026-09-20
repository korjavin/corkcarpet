# Builds one cork-mat tile in Blender. Run via blender-mcp execute_code or Blender text editor.
# Frame floats on the corks: corks protrude ~5 mm below the plastic and touch the floor themselves.
import bpy, bmesh, math, mathutils

SOCKET_D = 20.0   # calibrated 2026-09-10: PLA test, middle of 3-row; caliper reads 20.0
PITCH    = 25.0   # cork top Ø23 max + 2 mm gap
COLS, ROWS = 5, 5 # 25 corks/tile, 4 tiles = 100; 2nd row of tiles rotated 180° (odd rows). 138x113 mm
TUBE_D   = 26.0   # outer Ø, overlaps neighbour by 1 mm
GRIP     = 15.0   # tube height = LEADIN_H cone + cylindrical grip; open bottom, no lip
LEADIN_H = 5.0    # conical entry height
LEADIN_D = 22.5   # socket Ø at the very top (cone narrows to SOCKET_D)
DOWEL    = 4.0    # square dowel joining tiles, sits in wall tunnels at a seam
TUNNEL   = DOWEL + 0.4
TUNNEL_Z = 2.0    # tunnel bottom above tube bottom
BELOW    = 5.0    # how far corks stick out under the frame (assembly spacer height)
H = GRIP
ROW_DY = PITCH * math.sqrt(3) / 2

def centers():
    for r in range(ROWS):
        for c in range(COLS):
            yield (c * PITCH + (PITCH / 2 if r % 2 else 0), r * ROW_DY)

def cyl(r, depth, loc, v=96):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=depth, location=loc)
    return bpy.context.object

def cone(r1, r2, depth, loc, v=96):
    bpy.ops.mesh.primitive_cone_add(vertices=v, radius1=r1, radius2=r2, depth=depth, location=loc)
    return bpy.context.object

def box(sx, sy, sz, loc, rz=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=(0, 0, rz))
    o = bpy.context.object; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True); return o

def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join(); objs[0].name = name; return objs[0]

def boolean(target, cutter, op):
    m = target.modifiers.new(op, 'BOOLEAN'); m.operation = op; m.object = cutter
    m.solver = 'EXACT'; m.use_self = True
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter)

def nonmanifold(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    n = sum(1 for e in bm.edges if not e.is_manifold); bm.free(); return n

def build(name='tile', pts=None, diams=None, clip=True):
    for o in list(bpy.data.objects):
        if o.name.startswith(name): bpy.data.objects.remove(o)
    pts = pts or list(centers())
    diams = diams or [SOCKET_D] * len(pts)
    outers = [cyl(TUBE_D / 2, H, (x, y, H / 2)) for x, y in pts]
    body = outers[0]; body.name = name
    if len(outers) > 1:
        boolean(body, join(outers[1:], name + '_add'), 'UNION')
    cut = []
    for (x, y), sd in zip(pts, diams):
        cut.append(cyl(sd / 2, H + 2, (x, y, H / 2)))                                    # through socket
        cut.append(cone(sd / 2, LEADIN_D / 2 + .01, LEADIN_H + .01,
                        (x, y, H - LEADIN_H / 2 + .005)))                                 # conical lead-in
        for k in range(3):                                                               # dowel tunnels
            cut.append(box(TUBE_D + 2, TUNNEL, TUNNEL, (x, y, TUNNEL_Z + TUNNEL / 2), k * math.pi / 3))
        if clip:  # shave the 0.5 mm the tube pokes past its hex cell where no neighbour: tiles then nest at PITCH
            for k in range(6):
                a = k * math.pi / 3; nx, ny = x + PITCH * math.cos(a), y + PITCH * math.sin(a)
                if any(math.hypot(px - nx, py - ny) < 1 for px, py in pts): continue
                cut.append(box(5, PITCH / math.sqrt(3), H + 2,
                               (x + (PITCH / 2 + 2.5) * math.cos(a), y + (PITCH / 2 + 2.5) * math.sin(a), H / 2), a))
    boolean(body, join(cut, name + '_cut'), 'DIFFERENCE')
    return body, nonmanifold(body)

def build_dowel(name='dowel', w=DOWEL, l=8):
    # 4x4x8: spans both 3 mm walls at a seam, 1 mm into each cork; corks keep it in. 3 per seam.
    # w=3.4: for unclipped tiles on the straight seam, where diagonal tunnels are 0.57 mm off-axis.
    for o in list(bpy.data.objects):
        if o.name.startswith(name): bpy.data.objects.remove(o)
    d = box(l, w, DOWEL, (0, 0, DOWEL / 2)); d.name = name; return d

def build_dowel_wedge(name='dowel_wedge', s1=2.0, s2=5.0, l=10):
    # square wedge pin for old+new seams and sloppy tunnels: pushed tip-first through both walls, the widening
    # tail jams in the near wall (tunnel 4.4 modelled, ~4.2 printed) while the thin part sits in the far one
    # with ~0.8 mm slack for the off-axis tunnel. s1 x s1 tip -> s2 x s2 tail, flat bottom: prints lying down.
    # 3 per seam, dowel_wedge_x12.stl.
    for o in list(bpy.data.objects):
        if o.name.startswith(name): bpy.data.objects.remove(o)
    d = box(l, 1, 1, (l / 2, 0, 0)); d.name = name
    for v in d.data.vertices:
        k = s2 if v.co.x > 0 else s1
        v.co.y *= k; v.co.z = (v.co.z + 0.5) * k
    return d

def build_spacer(name='spacer'):
    # put 2-3 under the frame while pressing corks in, so they stick out BELOW mm
    for o in list(bpy.data.objects):
        if o.name.startswith(name): bpy.data.objects.remove(o)
    s = box(60, 12, BELOW, (0, 0, BELOW / 2)); s.name = name; return s

def build_test(name='test_tubes'):
    # 7 tubes, 2 staggered rows, socket 18.5..21.5 step 0.5; notch marks the 18.5 end
    D = [18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5]
    pts = [(i // 2 * PITCH + (PITCH / 2 if i % 2 else 0), ROW_DY if i % 2 else 0) for i in range(len(D))]
    body, nonman = build(name, pts, D)
    notch = box(4, 4, 6, (-TUBE_D / 2, 0, H)); boolean(body, notch, 'DIFFERENCE')
    return body, nonman
