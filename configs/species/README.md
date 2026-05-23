# 식물 종별 설정 프로필

사용법: base config에 species 프로필을 병합(merge)해서 사용.

예:
```python
base = SimConfig.from_json("configs/mvp.json")
species = SimConfig.from_json("configs/species/monstera.json")
# species 값으로 base 덮어쓰기
base.root.initial_roots = species.root.initial_roots
base.root.radii_cm = species.root.radii_cm
base.root.noise_deg = species.root.noise_deg
# ... etc
```

또는 pipeline 단계에서 별도 인자로 넘겨서 SimConfig 생성 시 적용.
확장 단계에서 species 필드를 SimConfig에 직접 추가 예정.
