"""
그림 9. 운행 1건 이동거리 분포: 외곽 vs 시내
  → 저장: figures/fig09_trip_distance.png  (보고서 '분석결과 이미지' 그림 9)

사용 데이터: done의 이동거리_km, 구간
처리:
  외곽·시내 이동거리를 1km 간격 히스토그램(비율)으로, 40km 이상은 40에 합침
그림: 계단형 히스토그램 2개 (중앙값 시내 4.3km / 외곽 11.7km)

실행: VS Code에서 이 파일을 열고 오른쪽 위 ▷(Run Python File)  또는  터미널에서  python analysis/fig09_trip_distance.py
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd())
from common import *   # 데이터 위치·폰트·스타일·공통 데이터(hc, done, bnd, HUB, CORE 등)·공통 계산 함수

# 그림 2. 1건 이동거리 분포 (외곽 vs 시내)
fig, ax = plt.subplots(figsize=(7.5, 3.6))
bins = np.arange(0, 40.5, 1)
for k, col in [('시내', C_IN), ('외곽', C_OUT)]:
    x = done.loc[done.구간.eq(k), '이동거리_km'].clip(upper=40)
    ax.hist(x, bins=bins, density=True, histtype='step', linewidth=2, color=col,
            label=f'{k} (중앙값 {x.median():.1f}km)')
ax.set_xlabel('1건 이동거리 (km, 40km 이상은 40에 합침)'); ax.set_ylabel('비율 밀도')
ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
ax.legend(loc='upper right'); ax.grid(axis='x', visible=False)
ax.set_title('외곽 운행은 시내보다 2.7배 멀리 달린다')
save(fig, 'fig09_trip_distance')
