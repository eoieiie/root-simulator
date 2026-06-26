"""IR용: GA 최적 정사면체 에어룸 위치 standalone 3D 이미지"""
import os, sys, math, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import warnings
warnings.filterwarnings('ignore')

for fn in ['Malgun Gothic', 'NanumGothic', 'AppleGothic']:
    try: plt.rcParams['font.family'] = fn; break
    except: pass
plt.rcParams['axes.unicode_minus'] = False

POT_R = 6.5; POT_H = 15.0

OPTIMIZED_AIRROOMS = [
    (1.84, 3.74, 0.51), (1.96, 6.26, 0.82),
    (2.60, 8.44, 0.50), (4.70, 12.10, 0.50),
    (3.27, 9.82, 0.50), (1.80, 2.45, 0.90),
]

def draw_tetrahedron(ax, cx, cy, cz, size, alpha=0.45, cf='#A8C8E8', ce='#2C3E7A'):
    h = size * math.sqrt(2/3); r = size / math.sqrt(3)
    v = np.array([
        [cx+r*math.cos(0),           cy+r*math.sin(0),           cz-h/3],
        [cx+r*math.cos(2*math.pi/3), cy+r*math.sin(2*math.pi/3), cz-h/3],
        [cx+r*math.cos(4*math.pi/3), cy+r*math.sin(4*math.pi/3), cz-h/3],
        [cx,                          cy,                          cz+2*h/3],
    ])
    faces = [[v[0],v[1],v[2]],[v[0],v[1],v[3]],[v[1],v[2],v[3]],[v[0],v[2],v[3]]]
    ax.add_collection3d(Poly3DCollection(faces, alpha=alpha, facecolor=cf,
        edgecolor=ce, linewidth=1.5))

def draw_pot_wire(ax, alpha=0.25):
    th = np.linspace(0, 2*math.pi, 48)
    for z in [0, POT_H]:
        ax.plot(POT_R*np.cos(th), POT_R*np.sin(th), np.full_like(th, z),
                color='#8B6F47', lw=1.0, alpha=alpha)
    for a in [0, math.pi/2, math.pi, 3*math.pi/2]:
        ax.plot([POT_R*math.cos(a)]*2, [POT_R*math.sin(a)]*2, [0, POT_H],
                color='#8B6F47', lw=0.8, alpha=alpha*0.5)

# Positions
airrooms_3d = []
idx_map = {}
for i, (r, z, rad) in enumerate(OPTIMIZED_AIRROOMS):
    group = []
    for k in range(3):
        th = k * 2*math.pi/3
        group.append((r*math.cos(th), r*math.sin(th), z, rad))
    airrooms_3d.append((group, r, z, rad))

# Figure
fig = plt.figure(figsize=(14, 7))
fig.patch.set_facecolor('#FAFAFA')

# -- Main 3D view --
ax1 = fig.add_subplot(1, 2, 1, projection='3d')
draw_pot_wire(ax1)
colors = ['#E07A5F', '#3D5A80', '#81B29A', '#E09F3E', '#9C89B8', '#F2CC8F']
labels_added = {}
for gi, (group, r, z, rad) in enumerate(airrooms_3d):
    c = colors[gi % len(colors)]
    for k, (cx, cy, cz, rad2) in enumerate(group):
        draw_tetrahedron(ax1, cx, cy, cz, rad2, alpha=0.5, cf=c, ce=c)
    # Label
    ax1.text(group[0][0], group[0][1], group[0][2]+0.8, f'#{gi+1}',
             fontsize=8, fontweight='bold', color=c, ha='center')

ax1.set_xlim(-POT_R*1.2, POT_R*1.2)
ax1.set_ylim(-POT_R*1.2, POT_R*1.2)
ax1.set_zlim(0, POT_H*1.1)
ax1.set_xlabel('X (cm)', fontsize=8); ax1.set_ylabel('Y (cm)', fontsize=8)
ax1.set_zlabel('Height (cm)', fontsize=8)
ax1.set_title('GA-Optimized Tetrahedron Airrooms (3D)', fontsize=13, fontweight='bold', color='#1B4332')
ax1.view_init(elev=20, azim=35)
ax1.grid(True, alpha=0.08)
for d in 'xyz': getattr(ax1, f'{d}axis').pane.fill = False

# Legend
leg_el = []
for gi, (group, r, z, rad) in enumerate(airrooms_3d):
    c = colors[gi % len(colors)]
    leg_el.append(mpatches.Patch(facecolor=c, edgecolor=c, alpha=0.5,
        label=f'#{gi+1}  r={r:.1f}  z={z:.1f}  ø{rad:.2f}'))
ax1.legend(handles=leg_el, loc='upper left', fontsize=7, framealpha=0.9,
           bbox_to_anchor=(0.0, 1.02))

# -- Top-down view --
ax2 = fig.add_subplot(1, 2, 2)
ax2.set_aspect('equal')
th = np.linspace(0, 2*math.pi, 100)
ax2.plot(POT_R*np.cos(th), POT_R*np.sin(th), color='#8B6F47', lw=1.5)
ax2.plot([0,0],[-POT_R,POT_R], color='#DDD', lw=0.5, ls='--')
ax2.plot([-POT_R,POT_R],[0,0], color='#DDD', lw=0.5, ls='--')

for gi, (group, r, z, rad) in enumerate(airrooms_3d):
    c = colors[gi % len(colors)]
    xs = [g[0] for g in group]
    ys = [g[1] for g in group]
    ax2.scatter(xs, ys, s=220, c=c, edgecolors='#333', linewidths=0.8, zorder=5, alpha=0.8)
    # Draw triangle connecting the 3
    xs.append(xs[0]); ys.append(ys[0])
    ax2.plot(xs, ys, color=c, lw=1.0, alpha=0.4, ls='--')
    # Label one per group
    ax2.text(xs[0], ys[0]+0.7, f'#{gi+1}', fontsize=7, ha='center', color=c, fontweight='bold')

ax2.set_xlim(-POT_R*1.15, POT_R*1.15)
ax2.set_ylim(-POT_R*1.15, POT_R*1.15)
ax2.set_xlabel('X (cm)', fontsize=9); ax2.set_ylabel('Y (cm)', fontsize=9)
ax2.set_title('Top-Down View (z-axis)', fontsize=13, fontweight='bold', color='#1B4332')
ax2.grid(True, alpha=0.2, ls='--')
ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)

# Caption
fig.text(0.5, 0.02,
    '6 tetrahedrons × 3 directions (120°) = 18 air voids · Each # = 3 at same (r,z) height',
    ha='center', fontsize=9, color='#555', style='italic')

# Info table on the side
info_text = "Optimal Airroom Positions (GA Final Run)\n\n"
for gi, (group, r, z, rad) in enumerate(airrooms_3d):
    zone = "L" if z < 5 else ("M" if z < 9 else "U")
    info_text += f"#{gi+1} ({zone}): r={r:.2f}cm  z={z:.2f}cm  rad={rad:.2f}cm\n"
info_text += f"\nPot: 13cm × 15cm"
fig.text(0.5, 0.93, info_text, ha='center', fontsize=8.5, color='#333',
         fontfamily='monospace',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#F0F4F0', edgecolor='#2D6A4F', lw=1))

plt.tight_layout(rect=[0, 0.05, 1, 0.88])
from datetime import datetime
date_str = datetime.now().strftime("%Y-%m-%d")
runs_dir = os.path.join(os.path.dirname(__file__), '..', 'output', date_str)
run_num = 1
while os.path.exists(os.path.join(runs_dir, f"run-{run_num:03d}")):
    run_num += 1
run_dir = os.path.join(runs_dir, f"run-{run_num:03d}")
out_dir = os.path.join(run_dir, "viz")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "gwc_airroom_layout.png")
plt.savefig(out, dpi=200, bbox_inches='tight', facecolor='white', edgecolor='none')
print(f"Saved: {out}")
plt.close()
