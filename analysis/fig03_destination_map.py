"""
그림 3. 외곽 출발 해피콜의 도착 동과 읍면 Hub (지도)
  → 저장: figures/fig03_destination_map.png  (보고서 '분석결과 이미지' 그림 3)

사용 데이터: 외곽 출발 → 시내 도착 17,910건(outer_destinations), 행정동 경계, Hub·종합병원 좌표
처리:
  도착 동별 건수를 동 경계에 음영으로 표시
그림: 지도 (파란 음영=도착 건수, 베이지=외곽 12개 읍면, 빗금=오송읍, 주황 점=Hub, 십자=종합병원)

실행: VS Code에서 이 파일을 열고 오른쪽 위 ▷(Run Python File)  또는  터미널에서  python analysis/fig03_destination_map.py
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd())
from common import *   # 데이터 위치·폰트·스타일·공통 데이터(hc, done, bnd, HUB, CORE 등)·공통 계산 함수

out, dest, core_share = outer_destinations()

# 그림 6. 지도: 외곽 출발 운행의 목적지 동별 건수
m = bnd.merge(dest.rename('건수'), left_on='ADM_NM', right_index=True, how='left').fillna({'건수': 0})
fig, ax = plt.subplots(figsize=(8, 8))
m[m.구분.eq('동')].plot(column='건수', cmap='Blues', ax=ax, edgecolor='white', linewidth=0.6, legend=True,
                       legend_kwds={'label': '외곽 출발 운행 도착 건수 (연간)', 'shrink': 0.55})
m[m.ADM_NM.isin(OUTER12)].plot(ax=ax, color='#f3efe6', edgecolor=GRID, linewidth=0.6)
m[m.ADM_NM.eq('오송읍')].plot(ax=ax, color='white', edgecolor=GRID, linewidth=0.6, hatch='///')
hp = gpd.GeoDataFrame(HUB, geometry=gpd.points_from_xy(HUB.경도, HUB.위도), crs=4326)
hp.plot(ax=ax, color=C_OUT, markersize=40, edgecolor='white', linewidth=1, zorder=3)
hos.plot(ax=ax, color=INK, marker='P', markersize=70, edgecolor='white', linewidth=0.8, zorder=3)
for _, r in hp.iterrows():
    ax.annotate(r.읍면, (r.geometry.x, r.geometry.y), xytext=(4, 4), textcoords='offset points', fontsize=8, color=INK2)
ax.legend(handles=[plt.Line2D([], [], marker='o', ls='', color=C_OUT, label='읍면 Hub 정류장'),
                   plt.Line2D([], [], marker='P', ls='', color=INK, label='종합병원'),
                   Patch(facecolor='#f3efe6', edgecolor=GRID, label='외곽 12개 읍면 (출발지)')], loc='lower left')
ax.set_axis_off(); ax.set_title('외곽 출발 해피콜은 도심 몇 개 동으로 모인다')
save(fig, 'fig03_destination_map')
