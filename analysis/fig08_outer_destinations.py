"""
그림 8. 외곽 출발 해피콜의 도착 동 상위 12곳
  → 저장: figures/fig08_outer_destinations.png  (보고서 '분석결과 이미지' 그림 8)

사용 데이터: 도착 동별 건수(outer_destinations), 핵심 목적지 동
처리:
  상위 12개 동을 핵심 목적지 동(주황)과 그 외(회색)로 구분
그림: 가로 막대 (1위 율량·사천동 2,471건)

실행: VS Code에서 이 파일을 열고 오른쪽 위 ▷(Run Python File)  또는  터미널에서  python analysis/fig08_outer_destinations.py
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd())
from common import *   # 데이터 위치·폰트·스타일·공통 데이터(hc, done, bnd, HUB, CORE 등)·공통 계산 함수

out, dest, core_share = outer_destinations()

fig, ax = plt.subplots(figsize=(8, 4.6))
top = dest.head(12)[::-1]
cols = [C_OUT if d in CORE else C_GRAY for d in top.index]
bars = ax.barh(top.index, top.values, color=cols, height=0.6)
for b, v in zip(bars, top.values):
    ax.text(v + top.max() * 0.01, b.get_y() + b.get_height() / 2, f'{v:,}', va='center', fontsize=9, color=INK2)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C_OUT, label='핵심 목적지 동 (주요 정류장 권역·종합병원)'), Patch(color=C_GRAY, label='그 외 동')],
          loc='lower right')
ax.set_xlabel('연간 운행 건수'); ax.grid(axis='y', visible=False)
ax.set_title(f'외곽 출발 운행의 {core_share:.0%}가 저상버스 거점이 있는 동으로 간다')
save(fig, 'fig08_outer_destinations')
