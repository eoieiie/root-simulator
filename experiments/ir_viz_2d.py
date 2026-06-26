"""IR: 2D r-z cross-section from actual simulation engine data."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import SimConfig
from src.pipeline import SimPipeline
from src.geometry import Airroom, generate_random_airrooms

OPT_AR = [
    Airroom(r=1.84, z=3.74, radius=0.51),
    Airroom(r=1.96, z=6.26, radius=0.82),
    Airroom(r=2.60, z=8.44, radius=0.50),
    Airroom(r=4.70, z=12.10, radius=0.50),
    Airroom(r=3.27, z=9.82, radius=0.50),
    Airroom(r=1.80, z=2.45, radius=0.90),
]
POT_R, POT_H = 6.5, 15.0

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg_path = os.path.join(PROJ_ROOT, "configs", "pot_13.json")
cfg = SimConfig.from_json(cfg_path)

# Run engine for both cases
print("Running control...")
rng = random.Random(42)
ctrl_res = SimPipeline(cfg).run(seed=42, airrooms_override=generate_random_airrooms(cfg, n=0, rng=rng))
print("Running experimental...")
exp_res = SimPipeline(cfg).run(seed=42, airrooms_override=OPT_AR)

ctrl_rs = ctrl_res["root_system"]
exp_rs = exp_res["root_system"]
ctrl_stats = ctrl_rs.statistics()
exp_stats = exp_rs.statistics()

print(f"Control: {ctrl_stats['total_segments']} segs, {ctrl_stats['total_surface_area_mm2']:.0f}mm2")
print(f"Exp: {exp_stats['total_segments']} segs, {exp_stats['total_surface_area_mm2']:.0f}mm2")

eff_ctrl = ctrl_rs.effective_surface_area()
eff_exp = exp_rs.effective_surface_area()
print(f"Eff: Ctrl={eff_ctrl:.0f} Exp={eff_exp:.0f}")

# ── Plot ──
fig, axes = plt.subplots(1, 2, figsize=(14, 7), facecolor='white')
fig.patch.set_facecolor('white')

for idx, (ax, rs, ar_list, label) in enumerate(zip(
    axes, [ctrl_rs, exp_rs], [[], OPT_AR],
    ['(A) Control — Natural Growth', '(B) GwC Air-Pruning Pot']
)):
    # Pot outline (trapezoid for tetrahedron pot)
    pot_x = [0, POT_R, POT_R, 0]
    pot_z = [0, 0, POT_H, POT_H]
    ax.fill(pot_x, pot_z, color='#f5f0e8', alpha=0.3, edgecolor='#8b7355', linewidth=1.5)

    # Soil fill
    ax.fill_between([0, POT_R], [0, 0], [POT_H, POT_H], color='#5d4037', alpha=0.06)

    # Airrooms (experimental only)
    for ar in ar_list:
        zone = plt.Circle((ar.r, ar.z), ar.radius * 1.15, color='#ff6b35', alpha=0.08, lw=0)
        ax.add_patch(zone)
        circle = plt.Circle((ar.r, ar.z), ar.radius, color='#ff6b35', alpha=0.35,
                           edgecolor='#cc4400', linewidth=1.0)
        ax.add_patch(circle)

    # Root segments
    gen_colors = {1: '#1B4332', 2: '#2D6A4F', 3: '#74C69D'}
    gen_lw = {1: 2.5, 2: 1.5, 3: 0.8}
    gen_alpha = {1: 0.9, 2: 0.7, 3: 0.5}

    for seg in rs.segments:
        c = gen_colors.get(seg.generation, '#A8C8E8')
        lw = gen_lw.get(seg.generation, 0.5)
        al = gen_alpha.get(seg.generation, 0.4)
        ax.plot([seg.start_r, seg.end_r], [seg.start_z, seg.end_z],
                color=c, linewidth=lw, alpha=al, solid_capstyle='round')

    # Pruning markers
    for r, z, gen in rs.pruning_locations:
        ax.scatter(r, z, s=40, marker='*', color='#FFD700', edgecolors='#333',
                   linewidths=0.5, zorder=10, alpha=0.9)

    # Center line
    ax.axvline(0, color='#999', linestyle='--', linewidth=0.5, alpha=0.3)

    ax.set_xlim(-0.5, POT_R + 0.8)
    ax.set_ylim(-1, POT_H + 1)
    ax.set_xlabel('Radius r (cm)', fontsize=9)
    ax.set_ylabel('Height z (cm)', fontsize=9)
    ax.set_title(label, fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.15)
    ax.set_aspect('equal')

    # Stats box
    n_seg = len(rs.segments)
    n_prune = rs.pruning_count()
    s_area = rs.statistics()['total_surface_area_mm2']
    eff = rs.effective_surface_area()
    score = (ctrl_res if idx == 0 else exp_res)['score']['total']
    stats_text = (
        f"Segments: {n_seg}\n"
        f"Pruning: {n_prune}\n"
        f"Area: {s_area:.0f}mm²\n"
        f"Absorption: {eff:.0f}mm²\n"
        f"Score: {score:.0f}"
    )
    ax.text(0.97, 0.97, stats_text, transform=ax.transAxes, fontsize=8,
            fontfamily='monospace', verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='#ccc'))

# Add legend at bottom
leg_elements = [
    plt.Line2D([0], [0], color='#1B4332', lw=2.5, label='Primary (Gen 1)'),
    plt.Line2D([0], [0], color='#2D6A4F', lw=1.5, label='Lateral (Gen 2)'),
    plt.Line2D([0], [0], color='#74C69D', lw=0.8, label='Fine (Gen 3)'),
    plt.Line2D([0], [0], marker='*', color='w', markerfacecolor='#FFD700',
               markersize=8, markeredgecolor='#333', label='Pruning'),
    mpatches.Patch(facecolor='#ff6b35', alpha=0.35, edgecolor='#cc4400', label='Airroom'),
]
fig.legend(handles=leg_elements, loc='lower center', ncol=5, fontsize=8,
           bbox_to_anchor=(0.5, 0.02), framealpha=0.9)

plt.tight_layout(rect=[0, 0.07, 1, 1])
from datetime import datetime
date_str = datetime.now().strftime("%Y-%m-%d")
runs_dir = os.path.join(PROJ_ROOT, "output", date_str)
run_num = 1
while os.path.exists(os.path.join(runs_dir, f"run-{run_num:03d}")):
    run_num += 1
run_dir = os.path.join(runs_dir, f"run-{run_num:03d}")
out_dir = os.path.join(run_dir, "viz")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "gwc_2d_cross_section.png")
plt.savefig(out, dpi=200, bbox_inches='tight', facecolor='white', edgecolor='none')
print(f"Saved: {out}")
plt.close()
