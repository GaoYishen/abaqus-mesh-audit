"""Build the explanatory README figure; requires Matplotlib for asset generation."""
from pathlib import Path
import importlib.util
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mesh_audit', ROOT / 'mesh_audit.py')
mesh_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mesh_audit)
report = mesh_audit.audit(ROOT / 'examples/inverted-triangle.inp')
assert report['issues'] == [{'kind': 'nonpositive_or_degenerate_area', 'element_id': 1}]
assert report['elements'][0]['signed_area'] == -0.5

plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none'})
fig = plt.figure(figsize=(12, 5.4), facecolor='#f3f6fb')
fig.text(.045, .9, 'Find the mesh issue. Locate the element.', fontsize=23, weight='bold', color='#122641')
fig.text(.045, .835, '2D finite element mesh checks | Python CLI + Agent Skill', fontsize=13, color='#465c77')

for x, width in [(.04, .40), (.47, .49)]:
    fig.add_artist(FancyBboxPatch((x, .16), width, .60, boxstyle='round,pad=0.01,rounding_size=0.02',
                   transform=fig.transFigure, facecolor='white', edgecolor='#dae2ef', zorder=0))
fig.text(.065, .695, 'INPUT: CLOCKWISE TRIANGLE', fontsize=11, weight='bold', color='#465c77')
fig.text(.495, .695, 'REPORT: ELEMENT 1 FLAGGED', fontsize=11, weight='bold', color='#b13242')

ax = fig.add_axes([.065, .245, .35, .40])
ax.set_aspect('equal')
ax.add_patch(Polygon([(0, 0), (0, 1), (1, 0)], facecolor='#fce3e6', edgecolor='#c53a4b', linewidth=2.5))
for x, y, label, dx, dy in [(0, 0, '1 (0, 0)', -.10, -.15), (0, 1, '3 (0, 1)', -.10, .09), (1, 0, '2 (1, 0)', -.15, -.15)]:
    ax.plot(x, y, 'o', color='#122641', markersize=6)
    ax.text(x+dx, y+dy, label, fontsize=11, color='#122641')
for start, end in [((0, .22), (0, .72)), ((.22, .78), (.68, .32)), ((.75, 0), (.25, 0))]:
    ax.annotate('', xy=end, xytext=start, arrowprops={'arrowstyle': '->', 'color': '#b13242', 'lw': 2})
ax.text(.08, .14, 'Element 1', fontsize=10, weight='bold', color='#b13242')
ax.set(xlim=(-.27, 1.3), ylim=(-.25, 1.25))
ax.axis('off')

fig.text(.495, .57, 'audit_pass: false', fontsize=18, weight='bold', color='#b13242', family='DejaVu Sans Mono')
fig.text(.495, .46, 'element_id: 1', fontsize=16, color='#122641', family='DejaVu Sans Mono')
fig.text(.495, .38, 'signed_area: -0.5', fontsize=16, color='#122641', family='DejaVu Sans Mono')
fig.text(.495, .28, 'nonpositive_or_degenerate_area', fontsize=12, color='#b13242', family='DejaVu Sans Mono')
fig.text(.495, .20, 'JSON report with element IDs and file SHA-256', fontsize=11, color='#465c77')
fig.text(.045, .075, 'Illustration from examples/inverted-triangle.inp | CLI output: JSON', fontsize=10, color='#465c77')
out = ROOT / 'docs/assets'
out.mkdir(parents=True, exist_ok=True)
fig.savefig(out / 'mesh-audit-preview.png', dpi=160, facecolor=fig.get_facecolor())
fig.savefig(out / 'mesh-audit-preview.svg', facecolor=fig.get_facecolor())
plt.close(fig)
