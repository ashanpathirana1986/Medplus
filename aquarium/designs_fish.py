"""Fish designs. All drawn facing +X, roughly 100-120 mm nose to tail."""
from lib import smooth, circle, rect
from fish import Fish


def clownfish():
    body = smooth([(41, 2), (37, 12), (26, 19), (10, 21), (-8, 18), (-24, 10), (-31, 5), (-33, 0),
                   (-31, -5), (-24, -9), (-8, -15), (10, -17), (26, -15), (37, -9), (42, -3)])
    tail = smooth([(-27, 6), (-38, 14), (-49, 16), (-55, 8), (-56, 0), (-55, -8), (-49, -14), (-38, -12), (-27, -5)])
    dorsal = smooth([(25, 14), (21, 25), (13, 29), (5, 27), (0, 24), (-6, 28), (-15, 31), (-23, 26), (-28, 10), (0, 13)])
    anal = smooth([(-3, -12), (-9, -25), (-18, -27), (-25, -17), (-21, -7)])
    pelvic = smooth([(16, -12), (12, -27), (5, -29), (2, -14)])
    pect = smooth([(15, -3), (8, 2), (1, 0), (-2, -5), (2, -10), (10, -10)])
    band1 = smooth([(24, 26), (29, 6), (26, -20), (18, -20), (20, 6), (16, 26)])
    band2 = smooth([(3, 36), (6, 8), (3, -34), (-7, -34), (-5, 8), (-9, 36)])
    band3 = smooth([(-24, 22), (-26, 0), (-24, -22), (-31, -22), (-33, 0), (-31, 22)])
    W = "white"
    return Fish(
        "clownfish",
        zones=[("body", body, 1.0), ("tail", tail, 2.6), ("dorsal", dorsal, 2.6),
               ("anal", anal, 2.6), ("pelvic", pelvic, 2.6)],
        zone_colors=dict(body="orange", tail="orange", dorsal="orange", anal="orange", pelvic="orange"),
        masks=[(pect, "orange", ["body"]), (band1, W, None), (band2, W, None), (band3, W, None)],
        eye=(32, 5, 4.6),
        rays={"tail": ((-26, 0), -45, 45, 7), "dorsal": ((4, -10), 50, 140, 9),
              "anal": ((-8, 2), -150, -100, 4), "pelvic": ((10, -6), -120, -80, 3)},
        tab=(4, -14, -28),
    )


def tang():
    body = smooth([(43, -1), (38, 9), (28, 20), (12, 26), (-6, 25), (-22, 18), (-30, 8), (-33, 0),
                   (-30, -8), (-22, -16), (-6, -22), (12, -23), (28, -17), (38, -8)])
    dorsal = smooth([(34, 14), (22, 28), (4, 33), (-14, 31), (-28, 21), (-33, 9), (-10, 16)])
    anal = smooth([(24, -14), (10, -28), (-8, -30), (-24, -25), (-32, -9), (-10, -16)])
    tail = smooth([(-28, 5), (-40, 13), (-54, 24), (-51, 9), (-48, 0), (-51, -9), (-54, -24), (-40, -13), (-28, -5)])
    pect = smooth([(22, -6), (14, 0), (6, -2), (6, -8), (14, -11)])
    mark = smooth([(32, 9), (22, 16), (4, 19), (-14, 16), (-28, 7), (-34, 0), (-26, -3), (-16, -4),
                   (-6, -9), (5, -8), (11, 0), (19, 4), (29, 3)])
    island = smooth([(3, 11), (-9, 11), (-15, 5), (-7, 1), (4, 4)])
    spine = smooth([(-24, -5), (-19, -3), (-24, -2)])
    return Fish(
        "tang",
        zones=[("body", body, 1.0), ("tail", tail, 2.4), ("dorsal", dorsal, 2.4), ("anal", anal, 2.4)],
        zone_colors=dict(body="blue", tail="orange", dorsal="blue", anal="blue"),
        masks=[(island, "blue", ["body"]), (pect, "orange", ["body"]), (mark, "black", ["body"])],
        eye=(31, 5, 4.4),
        rays={"tail": ((-27, 0), -40, 40, 9), "dorsal": ((4, 0), 40, 150, 11), "anal": ((4, 0), -150, -40, 9)},
        grooves=[[(24, 13), (21, 4), (22, -6), (26, -13)]],
        tab=(2, -20, -36),
    )


def angelfish():
    body = smooth([(33, 2), (27, 11), (14, 17), (0, 17), (-12, 11), (-18, 3), (-18, -4),
                   (-12, -11), (0, -16), (14, -16), (27, -9)])
    dorsal = smooth([(18, 14), (6, 30), (-8, 47), (-22, 60), (-19, 40), (-17, 22), (-13, 6), (4, 10)])
    anal = smooth([(16, -13), (4, -30), (-8, -47), (-22, -60), (-19, -40), (-17, -22), (-13, -6), (4, -10)])
    tail = smooth([(-15, 4), (-26, 13), (-38, 18), (-35, 0), (-38, -18), (-26, -13), (-15, -4)])
    pelvic = smooth([(14, -12), (9, -30), (6, -52), (2, -52), (3, -30), (6, -12)])
    s1 = smooth([(27, 22), (29, 0), (27, -22), (20, -22), (22, 0), (20, 22)])
    s2 = smooth([(10, 70), (12, 0), (10, -70), (1, -70), (3, 0), (1, 70)])
    s3 = smooth([(-8, 70), (-10, 0), (-8, -70), (-15, -70), (-17, 0), (-15, 70)])
    tips = smooth([(-12, 44), (-30, 70), (-30, 50), (-12, -44), (-30, -50), (-30, -70)])
    tipu = smooth([(0, 40), (-30, 74), (-30, 34), (-14, 34)])
    tipd = smooth([(0, -40), (-14, -34), (-30, -34), (-30, -74)])
    return Fish(
        "angelfish",
        zones=[("body", body, 1.0), ("dorsal", dorsal, 1.8), ("anal", anal, 1.8),
               ("tail", tail, 1.8), ("pelvic", pelvic, 1.0)],
        zone_colors=dict(body="white", dorsal="white", anal="white", tail="red", pelvic="red"),
        masks=[(tipu, "red", ["dorsal"]), (tipd, "red", ["anal"]),
               (s1, "black", None), (s2, "black", None), (s3, "black", None)],
        eye=(25, 4, 4.0),
        rays={"tail": ((-14, 0), -35, 35, 7), "dorsal": ((10, 0), 95, 130, 5), "anal": ((10, 0), -130, -95, 5)},
        tab=(6, -16, -30),
        peg_max=3,
    )


def betta():
    body = smooth([(31, 1), (27, 7), (16, 10.5), (0, 10.5), (-14, 7.5), (-21, 3), (-21, -3),
                   (-14, -7), (0, -9.5), (16, -9.5), (27, -6)])
    tail = smooth([(-16, 6), (-26, 23), (-40, 34), (-56, 33), (-67, 18), (-71, 0), (-67, -18),
                   (-56, -33), (-40, -36), (-26, -25), (-16, -6)])
    dorsal = smooth([(9, 9), (1, 21), (-11, 30), (-23, 29), (-22, 12), (-8, 8)])
    anal = smooth([(15, -7), (5, -22), (-9, -35), (-25, -39), (-28, -22), (-18, -6)])
    pelvic = smooth([(17, -7), (13, -20), (10, -36), (5, -35), (7, -18), (9, -7)])
    edge = offset_out(body)
    return Fish(
        "betta",
        zones=[("body", body, 1.0), ("tail", tail, 1.4), ("dorsal", dorsal, 1.4),
               ("anal", anal, 1.4), ("pelvic", pelvic, 1.0)],
        zone_colors=dict(body="red", tail="red", dorsal="red", anal="red", pelvic="blue"),
        masks=[(edge, "blue", ["tail", "dorsal", "anal"])],
        eye=(23, 3, 3.6),
        rays={"tail": ((-14, 0), -80, 80, 15), "dorsal": ((0, -4), 70, 150, 8), "anal": ((6, 4), -150, -80, 9)},
        grooves=[[(16, 9), (14, 1), (15, -8)]],
        tab=(-2, -8, -22),
        outline=1.0,
    )


def offset_out(body):
    # outer blue band of the betta fins = everything outside a scaled ellipse around the body
    from lib import offset, rect, smooth as sm
    inner = sm([(24, 0), (10, 18), (-12, 26), (-40, 22), (-52, 0), (-40, -24), (-14, -28), (8, -18)])
    return rect(-200, -200, 200, 200) - inner


def puffer():
    body = smooth([(33, -2), (31, 10), (22, 21), (6, 27), (-10, 26), (-22, 18), (-28, 6), (-29, -6),
                   (-23, -17), (-10, -24), (6, -25), (22, -20), (31, -11)])
    tail = smooth([(-24, 4), (-34, 11), (-43, 10), (-45, 0), (-43, -10), (-34, -11), (-24, -4)])
    dorsal = smooth([(-4, 22), (-11, 36), (-25, 36), (-27, 16)])
    anal = smooth([(-4, -20), (-11, -34), (-25, -34), (-27, -14)])
    pect = smooth([(8, -4), (0, 4), (-8, 3), (-6, -6), (2, -9)])
    import math
    spikes = []
    from lib import poly, union as un
    for i in range(26):
        a = math.radians(-60 + i * 300 / 25)
        if -40 < math.degrees(a) % 360 - 180 < 30:   # no spikes on the tail side
            continue
        c, s = math.cos(a), math.sin(a)
        rx, ry = 30 * 0.95, 25.5 * 0.95
        base = (rx * c, ry * s)
        tip = (base[0] + 8 * c, base[1] + 8 * s)
        n = (-s * 2.6, c * 2.6)
        spikes.append(poly([(base[0] - n[0] - 2 * c, base[1] - n[1] - 2 * s), tip,
                            (base[0] + n[0] - 2 * c, base[1] + n[1] - 2 * s)]))
    spikes = un(spikes)
    belly = smooth([(40, -4), (20, -8), (0, -9), (-20, -6), (-40, -4), (-40, -40), (40, -40)])
    spots = un([circle(2.2, p) for p in [(12, 17), (0, 20), (-12, 16), (6, 11), (-6, 11), (-18, 8),
                                         (18, 9), (-2, 3), (-14, 2), (-22, -1)]])
    return Fish(
        "puffer",
        zones=[("body", body, 1.0), ("spikes", spikes, 9), ("tail", tail, 1.6),
               ("dorsal", dorsal, 1.6), ("anal", anal, 1.6)],
        zone_colors=dict(body="orange", spikes="core", tail="blue", dorsal="blue", anal="blue"),
        masks=[(pect, "blue", ["body"]), (belly, "white", ["body"]), (spots, "core", ["body"])],
        eye=(17, 8, 5.6),
        rays={"tail": ((-22, 0), -40, 40, 6), "dorsal": ((-8, 10), 100, 150, 4), "anal": ((-8, -10), -150, -100, 4)},
        grooves=[[(31, -6), (28, -8), (25, -7)]],
        tab=(0, -22, -38),
    )
