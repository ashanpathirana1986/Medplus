"""Double-sided 'cartoon inlay' fish.

Construction (every part is one colour):
  * CORE    - a 3.2 mm black silhouette plate. Its edge shows as a black
              outline and the 1.2 mm gaps between colour pieces show as black
              'ink lines', like a stained-glass / cartoon fish.
  * PIECES  - 2.4 mm colour tiles that press onto both faces of the core with
              3 mm pegs. Printed face-down for a smooth, crisp show side.
              Side A pieces are mirrored copies of side B pieces.
  * EYE PIN - one black pin pushed through both eyes and the core = pupils.
  * TAB     - the core has a tab under the belly that plugs into a fork rod.
"""
import numpy as np
from lib import (CrossSection, Manifold, CLEAR, offset, components, union, circle,
                 rect, stroke, smooth, chamfered, cyl, extrude, peg_points)

CORE_T = 3.2
FACE_T = 2.4
GAP = 1.2          # width of the black 'ink line' between colour pieces
PEG_R = 1.5
PEG_H = 1.3
GROOVE_W = 0.9
GROOVE_D = 0.6


class Fish:
    def __init__(self, name, zones, zone_colors, masks=(), eye=None, rays=None,
                 grooves=None, tab=None, outline=1.0, peg_max=3):
        """
        zones:  list of (zone_name, CrossSection, margin) - first zone wins overlaps.
                margin = width of black core border visible along the outer edge.
        masks:  list of (CrossSection, colour, zone_names|None) in priority order.
        eye:    (x, y, r) white eye disc; a black pin forms the pupil.
        rays:   {zone_name: (origin_xy, a0_deg, a1_deg, count)} fin-ray grooves.
        grooves: list of polylines engraved on all pieces (gill lines etc).
        tab:    (x, y_top, y_bottom) mounting tab on the core.
        """
        self.name = name
        self.sil = _clean(union([z[1] for z in zones]))
        self.zones = zones
        self.zone_colors = zone_colors
        self.masks = list(masks)
        self.eye = eye
        self.rays = rays or {}
        self.grooves = grooves or []
        self.tab = tab
        self.outline = outline
        self.peg_max = peg_max
        self._build()

    # -------------------------------------------------------------- layout
    def _build(self):
        pieces = []           # (cs, colour, zone)
        taken = None
        eye_cs = circle(self.eye[2], self.eye[:2]) if self.eye else None
        eye_block = circle(self.eye[2] + GAP / 2, self.eye[:2]) if self.eye else None
        for zname, shape, margin in self.zones:
            allowed = offset(self.sil, -max(margin, self.outline)) ^ shape
            if taken is not None:
                allowed = allowed - taken
            taken = shape if taken is None else taken + shape
            if eye_block is not None:
                allowed = allowed - eye_block
            remaining = allowed
            for mshape, mcol, mzones in self.masks:
                if mzones is not None and zname not in mzones:
                    continue
                part = remaining ^ mshape
                if not part.is_empty():
                    pieces.append((part, mcol, zname))
                    remaining = remaining - mshape
            if not remaining.is_empty():
                pieces.append((remaining, self.zone_colors[zname], zname))
        out = []
        for cs, col, zname in pieces:
            if col == "core":       # leave empty: the black core shows through
                continue
            # morphological opening removes hair-thin necks and slivers
            for comp in components(_clean(offset(cs, -GAP / 2)), min_area=6.0):
                if offset(comp, -1.0).is_empty():     # sliver too thin to print / hold
                    continue
                out.append((comp, col, zname))
        if eye_cs is not None:
            out.append((eye_cs, "white", "eye"))
        self.pieces = []
        holes = []
        for cs, col, zname in out:
            if zname == "eye":
                pegs, pin_hole = [], self.eye[:2]
            else:
                pin_hole = None
                # at least two pegs so a tile can't spin; shrink pegs for small tiles
                pegs = []
                for r, spacing, margin in ((PEG_R, 13, 1.6), (PEG_R, 6.5, 1.2), (1.0, 4.5, 0.8)):
                    pegs = [(x, y, r) for x, y in peg_points(cs, r, spacing=spacing, maxn=self.peg_max, margin=margin)]
                    if len(pegs) >= 2:
                        break
                if len(pegs) < 2:   # too small to anchor - let the black core show instead
                    continue
            holes += pegs
            self.pieces.append(dict(cs=cs, color=col, zone=zname, pegs=pegs, pin=pin_hole))
        self.holes = holes

    # -------------------------------------------------------------- parts
    def piece_solid(self, p, mirror=False):
        cs = p["cs"]
        grooves = self._grooves_for(p)
        body = chamfered(cs, FACE_T, ch=0.4)
        if grooves is not None:
            body = body - extrude(grooves, GROOVE_D + 0.01, -0.01)
        pegs = [Manifold.hull(cyl(r, PEG_H - 0.3, FACE_T - 0.02, c=(x, y), seg=24) +
                              cyl(r - 0.3, 0.01, FACE_T + PEG_H - 0.01, c=(x, y), seg=24)) for x, y, r in p["pegs"]]
        m = union([body] + pegs)
        if p["pin"] is not None:
            m = m - cyl(PEG_R + CLEAR, 10, -1, c=p["pin"], seg=24)
        if mirror:
            m = m.mirror((1, 0, 0))
        return m

    def _grooves_for(self, p):
        lines = []
        if p["zone"] in self.rays:
            (ox, oy), a0, a1, n = self.rays[p["zone"]]
            for a in np.linspace(np.radians(a0), np.radians(a1), n):
                lines.append(stroke([(ox, oy), (ox + 200 * np.cos(a), oy + 200 * np.sin(a))], GROOVE_W, 8))
        for g in self.grooves:
            lines.append(stroke(g, GROOVE_W, 8))
        if not lines:
            return None
        g = union(lines) ^ offset(p["cs"], -1.1)
        return None if g.is_empty() else g

    def core_solid(self):
        sil = self.sil
        if self.tab:
            x, yt, yb = self.tab
            tab = rect(x - 5, yb + 1.5, x + 5, yt) + rect(x - 3.5, yb, x + 3.5, yb + 1.6) + \
                CrossSection.batch_hull([rect(x - 5, yb + 1.5, x + 5, yb + 1.6), rect(x - 3.5, yb, x + 3.5, yb + 0.1)])
            sil = sil + tab
        m = chamfered(sil, CORE_T, ch=0.4, top=True)
        holes = [cyl(r + CLEAR, CORE_T + 2, -1, c=(x, y), seg=24) for x, y, r in self.holes]
        if self.eye:
            holes.append(cyl(PEG_R + CLEAR, CORE_T + 2, -1, c=self.eye[:2], seg=24))
        if holes:
            m = m - union(holes)
        return m

    def pin_solid(self):
        L = CORE_T + 2 * FACE_T - 0.2
        return Manifold.hull(cyl(PEG_R - 0.32, L, 0, seg=24) + cyl(PEG_R - 0.02, L - 0.4, 0.2, seg=24))

    # -------------------------------------------------------------- outputs
    def print_parts(self):
        """[(filename, colour, solid_on_bed)]"""
        parts = [(f"{self.name}_core", "black", self.core_solid())]
        for i, p in enumerate(self.pieces):
            parts.append((f"{self.name}_{p['zone']}{i:02d}_sideA", p["color"], self.piece_solid(p, mirror=True)))
            parts.append((f"{self.name}_{p['zone']}{i:02d}_sideB", p["color"], self.piece_solid(p)))
        if self.eye:
            parts.append((f"{self.name}_eyepin", "black", self.pin_solid()))
        return parts

    def assembly(self):
        """Coloured parts in assembled position, fish in the XZ plane facing +X."""
        out = [(self.core_solid().translate((0, 0, -CORE_T / 2)), "black")]
        for p in self.pieces:
            s = self.piece_solid(p)
            out.append((s.mirror((0, 0, 1)).translate((0, 0, CORE_T / 2 + FACE_T)), p["color"]))
            out.append((s.translate((0, 0, -CORE_T / 2 - FACE_T)), p["color"]))
        if self.eye:
            L = CORE_T + 2 * FACE_T - 0.2
            out.append((self.pin_solid().translate((self.eye[0], self.eye[1], -L / 2)), "black"))
        # stand the fish up: fish XY plane -> world XZ plane
        return [(m.rotate((90, 0, 0)), c) for m, c in out]


def _clean(cs, r=0.6):
    """Closing then opening: removes touching points, hair-thin necks and slivers
    (they print badly and make non-watertight meshes)."""
    cs = offset(offset(cs, r), -r)
    return offset(offset(cs, -r), r)


def _contains(cs, pt):
    return not (cs ^ circle(0.05, pt, 8)).is_empty()


# ------------------------------------------------------------------ fork rod
def fork_rod(length):
    """Square stand rod printed lying flat. Top end is a fork for the fish tab,
    bottom end plugs into a rock socket."""
    w = 7.0
    rod = Manifold.cube((length, w, w)).translate((0, -w / 2, 0))
    slot_w = CORE_T + 2 * CLEAR + 0.1
    rod = rod - Manifold.cube((10, slot_w, w + 2)).translate((length - 9.5, -slot_w / 2, -1))
    # lead-in chamfer at the mouth of the slot
    lead = Manifold.hull(Manifold.cube((0.01, slot_w + 1.6, w + 2)).translate((length, -(slot_w + 1.6) / 2, -1)) +
                         Manifold.cube((0.01, slot_w, w + 2)).translate((length - 1.2, -slot_w / 2, -1)))
    rod = rod - lead
    # rounded bottom edges of the socket end (easy insertion)
    rod = rod - _end_chamfer(w)
    return rod


def _end_chamfer(w):
    c = 0.8
    parts = []
    for sy in (-1, 1):
        parts.append(Manifold.hull(Manifold.cube((c, 0.01, w + 2)).translate((0, sy * w / 2 - (0.01 if sy > 0 else 0), -1)) +
                                   Manifold.cube((0.01, c, w + 2)).translate((0, sy * (w / 2 - c) - (c if sy > 0 else 0) + (0 if sy > 0 else 0), -1))))
    return union(parts)
