"""시각화 모듈 (MVP 3패널).

plan.md §7 Phase E 참조.
MVP 패널:
  (B) 2D 단면도 — 흙 종류 + 에어룸 + 뿌리 경로 + 프루닝 지점
  (C) 프루닝 분포 — 상/중/하 구간별 프루닝 횟수
  (D) 정보 박스 — 설계 통계
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

from .config import SimConfig
from .geometry import Airroom
from .grid import VoxelGrid
from .root import RootSystem

# 흙 종류별 색상 (r, g, b 0~1)
SOIL_COLORS = {
    0: (0.55, 0.35, 0.20),   # 배양토 — brown
    1: (0.85, 0.82, 0.75),   # 펄라이트 — light beige
}

# 세대별 뿌리 색상
ROOT_COLORS = {1: "#1a3a1a", 2: "#2d6a2d", 3: "#5a9e5a"}
# 세대별 뿌리 두께 (선 두께, pt)
ROOT_LW = {1: 2.5, 2: 1.8, 3: 1.2}


def plot_cross_section(
    grid: VoxelGrid,
    root_system: RootSystem,
    airrooms: List[Airroom],
    ax: plt.Axes,
) -> None:
    """(B) 2D r-z 단면도: 흙 + 에어룸 + 뿌리 + 프루닝."""
    nr, nz = grid.nr, grid.nz
    extent = [0, grid.pot_radius, 0, grid.pot_height]

    # 흙 배경
    rgb = np.zeros((nr, nz, 3), dtype=float)
    for tid, color in SOIL_COLORS.items():
        mask = grid.soil_type == tid
        for c in range(3):
            rgb[:, :, c] = np.where(mask, color[c], rgb[:, :, c])
    # 에어룸 — 흰색
    for c in range(3):
        rgb[:, :, c] = np.where(grid.is_airroom, 1.0, rgb[:, :, c])
    rgb = rgb.transpose(1, 0, 2)  # imshow는 (nz, nr) 순서

    ax.imshow(rgb, origin="lower", extent=extent, aspect="auto")

    # 뿌리 경로
    for seg in root_system.segments:
        color = ROOT_COLORS.get(seg.generation, "#888")
        lw = ROOT_LW.get(seg.generation, 1.0)
        ax.plot(
            [seg.start_r, seg.end_r],
            [seg.start_z, seg.end_z],
            color=color,
            linewidth=lw,
            alpha=0.7,
        )

    # 프루닝 지점
    if root_system.pruning_locations:
        pr = np.array(root_system.pruning_locations)
        ax.scatter(pr[:, 0], pr[:, 1], color="red", s=15, zorder=5, alpha=0.8)

    # 에어룸 경계 (점선 원)
    for ar in airrooms:
        circle = Circle(
            (ar.r, ar.z), ar.radius,
            fill=False, edgecolor="white", linewidth=1.5,
            linestyle="--", alpha=0.9,
        )
        ax.add_patch(circle)
        pz_circle = Circle(
            (ar.r, ar.z), ar.pruning_zone_radius,
            fill=False, edgecolor="red", linewidth=0.8,
            linestyle=":", alpha=0.5,
        )
        ax.add_patch(pz_circle)

    ax.set_xlabel("r (cm)")
    ax.set_ylabel("z (cm)")
    ax.set_title("2D r-z Cross-section")
    ax.set_xlim(0, grid.pot_radius)
    ax.set_ylim(0, grid.pot_height)


def plot_pruning_distribution(
    metrics: Dict,
    ax: plt.Axes,
) -> None:
    """(C) 상/중/하 프루닝 분포 가로 막대."""
    by_zone = metrics.get("pruning_by_zone", {"lower": 0, "middle": 0, "upper": 0})
    zones = ["upper", "middle", "lower"]
    labels = ["Upper", "Middle", "Lower"]
    values = [by_zone.get(z, 0) for z in zones]
    colors = ["#e74c3c", "#f39c12", "#27ae60"]

    bars = ax.barh(labels, values, color=colors, height=0.5)
    for bar, v in zip(bars, values):
        if v > 0:
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                    str(v), va="center", fontsize=10)

    ax.set_xlabel("Pruning count")
    ax.set_title("Pruning by Zone")
    ax.margins(y=0.3)


def plot_info_box(
    result: Dict,
    ax: plt.Axes,
) -> None:
    """(D) 설계 통계 정보 박스."""
    comp = result.get("components", {})
    metrics = result.get("metrics", {})

    lines = [
        f"G-Health Score: {result.get('total', '?'):.2f}",
        "",
        f"Surface Area: {metrics.get('surface_area_mm2', '?'):.1f} mm²",
        f"  weight: {comp.get('surface_area', '?'):.2f}",
        f"Pruning: {metrics.get('pruning_count', '?')} times",
        f"  weight: {comp.get('pruning', '?'):.2f}",
        f"Soil Loss: {metrics.get('soil_loss_ratio', '?')*100:.2f}%",
        f"  penalty: {comp.get('soil_loss', '?'):.2f}",
        "",
        f"Airrooms: {metrics.get('total_airrooms', '?')} total",
        f"  unused: {metrics.get('unused_airrooms', '?')}",
        f"Steps: {metrics.get('steps_run', '?')}",
    ]
    z = metrics.get("pruning_by_zone", {})
    lines.append(f"Pruning: L{z.get('lower',0)} M{z.get('middle',0)} U{z.get('upper',0)}")

    ax.axis("off")
    ax.text(0.05, 0.95, "\n".join(lines), transform=ax.transAxes,
            fontfamily="monospace", fontsize=9, va="top",
            bbox=dict(boxstyle="round", facecolor="#f8f8f8", edgecolor="#ccc"))


def plot_single_run(
    grid: VoxelGrid,
    root_system: RootSystem,
    airrooms: List[Airroom],
    score_result: Dict,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """단일 실행 결과 3패널 시각화.

    (B) 단면도 | (C) 프루닝 분포 | (D) 정보 박스
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5),
                              gridspec_kw={"width_ratios": [2, 1, 1.3]})

    plot_cross_section(grid, root_system, airrooms, axes[0])
    plot_pruning_distribution(score_result.get("metrics", {}), axes[1])

    metrics = dict(score_result.get("metrics", {}))
    metrics["steps_run"] = root_system.step_count
    score_with_metrics = dict(score_result)
    score_with_metrics["metrics"] = metrics
    plot_info_box(score_with_metrics, axes[2])

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"saved: {save_path}")
    return fig


def plot_top5_barchart(
    top5_results: List[Dict],
    ax: plt.Axes,
) -> None:
    """(A) Top5 점수 막대그래프 + 에어룸 개수/표면적 오버레이."""
    scores = [r["score"]["total"] for r in top5_results]
    n_air = [r["n_airrooms"] for r in top5_results]
    labels = [f"#{r['rank']}" for r in top5_results]

    bars = ax.bar(labels, scores, color="#3498db", width=0.5, edgecolor="#2c3e50")
    for bar, s, n, r in zip(bars, scores, n_air, top5_results):
        surf = r["score"]["metrics"]["surface_area_mm2"]
        spread = r["score"]["metrics"]["spread_ratio"]
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 80,
                f"{s:.0f}\nn={n}  S={surf:.0f}\nSpread={spread:.0%}",
                ha="center", va="bottom", fontsize=7, linespacing=1.2)

    ax.set_ylabel("G-Health Score")
    ax.set_title("Top 5 Designs")
    ax.set_ylim(0, max(scores) * 1.3)


def plot_search_results(
    top5_results: List[Dict],
    save_path: Optional[str] = None,
) -> plt.Figure:
    """4패널: (A) Top5 막대 | (B) #1 단면도 | (C) 프루닝 분포 | (D) 정보박스."""
    best = top5_results[0]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10),
                              gridspec_kw={"width_ratios": [2, 1.2],
                                            "height_ratios": [0.8, 1.2]})

    plot_top5_barchart(top5_results, axes[0, 0])
    plot_cross_section(best["grid"], best["root_system"], best["airrooms"], axes[1, 0])
    plot_pruning_distribution(best["score"].get("metrics", {}), axes[1, 1])

    metrics = dict(best["score"].get("metrics", {}))
    metrics["steps_run"] = best["root_system"].step_count
    score_with_metrics = dict(best["score"])
    score_with_metrics["metrics"] = metrics
    score_with_metrics["total"] = best["score"]["total"]
    plot_info_box(score_with_metrics, axes[0, 1])

    axes[0, 0].set_title(f"Top 5 (of {top5_results[0].get('n_total', '?')} candidates)")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"saved: {save_path}")
    return fig
