"""IR: 2×3 panel figure from actual 2D simulation engine data.

Uses real VoxelGrid soil data, RootSystem segments, and pruning locations.
Panels:
  (A) Control cross-section  | (B) Experimental cross-section | (C) Pruning L/M/U
  (D) Quantitative Metrics   | (E) Design spec / Info        | (F) Key Insight
"""
import os, sys, math, random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle as MplCircle
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import SimConfig
from src.pipeline import SimPipeline
from src.geometry import Airroom, generate_random_airrooms

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Constants ──
POT_R, POT_H = 6.5, 15.0
C = {
    "bg": "#FAFAFA", "gen1": "#1B4332", "gen2": "#2D6A4F", "gen3": "#74C69D",
    "pruning_star": "#FFD700", "control": "#B0B0B0", "pot_edge": "#8B6F47",
    "airroom_fill": "#ff6b35", "airroom_edge": "#cc4400",
    "prune_zone": "#ff6b35",
}
SOIL_COLORS = {
    0: (0.55, 0.35, 0.20),   # 배양토 — brown
    1: (0.85, 0.82, 0.75),   # 펄라이트 — light beige
}
ROOT_COLORS = {1: C["gen1"], 2: C["gen2"], 3: C["gen3"]}
ROOT_LW = {1: 2.0, 2: 1.2, 3: 0.6}
ROOT_ALPHA = {1: 0.9, 2: 0.7, 3: 0.5}

OPT_AR = [
    Airroom(r=1.84, z=3.74, radius=0.51),
    Airroom(r=1.96, z=6.26, radius=0.82),
    Airroom(r=2.60, z=8.44, radius=0.50),
    Airroom(r=4.70, z=12.10, radius=0.50),
    Airroom(r=3.27, z=9.82, radius=0.50),
    Airroom(r=1.80, z=2.45, radius=0.90),
]


def render_voxel_bg(grid, ax):
    """Render the VoxelGrid soil type + airroom mask as a colored image."""
    nr, nz = grid.nr, grid.nz
    extent = [0, grid.pot_radius, 0, grid.pot_height]
    rgb = np.zeros((nr, nz, 3), dtype=float)
    for tid, color in SOIL_COLORS.items():
        mask = grid.soil_type == tid
        for c in range(3):
            rgb[:, :, c] = np.where(mask, color[c], rgb[:, :, c])
    for c in range(3):
        rgb[:, :, c] = np.where(grid.is_airroom, 1.0, rgb[:, :, c])
    rgb = rgb.transpose(1, 0, 2)
    ax.imshow(rgb, origin="lower", extent=extent, aspect="auto")


def draw_cross_section(ax, grid, root_system, airrooms, title, show_airrooms=True):
    """Draw a complete r-z cross-section: voxel bg + roots + pruning + airrooms."""
    render_voxel_bg(grid, ax)

    # Root segments
    for seg in root_system.segments:
        c = ROOT_COLORS.get(seg.generation, "#888")
        lw = ROOT_LW.get(seg.generation, 0.5)
        al = ROOT_ALPHA.get(seg.generation, 0.4)
        ax.plot([seg.start_r, seg.end_r], [seg.start_z, seg.end_z],
                color=c, linewidth=lw, alpha=al, solid_capstyle='round')

    # Pruning stars
    for r, z, gen in root_system.pruning_locations:
        ax.scatter(r, z, s=35, marker='*', color=C["pruning_star"],
                   edgecolors='#333', linewidths=0.4, zorder=10, alpha=0.9)

    # Airroom circles + pruning zones
    for ar in airrooms:
        zone = MplCircle((ar.r, ar.z), ar.radius * 1.15,
                         color=C["prune_zone"], alpha=0.06, lw=0)
        ax.add_patch(zone)
        circle = MplCircle((ar.r, ar.z), ar.radius,
                           color=C["airroom_fill"], alpha=0.30,
                           edgecolor=C["airroom_edge"], linewidth=1.0)
        ax.add_patch(circle)
        pz_circle = MplCircle((ar.r, ar.z), ar.pruning_zone_radius,
                              fill=False, edgecolor="red", linewidth=0.8,
                              linestyle=":", alpha=0.5)
        ax.add_patch(pz_circle)

    # Center line
    ax.axvline(0, color='#999', linestyle='--', linewidth=0.5, alpha=0.3)

    ax.set_xlim(-0.5, POT_R + 0.8)
    ax.set_ylim(-1, POT_H + 1)
    ax.set_xlabel('Radius r (cm)', fontsize=8)
    ax.set_ylabel('Height z (cm)', fontsize=8)
    ax.set_title(title, fontsize=10, fontweight='bold', color='#222')
    ax.grid(True, alpha=0.12)
    ax.set_aspect('equal')


def main():
    print("=" * 55)
    print("GWC IR 2D Viz v2 — Real Engine Data")
    print("=" * 55)

    cfg_path = os.path.join(PROJ_ROOT, "configs", "pot_13.json")
    cfg = SimConfig.from_json(cfg_path)

    # ── Run engine ──
    print("\n[1/3] Running control (0 airrooms)...")
    rng = random.Random(42)
    ctrl_res = SimPipeline(cfg).run(seed=42, airrooms_override=generate_random_airrooms(cfg, n=0, rng=rng))
    print("[2/3] Running experimental (optimized airrooms)...")
    exp_res = SimPipeline(cfg).run(seed=42, airrooms_override=OPT_AR)

    ctrl_rs = ctrl_res["root_system"]
    exp_rs = exp_res["root_system"]
    ctrl_grid = ctrl_res["grid"]
    exp_grid = exp_res["grid"]
    ctrl_stats = ctrl_rs.statistics()
    exp_stats = exp_rs.statistics()
    ctrl_score = ctrl_res["score"]["total"]
    exp_score = exp_res["score"]["total"]

    seg_ctrl = ctrl_stats["total_segments"]
    seg_exp = exp_stats["total_segments"]
    s_ctrl = ctrl_stats["total_surface_area_mm2"]
    s_exp = exp_stats["total_surface_area_mm2"]
    p_exp = exp_stats["pruning_count"]
    p_ctrl = 0

    # Effective (absorption-weighted) surface area
    eff_ctrl = ctrl_rs.effective_surface_area()
    eff_exp = exp_rs.effective_surface_area()

    # Pruning by zone
    prune_zones_ctrl = exp_rs.pruning_by_zone() if hasattr(exp_rs, 'pruning_by_zone') else {"lower": 0, "middle": 0, "upper": 0}
    prune_zones_exp = exp_rs.pruning_by_zone() if hasattr(exp_rs, 'pruning_by_zone') else {"lower": 0, "middle": 0, "upper": 0}

    # Spread ratio
    spread_ctrl = ctrl_res["score"]["metrics"].get("spread_ratio", 0)
    spread_exp = exp_res["score"]["metrics"].get("spread_ratio", 0)

    print(f"  Ctrl: {seg_ctrl}seg  {s_ctrl:.0f}mm²  eff={eff_ctrl:.0f}  score={ctrl_score:.0f}")
    print(f"  Exp:  {seg_exp}seg  {s_exp:.0f}mm²  eff={eff_exp:.0f}  pruning={p_exp}  score={exp_score:.0f}")
    print(f"  Spread: Ctrl={spread_ctrl:.1%}  Exp={spread_exp:.1%}")

    # ── Figure ──
    print("[3/3] Plotting 6-panel figure...")
    fig = plt.figure(figsize=(20, 12))
    fig.patch.set_facecolor(C["bg"])
    fig.suptitle('Garden with Couch — Air-Pruning Optimization Simulation (2D Engine)',
                 fontsize=17, fontweight='bold', y=0.98, color='#1B4332')
    fig.text(0.5, 0.955,
             'Actual VoxelGrid data · RootSystem segments · Real pruning locations',
             ha='center', fontsize=9, color='#555')

    # ── (A) Control cross-section ──
    ax1 = fig.add_subplot(2, 3, 1)
    draw_cross_section(ax1, ctrl_grid, ctrl_rs, [],
                       '(A) Control — Natural Growth', show_airrooms=False)
    # Stats overlay
    ax1.text(0.97, 0.97,
             f"Segments: {seg_ctrl}\nArea: {s_ctrl:.0f}mm²\nAbsorption: {eff_ctrl:.0f}mm²\nScore: {ctrl_score:.0f}",
             transform=ax1.transAxes, fontsize=7, fontfamily='monospace',
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='#ccc'))

    # ── (B) Experimental cross-section ──
    ax2 = fig.add_subplot(2, 3, 2)
    draw_cross_section(ax2, exp_grid, exp_rs, OPT_AR,
                       '(B) GwC Air-Pruning Pot', show_airrooms=True)
    ax2.text(0.97, 0.97,
             f"Segments: {seg_exp}\nArea: {s_exp:.0f}mm²\nAbsorption: {eff_exp:.0f}mm²\nScore: {exp_score:.0f}",
             transform=ax2.transAxes, fontsize=7, fontfamily='monospace',
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='#ccc'))

    # Legend for cross-sections
    leg_elements = [
        plt.Line2D([0], [0], color=C["gen1"], lw=2.0, label='Primary (Gen 1)'),
        plt.Line2D([0], [0], color=C["gen2"], lw=1.2, label='Lateral (Gen 2)'),
        plt.Line2D([0], [0], color=C["gen3"], lw=0.6, label='Fine (Gen 3)'),
        plt.Line2D([0], [0], marker='*', color='w', markerfacecolor=C["pruning_star"],
                   markersize=8, markeredgecolor='#333', label='Pruning (★)'),
        mpatches.Patch(facecolor=C["airroom_fill"], alpha=0.30,
                       edgecolor=C["airroom_edge"], label='Airroom'),
        plt.Line2D([0], [0], color='red', lw=0.8, ls=':', label='Prune zone'),
    ]
    fig.legend(handles=leg_elements, loc='lower center', ncol=6, fontsize=7.5,
               bbox_to_anchor=(0.36, 0.935), framealpha=0.9)

    # ── (C) Pruning distribution ──
    ax3 = fig.add_subplot(2, 3, 3)
    zones = ["lower", "middle", "upper"]
    labels = ["Lower", "Middle", "Upper"]
    pz = exp_rs.pruning_by_zone() if hasattr(exp_rs, 'pruning_by_zone') else {}
    values = [pz.get(z, 0) for z in zones]
    zone_colors = ["#27ae60", "#f39c12", "#e74c3c"]
    bars = ax3.barh(labels, values, color=zone_colors, height=0.5)
    for bar, v in zip(bars, values):
        if v > 0:
            ax3.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                     str(v), va='center', fontsize=10, fontweight='bold')
    ax3.set_xlabel('Pruning count', fontsize=9)
    ax3.set_title('(C) Pruning by Depth Zone', fontsize=11, fontweight='bold')
    ax3.margins(y=0.3)
    ax3.grid(True, axis='x', alpha=0.3, ls='--')
    ax3.spines['top'].set_visible(False); ax3.spines['right'].set_visible(False)

    # ── (D) Quantitative Metrics (3 independent mini-charts) ──
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    ax4 = fig.add_subplot(2, 3, 4)
    ax4.set_title('(D) Quantitative Metrics', fontsize=11, fontweight='bold')

    def mini_bar(parent, x_ctr, v_ctrl, v_exp, ylabel, title, offset_y, offset_x=0.02, fmt='.0f'):
        """Create a mini bar chart inset. x_ctr = center x position (float)."""
        w = 0.35
        ax_in = inset_axes(parent, width='40%', height='40%', loc='upper left',
                           bbox_to_anchor=(offset_x, offset_y, 0.45, 0.45),
                           bbox_transform=parent.transAxes)
        ax_in.bar(x_ctr - w / 2, v_ctrl, w, color=C["control"], edgecolor='#666', lw=0.8)
        ax_in.bar(x_ctr + w / 2, v_exp, w, color=C["gen2"], edgecolor='#333', lw=0.8)
        ax_in.set_xticks([x_ctr - w / 2, x_ctr + w / 2])
        ax_in.set_xticklabels(['Ctrl', 'Exp'], fontsize=7)
        ax_in.set_ylabel(ylabel, fontsize=7)
        ax_in.set_title(title, fontsize=8, fontweight='bold')
        ratio = v_exp / max(v_ctrl, 1)
        if ratio > 1.05:
            lbl = f'{v_exp:{fmt}} ({ratio:.1f}x)'
        else:
            lbl = f'{v_exp:{fmt}}'
        ax_in.text(x_ctr - w / 2, v_ctrl + max(v_ctrl, v_exp) * 0.02,
                   f'{v_ctrl:{fmt}}', ha='center', fontsize=7, color='#666')
        ax_in.text(x_ctr + w / 2, v_exp + max(v_ctrl, v_exp) * 0.02,
                   lbl, ha='center', fontsize=7, fontweight='bold', color=C["gen1"])
        ax_in.set_ylim(0, max(v_ctrl, v_exp) * 1.4)
        ax_in.grid(True, axis='y', alpha=0.3, ls='--')
        ax_in.spines['top'].set_visible(False); ax_in.spines['right'].set_visible(False)

    mini_bar(ax4, 0, seg_ctrl, seg_exp, 'Count', 'Root Segments', 0.52)
    mini_bar(ax4, 0, eff_ctrl, eff_exp, 'mm²', 'Absorption Area', 0.05)
    mini_bar(ax4, 0, ctrl_score, exp_score, 'Score', 'G-Health Score', 0.52, offset_x=0.55)

    ax4.legend(handles=[
        plt.Rectangle((0, 0), 1, 1, facecolor=C["control"], edgecolor='#666', lw=0.8, label='Control'),
        plt.Rectangle((0, 0), 1, 1, facecolor=C["gen2"], edgecolor='#333', lw=0.8, label='GwC'),
    ], loc='lower right', fontsize=7, framealpha=0.9)
    ax4.axis('off')

    # ── (E) Info box ──
    ax5 = fig.add_subplot(2, 3, 5)
    ax5.axis('off')
    rs = exp_score / max(ctrl_score, 1)
    reff = eff_exp / max(eff_ctrl, 1)
    active_airrooms = len(OPT_AR)
    info = (
        "━━━ Optimal Design ───\n\n"
        "■ Search\n  Genetic Algorithm (GA)\n"
        "  Population: 30 × Gen: 20\n"
        "  1,800 simulations\n\n"
        "■ Pot\n  Ø13cm × H15cm\n"
        "  6 tetrahedron airrooms\n\n"
        "■ Optimal positions\n"
    )
    for i, ar in enumerate(OPT_AR, 1):
        zone = "L" if ar.z < 5 else ("M" if ar.z < 10 else "U")
        info += f"  #{i}: r={ar.r:.1f}  z={ar.z:.1f}  r{ar.radius:.2f} ({zone})\n"
    info += (
        "\n■ Performance\n"
        f"  Score: {exp_score:.0f} ({rs:.1f}x)\n"
        f"  Segments: {seg_exp}\n"
        f"  Absorption area: {eff_exp:.0f}mm² ({reff:.1f}x)\n"
        f"  Pruning: {p_exp}\n"
        f"  Spread: {spread_exp:.1%}\n"
        "\n━━━━━━━━━━━━━━\nGarden with Couch"
    )
    ax5.text(0.08, 0.97, info, transform=ax5.transAxes, fontsize=8.5,
             fontfamily='monospace', color='#222', verticalalignment='top',
             bbox=dict(boxstyle='round,pad=0.8', facecolor='#F0F4F0',
                       edgecolor=C["gen1"], lw=1.5))

    # ── (F) Key Insight ──
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.axis('off')
    insight = (
        "KEY INSIGHT\n\n"
        "Real simulation engine shows:\n\n"
        f"  Gen 1: 3 primary roots\n"
        f"  Gen 2: lateral spread (+-75 deg)\n"
        f"  -> hit airroom pruning zone\n"
        f"  -> prune -> 2~6 new branches\n"
        f"  Gen 3: fine roots absorb\n"
        f"  10x more per unit area\n\n"
        f"Voxel grid renders every cell:\n"
        f"  Brown = potting mix\n"
        f"  Beige = perlite (aeration)\n"
        f"  White = airroom void\n"
        f"  Red dot circle = prune zone\n\n"
        f"Result: {seg_ctrl} -> {seg_exp} segments\n"
        f"        {eff_ctrl:.0f} -> {eff_exp:.0f}mm2 eff. area\n"
        f"        {ctrl_score:.0f} -> {exp_score:.0f} score"
    )
    ax6.text(0.08, 0.97, insight, transform=ax6.transAxes, fontsize=9,
             fontfamily='monospace', color='#1B4332', verticalalignment='top',
             bbox=dict(boxstyle='round,pad=0.8', facecolor='#E8F5E9',
                       edgecolor=C["gen1"], lw=1.5))

    # ── Caption ──
    cap = (
        "GwC Air-Pruning Pot — 2D Engine Data. "
        "(A) Control: 3 primary roots in natural soil voxel grid. "
        "(B) GwC pot: airrooms (orange circles) trigger pruning (★) at dotted red zones; "
        "gen-2 lateral roots spread sideways (±75°) and hit airrooms. "
        "(C) Pruning events by pot depth zone. "
        "(D) Independent-scale comparison bars. "
        "(E) Final design specification. (F) Biological interpretation."
    )
    fig.text(0.5, 0.02, cap, ha='center', va='bottom', fontsize=8,
             color='#444', style='italic',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#F8F9FA',
                       edgecolor='#DDD', lw=0.5))

    plt.subplots_adjust(left=0.04, right=0.98, bottom=0.08, top=0.92, wspace=0.25, hspace=0.25)

    # ── Save ──
    date_str = datetime.now().strftime("%Y-%m-%d")
    runs_dir = os.path.join(PROJ_ROOT, "output", date_str)
    run_num = 1
    while os.path.exists(os.path.join(runs_dir, f"run-{run_num:03d}")):
        run_num += 1
    run_dir = os.path.join(runs_dir, f"run-{run_num:03d}")
    out_dir = os.path.join(run_dir, "viz")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "gwc_2d_ir_visualization.png")
    plt.savefig(out, dpi=200, facecolor='white', edgecolor='none')
    print(f"\nSaved: {out}")
    print("=" * 55)
    plt.close()


if __name__ == "__main__":
    main()
