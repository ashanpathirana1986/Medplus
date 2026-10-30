"""Geometry helpers for the snap-together aquarium set.

Everything is built with manifold3d (robust booleans -> watertight STLs).
Units are millimetres. Z is up on the print bed.
"""
import math
import numpy as np
from manifold3d import CrossSection, Manifold, JoinType, FillRule

# ---------------------------------------------------------------- settings
CLEAR = 0.10        # radial clearance for pegs / sockets (raise if fits are too tight)
SEG = 48            # circle resolution

COLORS = {
    "orange": (1.00, 0.47, 0.12),   # mandarin orange
    "red":    (0.80, 0.10, 0.13),   # scarlet red
    "blue":   (0.05, 0.28, 0.72),   # cobalt blue
    "gray":   (0.55, 0.56, 0.55),
    "white":  (0.95, 0.93, 0.86),   # ivory white
    "black":  (0.10, 0.10, 0.11),
}


# ---------------------------------------------------------------- 2D helpers
def catmull(points, n=12, closed=True):
    """Smooth closed curve through control points (centripetal-ish Catmull-Rom)."""
    p = np.asarray(points, float)
    m = len(p)
    out = []
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = p[(i - 1) % m] if closed or i > 0 else p[i]
        p1 = p[i]
        p2 = p[(i + 1) % m]
        p3 = p[(i + 2) % m] if closed or i + 2 < m else p2
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t +
                              (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(p[-1])
    return np.array(out)


def poly(points):
    return CrossSection([np.asarray(points, float)], FillRule.Positive)


def smooth(points, n=12):
    pts = catmull(points, n)
    cs = CrossSection([pts], FillRule.NonZero)
    if cs.area() < 0:
        cs = CrossSection([pts[::-1]], FillRule.NonZero)
    return cs


def circle(r, c=(0, 0), seg=SEG):
    return CrossSection.circle(r, seg).translate(c)


def rect(x0, y0, x1, y1):
    return CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))


def stroke(pts, w, seg=16):
    """Thick polyline with round caps."""
    pts = np.asarray(pts, float)
    parts = []
    for a, b in zip(pts[:-1], pts[1:]):
        parts.append(CrossSection.batch_hull([circle(w / 2, a, seg), circle(w / 2, b, seg)]))
    return CrossSection.batch_boolean(parts, _ADD())


def _ADD():
    from manifold3d import OpType
    return OpType.Add


def union(items):
    items = [i for i in items if i is not None]
    if not items:
        return None
    if isinstance(items[0], CrossSection):
        return CrossSection.batch_boolean(items, _ADD())
    return Manifold.batch_boolean(items, _ADD())


def offset(cs, d):
    return cs.offset(d, JoinType.Round, 2.0, 24)


def components(cs, min_area=4.0):
    return [c for c in cs.decompose() if c.area() > min_area]


def point_in(cs, pt):
    return not (cs ^ circle(0.01, pt, 6)).is_empty()


def bbox2(cs):
    b = cs.bounds()
    return b  # (xmin, ymin, xmax, ymax)


def peg_points(cs, r_peg, spacing=13.0, maxn=4, margin=1.6):
    """Pick well-spread peg locations safely inside a 2D region."""
    safe = offset(cs, -(r_peg + margin))
    if safe.is_empty():
        safe = offset(cs, -(r_peg + 0.6))
        if safe.is_empty():
            return []
    x0, y0, x1, y1 = safe.bounds()
    cands = []
    step = 1.0
    for x in np.arange(x0, x1 + step, step):
        for y in np.arange(y0, y1 + step, step):
            cands.append((x, y))
    polys = safe.to_polygons()
    cands = np.array(cands)
    inside = _pip_many(polys, cands)
    cands = cands[inside]
    if len(cands) == 0:
        return []
    # start from the point deepest inside (approx: closest to centroid)
    c = cands.mean(0)
    chosen = [cands[np.argmin(((cands - c) ** 2).sum(1))]]
    if len(cands) > 1 and maxn > 1:
        # farthest-point sampling
        chosen = [cands[np.argmax(((cands - chosen[0]) ** 2).sum(1))]]
        while len(chosen) < maxn:
            d = np.min([((cands - q) ** 2).sum(1) for q in chosen], axis=0)
            i = np.argmax(d)
            if d[i] < spacing ** 2:
                break
            chosen.append(cands[i])
        if len(chosen) == 1:
            chosen = [cands[np.argmin(((cands - c) ** 2).sum(1))]]
    return [tuple(p) for p in chosen]


def _pip_many(polys, pts):
    inside = np.zeros(len(pts), bool)
    for poly_ in polys:
        poly_ = np.asarray(poly_)
        x, y = pts[:, 0], pts[:, 1]
        j = len(poly_) - 1
        for i in range(len(poly_)):
            xi, yi = poly_[i]
            xj, yj = poly_[j]
            cond = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi)
            inside ^= cond
            j = i
    return inside


# ---------------------------------------------------------------- 3D helpers
def extrude(cs, h, z0=0.0):
    # drop near-duplicate vertices first: they collapse in float32 STL export
    return Manifold.extrude(cs.simplify(0.01), h).translate((0, 0, z0))


def chamfered(cs, h, ch=0.4, top=False, bottom=True):
    """Extrude with a small 45deg chamfer approximated by two steps.
    Layers overlap slightly so no coincident faces end up in the mesh."""
    e = 0.02
    parts = []
    z = 0.0
    if bottom and ch > 0:
        inner = offset(cs, -ch)
        if not inner.is_empty():
            parts.append(extrude(inner, ch / 2 + e, 0))
            parts.append(extrude(offset(cs, -ch / 2), ch / 2 + e, ch / 2))
        z = ch
    ztop = h - (ch if top else 0)
    parts.append(extrude(cs, ztop - z + (e if top else 0), z))
    if top and ch > 0:
        parts.append(extrude(offset(cs, -ch / 2), ch / 2 + e, ztop))
        parts.append(extrude(offset(cs, -ch), ch / 2, ztop + ch / 2))
    return union(parts)


def cyl(r, h, z0=0.0, r2=None, seg=SEG, c=(0, 0)):
    return Manifold.cylinder(h, r, r if r2 is None else r2, seg).translate((c[0], c[1], z0))


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def to_bed(m):
    """Drop a part so it rests on z=0, centred on xy origin."""
    (x0, y0, z0), (x1, y1, z1) = _bb(m)
    return m.translate((-(x0 + x1) / 2, -(y0 + y1) / 2, -z0))


def _bb(m):
    b = m.bounding_box()
    return (b[0], b[1], b[2]), (b[3], b[4], b[5])


def mesh_arrays(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64)
    f = np.asarray(mesh.tri_verts).astype(np.int64)
    return v, f


def write_stl(m, path, name="part"):
    v, f = mesh_arrays(m)
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    n = n / np.where(ln == 0, 1, ln)
    data = np.zeros(len(f), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    data["n"] = n
    data["v"] = tri
    with open(path, "wb") as fh:
        hdr = (name.encode()[:79]).ljust(80, b" ")
        fh.write(hdr)
        fh.write(np.uint32(len(f)).tobytes())
        fh.write(data.tobytes())


def rot_x(m, deg):
    return m.rotate((deg, 0, 0))


def rot_y(m, deg):
    return m.rotate((0, deg, 0))


def rot_z(m, deg):
    return m.rotate((0, 0, deg))


# ---------------------------------------------------------------- low-poly rock
def rock_hull(rx, ry, h, seed=1, n=26, flat_top=None):
    """Faceted low-poly rock: convex hull of jittered points, flat bottom."""
    rs = np.random.RandomState(seed)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + rs.uniform(-0.12, 0.12)
        k = rs.uniform(0.86, 1.04)
        pts.append((rx * k * math.cos(a), ry * k * math.sin(a), 0.0))
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n + rs.uniform(-0.15, 0.15)
        k = rs.uniform(0.80, 1.0)
        z = h * rs.uniform(0.25, 0.45)
        pts.append((rx * k * math.cos(a), ry * k * math.sin(a), z))
    m2 = max(6, n // 2)
    for i in range(m2):
        a = 2 * math.pi * i / m2 + rs.uniform(-0.3, 0.3)
        k = rs.uniform(0.45, 0.75)
        z = h * rs.uniform(0.70, 0.92)
        pts.append((rx * k * math.cos(a), ry * k * math.sin(a), z))
    for i in range(5):
        a = rs.uniform(0, 2 * math.pi)
        k = rs.uniform(0.0, 0.3)
        pts.append((rx * k * math.cos(a), ry * k * math.sin(a), h * rs.uniform(0.92, 1.0)))
    return Manifold.hull_points(np.array(pts))
