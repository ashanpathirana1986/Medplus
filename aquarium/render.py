"""Tiny numpy z-buffer renderer for preview images (no GPU / OpenGL needed)."""
import math
import numpy as np
from PIL import Image
from lib import mesh_arrays, COLORS


def look_matrix(az, el):
    az, el = math.radians(az), math.radians(el)
    # camera looks toward the origin from direction d
    d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    fwd = -d
    up = np.array([0, 0, 1.0])
    right = np.cross(fwd, up)
    right /= np.linalg.norm(right)
    up2 = np.cross(right, fwd)
    return np.stack([right, up2, -fwd])  # rows: x, y, z(towards camera)


def render(parts, path, az=-60, el=25, size=900, ss=2, bg=(232, 240, 246), margin=0.08):
    """parts: list of (Manifold, color_name_or_rgb)."""
    R = look_matrix(az, el)
    tris, cols = [], []
    for m, c in parts:
        v, f = mesh_arrays(m)
        if len(f) == 0:
            continue
        tris.append((v @ R.T)[f])
        rgb = COLORS[c] if isinstance(c, str) else c
        cols.append(np.tile(np.array(rgb), (len(f), 1)))
    T = np.concatenate(tris)
    C = np.concatenate(cols)
    W = size * ss
    mn = T.reshape(-1, 3).min(0)
    mx = T.reshape(-1, 3).max(0)
    span = max(mx[0] - mn[0], mx[1] - mn[1]) * (1 + 2 * margin)
    s = W / span
    cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
    P = np.empty_like(T)
    P[..., 0] = (T[..., 0] - cx) * s + W / 2
    P[..., 1] = W / 2 - (T[..., 1] - cy) * s
    P[..., 2] = T[..., 2]

    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    n = n / np.where(ln == 0, 1, ln)
    L1 = np.array([-0.35, 0.55, 0.75]); L1 /= np.linalg.norm(L1)
    L2 = np.array([0.6, -0.2, 0.5]); L2 /= np.linalg.norm(L2)
    nn = np.where((n[:, 2:3] < 0), -n, n)
    diff = np.clip(nn @ L1, 0, 1) * 0.70 + np.clip(nn @ L2, 0, 1) * 0.22
    h = (L1 + np.array([0, 0, 1])); h /= np.linalg.norm(h)
    spec = np.clip(nn @ h, 0, 1) ** 40 * 0.25
    shade = C * (0.30 + diff[:, None]) + spec[:, None]
    shade = np.clip(shade, 0, 1)

    zbuf = np.full((W, W), -1e9)
    img = np.zeros((W, W, 3))
    img[:] = np.array(bg) / 255.0
    for i in range(len(P)):
        p = P[i]
        x0 = int(max(0, math.floor(p[:, 0].min())))
        x1 = int(min(W - 1, math.ceil(p[:, 0].max())))
        y0 = int(max(0, math.floor(p[:, 1].min())))
        y1 = int(min(W - 1, math.ceil(p[:, 1].max())))
        if x1 < x0 or y1 < y0:
            continue
        (ax, ay, az_), (bx, by, bz), (qx, qy, qz) = p
        den = (by - qy) * (ax - qx) + (qx - bx) * (ay - qy)
        if abs(den) < 1e-9:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((by - qy) * (xs - qx) + (qx - bx) * (ys - qy)) / den
        w1 = ((qy - ay) * (xs - qx) + (ax - qx) * (ys - qy)) / den
        w2 = 1 - w0 - w1
        mask = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not mask.any():
            continue
        z = w0 * az_ + w1 * bz + w2 * qz
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        upd = mask & (z > sub)
        sub[upd] = z[upd]
        img[y0:y1 + 1, x0:x1 + 1][upd] = shade[i]
    # subtle edge darkening from depth discontinuities
    zb = zbuf.copy()
    fg = zb > -1e8
    zb[~fg] = zb[fg].min() - 50 if fg.any() else 0
    gx = np.abs(np.diff(zb, axis=1, append=zb[:, -1:]))
    gy = np.abs(np.diff(zb, axis=0, append=zb[-1:, :]))
    edge = (np.maximum(gx, gy) > 1.2)
    img[edge] *= 0.35
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    out = out.resize((size, size), Image.LANCZOS)
    out.save(path)
    return out
