"""
대칭 배치 싱글시드 테스트: 상중하 × r 그리드
상중하 3개 구역, 각 구역에 대칭적인 정사면체 배치
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import SimConfig
from src.pipeline import SimPipeline
from src.geometry import Airroom

POT_R = 6.5; POT_H = 15.0

# ── 대칭 배치 Config A: 6개 (2r × 3h) ──
SYM_6 = []
# lower (z=3.5): inner (r=2.0), outer (r=4.5)
for r in [2.0, 4.5]:
    SYM_6.append(Airroom(r=r, z=3.5, radius=0.65))
# middle (z=7.5): inner, outer
for r in [2.0, 4.5]:
    SYM_6.append(Airroom(r=r, z=7.5, radius=0.65))
# upper (z=11.5): inner, outer
for r in [2.0, 4.5]:
    SYM_6.append(Airroom(r=r, z=11.5, radius=0.65))

# ── 대칭 배치 Config B: 9개 (3r × 3h) ──
SYM_9 = []
# r values: inner(1.5), mid(3.5), outer(5.0)
# z values: lower(3), mid(7), upper(11)
for r in [1.5, 3.5, 5.0]:
    for z in [3.0, 7.0, 11.0]:
        SYM_9.append(Airroom(r=r, z=z, radius=0.55))

# ── GA 최적 config (비교용) ──
GA_OPT = [
    Airroom(r=1.84, z=3.74, radius=0.51),
    Airroom(r=1.96, z=6.26, radius=0.82),
    Airroom(r=2.60, z=8.44, radius=0.50),
    Airroom(r=4.70, z=12.10, radius=0.50),
    Airroom(r=3.27, z=9.82, radius=0.50),
    Airroom(r=1.80, z=2.45, radius=0.90),
]

def run_test(config_path, airrooms, label):
    cfg = SimConfig.from_json(config_path)
    pipeline = SimPipeline(cfg)
    result = pipeline.run(seed=42, airrooms_override=airrooms)
    rs = result["root_system"]
    st = rs.statistics()
    sc = result["score"]
    print(f"\n━━━ {label} ━━━")
    print(f"  에어룸: {len(airrooms)}개")
    print(f"  세그먼트: {st['total_segments']}")
    print(f"  표면적: {st['total_surface_area_mm2']:.0f}mm²")
    print(f"  프루닝: {st['pruning_count']}회 | 구역: {st['pruning_by_zone']}")
    print(f"  Score: {sc['total']:.0f} (표면적 {sc['components']['surface_area']:.0f} + "
          f"프루닝 {sc['components']['pruning']:.0f} + "
          f"흡수 {sc['components']['n_uptake']:.0f})")
    print(f"  Spread: {st.get('spread_ratio', sc['metrics']['spread_ratio']):.3f}")
    return sc['total']

def print_positions(airrooms):
    for i, ar in enumerate(airrooms, 1):
        print(f"    {i}: r={ar.r:.2f}  z={ar.z:.2f}  rad={ar.radius:.2f}")

if __name__ == "__main__":
    cfg_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'pot_13.json')
    SEED = 42

    print("="*55)
    print("대칭 배치 싱글시드 테스트")
    print(f"화분: 13cm × 15cm | Seed: {SEED}")
    print("="*55)

    # GA 최적
    print("\n◆ GA 최적 (참조용):")
    print_positions(GA_OPT)
    ga_score = run_test(cfg_path, GA_OPT, "GA 최적 (6개)")

    # 대칭 6개
    print("\n◆ 대칭 6개 (2r×3h):")
    print_positions(SYM_6)
    sym6_score = run_test(cfg_path, SYM_6, "대칭 6개")

    # 대칭 9개
    print("\n◆ 대칭 9개 (3r×3h):")
    print_positions(SYM_9)
    sym9_score = run_test(cfg_path, SYM_9, "대칭 9개")

    # 비교
    print("\n" + "="*55)
    print("비교 요약")
    print("="*55)
    print(f"  GA 최적 (6개):  Score = {ga_score:.0f}")
    print(f"  대칭 6개 (2r×3h): Score = {sym6_score:.0f} "
          f"({'△' if sym6_score>ga_score else '▽'}{abs(sym6_score-ga_score):.0f})")
    print(f"  대칭 9개 (3r×3h): Score = {sym9_score:.0f} "
          f"({'△' if sym9_score>ga_score else '▽'}{abs(sym9_score-ga_score):.0f})")
    print("="*55)

    # Save summary
    summary = {
        "seed": SEED,
        "ga_opt": {"n": 6, "score": round(ga_score, 1)},
        "sym_6": {"n": 6, "score": round(sym6_score, 1),
                   "positions": [(ar.r, ar.z, ar.radius) for ar in SYM_6]},
        "sym_9": {"n": 9, "score": round(sym9_score, 1),
                   "positions": [(ar.r, ar.z, ar.radius) for ar in SYM_9]},
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'symmetric_test.json')
    with open(out_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\n결과 저장: {out_path}")
