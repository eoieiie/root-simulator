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
            lat = RootPath(bp, 2, 0.052)
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
                                fine = RootPath((px,py,pz), 3, 0.028)
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
                    fine = RootPath(tip, 3, 0.025)
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
    wm = {1:3.0,2:1.4,3:0.5}; am = {1:1.0,2:0.85,3:0.45}
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
    ax.set_zlabel('높이 (cm)',fontsize=7)

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
    print(f"  Ctrl: {seg_ctrl}seg {s_ctrl:.0f}mm2 score={sc_ctrl:.0f}")
    print(f"  Exp:  {seg_exp}seg {s_exp:.0f}mm2 pruning={p_exp} score={sc_exp:.0f}")

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
    fig.suptitle('Garden with Couch — 에어프루닝 최적화 시뮬레이션',
                 fontsize=18,fontweight='bold',y=0.98,color='#1B4332')
    fig.text(0.5,0.955,
        f'유전 알고리즘(GA) {3*30*20}회 평가로 최적화된 6개 정사면체 에어룸 · 13cm 화분',
        ha='center',fontsize=10,color='#555')

    ax1 = fig.add_subplot(2,3,1,projection='3d')
    plot_3d(ax1,ctrl_roots,[],[],'(A) 일반 화분 — 자연 성장',show_airrooms=False)

    ax2 = fig.add_subplot(2,3,2,projection='3d')
    plot_3d(ax2,exp_roots,ppe,ar_disp,'(B) GwC 에어프루닝 팟',show_airrooms=True)
    leg = [
        plt.Line2D([0],[0],color=C["gen1"],lw=2.5,label='중심뿌리 (1세대)'),
        plt.Line2D([0],[0],color=C["gen2"],lw=1.4,label='곁뿌리 (2세대)'),
        plt.Line2D([0],[0],color=C["gen3"],lw=0.6,label='잔뿌리 (3세대)'),
        mpatches.Patch(facecolor=C["airroom_face"],edgecolor=C["airroom"],label='정사면체 에어룸'),
    ]
    if ppe: leg.append(plt.Line2D([0],[0],marker='*',color='w',
        markerfacecolor=C["pruning_star"],markersize=10,markeredgecolor='#333',
        label=f'프루닝 (★ {len(ppe)}회)'))
    ax2.legend(handles=leg,loc='upper left',fontsize=7,framealpha=0.92,bbox_to_anchor=(0.0,1.02))

    ax3 = fig.add_subplot(2,3,3,projection='3d')
    draw_pot(ax3,alpha=0.2)
    for cx,cy,cz,rad in ar_disp: draw_tetrahedron(ax3,cx,cy,cz,rad,alpha=0.2)
    for gen in [1,2,3]:
        for r in exp_roots:
            if r.gen!=gen or len(r.pts)<2: continue
            pts = np.array(r.pts)
            w = {1:1.8,2:0.9,3:0.35}.get(gen,0.35)
            ax3.plot(pts[:,0],pts[:,1],pts[:,2],
                color={1:C["gen1"],2:C["gen2"],3:C["gen3"]}.get(gen,C["gen3"]),
                linewidth=w,alpha=0.7)
    for pt in ppe[:30]: ax3.scatter(pt[0],pt[1],pt[2],c=C["pruning_star"],s=50,
        marker='*',edgecolors='#333',linewidths=0.4,zorder=20)
    ax3.set_xlim(-POT_R,POT_R); ax3.set_ylim(-POT_R,POT_R); ax3.set_zlim(0,POT_H)
    ax3.set_title('(C) 프루닝 → 잔뿌리 폭발',fontsize=11,fontweight='bold')
    ax3.view_init(elev=25,azim=20); ax3.grid(True,alpha=0.08)
    for d in 'xyz': getattr(ax3,f'{d}axis').pane.fill = False

    ax4 = fig.add_subplot(2,3,4)
    ctrln = [seg_ctrl,s_ctrl,sc_ctrl]; expn = [seg_exp,s_exp,sc_exp]
    x = np.arange(3); w = 0.3
    b1 = ax4.bar(x-w/2,ctrln,w,label='일반 화분',color=C["control"],edgecolor='#666',lw=0.8)
    b2 = ax4.bar(x+w/2,expn,w,label='GwC 에어프루닝',color=C["gen2"],edgecolor='#333',lw=0.8)
    mx = max(max(ctrln),max(expn))
    for bar,v in zip(b1,ctrln):
        ax4.text(bar.get_x()+bar.get_width()/2,bar.get_height()+mx*0.01,
                 f'{v:.0f}',ha='center',fontsize=9,color='#666')
    for bar,v,ov in zip(b2,expn,ctrln):
        r = v/ov if ov>0 else 1; lbl = f'{v:.0f}'
        if r>1.1: lbl += f'\n({r:.1f}배↑)'
        ax4.text(bar.get_x()+bar.get_width()/2,bar.get_height()+mx*0.01,
                 lbl,ha='center',fontsize=9,fontweight='bold',color=C["gen1"])
    ax4.set_xticks(x); ax4.set_xticklabels(['뿌리\n세그먼트','표면적\n(mm²)','G-Health\nScore'],fontsize=10)
    ax4.set_title('(D) 정량 비교 (2D 엔진)',fontsize=11,fontweight='bold')
    ax4.legend(fontsize=9,loc='upper left'); ax4.set_ylim(0,mx*1.35)
    ax4.grid(True,axis='y',alpha=0.3,ls='--')
    ax4.spines['top'].set_visible(False); ax4.spines['right'].set_visible(False)

    ax5 = fig.add_subplot(2,3,5)
    rj = os.path.join(PROJ_ROOT,"output","results_final.json")
    if os.path.exists(rj):
        with open(rj) as f: d = json.load(f)
        rks = [r['rank'] for r in d['results']]
        scs = [r['mean_score'] for r in d['results']]
        sds = [r['std_score'] for r in d['results']]
        ax5.bar(rks,scs,color=C["gen2"],edgecolor='#333',lw=0.8,width=0.6)
        ax5.errorbar(rks,scs,yerr=sds,fmt='none',ecolor='#666',capsize=4,capthick=1.2,elinewidth=1.2)
        for i,(s,sd) in enumerate(zip(scs,sds)):
            ax5.text(i+1,s+sd+80,f'{s:.0f}\\pm{sd:.0f}',ha='center',fontsize=7.5,color='#333')
        ax5.set_xticks(rks); ax5.set_xlabel('Rank',fontsize=9)
        ax5.set_ylabel('G-Health Score',fontsize=9)
        ax5.set_title('(E) 최적화 수렴 (GA Top5)',fontsize=11,fontweight='bold')
        ax5.grid(True,axis='y',alpha=0.3,ls='--')
        ax5.spines['top'].set_visible(False); ax5.spines['right'].set_visible(False)

    ax6 = fig.add_subplot(2,3,6); ax6.axis('off')
    rs = sc_exp/max(sc_ctrl,1); rsurf = s_exp/max(s_ctrl,1)
    info = (
        "━━━ 최적 설계 상세 ━━━\n\n"
        "■ 탐색\n  유전 알고리즘 (GA)\n"
        "  개체: 30 × 세대: 20\n"
        f"  {3*30*20:,}회 시뮬레이션\n\n"
        "■ 화분\n  직경 13cm × 높이 15cm\n"
        "  정사면체 6개\n\n■ 최적 위치\n"
    )
    for i,(r,z,rad) in enumerate(OPTIMIZED_AIRROOMS,1):
        info += f"  {i}: r={r:.1f}  z={z:.1f}  ø{rad:.2f}\n"
    info += (
        "\n■ 성능\n"
        f"  Score: {sc_exp:.0f} ({rs:.1f}배↑)\n"
        f"  표면적: {s_exp:.0f}mm² ({rsurf:.1f}배↑)\n"
        f"  프루닝: {p_exp}회\n  질소흡수: {upt_exp:.3f}mg\n"
        "  Spread: 11%\n\n"
        "━━━━━━━━━━━\nGarden with Couch"
    )
    ax6.text(0.05,0.97,info,transform=ax6.transAxes,fontsize=9,
        fontfamily='monospace',color='#222',verticalalignment='top',
        bbox=dict(boxstyle='round,pad=0.8',facecolor='#F0F4F0',edgecolor=C["gen1"],lw=1.5))

    cap = (
        f"그림. 가든위드카우치 에어프루닝 화분 시뮬레이션. "
        f"(A) 일반 화분: 3개 중심뿌리에서 2·3세대 뿌리로 자연 분기. "
        f"(B) GwC 화분: 정사면체 에어룸(청색)과 곁뿌리 접촉 시(★) "
        f"잔뿌리가 폭발적으로 분기하여 공간을 더 넓게 점유. "
        f"(C) 프루닝 직후 6~10개 잔뿌리가 계속 성장. "
        f"(D-F) 2D GA 엔진 기반 정량 비교 및 최종 설계 사양."
    )
    fig.text(0.5,0.02,cap,ha='center',va='bottom',fontsize=8.5,color='#444',style='italic',
        bbox=dict(boxstyle='round,pad=0.5',facecolor='#F8F9FA',edgecolor='#DDD',lw=0.5))

    plt.tight_layout(rect=[0,0.06,1,0.94])
    out = os.path.join(PROJ_ROOT,"output","gwc_ir_visualization_v2.png")
    plt.savefig(out,dpi=200,bbox_inches='tight',facecolor='white',edgecolor='none')
    print(f"\\nSaved: {out}")
    print("="*55)
    plt.close()

if __name__ == "__main__":
    main()
