"""Aquarium decor: lighthouse, torii gate, crossed coral, starfish, rock stands.

Each item returns dict(parts=[(name, colour, solid_on_bed)], assembly=[(solid, colour)]).
All hollow parts are vented so no air gets trapped under water.
"""
import math
import numpy as np
from lib import (mesh_arrays, CrossSection, Manifold, CLEAR, offset, union, circle, rect, poly, smooth,
                 stroke, extrude, chamfered, cyl, box, to_bed, rock_hull, SEG)
from fish import fork_rod, CORE_T


def _item(parts, assembly):
    return dict(parts=parts, assembly=assembly)


def _ring(r_out, r_in, h, z0=0, r_out2=None, r_in2=None, seg=SEG):
    return cyl(r_out, h, z0, r2=r_out2, seg=seg) - cyl(r_in, h + 0.02, z0 - 0.01, r2=r_in2, seg=seg)


def _radial_cut(shape2d, angle_deg, r_from, depth):
    """Cut a 2D shape (drawn in XZ, x = sideways, y = height) radially through a wall."""
    m = Manifold.extrude(shape2d, depth).rotate((90, 0, 0))      # extrude along -y ... after rotate
    m = m.translate((0, -r_from + depth, 0)).mirror((0, 1, 0))
    return m.rotate((0, 0, angle_deg))


def _arch(w, h):
    """Pointed (gothic) arch: no overhang beyond 45deg so it prints without support."""
    return poly([(-w / 2, 0), (w / 2, 0), (w / 2, h - w / 2), (0, h), (-w / 2, h - w / 2)])


# ------------------------------------------------------------------ rocks
def _tent_cavity(rx, ry, h_apex, z_bottom=-1):
    """45-degree tent-shaped cavity: printable without support, open at the bottom."""
    half = min(ry, h_apex)
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            pts.append((sx * rx, sy * half, z_bottom))
    pts += [(-(rx - half), 0, z_bottom + half + 1), ((rx - half), 0, z_bottom + half + 1)]
    return Manifold.hull_points(np.array(pts, float))


def _inner_offset(hull, t):
    """Convex hull shrunk by t (intersect all face planes moved inwards)."""
    v, f = mesh_arrays(hull)
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    d = (n * tri[:, 0]).sum(1)
    planes = []
    for ni, di in zip(n, d):
        if ni[2] < -0.99:          # keep the bottom open
            continue
        if any(np.dot(ni, pn) > 0.9999 and abs(di - pd) < 1e-3 for pn, pd in planes):
            continue
        planes.append((ni, di))
    inner = hull.translate((0, 0, -1)) + hull
    for ni, di in planes:
        inner = inner.trim_by_plane(tuple(-ni), -(di - t))
    return inner


def hollow(lumps, t=2.4, max_z=None, keep_solid=None):
    """Open-bottom cavity for a rock made of convex lumps, with a roof made of
    45-degree cones so the inside prints without supports. Returns (cavity, vent_xy)."""
    inner = union([_inner_offset(h, t) for h in lumps])
    if max_z is not None:
        inner = inner.trim_by_plane((0, 0, -1), -max_z)
    fp = inner.slice(0.05)
    rings = [(d, offset(fp, -d)) for d in np.arange(1.0, 40.0, 1.0)]
    x0, y0, x1, y1 = fp.bounds()
    grid = {}
    for x in np.arange(x0, x1, 5.0):
        for y in np.arange(y0, y1, 5.0):
            dd = 0
            for d, r in rings:
                if r.is_empty() or (r ^ circle(0.05, (x, y), 6)).is_empty():
                    break
                dd = d
            if dd >= 3:
                grid[(round(x, 2), round(y, 2))] = dd
    cones = [cyl(d + 1.0, d + 1.0, -1.0, r2=0.0, c=p, seg=24) for p, d in grid.items()]
    cav = (inner + Manifold.extrude(fp, 1.2).translate((0, 0, -1.1))) ^ union(cones)
    if keep_solid is not None:
        cav = cav - keep_solid
    # vents at the highest cone tips so no air is trapped
    vents = []
    for p, d in sorted(grid.items(), key=lambda kv: -kv[1]):
        if d < 6:
            break
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > 16 ** 2 for q in vents):
            vents.append(p)
    return cav, vents


def rock_cluster(lumps):
    """Several overlapping low-poly lumps = a more natural reef rock."""
    hulls = [rock_hull(rx, ry, h, seed).translate((cx, cy, 0)) for cx, cy, rx, ry, h, seed in lumps]
    return union(hulls), hulls


def rock(lumps, h, sockets=(), socket_size=7.0, socket_depth=14,
         flat_top=None, extra_solid=None):
    """Rock base: thin shell with an open, vented bottom cavity + square rod sockets."""
    m = union(lumps)
    vents = []
    if flat_top is not None:
        cx, cy, r, z = flat_top
        m = m - cyl(r, 100, z, c=(cx, cy))
    solids = []
    s = socket_size + 2 * CLEAR + 0.1
    zsock = [_surface_z(m, x, y) for (x, y) in sockets]
    for (x, y), zs in zip(sockets, zsock):
        # sleeve around the socket with a 45-degree pyramid underneath (printable)
        w = s / 2 + 2.4
        zb = zs - socket_depth - 2.4
        solids.append(Manifold.hull(box(x - w, y - w, zb, x + w, y + w, h + 10) +
                                    box(x - 0.1, y - 0.1, zb - w, x + 0.1, y + 0.1, zb)))
    if extra_solid is not None:
        solids.append(extra_solid)
    cav, vents = hollow(lumps, max_z=(flat_top[3] - 2.4) if flat_top else None,
                        keep_solid=union(solids) if solids else None)
    m = m - cav
    for (x, y), zs in zip(sockets, zsock):
        m = m - box(x - s / 2, y - s / 2, zs - socket_depth, x + s / 2, y + s / 2, h + 10)
    for (x, y) in vents:
        if extra_solid is not None:
            b = extra_solid.bounding_box()
            if b[0] - 3 < x < b[3] + 3 and b[1] - 3 < y < b[4] + 3:
                continue
        if all((x - a) ** 2 + (y - b) ** 2 > 8 ** 2 for a, b in sockets):
            m = m - cyl(1.5, 100, 2, c=(x, y), seg=16)
    return m, zsock


def _surface_z(m, x, y):
    """Height of the rock top at (x, y) (min over the socket footprint)."""
    zs = []
    for dx in (-3.5, 0, 3.5):
        for dy in (-3.5, 0, 3.5):
            col = m ^ box(x + dx - 0.05, y + dy - 0.05, -1, x + dx + 0.05, y + dy + 0.05, 200)
            if not col.is_empty():
                zs.append(col.bounding_box()[5])
    return min(zs) if zs else 10


def rock_stands():
    big_sockets = [(-34, -6), (0, 7), (34, -4)]
    _, big_lumps = rock_cluster([(-30, -4, 32, 28, 25, 7), (4, 6, 30, 26, 19, 8), (34, -4, 28, 24, 28, 9)])
    big, big_z = rock(big_lumps, 28, sockets=big_sockets)
    small_sockets = [(-14, 3), (15, -4)]
    _, small_lumps = rock_cluster([(-14, 2, 28, 24, 25, 11), (16, -4, 26, 24, 19, 12)])
    small, small_z = rock(small_lumps, 25, sockets=small_sockets)
    rods = [(L, fork_rod(L)) for L in (45, 65, 85, 105, 125)]
    parts = [("rock_large", "gray", big),
             ("rock_small", "gray", small)]
    for L, r in rods:
        parts.append((f"rod_{L}mm", "black", to_bed(r)))
    item = _item(parts, [(big, "gray"), (small.translate((0, 90, 0)), "gray")])
    item["big"] = (big, list(zip(big_sockets, big_z)))
    item["small"] = (small, list(zip(small_sockets, small_z)))
    item["rods"] = rods
    return item


# ------------------------------------------------------------------ lighthouse
LH_R0, LH_R1, LH_H, LH_N, LH_W = 22.0, 14.0, 100.0, 5, 3.0
SPIG_H = 3.0


def _lh_r(z):
    return LH_R0 + (LH_R1 - LH_R0) * z / LH_H


def _lh_ring(i):
    h = LH_H / LH_N
    za, zb = i * h, (i + 1) * h
    ra, rb = _lh_r(za), _lh_r(zb)
    m = _ring(ra, ra - LH_W, h, 0, r_out2=rb, r_in2=rb - LH_W, seg=72)
    # spigot on top (inner half of the wall)
    m = m + _ring(rb - LH_W / 2 - CLEAR, rb - LH_W, SPIG_H, h, seg=72)
    # socket underneath (every ring sits on a spigot, ring 0 sits on the rock's spigot)
    m = m - _ring(ra - LH_W / 2, ra - LH_W - 0.5, SPIG_H + 0.2, -0.01, seg=72)
    if i == 0:   # front door
        m = m - _radial_cut(_arch(9, 15).translate((0, 2.5)), 180, ra + 1, LH_W + 3)
    if i in (1, 3):
        for a in ((150, 270) if i == 1 else (210, 30)):
            m = m - _radial_cut(_arch(4.5, 8).translate((0, 6)), a, ra + 1, LH_W + 3)
    if i == 2:
        m = m - _radial_cut(_arch(4.5, 8).translate((0, 6)), 200, ra + 1, LH_W + 3)
    return m


def _lh_gallery():
    rb = LH_R1
    disc = cyl(19.5, 4.5, 0, seg=72)
    disc = disc - _ring(rb - LH_W / 2, rb - LH_W - 0.4, SPIG_H + 0.2, -0.01, seg=72)
    # vents for the tower (outside the lamp, inside the lantern)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        disc = disc - cyl(1.4, 10, -1, c=(7.2 * math.cos(a), 7.2 * math.sin(a)), seg=16)
    disc = disc + cyl(3.0, 3.0, 4.5, seg=24)              # peg the lamp sits on
    # lantern room with tall windows
    lantern = _ring(10, 8.4, 16, 4.5, seg=72)
    for k in range(6):
        a = 360 / 6 * k
        lantern = lantern - box(-2.6, 0, 7, 2.6, 12, 18.5).rotate((0, 0, a))
    # railing: posts + top rail
    posts = union([cyl(0.9, 6.5, 4.5, c=(17.8 * math.cos(math.radians(a)), 17.8 * math.sin(math.radians(a))), seg=12)
                   for a in range(0, 360, 30)])
    rail = _ring(18.8, 16.8, 1.4, 10.6, seg=72)
    return disc + lantern + posts + rail


def _lh_lamp():
    body = cyl(5.6, 12, 0, seg=48) + cyl(6.4, 1.5, 4.5, seg=48)
    gem = cyl(5.6, 2.5, 12, r2=2.5, seg=48)
    return union([body, gem]) - cyl(3.0 + CLEAR, 3.3, -0.01, seg=24)


def _lh_roof():
    base = cyl(12.5, 2.0, 0, seg=72)
    groove = _ring(10 + CLEAR + 0.05, 8.4 - CLEAR - 0.05, 1.6, -0.01, seg=72)
    cone = cyl(11.5, 9.0, 2.0, r2=2.6, seg=72)
    stem = cyl(1.3, 3.0, 10.5, seg=16)
    finial = cyl(1.3, 1.5, 12.5, r2=2.8, seg=32) + cyl(2.8, 3.0, 14.0, r2=0.3, seg=32)   # no overhangs
    m = union([base, cone, stem, finial]) - groove
    m = m - cyl(1.1, 30, -1, seg=16)           # air vent
    return m


def lighthouse():
    h = LH_H / LH_N
    rings = [_lh_ring(i) for i in range(LH_N)]
    gallery, lamp, roof = _lh_gallery(), _lh_lamp(), _lh_roof()
    top_z = 22
    rock_m, _ = rock([rock_hull(44, 38, 26, 3)], 26, flat_top=(0, 0, 27, top_z))
    # base spigot that the first ring sits on + door step
    rock_m = rock_m + _ring(LH_R0 - LH_W / 2 - CLEAR, LH_R0 - LH_W, SPIG_H, top_z, seg=72)
    rock_m = rock_m + (box(-7, -LH_R0 - 6, top_z - 6, 7, -LH_R0 + 1, top_z + 0.01) ^ rock_hull(44, 38, 26, 3))
    cols = ["red", "white"]
    parts = [(f"lighthouse_ring{i + 1}", cols[i % 2], rings[i]) for i in range(LH_N)]
    parts += [("lighthouse_gallery", "black", gallery), ("lighthouse_lamp", "orange", lamp),
              ("lighthouse_roof", "red", roof),
              ("lighthouse_rock", "gray", rock_m)]
    asm = [(rock_m, "gray")]
    for i, r in enumerate(rings):
        asm.append((r.translate((0, 0, top_z + i * h)), cols[i % 2]))
    zg = top_z + LH_H
    asm += [(gallery.translate((0, 0, zg)), "black"), (lamp.translate((0, 0, zg + 4.5)), "orange"),
            (roof.translate((0, 0, zg + 4.5 + 16 - 1.6)), "red")]
    return _item(parts, asm)


# ------------------------------------------------------------------ torii gate
T_SPAN = 64.0        # pillar spacing
T_H = 72.0           # pillar height
T_NUKI_Z = 52.0
PEG = 4.0


def _pillar():
    m = cyl(4.9, T_H, 0, r2=4.2, seg=48)
    # through-slot for the nuki (tie beam)
    m = m - box(-6, -(3.2 + 2 * CLEAR) / 2, T_NUKI_Z, 6, (3.2 + 2 * CLEAR) / 2, T_NUKI_Z + 7 + 2 * CLEAR)
    # square pegs top and bottom
    top = box(-PEG / 2, -PEG / 2, T_H - 0.01, PEG / 2, PEG / 2, T_H + 4.5)
    s = PEG + 2 * CLEAR + 0.1
    return (m + top) - box(-s / 2, -s / 2, -1, s / 2, s / 2, 5.0)   # socket for the base peg


def _nuki():
    L = T_SPAN + 22
    prof = rect(-L / 2, 0, L / 2, 7)
    return extrude(prof, 3.2)     # printed flat; stands on edge when assembled


def _kasagi_profile():
    L = 112.0
    pts_top, pts_bot = [], []
    for x in np.linspace(-L / 2, L / 2, 41):
        u = abs(x) / (L / 2)
        lift = 9.0 * u ** 2.6
        pts_top.append((x, 15 + lift))
        pts_bot.append((x, 8 + lift * 1.15 - 2.0 * (u > 0.97)))
    kasagi = poly(pts_bot + pts_top[::-1])
    # shimaki: the straight lower beam
    shimaki = rect(-50, 2.5, 50, 9.0)
    # gakuzuka plaque post stub
    return kasagi + shimaki


def _kasagi():
    prof = _kasagi_profile()
    m = extrude(prof, 11)        # printed lying on its face; z = depth
    s = PEG + 2 * CLEAR + 0.1
    for x in (-T_SPAN / 2, T_SPAN / 2):
        m = m - box(x - s / 2, 2.5 - 0.01, 5.5 - s / 2, x + s / 2, 2.5 + 5.0, 5.5 + s / 2)
    # centre socket for the plaque
    m = m - box(-s / 2, 2.5 - 0.01, 5.5 - s / 2, s / 2, 2.5 + 4, 5.5 + s / 2)
    return m


def _plaque():
    """Gakuzuka: the little name plaque between the beams (ivory face, sits in the nuki)."""
    face = rect(-6, 0, 6, 16)
    m = chamfered(face, PEG, ch=0.5, top=True)
    # peg up into the top beam (same thickness as the plaque, so it prints flat)
    m = m + box(-PEG / 2, 16 - 0.01, 0, PEG / 2, 16 + 4, PEG)
    return m


def _foot():
    return _ring(6.8, 4.9 + CLEAR + 0.1, 6, 0, r_out2=6.0, seg=48) + _ring(7.2, 4.9 + CLEAR + 0.1, 1.2, 0, seg=48)


def torii():
    pillar, nuki, kasagi, foot, plaque = _pillar(), _nuki(), _kasagi(), _foot(), _plaque()
    base_h = 9.0
    base = rock_hull(60, 22, 14, seed=21) - box(-100, -100, base_h, 100, 100, 100)
    base = base - _tent_cavity(44, 12, 7)
    for x in (-18, 0, 18):      # air vents at the top of the cavity
        base = base - cyl(1.5, 20, 2, c=(x, 0), seg=16)
    # square pegs the pillars (with their black foot rings) slide onto
    for x in (-T_SPAN / 2, T_SPAN / 2):
        base = base + box(x - PEG / 2, -PEG / 2, base_h - 0.5, x + PEG / 2, PEG / 2, base_h + 4.5)
    parts = [("torii_pillar_L", "red", pillar), ("torii_pillar_R", "red", pillar),
             ("torii_tiebeam", "red", nuki), ("torii_topbeam", "black", kasagi),
             ("torii_plaque", "white", plaque),
             ("torii_foot_L", "black", foot), ("torii_foot_R", "black", foot), ("torii_base", "gray", base)]
    asm = [(base, "gray")]
    z0 = base_h - 4.5   # pillar bottom sits on the base top (z0 + 4.5)
    for x in (-T_SPAN / 2, T_SPAN / 2):
        asm.append((pillar.translate((x, 0, z0 + 4.5)), "red"))
        asm.append((foot.translate((x, 0, base_h)), "black"))
    asm.append((nuki.rotate((90, 0, 0)).translate((0, 1.6, z0 + 4.5 + T_NUKI_Z + CLEAR)), "red"))
    zk = z0 + 4.5 + T_H - 2.5
    asm.append((kasagi.rotate((90, 0, 0)).translate((0, 5.5, zk)), "black"))
    asm.append((plaque.rotate((90, 0, 0)).translate((0, PEG / 2, zk + 2.5 - 16)), "white"))
    return _item(parts, asm)


# ------------------------------------------------------------------ crossed coral
CORAL_T = 3.6
SLOT_W = CORAL_T + 2 * CLEAR + 0.1
LAP = 40.0       # height of the interlocking trunk


def _branches(segs):
    parts = []
    for (x0, y0, r0), (x1, y1, r1) in segs:
        parts.append(CrossSection.batch_hull([circle(r0, (x0, y0), 24), circle(r1, (x1, y1), 24)]))
    return union(parts)


def _coral_plate(segs, slot_from_top, seed):
    shape = (_branches(segs) + rect(-6.5, -6, 6.5, LAP)) ^ rect(-200, -6, 200, 200)
    m = chamfered(shape, CORAL_T, ch=0.5, top=True)
    if slot_from_top:
        m = m - box(-SLOT_W / 2, LAP / 2, -1, SLOT_W / 2, LAP + 0.01, 10)
        m = m - Manifold.hull(box(-SLOT_W / 2, LAP - 0.01, -1, SLOT_W / 2, LAP, 10) +
                              box(-SLOT_W / 2 - 1.2, LAP + 1.2, -1, SLOT_W / 2 + 1.2, LAP + 1.21, 10))
    else:
        m = m - box(-SLOT_W / 2, -7, -1, SLOT_W / 2, LAP / 2, 10)
    # polyp dimples on both faces
    rs = np.random.RandomState(seed)
    x0, y0, x1, y1 = shape.bounds()
    inner = offset(shape, -2.2)
    dimples = []
    for _ in range(140):
        p = (rs.uniform(x0, x1), rs.uniform(10, y1))
        if abs(p[0]) < SLOT_W and p[1] < LAP + 2:
            continue
        if not (inner ^ circle(0.05, p, 6)).is_empty():
            dimples.append(cyl(0.9, 0.8, CORAL_T - 0.8, c=p, seg=12))
            dimples.append(cyl(0.9, 0.8, -0.01, c=p, seg=12))
    if dimples:
        m = m - union(dimples)
    return m


def coral():
    A = [((0, -6, 6.5), (0, LAP, 6.5)),
         ((0, LAP - 4, 4.6), (-12, 58, 3.8)), ((-12, 58, 3.8), (-17, 74, 2.8)),
         ((-12, 58, 3.4), (-4.5, 70, 2.4)),
         ((0, LAP - 4, 4.6), (13, 56, 3.8)), ((13, 56, 3.8), (17, 71, 2.8)),
         ((13, 56, 3.2), (24, 63, 2.4)),
         ((0, 14, 4.6), (-17, 26, 3.8)), ((-17, 26, 3.8), (-25, 44, 2.8)), ((-17, 26, 3.2), (-31, 30, 2.4)),
         ((0, 22, 4.6), (16, 31, 3.8)), ((16, 31, 3.8), (24, 46, 2.8)), ((16, 31, 3.2), (29, 32, 2.4))]
    B = [((0, -6, 6.5), (0, LAP, 6.5)),
         ((0, LAP, 5.0), (2, 62, 3.8)), ((2, 62, 3.8), (-1, 78, 2.8)), ((2, 62, 3.2), (12, 70, 2.4)),
         ((0, 50, 3.6), (-12, 60, 2.6)),
         ((0, 10, 4.6), (16, 22, 3.8)), ((16, 22, 3.8), (21, 41, 2.8)), ((16, 22, 3.2), (28, 25, 2.4)),
         ((21, 41, 3.0), (30, 47, 2.2)),
         ((0, 18, 4.6), (-15, 30, 3.8)), ((-15, 30, 3.8), (-22, 52, 2.8)), ((-15, 30, 3.2), (-27, 32, 2.4))]
    a = _coral_plate(A, True, 5)
    b = _coral_plate(B, False, 6)
    hull = rock_hull(30, 26, 18, 31)
    top = _surface_z(hull, 0, 0)
    base, _ = rock([hull], 18, extra_solid=box(-10, -10, 0, 10, 10, 40))
    sl = 13 + 2 * CLEAR + 0.2
    cross = box(-sl / 2, -SLOT_W / 2, top - 7, sl / 2, SLOT_W / 2, 60) + \
        box(-SLOT_W / 2, -sl / 2, top - 7, SLOT_W / 2, sl / 2, 60)
    base = base - cross
    parts = [("coral_A", "red", a), ("coral_B", "orange", b), ("coral_rock", "gray", base)]
    z = top - 7 + 6
    asm = [(base, "gray"),
           (a.translate((0, 0, -CORAL_T / 2)).rotate((90, 0, 0)).translate((0, 0, z)), "red"),
           (b.translate((0, 0, -CORAL_T / 2)).rotate((90, 0, 0)).rotate((0, 0, 90)).translate((0, 0, z)), "orange")]
    return _item(parts, asm)


# ------------------------------------------------------------------ starfish
def _star(R, r_in, n=5, curve=0.0):
    pts = []
    for i in range(n):
        a = math.radians(90 + 360 * i / n)
        pts.append((R * math.cos(a), R * math.sin(a)))
        b = a + math.pi / n
        pts.append((r_in * math.cos(b), r_in * math.sin(b)))
    return smooth(pts, 10)


def starfish():
    star = _star(46, 15)
    steps = 11
    layers = []
    h0 = 2.4
    layers.append(extrude(offset(star, -0.4), 0.4) + extrude(star, h0 - 0.4, 0.4))
    z = h0
    for k in range(1, steps + 1):
        o = offset(star, -1.15 * k)
        if o.is_empty():
            break
        layers.append(extrude(o, 0.55, z))
        z += 0.55
    body = union(layers)
    holes, studs_at = [], []
    for i in range(5):
        a = math.radians(90 + 72 * i)
        for d, col in ((14, "white"), (23, "orange"), (31, "orange"), (38.5, "orange")):
            studs_at.append(((d * math.cos(a), d * math.sin(a)), col))
    for (p, c) in studs_at:
        holes.append(cyl(1.5 + CLEAR, 10, 1.4, c=p, seg=24))
    body = body - union(holes)
    # flat-faced studs: face prints on the bed, peg up
    def stud(r):
        return union([cyl(r, 0.6, 0, seg=32), cyl(r, 1.0, 0.6, r2=r - 0.7, seg=32), cyl(1.5, 3.2, 1.5, seg=24)])
    st_o, st_w = stud(2.9), stud(3.3)
    parts = [("starfish_body", "blue", body)]
    nw = sum(1 for _, c in studs_at if c == "white")
    no = len(studs_at) - nw
    parts += [(f"starfish_stud_orange_{i + 1:02d}", "orange", st_o) for i in range(no)]
    parts += [(f"starfish_stud_white_{i + 1:02d}", "white", st_w) for i in range(nw)]
    asm = [(body, "blue")]
    for (p, c) in studs_at:
        s = st_w if c == "white" else st_o
        # sit the stud face on the local surface height
        zt = 0
        for k in range(8):
            q = (p[0] + 2.4 * math.cos(k * math.pi / 4), p[1] + 2.4 * math.sin(k * math.pi / 4))
            col = body ^ box(q[0] - 0.1, q[1] - 0.1, -1, q[0] + 0.1, q[1] + 0.1, 20)
            if not col.is_empty():
                zt = max(zt, col.bounding_box()[5])
        asm.append((s.mirror((0, 0, 1)).translate((p[0], p[1], zt + 1.6)), c))
    return _item(parts, asm)


# ------------------------------------------------------------------ fit test
def fit_test():
    """Print this first (black + any colour). Holes get looser left -> right
    (clearance 0.05 / 0.10 / 0.15 / 0.20 mm, marked by 1-4 edge notches).
    Pick the hole that grips the peg firmly, then set CLEAR in lib.py and rebuild."""
    from fish import PEG_R, PEG_H, FACE_T, CORE_T
    clears = (0.05, 0.10, 0.15, 0.20)
    bar = box(0, 0, 0, 56, 14, CORE_T)
    tile = box(0, 0, 0, 56, 10, FACE_T)
    for i, c in enumerate(clears):
        x = 8 + 13 * i
        bar = bar - cyl(PEG_R + c, 10, -1, c=(x, 7), seg=32)
        for k in range(i + 1):
            bar = bar - box(x - 3 + 2 * k, -1, -1, x - 2 + 2 * k, 1.0, 10)
        tile = tile + cyl(PEG_R, PEG_H, FACE_T, c=(x, 5), seg=32)
    return _item([("fit_test_holes", "black", bar), ("fit_test_pegs", "white", tile)],
                 [(bar, "black"), (tile.translate((0, 20, 0)), "white")])
