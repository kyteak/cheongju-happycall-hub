"""
그림 5. 읍면별 운행 1건 차량점유: 현재 vs Hub 연계
  → 저장: figures/fig05_hub_occupancy.png  (보고서 '분석결과 이미지' 그림 5)

사용 데이터: done의 실제 픽업·탑승시간·이동거리, 읍면 Hub 거리, 핵심 목적지 동 (hub_effect)
처리:
  Hub 거리 ≤ 이동거리 70%인 30,125건의 탑승시간을 Hub 거리 비율로 줄여 차량점유 재계산, 시나리오 표(sc) 출력
그림: 덤벨 차트 (읍면별 현재 파랑 → Hub 연계 주황, * = 현행 노선 연결 미확인)

실행: VS Code에서 이 파일을 열고 오른쪽 위 ▷(Run Python File)  또는  터미널에서  python analysis/fig05_hub_occupancy.py
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd())
from common import *   # 데이터 위치·폰트·스타일·공통 데이터(hc, done, bnd, HUB, CORE 등)·공통 계산 함수

cand, el, per, sc = hub_effect()

# 그림 7. 읍면별 1건 차량점유: 현재 vs Hub 연계 (외곽→시내)
fig, ax = plt.subplots(figsize=(8, 5))
y = np.arange(len(per))
ax.hlines(y, per.Hub점유, per.현재점유, color=GRID, linewidth=3, zorder=1)
ax.scatter(per.현재점유, y, color=C_IN, s=70, zorder=2, label='현재 (목적지 직행)', edgecolor='white', linewidth=1)
ax.scatter(per.Hub점유, y, color=C_OUT, s=70, zorder=2, label='Hub 정류장 연계', edgecolor='white', linewidth=1)
for i, (k, r) in enumerate(per.iterrows()):
    ax.text(r.현재점유 + 1, i, f'−{r.절감분:.0f}분', va='center', fontsize=9, color=INK2)
ax.set_yticks(y, [f'{k}{"" if per.loc[k, "현행노선연결"] else " *"}' for k in per.index])
ax.set_xlabel('운행 1건의 평균 차량점유 (분, 배차→하차)'); ax.grid(axis='y', visible=False)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2)
ax.set_title('Hub 연계 시 외곽 운행 1건의 차량점유가 줄어드는 폭')
ax.text(0, -0.25, '* 현행 노선으로 충북대병원 연결이 확인되지 않은 읍면 (제안 노선 필요)', transform=ax.transAxes, fontsize=9, color=INK2)
save(fig, 'fig05_hub_occupancy')
