"""
그림 6. 평일 시간대별 동시 운행 특장차
  → 저장: figures/fig06_wheelchair_busy.png  (보고서 '분석결과 이미지' 그림 6)

사용 데이터: done 중 특장차의 배차시각·점유시간 (wheelchair_busy)
처리:
  1분 단위로 운행 구간을 쌓은 평일 시각별 평균을 외곽·그 외로 분리
그림: 누적 영역 차트 (시내·기타 파랑 + 외곽 주황, 9시 약 38대 최대)

실행: VS Code에서 이 파일을 열고 오른쪽 위 ▷(Run Python File)  또는  터미널에서  python analysis/fig06_wheelchair_busy.py
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd())
from common import *   # 데이터 위치·폰트·스타일·공통 데이터(hc, done, bnd, HUB, CORE 등)·공통 계산 함수

sp, T0, n_min, busy, hourly, peak_h = wheelchair_busy()

fig, ax = plt.subplots(figsize=(9, 3.8))
x = hourly.index
ax.stackplot(x, hourly['그 외'], hourly['외곽'], colors=[C_IN, C_OUT], alpha=0.9,
             labels=['시내·기타 운행', '외곽 12개 읍면 운행'], edgecolor='#fcfcfb', linewidth=1)
ax.set_xticks(range(0, 24, 2)); ax.set_xlim(0, 23)
ax.set_xlabel('시각 (시, 평일 평균)'); ax.set_ylabel('동시에 운행 중인 특장차 (대)')
ax.legend(loc='upper left'); ax.grid(axis='x', visible=False)
ax.set_title(f'특장차는 {peak_h}시 전후 가장 바쁘고, 외곽 운행이 그중 일부를 길게 묶는다')
save(fig, 'fig06_wheelchair_busy')
