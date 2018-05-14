# -----------------------------------------------------------------------------
# Color surfaces near specified points.
#

# -----------------------------------------------------------------------------
# Color the surface model within specified distances of the given
# list of points using the corresponding point colors.
# The points are in model object coordinates.
#
def color_zone(surface, points, point_colors, distance,
               sharp_edges = False, auto_update = True):

    color_surface(surface, points, point_colors, distance)

    if sharp_edges:
        color_zone_sharp_edges(surface, points, point_colors, distance, replace = True)

    if auto_update:
        recolor = ZoneRecolor(surface, points, point_colors, distance, sharp_edges)
        from .updaters import add_updater_for_session_saving
        add_updater_for_session_saving(surface.session, recolor)
    else:
        recolor = None
    surface.auto_recolor_vertices = recolor

# -----------------------------------------------------------------------------
#
def points_and_colors(atoms, bonds, bond_point_spacing = None):

    points = atoms.scene_coords
    colors = atoms.colors

    if bonds is not None:
        raise ValueError('bond points currently not supported')
        from .bondzone import bond_points_and_colors, concatenate_points
        bpoints, bcolors = bond_points_and_colors(bonds, bond_point_spacing)
        if not bpoints is None:
            points = concatenate_points(points, bpoints)
            colors.extend(bcolors)

    return points, colors

# -----------------------------------------------------------------------------
#
def color_surface(surf, points, point_colors, distance):

    varray = surf.vertices
    from chimerax.core.geometry import find_closest_points
    i1, i2, n1 = find_closest_points(varray, points, distance)

    from numpy import empty, uint8
    rgba = empty((len(varray),4), uint8)
    rgba[:,:] = surf.color
    for k in range(len(i1)):
        rgba[i1[k],:] = point_colors[n1[k]]
        
    surf.vertex_colors = rgba
    surf.coloring_zone = True

# -----------------------------------------------------------------------------
# Stop updating surface zone.
#
def uncolor_zone(model):
    model.vertex_colors = None
    model.auto_recolor_vertices = None

# -----------------------------------------------------------------------------
#
from chimerax.core.state import State
class ZoneRecolor(State):
    def __init__(self, surface, points, point_colors, distance, sharp_edges):
        self.surface = surface
        self.points = points
        self.point_colors = point_colors
        self.distance = distance
        self.sharp_edges = sharp_edges

    def __call__(self):
        self.set_vertex_colors()

    def set_vertex_colors(self):
        surf = self.surface
        if surf.vertices is not None:
            color_zone(surf, self.points, self.point_colors, self.distance,
                       sharp_edges = self.sharp_edges, auto_update = False)
        surf.auto_recolor_vertices = self

    # -------------------------------------------------------------------------
    #
    def take_snapshot(self, session, flags):
        data = {
            'surface': self.surface,
            'points': self.points,
            'point_colors': self.point_colors,
            'distance': self.distance,
            'sharp_edges': self.sharp_edges,
            'version': 1,
        }
        return data

    # -------------------------------------------------------------------------
    #
    @classmethod
    def restore_snapshot(cls, session, data):
        surf = data['surface']
        if surf is None:
            return None		# Surface to color is gone.
        c = cls(surf, data['points'], data['point_colors'], data['distance'], data['sharp_edges'])
        c.set_vertex_colors()
        return c

        
# -----------------------------------------------------------------------------
#
def color_zone_sharp_edges(surface, points, colors, distance, replace = False):
    surface.scene_position.inverse().move(points)	# Transform points to surface coordinates

    varray = surface.vertices
    from chimerax.core.geometry import find_closest_points
    i1, i2, n1 = find_closest_points(varray, points, distance)

    tarray = surface.triangles
    ec = _edge_cuts(varray, tarray, i1, n1, points, colors, distance)
    
    from numpy import empty, uint8
    carray = empty((len(varray),4), uint8)
    carray[:,:] = surface.color
    for vi,ai in zip(i1, n1):
        carray[vi,:] = colors[ai]

    va, na, ta, ca = _cut_triangles(ec, varray, surface.normals, tarray, carray)

    if replace:
        surface.set_geometry(va, na, ta)
        surface.vertex_colors = ca
        
    return va, na, ta, ca

# -----------------------------------------------------------------------------
#
def _edge_cuts(varray, tarray, vi, pi, points, colors, distance):
    ec = []	# List of triples, two vertex indices and fraction (0-1) indicating cut point
    edges = _triangle_edges(tarray)
    vp = dict(zip(vi,pi))
    for v1,v2 in edges:
        p1,p2 = vp.get(v1), vp.get(v2)
        f = _edge_cut_position(varray, v1, v2, p1, p2, points, colors, distance)
        if f is not None:
            ec.append((v1,v2,f))
    return ec

# -----------------------------------------------------------------------------
#
def _triangle_edges(triangles):
    edges = set()
    for v1,v2,v3 in triangles:
        edges.add((v1,v2) if v1 < v2 else (v2,v1))
        edges.add((v2,v3) if v2 < v3 else (v3,v2))
        edges.add((v3,v1) if v3 < v1 else (v1,v3))
    return edges

# -----------------------------------------------------------------------------
#
def _edge_cut_position(varray, v1, v2, p1, p2, points, colors, distance):
    if p1 == p2:
        return None
    x1, x2 = varray[v1], varray[v2]
    if p2 is None:
        f = _cut_at_range(x1, x2, points[p1], distance)
    elif p1 is None:
        f = _cut_at_range(x1, x2, points[p2], distance)
    else:
        if (colors[p1] == colors[p2]).all():
            return None
        dx = x2-x1
        dp = points[p2]-points[p1]
        px = 0.5*(points[p2]+points[p1]) - x1
        from chimerax.core.geometry import inner_product
        f = inner_product(px, dp) / inner_product(dx, dp)
        if f <= -0.1 or f >= 1.1:
            raise ValueError('Cut fraction %.5g is out of range (0,1)' % f)
        if f < 0:
            f = 0
        elif f > 1:
            f = 1
    return f

# -----------------------------------------------------------------------------
#
def _cut_at_range(x1, x2, p, distance):
    from chimerax.core.geometry import distance as dist
    d1 = dist(x1, p)
    d2 = dist(x2, p)
    f = (d1-distance)/(d1-d2)
    return f
    
# -----------------------------------------------------------------------------
#
def _cut_triangles(edge_cuts, varray, narray, tarray, carray):
    e = {}
    vae = []
    nae = []
    cae = []
    nv = len(varray)
    from chimerax.core.geometry import normalize_vector
    for v1, v2, f in edge_cuts:
        p = (1-f)*varray[v1] + f*varray[v2]
        n = normalize_vector((1-f)*narray[v1] + f*narray[v2])
        vi = nv + len(vae)
        vae.extend((p,p))
        nae.extend((n,n))
        cae.extend((carray[v1], carray[v2]))
        e[(v1,v2)] = vi
        e[(v2,v1)] = vi+1

    if len(vae) == 0:
        return varray, narray, tarray, carray

    tae = []
    for v1,v2,v3 in tarray:
        p12, p23, p31 = e.get((v1,v2)), e.get((v2,v3)), e.get((v3,v1))
        cuts = 3 - [p12, p23, p31].count(None)
        p21, p32, p13 = e.get((v2,v1)), e.get((v3,v2)), e.get((v1,v3))
        if cuts == 3:
            # Add triangle center point, 3 copies
            p = (vae[p12-nv] + vae[p23-nv] + vae[p31-nv]) / 3
            n = normalize_vector(nae[p12-nv] + nae[p23-nv] + nae[p31-nv])
            tc1 = nv + len(vae)
            tc2 = tc1 + 1
            tc3 = tc1 + 2
            vae.extend((p,p,p))
            nae.extend((n,n,n))
            cae.extend((carray[v1], carray[v2], carray[v3]))
            tae.extend(((v1, p12, tc1), (v1, tc1, p13),
                        (v2, p23, tc2), (v2, tc2, p21),
                        (v3, p31, tc3), (v3, tc3, p32)))
        elif cuts == 2:
            if p31 is None:
                tae.extend(((v1, p12, p32), (v1, p32, v3), (v2, p23, p21)))
            elif p12 is None:
                tae.extend(((v2, p23, p13), (v2, p13, v1), (v3, p31, p32)))
            elif p23 is None:
                tae.extend(((v3, p31, p21), (v3, p21, v2), (v1, p12, p13)))
        elif cuts == 1:
            raise ValueError('Triangle with one cut edge')
        elif cuts == 0:
            tae.append((v1,v2,v3))

    from numpy import concatenate, array
    va = concatenate((varray, array(vae, varray.dtype)))
    na = concatenate((narray, array(nae, narray.dtype)))
    ta = array(tae, tarray.dtype)
    ca = concatenate((carray, array(cae, carray.dtype)))
    return va, na, ta, ca
