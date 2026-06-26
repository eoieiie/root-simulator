# IR v2 - Procedural organic 3D root system
# - Organic random growth with 3 generations
# - Pruning → fine root explosion that KEEPS GROWING
# - Numbers from real 2D engine, visuals from procedural generation
# - Unused airrooms removed, control has gen2+gen3 too

import os, sys, math, random, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import warnings
warnings.filterwarnings('ignore')

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ_ROOT)
from src.config import SimConfig
from src.pipeline import SimPipeline
from src.geometry import Airroom

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

C = {
    "pot_edge": "#8B6F47", "airroom": "#2C3E7A",
    "airroom_face": "#A8C8E8",
    "gen1": "#1B4332", "gen2": "#2D6A4F", "gen3": "#74C69D",
    "pruning_star": "#FFD700", "bg": "#FAFAFA", "control": "#B0B0B0",
}

def draw_tetrahedron(ax, cx, cy, cz, size, alpha=0.3, cf=None, ce=None):
    h = size * math.sqrt(2/3)
    r = size / math.sqrt(3)
    v = np.array([
        [cx+r*math.cos(0),           cy+r*math.sin(0),           cz-h/3],
        [cx+r*math.cos(2*math.pi/3), cy+r*math.sin(2*math.pi/3), cz-h/3],
        [cx+r*math.cos(4*math.pi/3), cy+r*math.sin(4*math.pi/3), cz-h/3],
        [cx,                          cy,                          cz+2*h/3],
    ])
    faces = [[v[0],v[1],v[2]],[v[0],v[1],v[3]],[v[1],v[2],v[3]],[v[0],v[2],v[3]]]
    ax.add_collection3d(Poly3DCollection(faces, alpha=alpha,
        facecolor=cf or C["airroom_face"], edgecolor=ce or C["airroom"], linewidth=1.2))

def draw_pot(ax, alpha=0.3):
    th = np.linspace(0, 2*math.pi, 48)
    ax.plot(POT_R*np.cos(th), POT_R*np.sin(th), np.full_like(th, POT_H),
            color=C["pot_edge"], lw=1.5, alpha=alpha)
    ax.plot(POT_R*np.cos(th), POT_R*np.sin(th), np.full_like(th, 0),
            color=C["pot_edge"], lw=1.5, alpha=alpha)
    for a in [0, math.pi/2, math.pi, 3*math.pi/2]:
        ax.plot([POT_R*math.cos(a)]*2, [POT_R*math.sin(a)]*2, [0, POT_H],
                color=C["pot_edge"], lw=1.0, alpha=alpha*0.5)

def in_bounds(x, y, z):
    return math.sqrt(x*x + y*y) < POT_R*0.92 and 0.3 < z < POT_H+0.5

def normalize(v):
    l = math.sqrt(v[0]**2+v[1]**2+v[2]**2)
    if l < 1e-10: return [0,0,-1]
    return [v[0]/l, v[1]/l, v[2]/l]

class RootPath:
    def __init__(self, pos, gen, thickness):
        self.pts = [tuple(pos)]
        self.gen = gen
        self.thk = thickness
        self.alive = True
        self.dir = [0, 0, -0.8]

def grow_primary(seed):
    rng = random.Random(seed+1000)
    roots = []
    for i in range(3):
        ang = i*2*math.pi/3 + rng.uniform(-0.15, 0.15)
        sx = rng.uniform(0,0.3)*math.cos(ang)
        sy = rng.uniform(0,0.3)*math.sin(ang)
        r = RootPath((sx,sy,POT_H-0.3), 1, 0.18)
        for _ in range(75):
            if not r.alive: break
            nx = rng.uniform(-0.05,0.05); ny = rng.uniform(-0.05,0.05)
            nz = rng.uniform(-0.08,0.02)
            d = normalize([r.dir[0]+nx, r.dir[1]+ny, r.dir[2]-0.1+nz])
            px = r.pts[-1][0] + d[0]*0.25; py = r.pts[-1][1] + d[1]*0.25
            pz = r.pts[-1][2] + d[2]*0.25
            if not in_bounds(px,py,pz): r.alive = False; break
            r.pts.append((px,py,pz)); r.dir = d
        roots.append(r)
    return roots

def grow_lateral(primary_roots, airrooms_3d, seed, is_control=False):
    rng = random.Random(seed+2000)
    roots = []; pruning_pts = []; hit = set()
    step = 0.25
    for pri in primary_roots:
        if len(pri.pts) < 8: continue
        n = 6 if is_control else 12
        for li in range(n):
            idx = int(4 + li*(len(pri.pts)-6)/max(n-1,1))
            if idx >= len(pri.pts): idx = len(pri.pts)-1
            bp = pri.pts[idx]
            ba = rng.uniform(0,2*math.pi)
            bz = -0.1 + rng.uniform(-0.15, 0.2)
            lat = RootPath(bp, 2, 0.155)
            lat.dir = normalize([math.cos(ba), math.sin(ba), bz])
            pruned = False
            for _ in range(35):
                if not lat.alive: break
                nx = rng.uniform(-0.08,0.08); ny = rng.uniform(-0.08,0.08)
                nz = rng.uniform(-0.06,0.04)
                d = normalize([lat.dir[0]+nx, lat.dir[1]+ny, lat.dir[2]-0.04+nz])
                px = lat.pts[-1][0]+d[0]*step; py = lat.pts[-1][1]+d[1]*step
                pz = lat.pts[-1][2]+d[2]*step
                if not in_bounds(px,py,pz): lat.alive = False; break
                lat.pts.append((px,py,pz)); lat.dir = d
                if not is_control and not pruned and len(lat.pts) >= 3:
                    for ai,(cx,cy,cz,rad) in enumerate(airrooms_3d):
                        if ai in hit and rng.random() > 0.2: continue
                        if math.sqrt((px-cx)**2+(py-cy)**2+(pz-cz)**2) < rad*2.0:
                            pruned = True; hit.add(ai)
                            for fi in range(rng.randint(8,14)):
                                fa = rng.uniform(0,2*math.pi)
                                fz = -0.1+rng.uniform(-0.15,0.1)
                                fine = RootPath((px,py,pz), 3, 0.133)
                                fine.dir = normalize([math.cos(fa), math.sin(fa), fz])
                                for _ in range(rng.randint(12,20)):
                                    if not fine.alive: break
                                    f_nx = rng.uniform(-0.12,0.12)
                                    f_ny = rng.uniform(-0.12,0.12)
                                    f_nz = rng.uniform(-0.08,0.06)
                                    f_d = normalize([fine.dir[0]+f_nx, fine.dir[1]+f_ny, fine.dir[2]+f_nz])
                                    fpx = fine.pts[-1][0]+f_d[0]*step*0.8
                                    fpy = fine.pts[-1][1]+f_d[1]*step*0.8
                                    fpz = fine.pts[-1][2]+f_d[2]*step*0.8
                                    if not in_bounds(fpx,fpy,fpz): fine.alive=False; break
                                    fine.pts.append((fpx,fpy,fpz)); fine.dir = f_d
                                roots.append(fine)
                            pruning_pts.append((px,py,pz)); break
            roots.append(lat)
            if not pruned and len(lat.pts) >= 5 and rng.random() < (0.5 if is_control else 0.6):
                tip = lat.pts[-1]
                for fi in range(rng.randint(3,5)):
                    fa = rng.uniform(0,2*math.pi); fz = -0.15+rng.uniform(-0.1,0.1)
                    fine = RootPath(tip, 3, 0.133)
                    fine.dir = normalize([math.cos(fa), math.sin(fa), fz])
                    for _ in range(rng.randint(8,14)):
                        if not fine.alive: break
                        f_nx = rng.uniform(-0.1,0.1); f_ny = rng.uniform(-0.1,0.1)
                        f_nz = rng.uniform(-0.06,0.06)
                        f_d = normalize([fine.dir[0]+f_nx,fine.dir[1]+f_ny,fine.dir[2]+f_nz])
                        fpx = fine.pts[-1][0]+f_d[0]*step*0.8
                        fpy = fine.pts[-1][1]+f_d[1]*step*0.8
                        fpz = fine.pts[-1][2]+f_d[2]*step*0.8
                        if not in_bounds(fpx,fpy,fpz): fine.alive=False; break
                        fine.pts.append((fpx,fpy,fpz)); fine.dir = f_d
                    roots.append(fine)
    return roots, pruning_pts, hit

def assign_airroom_3d(airroom_2d, n_rot=3):
    result = []
    for r,z,rad in airroom_2d:
        for k in range(n_rot):
            th = k*2*math.pi/n_rot + random.uniform(-0.05,0.05)
            result.append((r*math.cos(th), r*math.sin(th), z, rad))
    return result

def run_engine(cfg_path, airrooms_list, seed=42):
    cfg = SimConfig.from_json(cfg_path)
    return SimPipeline(cfg).run(seed=seed, airrooms_override=airrooms_list)

def run_control(cfg_path, seed=42):
    cfg = SimConfig.from_json(cfg_path)
    from src.geometry import generate_random_airrooms
    rng = random.Random(seed)
    return SimPipeline(cfg).run(seed=seed, airrooms_override=generate_random_airrooms(cfg,n=0,rng=rng))

def plot_3d(ax, roots, pruning_pts, airrooms, title, show_airrooms=True):
    draw_pot(ax)
    if show_airrooms:
        for cx,cy,cz,rad in airrooms:
            draw_tetrahedron(ax,cx,cy,cz,rad,alpha=0.25)
    cm = {1:C["gen1"],2:C["gen2"],3:C["gen3"]}
    # Line widths proportional to sqrt(radius) for visual hierarchy
    # slope=0.85 radii: gen1=0.18, gen2=0.155, gen3=0.133
    wm = {1:3.0,2:2.2,3:1.4}; am = {1:1.0,2:0.85,3:0.55}
    for gen in [1,2,3]:
        for r in roots:
            if r.gen != gen or len(r.pts) < 2: continue
            pts = np.array(r.pts)
            ax.plot(pts[:,0],pts[:,1],pts[:,2],color=cm.get(gen,C["gen3"]),
                    linewidth=wm.get(gen,0.5),alpha=am.get(gen,0.5),solid_capstyle='round')
    for pt in pruning_pts:
        ax.scatter(pt[0],pt[1],pt[2],c=C["pruning_star"],s=65,marker='*',
                   edgecolors='#333',linewidths=0.5,zorder=20)
    ax.set_xlim(-POT_R*1.15,POT_R*1.15); ax.set_ylim(-POT_R*1.15,POT_R*1.15)
    ax.set_zlim(0,POT_H*1.08)
    ax.set_title(title,fontsize=11,fontweight='bold',pad=12,color='#222')
    ax.view_init(elev=22,azim=38); ax.grid(True,alpha=0.08)
    for d in 'xyz': getattr(ax,f'{d}axis').pane.fill = False
    ax.set_xlabel('X (cm)',fontsize=7); ax.set_ylabel('Y (cm)',fontsize=7)
    ax.set_zlabel('Height (cm)',fontsize=7)

def main():
    print("="*55)
    print("GWC IR 3D Viz v2 — Procedural Organic Roots")
    print("="*55)
    cfg_path = os.path.join(PROJ_ROOT,"configs","pot_13.json"); SEED=42
    random.seed(SEED)

    print("\n[1/5] Real engine (numbers)...")
    opt_ar_2d = [Airroom(r=r,z=z,radius=rad) for r,z,rad in OPTIMIZED_AIRROOMS]
    res_exp = run_engine(cfg_path,opt_ar_2d,SEED)
    res_ctrl = run_control(cfg_path,SEED)
    st_exp = res_exp["root_system"].statistics()
    st_ctrl = res_ctrl["root_system"].statistics()
    s_ctrl, s_exp = st_ctrl['total_surface_area_mm2'], st_exp['total_surface_area_mm2']
    seg_ctrl, seg_exp = st_ctrl['total_segments'], st_exp['total_segments']
    p_exp = st_exp['pruning_count']
    sc_ctrl = res_ctrl['score']['total']; sc_exp = res_exp['score']['total']
    upt_exp = res_exp['score']['metrics']['n_uptake_mg']
    # Effective (absorption-weighted) surface area
    eff_ctrl = res_ctrl["root_system"].effective_surface_area()
    eff_exp = res_exp["root_system"].effective_surface_area()
    print(f"  Ctrl: {seg_ctrl}seg {s_ctrl:.0f}mm2 eff={eff_ctrl:.0f} score={sc_ctrl:.0f}")
    print(f"  Exp:  {seg_exp}seg {s_exp:.0f}mm2 eff={eff_exp:.0f} pruning={p_exp} score={sc_exp:.0f}")

    print("[2/5] 3D airrooms...")
    all_ar = assign_airroom_3d(OPTIMIZED_AIRROOMS,3)
    print(f"  Total 3D airrooms: {len(all_ar)}")

    print("[3/5] Procedural roots: control...")
    pc = grow_primary(SEED+1); lc,_,_ = grow_lateral(pc,[],SEED+2,is_control=True)
    ctrl_roots = pc+lc

    print("[4/5] Procedural roots: experimental...")
    pe = grow_primary(SEED+3); le,ppe,hit = grow_lateral(pe,all_ar,SEED+4,is_control=False)
    exp_roots = pe+le
    ar_disp = [all_ar[i] for i in sorted(hit)]
    print(f"  Used airrooms: {len(ar_disp)}/{len(all_ar)}  Pruning: {len(ppe)}")

    def cg(r,g): return len([x for x in r if x.gen==g])
    print(f"  Ctrl gens: {cg(ctrl_roots,1)},{cg(ctrl_roots,2)},{cg(ctrl_roots,3)}")
    print(f"  Exp  gens: {cg(exp_roots,1)},{cg(exp_roots,2)},{cg(exp_roots,3)}")

    print("[5/5] Figure...")
    fig = plt.figure(figsize=(20,12))
    fig.patch.set_facecolor(C["bg"])
    fig.suptitle('Garden with Couch — Air-Pruning Optimization Simulation',
                 fontsize=18,fontweight='bold',y=0.98,color='#1B4332')
    fig.text(0.5,0.955,
        f'GA-optimized 6 tetrahedron airrooms · 13cm pot · {3*30*20} evaluations',
        ha='center',fontsize=10,color='#555')

    ax1 = fig.add_subplot(2,3,1,projection='3d')
    plot_3d(ax1,ctrl_roots,[],[],'(A) Control — Natural Growth',show_airrooms=False)

    ax2 = fig.add_subplot(2,3,2,projection='3d')
    plot_3d(ax2,exp_roots,ppe,ar_disp,'(B) GwC Air-Pruning Pot',show_airrooms=True)
    leg = [
        plt.Line2D([0],[0],color=C["gen1"],lw=2.5,label='Primary roots (Gen 1)'),
        plt.Line2D([0],[0],color=C["gen2"],lw=1.4,label='Lateral roots (Gen 2)'),
        plt.Line2D([0],[0],color=C["gen3"],lw=0.6,label='Fine roots (Gen 3)'),
        mpatches.Patch(facecolor=C["airroom_face"],edgecolor=C["airroom"],label='Tetrahedron airroom'),
    ]
    if ppe: leg.append(plt.Line2D([0],[0],marker='*',color='w',
        markerfacecolor=C["pruning_star"],markersize=10,markeredgecolor='#333',
        label=f'Pruning (★ {len(ppe)})'))
    ax2.legend(handles=leg,loc='upper left',fontsize=7,framealpha=0.92,bbox_to_anchor=(0.0,1.02))

    ax3 = fig.add_subplot(2,3,3,projection='3d')
    draw_pot(ax3,alpha=0.2)
    for cx,cy,cz,rad in ar_disp: draw_tetrahedron(ax3,cx,cy,cz,rad,alpha=0.2)
    for gen in [1,2,3]:
        for r in exp_roots:
            if r.gen!=gen or len(r.pts)<2: continue
            pts = np.array(r.pts)
            w = {1:1.8,2:1.4,3:0.9}.get(gen,0.9)
            ax3.plot(pts[:,0],pts[:,1],pts[:,2],
                color={1:C["gen1"],2:C["gen2"],3:C["gen3"]}.get(gen,C["gen3"]),
                linewidth=w,alpha=0.7)
    for pt in ppe[:30]: ax3.scatter(pt[0],pt[1],pt[2],c=C["pruning_star"],s=50,
        marker='*',edgecolors='#333',linewidths=0.4,zorder=20)
    ax3.set_xlim(-POT_R,POT_R); ax3.set_ylim(-POT_R,POT_R); ax3.set_zlim(0,POT_H)
    ax3.set_title('(C) Pruning → Fine Root Explosion',fontsize=11,fontweight='bold')
    ax3.view_init(elev=25,azim=20); ax3.grid(True,alpha=0.08)
    for d in 'xyz': getattr(ax3,f'{d}axis').pane.fill = False

    # ── (D) Quantitative Metrics — 3 enlarged inset charts ──
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    ax4 = fig.add_subplot(2,3,4)
    ax4.set_title('(D) Quantitative Metrics',fontsize=11,fontweight='bold')

    def _bar_inset(parent, v_ctrl, v_exp, title, ylabel, anchor, fmt='.0f'):
        """Create an enlarged bar inset for panel D."""
        left, bottom, w, h = anchor
        ax_in = inset_axes(parent, width=f'{w*100:.0f}%', height=f'{h*100:.0f}%',
                           loc='upper left',
                           bbox_to_anchor=(left, bottom, w, h),
                           bbox_transform=parent.transAxes)
        bw = 0.30
        ax_in.bar(0 - bw/2, v_ctrl, bw, color=C["control"], edgecolor='#666', lw=0.8)
        ax_in.bar(1 - bw/2, v_exp, bw, color=C["gen2"], edgecolor='#333', lw=0.8)
        ax_in.set_xticks([0, 1])
        ax_in.set_xticklabels(['Ctrl', 'Exp'], fontsize=9)
        ax_in.set_ylabel(ylabel, fontsize=9)
        ax_in.set_title(title, fontsize=10, fontweight='bold')
        yrng = max(v_ctrl, v_exp) * 1.35
        ax_in.text(0, v_ctrl + yrng * 0.03, f'{v_ctrl:{fmt}}',
                   ha='center', fontsize=9, color='#666')
        ratio = v_exp / max(v_ctrl, 1)
        lbl = f'{v_exp:{fmt}} ({ratio:.1f}x)' if ratio > 1.05 else f'{v_exp:{fmt}}'
        ax_in.text(1, v_exp + yrng * 0.03, lbl,
                   ha='center', fontsize=9, fontweight='bold', color=C["gen1"])
        ax_in.set_ylim(0, yrng)
        ax_in.grid(True, axis='y', alpha=0.3, ls='--')
        ax_in.spines['top'].set_visible(False)
        ax_in.spines['right'].set_visible(False)
        return ax_in

    # Left column: Segments (top) + Absorption Area (bottom)
    _bar_inset(ax4, seg_ctrl, seg_exp, 'Root Segments', 'Count',
               (0.02, 0.53, 0.47, 0.44))
    _bar_inset(ax4, eff_ctrl, eff_exp, 'Absorption Area', 'mm²',
               (0.02, 0.03, 0.47, 0.44))
    # Right column: G-Health Score (full height, left-anchored)
    _bar_inset(ax4, sc_ctrl, sc_exp, 'G-Health Score', 'Score',
               (0.52, 0.03, 0.46, 0.94))

    ax4.legend(handles=[
        plt.Rectangle((0,0),1,1,facecolor=C["control"],edgecolor='#666',lw=0.8,label='Control'),
        plt.Rectangle((0,0),1,1,facecolor=C["gen2"],edgecolor='#333',lw=0.8,label='GwC Air-Pruning'),
    ], loc='lower center', fontsize=8, framealpha=0.9,
       bbox_to_anchor=(0.24, 0.01, 0.46, 0.02), ncol=2)
    ax4.axis('off')

    # ── (E) Info box (replaces old Top5) ──
    ax5 = fig.add_subplot(2,3,5); ax5.axis('off')
    rs = sc_exp/max(sc_ctrl,1); reff = eff_exp/max(eff_ctrl,1)
    info = (
        "━━━ Optimal Design ───\n\n"
        "■ Search\n  Genetic Algorithm (GA)\n"
        "  Population: 30 × Gen: 20\n"
        f"  {3*30*20:,} simulations\n\n"
        "■ Pot\n  Ø13cm × H15cm\n"
        "  6 tetrahedron airrooms\n\n"
        "■ Optimal positions\n"
    )
    for i,(r,z,rad) in enumerate(OPTIMIZED_AIRROOMS,1):
        info += f"  #{i}: r={r:.1f}  z={z:.1f}  r{rad:.2f}\n"
    info += (
        "\n■ Performance\n"
        f"  Score: {sc_exp:.0f} ({rs:.1f}x)\n"
        f"  Segments: {seg_exp} ({seg_exp/seg_ctrl:.0f}x)\n"
        f"  Absorption area: {eff_exp:.0f}mm² ({reff:.1f}x)\n"
        f"  Pruning: {p_exp}\n  N uptake: {upt_exp:.3f}mg\n"
        "\n━━━━━━━━━━━\nGarden with Couch"
    )
    ax5.text(0.08,0.97,info,transform=ax5.transAxes,fontsize=9,
        fontfamily='monospace',color='#222',verticalalignment='top',
        bbox=dict(boxstyle='round,pad=0.8',facecolor='#F0F4F0',edgecolor=C["gen1"],lw=1.5))

    # ── (F) Key insight callout ──
    ax6 = fig.add_subplot(2,3,6); ax6.axis('off')
    insight = (
        "KEY INSIGHT\n\n"
        "Air-pruning transforms\n"
        "root architecture:\n\n"
        f"  3 → {seg_exp} segments\n"
        f"  0 → {p_exp} pruning events\n\n"
        "Fine roots (Gen 3) have\n"
        "10× higher absorption\n"
        "efficiency than primary\n"
        "roots (Gen 1).\n\n"
        "Effective absorption area\n"
        f"increases {reff:.1f}x\n"
        "despite geometric area\n"
        "being redistributed to\n"
        "finer, more efficient roots."
    )
    ax6.text(0.08,0.97,insight,transform=ax6.transAxes,fontsize=9.5,
        fontfamily='monospace',color='#1B4332',verticalalignment='top',
        bbox=dict(boxstyle='round,pad=0.8',facecolor='#E8F5E9',edgecolor=C["gen1"],lw=1.5))

    cap = (
        f"GwC Air-Pruning Pot Simulation. "
        f"(A) Control: 3 primary roots with natural gen-2/3 branching. "
        f"(B) GwC pot: tetrahedron airrooms (blue) trigger pruning (★) "
        f"and explosive fine root branching. "
        f"(C) Fine roots keep growing after pruning. "
        f"(D) Segments, absorption area, and score — each on independent scales. "
        f"(E) Final design specification. (F) Biological interpretation."
    )
    fig.text(0.5,0.02,cap,ha='center',va='bottom',fontsize=8.5,color='#444',style='italic',
        bbox=dict(boxstyle='round,pad=0.5',facecolor='#F8F9FA',edgecolor='#DDD',lw=0.5))

    plt.subplots_adjust(left=0.04, right=0.98, bottom=0.08, top=0.92, wspace=0.25, hspace=0.25)
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    runs_dir = os.path.join(PROJ_ROOT, "output", date_str)
    run_num = 1
    while os.path.exists(os.path.join(runs_dir, f"run-{run_num:03d}")):
        run_num += 1
    run_dir = os.path.join(runs_dir, f"run-{run_num:03d}")
    out_dir = os.path.join(run_dir, "viz")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "gwc_ir_visualization_v2.png")
    plt.savefig(out,dpi=200,facecolor='white',edgecolor='none')
    print(f"\\nSaved: {out}")
    print("="*55)
    plt.close()

if __name__ == "__main__":
    main()
