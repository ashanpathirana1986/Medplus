"""Build every model: individual STLs, per-colour print plates (3MF + STL),
preview renders and a GLB scene for the web viewer.

    pip install manifold3d numpy pillow trimesh
    python build.py            # everything
    python build.py --no-render
"""
import os
import sys
import json
import shutil
import zipfile
import numpy as np

from lib import write_stl, mesh_arrays, to_bed, COLORS, Manifold
import designs_fish as F
import decor
from fish import CORE_T

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
BED = 250.0          # usable bed (256 mm printers: Bambu X1/P1/A1, Prusa MK4 is 250x210 -> see README)
GAP = 5.0
COLOR_NAMES = {"orange": "Mandarin Orange", "red": "Scarlet Red", "blue": "Cobalt Blue",
               "gray": "Gray", "white": "Ivory White", "black": "Black"}


# ------------------------------------------------------------------ items
def fish_item(fish):
    return dict(parts=fish.print_parts(), assembly=fish.assembly(), fish=fish)


def all_items():
    fish = [("01_clownfish", "Clownfish", F.clownfish()),
            ("02_tang", "Cobalt Tang", F.tang()),
            ("03_angelfish", "Zebra Angelfish", F.angelfish()),
            ("04_betta", "Halfmoon Betta", F.betta()),
            ("05_puffer", "Spiky Pufferfish", F.puffer())]
    items = [(k, t, fish_item(f)) for k, t, f in fish]
    items += [("06_lighthouse", "Striped Lighthouse", decor.lighthouse()),
              ("07_torii", "Sunken Torii Gate", decor.torii()),
              ("08_coral", "Crossed Staghorn Coral", decor.coral()),
              ("09_starfish", "Blue Starfish", decor.starfish()),
              ("10_rock_stands", "Reef Rock Fish Stands", decor.rock_stands()),
              ("00_fit_test", "Fit test coupon (print first)", decor.fit_test())]
    return items


# ------------------------------------------------------------------ mounting the fish on rods
MOUNTS = {  # fish key -> (rock, socket index, rod length)
    "01_clownfish": ("big", 1, 65),
    "02_tang": ("big", 2, 105),
    "04_betta": ("big", 0, 85),
    "03_angelfish": ("small", 0, 125),
    "05_puffer": ("small", 1, 45),
}


def mounted_fish(item, rock_item, key, rock_pos):
    rock_name, idx, L = MOUNTS[key]
    _, sockets = rock_item[rock_name]
    (sx, sy), zs = sockets[idx]
    rod = dict(rock_item["rods"])[L]
    floor = zs - 14
    rod_w = rod.rotate((0, -90, 0)).translate((3.5, 0, 0)).translate((sx, sy, floor))
    fish = item["fish"]
    tx, yt, yb = fish.tab
    dz = floor + L - 9.3 - yb
    out = [(rod_w, "black")]
    for m, c in item["assembly"]:
        out.append((m.translate((sx - tx, sy, dz)), c))
    return [(m.translate(rock_pos), c) for m, c in out]


def hero_scene(items):
    d = {k: it for k, _, it in items}
    rocks = d["10_rock_stands"]
    big, _ = rocks["big"]
    small, _ = rocks["small"]
    scene = []
    pb, ps = (0, 0, 0), (135, 55, 0)
    scene.append((big.translate(pb), "gray"))
    scene.append((small.translate(ps), "gray"))
    for key, (rk, _, _) in MOUNTS.items():
        scene += mounted_fish(d[key], rocks, key, pb if rk == "big" else ps)
    place = {"06_lighthouse": (-140, 70, 0, 0), "07_torii": (40, 150, 0, 0),
             "08_coral": (-75, 140, 0, 30), "09_starfish": (95, -60, 0, 15)}
    for key, (x, y, z, rot) in place.items():
        for m, c in d[key]["assembly"]:
            scene.append((m.rotate((0, 0, rot)).translate((x, y, z)), c))
    return scene


# ------------------------------------------------------------------ plate packing
def pack(parts):
    """Shelf-pack parts (already on the bed) into as many BED x BED plates as needed."""
    boxes = []
    for name, m in parts:
        b = m.bounding_box()
        w, h = b[3] - b[0], b[4] - b[1]
        if h > w:                       # long side along X
            m = m.rotate((0, 0, 90))
        m = to_bed(m)
        b = m.bounding_box()
        boxes.append((name, m, b[3] - b[0], b[4] - b[1]))
    boxes.sort(key=lambda t: (-t[3], -t[2]))
    plates = []
    for name, m, w, h in boxes:
        placed = False
        for pl in plates:
            for sh in pl["shelves"]:
                if h <= sh["h"] and sh["x"] + w <= BED:
                    pl["items"].append((name, m.translate((sh["x"] + w / 2, sh["y"] + h / 2, 0))))
                    sh["x"] += w + GAP
                    placed = True
                    break
            if placed:
                break
            if pl["y"] + h <= BED:
                sh = dict(y=pl["y"], h=h, x=w + GAP)
                pl["shelves"].append(sh)
                pl["items"].append((name, m.translate((w / 2, pl["y"] + h / 2, 0))))
                pl["y"] += h + GAP
                placed = True
                break
        if not placed:
            pl = dict(shelves=[dict(y=0, h=h, x=w + GAP)], y=h + GAP,
                      items=[(name, m.translate((w / 2, h / 2, 0)))])
            plates.append(pl)
    # centre each plate's content on the bed
    out = []
    for pl in plates:
        allm = Manifold.batch_boolean([m for _, m in pl["items"]], _add())
        b = allm.bounding_box()
        dx = (BED - (b[3] - b[0])) / 2 - b[0] + 3
        dy = (BED - (b[4] - b[1])) / 2 - b[1] + 3
        out.append([(n, m.translate((dx, dy, 0))) for n, m in pl["items"]])
    return out


def _add():
    from manifold3d import OpType
    return OpType.Add


def write_3mf(objs, path, rgb=None):
    """objs: [(name, Manifold)] already positioned on the plate."""
    res, build = [], []
    for i, (name, m) in enumerate(objs, start=1):
        v, f = mesh_arrays(m)
        vs = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in v)
        ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
        res.append(f'<object id="{i}" name="{name}" type="model"><mesh><vertices>{vs}</vertices>'
                   f'<triangles>{ts}</triangles></mesh></object>')
        build.append(f'<item objectid="{i}"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<resources>{"".join(res)}</resources><build>{"".join(build)}</build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def write_combined_stl(objs, path):
    write_stl(Manifold.batch_boolean([m for _, m in objs], _add()), path)


# ------------------------------------------------------------------ GLB for the viewer
def write_glb(groups, path):
    """groups: {name: [(Manifold, colour)]} -> one GLB with a node per group."""
    import trimesh
    scene = trimesh.Scene()
    for gname, parts in groups.items():
        for i, (m, c) in enumerate(parts):
            v, f = mesh_arrays(m)
            if len(f) == 0:
                continue
            tm = trimesh.Trimesh(v, f, process=False)
            rgb = COLORS[c]
            mat = trimesh.visual.material.PBRMaterial(
                baseColorFactor=[rgb[0], rgb[1], rgb[2], 1.0], metallicFactor=0.0,
                roughnessFactor=0.55)
            tm.visual = trimesh.visual.TextureVisuals(material=mat)
            scene.add_geometry(tm, node_name=f"{gname}__{c}__{i}", geom_name=f"{gname}__{c}__{i}")
    scene.export(path)


# ------------------------------------------------------------------ main
def main():
    render_on = "--no-render" not in sys.argv
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    items = all_items()
    by_color = {}
    summary = []
    for key, title, it in items:
        d = os.path.join(OUT, "stl", key)
        os.makedirs(d, exist_ok=True)
        counts = {}
        for name, col, m in it["parts"]:
            m = to_bed(m)
            assert m.status().name == "NoError", name
            write_stl(m, os.path.join(d, f"{name}__{col}.stl"), name)
            if key != "00_fit_test":
                by_color.setdefault(col, []).append((name, m))
            counts[col] = counts.get(col, 0) + 1
        summary.append(dict(key=key, title=title, parts=len(it["parts"]), colors=counts))
        print(f"{key:18s} {len(it['parts']):3d} parts  {counts}")

    pdir = os.path.join(OUT, "plates")
    os.makedirs(pdir)
    fit = dict((k, it) for k, _, it in items)["00_fit_test"]
    write_3mf(pack([(n, to_bed(m)) for n, _, m in fit["parts"]])[0], os.path.join(pdir, "00_fit_test.3mf"))
    plate_info = []
    for col, parts in by_color.items():
        plates = pack(parts)
        for k, objs in enumerate(plates, start=1):
            base = os.path.join(pdir, f"{col}_plate{k}")
            write_3mf(objs, base + ".3mf")
            vol = sum(m.volume() for _, m in objs) / 1000
            plate_info.append(dict(color=col, plate=k, parts=len(objs), grams=round(vol * 1.24)))
            print(f"plate {col}_{k}: {len(objs)} parts, ~{vol * 1.24:.0f} g at 100% infill")
            if render_on:
                from render import render
                render([(m, col) for _, m in objs] + [(_bed(), (0.85, 0.87, 0.9))],
                       base + ".png", az=-90, el=89, size=700, margin=0.01)

    # every exported STL must be a closed, watertight solid after float32 export
    import glob
    import trimesh
    bad = [f for f in glob.glob(os.path.join(OUT, "stl", "*", "*.stl")) if not trimesh.load(f).is_watertight]
    print(f"watertight check: {len(bad)} problem files")
    for f in bad:
        print("  NOT WATERTIGHT:", os.path.relpath(f, OUT))

    with open(os.path.join(OUT, "summary.json"), "w") as fh:
        json.dump(dict(items=summary, plates=plate_info), fh, indent=1)

    groups = {key: it["assembly"] for key, _, it in items}
    groups["scene"] = hero_scene(items)
    write_glb({k: v for k, v in groups.items() if k != "scene"}, os.path.join(OUT, "items.glb"))
    write_glb({"scene": groups["scene"]}, os.path.join(OUT, "scene.glb"))

    if render_on:
        from render import render
        pv = os.path.join(OUT, "previews")
        os.makedirs(pv)
        for key, title, it in items:
            az, el = (-90, 6) if "fish" in it else (-70, 18)
            if key == "09_starfish":
                el = 45
            render(it["assembly"], os.path.join(pv, f"{key}.png"), az=az, el=el, size=800)
        render(groups["scene"], os.path.join(pv, "00_scene.png"), az=-78, el=14, size=1400, margin=0.03)


def _bed():
    return Manifold.cube((BED + 6, BED + 6, 0.2)).translate((0, 0, -0.25))


if __name__ == "__main__":
    main()
