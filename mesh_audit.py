"""Read-only audit of flat XY Abaqus CPE3/CPS3/CPE4/CPS4 meshes."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

TYPES = {'CPE3': 3, 'CPS3': 3, 'CPE4': 4, 'CPE4R': 4, 'CPS4': 4, 'CPS4R': 4}


def finite_float(value):
    result = float(value.replace('D', 'E').replace('d', 'e'))
    if not math.isfinite(result):
        raise ValueError('Coordinates must be finite')
    return result


def parse_inp(path):
    nodes, elements, elsets = {}, {}, defaultdict(set)
    mode, current_type, current_set, generate = None, None, None, False
    for lineno, raw in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('**'):
            continue
        try:
            if line.startswith('*'):
                fields = [v.strip() for v in line.split(',')]
                keyword = fields[0].lower()
                params = {v.split('=', 1)[0].strip().lower(): v.split('=', 1)[1].strip() for v in fields[1:] if '=' in v}
                flags = {v.lower() for v in fields[1:] if '=' not in v}
                if keyword in ('*include', '*part', '*assembly', '*instance', '*system', '*nmap', '*ngen', '*nfill', '*ncopy', '*elgen', '*elcopy'):
                    raise ValueError(f'{keyword} is not supported; export a flattened mesh first')
                if 'input' in params or 'instance' in params:
                    raise ValueError('External input files and instance-qualified mesh data are unsupported')
                mode = None; current_set = params.get('elset'); generate = 'generate' in flags
                if current_set:
                    current_set = current_set.strip('"').upper()
                if keyword == '*node':
                    if 'system' in params and params['system'].upper() != 'R':
                        raise ValueError('Only Cartesian node coordinates are supported')
                    mode = 'node'
                elif keyword == '*element':
                    current_type = params.get('type', '').upper()
                    if current_type not in TYPES:
                        raise ValueError(f'Unsupported element type: {current_type}')
                    mode = 'element'
                elif keyword == '*elset':
                    if not current_set:
                        raise ValueError('ELSET needs a name')
                    mode = 'elset'
                continue
            values = [v.strip() for v in line.split(',')]
            if values[-1] == '':
                values.pop()
            if mode == 'node':
                if len(values) not in (3, 4):
                    raise ValueError('Expected node id,x,y[,z] on one line')
                nid = int(values[0]); xy = tuple(finite_float(v) for v in values[1:3])
                if nid <= 0 or nid in nodes:
                    raise ValueError('Node ids must be positive and unique')
                if len(values) == 4 and finite_float(values[3]) != 0:
                    raise ValueError('Only flat XY meshes with z=0 are supported')
                nodes[nid] = xy
            elif mode == 'element':
                vals = [int(v) for v in values]
                if len(vals) != TYPES[current_type] + 1:
                    raise ValueError('Unexpected connectivity length; continued elements are unsupported')
                eid = vals[0]
                if eid <= 0 or eid in elements:
                    raise ValueError('Element ids must be positive and unique')
                elements[eid] = {'type': current_type, 'nodes': vals[1:]}
                if current_set:
                    elsets[current_set].add(eid)
            elif mode == 'elset':
                vals = [int(v) for v in values]
                if generate:
                    if len(vals) not in (2, 3):
                        raise ValueError('ELSET GENERATE needs start,end[,step]')
                    lo, hi = vals[:2]; step = vals[2] if len(vals) == 3 else 1
                    if lo <= 0 or hi < lo or step <= 0 or (hi-lo) % step:
                        raise ValueError('Invalid ELSET GENERATE range')
                    elsets[current_set].update(range(lo, hi + 1, step))
                else:
                    elsets[current_set].update(vals)
        except (ValueError, OverflowError) as error:
            raise ValueError(f'Line {lineno}: {error}') from error
    if not nodes or not elements:
        raise ValueError('Mesh needs both nodes and supported elements')
    for eid, element in elements.items():
        if any(n not in nodes for n in element['nodes']):
            raise ValueError(f'Element {eid} references missing nodes')
    if any(eid not in elements for ids in elsets.values() for eid in ids):
        raise ValueError('ELSET references missing elements')
    return nodes, elements, elsets


def signed_area(points):
    x0, y0 = points[0]
    p = [(x-x0, y-y0) for x, y in points]
    return sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p))) / 2


def min_angle(points):
    angles = []
    for i, p in enumerate(points):
        a, b = points[i-1], points[(i+1)%len(points)]
        u, v = (a[0]-p[0], a[1]-p[1]), (b[0]-p[0], b[1]-p[1])
        norm = math.hypot(*u)*math.hypot(*v)
        angles.append(math.degrees(math.acos(max(-1, min(1, (u[0]*v[0]+u[1]*v[1])/norm)))) if norm else 0)
    return min(angles)


def quad_jacobians(points):
    g = 1 / math.sqrt(3)
    sample = [(-g,-g), (g,-g), (g,g), (-g,g), (-1,-1), (1,-1), (1,1), (-1,1), (0,0)]
    result = []
    # Shift the coordinates to reduce cancellation without changing derivatives.
    points = [(x-points[0][0], y-points[0][1]) for x,y in points]
    for xi, eta in sample:
        dx = [-(1-eta), 1-eta, 1+eta, -(1+eta)]
        de = [-(1-xi), -(1+xi), 1+xi, 1-xi]
        xxi = sum(d*p[0]/4 for d,p in zip(dx,points))
        yxi = sum(d*p[1]/4 for d,p in zip(dx,points))
        xeta = sum(d*p[0]/4 for d,p in zip(de,points))
        yeta = sum(d*p[1]/4 for d,p in zip(de,points))
        result.append(xxi*yeta-xeta*yxi)
    return result


def audit(path, min_angle_deg=20, max_edge_ratio=10):
    if not math.isfinite(min_angle_deg) or not 0 <= min_angle_deg < 180:
        raise ValueError('min_angle must be finite and in [0,180)')
    if not math.isfinite(max_edge_ratio) or max_edge_ratio < 1:
        raise ValueError('max_edge_ratio must be finite and >= 1')
    nodes, elements, elsets = parse_inp(path)
    edges, coord_owners, connectivity_owners = defaultdict(list), defaultdict(list), defaultdict(list)
    issues, records = [], []
    for nid, xy in nodes.items(): coord_owners[xy].append(nid)
    for eids in coord_owners.values():
        if len(eids) > 1: issues.append({'kind':'coincident_nodes', 'node_ids':eids})
    for eid, element in elements.items():
        conn = element['nodes']; points = [nodes[n] for n in conn]
        connectivity_owners[tuple(sorted(conn))].append(eid)
        lengths = [math.dist(points[i], points[(i+1)%len(points)]) for i in range(len(points))]
        area, angle = signed_area(points), min_angle(points)
        ratio = max(lengths)/min(lengths) if min(lengths) else None
        tolerance = max(lengths)**2 * 1e-12
        row = {'element_id':eid, 'type':element['type'], 'signed_area':area,
               'min_angle_deg':angle, 'edge_length_ratio':ratio}
        problems = []
        if len(set(conn)) != len(conn): problems.append('repeated_connectivity_node')
        if area <= tolerance: problems.append('nonpositive_or_degenerate_area')
        if angle < min_angle_deg: problems.append('small_angle')
        if ratio is None or ratio > max_edge_ratio: problems.append('edge_length_ratio')
        if len(conn) == 4:
            row['min_sampled_jacobian'] = min(quad_jacobians(points))
            if row['min_sampled_jacobian'] <= tolerance / 4: problems.append('nonpositive_or_degenerate_q4_jacobian')
        for kind in problems: issues.append({'kind':kind,'element_id':eid})
        records.append(row)
        for i, nid in enumerate(conn): edges[tuple(sorted((nid,conn[(i+1)%len(conn)])))].append(eid)
    for ids in connectivity_owners.values():
        if len(ids)>1: issues.append({'kind':'duplicate_element_connectivity','element_ids':ids})
    for edge, owners in edges.items():
        if len(owners)>2: issues.append({'kind':'nonmanifold_edge','node_ids':list(edge),'element_ids':owners})
    return {'schema_version':1,'input_name':path.name,'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'audit_pass':not issues, 'thresholds':{'min_angle_deg':min_angle_deg,'max_edge_length_ratio':max_edge_ratio},
            'node_count':len(nodes),'element_count':len(elements),'boundary_edge_count':sum(len(v)==1 for v in edges.values()),
            'elset_element_counts':{k:len(v) for k,v in sorted(elsets.items())},
            'issues':issues,'elements':records,
            'limitations':['Only explicit, single-scope XY linear triangle/Q4 meshes are supported.',
                           'Boundary edges include the exterior and holes; they do not prove an unpaired material interface.',
                           'No full overlap/intersection search or solver-specific UEL validation is performed.',
                           'Positive geometric checks do not prove solution accuracy or physical correctness.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inp',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--min-angle',type=float,default=20)
    parser.add_argument('--max-edge-ratio',type=float,default=10)
    args=parser.parse_args()
    try:
        report=audit(args.inp,args.min_angle,args.max_edge_ratio)
        text=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        if args.output:
            with args.output.open('x',encoding='utf-8') as stream: stream.write(text)
        print(text,end='')
        return 0 if report['audit_pass'] else 1
    except (ValueError,OSError,TypeError,OverflowError) as error:
        parser.exit(2,f'Input/output error: {error}\n')


if __name__=='__main__':
    raise SystemExit(main())
