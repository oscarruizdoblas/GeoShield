#!/usr/bin/env python3
"""GeoShield - reusable route planner around circular no-fly zones.

    plan(start, dest, keepout) -> (waypoints[(lat, lon)], length_m, zones_crossed_by_straight_line)

Method: visibility graph + Dijkstra.
  1. Work in a local flat frame (metres East/North) centred on the start-dest midpoint.
  2. Graph nodes: start, destination and a ring of `nring` points around every zone, placed at
     radius r + margin (the margin is the safety buffer from the zone edge).
  3. Two nodes are connected if the straight segment between them does not enter any
     (inflated) zone; the edge weight is the segment length.
  4. Dijkstra gives the shortest path; it hugs the rings, i.e. it skirts each zone at ~margin.
Used by plan_and_fly.py (outbound route), return_home.py (way back) and make_qgc_plan.py.
"""
import math, heapq

def plan(start, dest, keepout, margin=75.0, nring=48):
    # Local equirectangular projection around the midpoint (error is negligible over ~2 km)
    lat0 = (start[0] + dest[0]) / 2.0
    lon0 = (start[1] + dest[1]) / 2.0
    MPLAT = 110540.0
    MPLON = 111320.0 * math.cos(math.radians(lat0))
    def en(lat, lon): return ((lon - lon0) * MPLON, (lat - lat0) * MPLAT)   # lat/lon -> metres
    def ll(e, n):     return (lat0 + n / MPLAT, lon0 + e / MPLON)           # metres -> lat/lon

    A = en(*start); B = en(*dest)
    ZON = [(en(z['lat'], z['lon']), z['r'], z['name']) for z in keepout]

    def seg_hits(p, q, c, r):
        """True if segment p-q passes closer than r to centre c (closest point on the segment)."""
        px, py = p; qx, qy = q; cx, cy = c
        dx, dy = qx - px, qy - py
        L2 = dx*dx + dy*dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((cx-px)*dx + (cy-py)*dy)/L2))
        hx, hy = px + t*dx, py + t*dy
        return math.hypot(cx-hx, cy-hy) < r - 1e-6
    cosr = math.cos(math.pi / nring)   # how far a chord between two neighbouring ring nodes dips inwards
    def blocked(p, q):
        # Test against the INFLATED radius (r + margin), reduced by the chord dip between
        # neighbouring ring nodes, so the route can follow the ring and still keep ~margin of
        # real clearance (testing only against r would let chords graze the zone).
        return any(seg_hits(p, q, c, (r + margin) * cosr - 0.5) for (c, r, _) in ZON)

    nodes = [A, B]
    for (c, r, _) in ZON:
        for k in range(nring):
            a = 2*math.pi*k/nring
            nodes.append((c[0] + (r+margin)*math.cos(a), c[1] + (r+margin)*math.sin(a)))
    N = len(nodes)
    adj = [[] for _ in range(N)]
    for i in range(N):
        for j in range(i+1, N):
            if not blocked(nodes[i], nodes[j]):
                d = math.hypot(nodes[i][0]-nodes[j][0], nodes[i][1]-nodes[j][1])
                adj[i].append((j, d)); adj[j].append((i, d))

    # Dijkstra from node 0 (start) to node 1 (destination)
    INF = float('inf'); dist = [INF]*N; prev = [-1]*N; dist[0] = 0.0
    pq = [(0.0, 0)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]: continue
        if u == 1: break
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))

    if dist[1] == INF:
        return None, INF, []          # no route (the zones block every path)
    path_m = []; u = 1
    while u != -1:
        path_m.append(nodes[u]); u = prev[u]
    path_m.reverse()
    waypoints = [ll(*p) for p in path_m]
    crossed = [nm for (c, r, nm) in ZON if seg_hits(A, B, c, r)]   # zones the direct line would cross
    return waypoints, dist[1], crossed


if __name__ == '__main__':
    import sys
    from zones import START, DEST, KEEPOUT
    wps, L, cr = plan(START, DEST, KEEPOUT)
    print("route: %.0f m, %d waypoints; the straight line crosses: %s" % (L, len(wps), ", ".join(cr) or "nothing"))
    for i, (la, lo) in enumerate(wps):
        print("  %d  %.7f, %.7f" % (i, la, lo))
