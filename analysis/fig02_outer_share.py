"""
그림 2. 외곽 12개 읍면 운행의 비중
  → 저장: figures/fig02_outer_share.png  (보고서 '분석결과 이미지' 그림 2)

사용 데이터: done(완료 운행)의 구간·차량점유·주행거리
처리:
  외곽(12개 읍면 출발·도착) / 시내(동↔동) / 기타로 나눠 건수·점유시간·주행거리 비중과 1건 평균 비교
그림: 가로 막대 3개 (건수 14.8% / 차량점유 17.8% / 주행거리 26.8%)

실행: VS Code에서 이 파일을 열고 오른쪽 위 ▷(Run Python File)  또는  터미널에서  python analysis/fig02_outer_share.py
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd())
from common import *   # 데이터 위치·폰트·스타일·공통 데이터(hc, done, bnd, HUB, CORE 등)·공통 계산 함수

g = done.groupby('구간')
share = pd.DataFrame({
    '건수': g.size(), '차량점유(시간)': g['점유'].sum() / 60, '주행거리(km)': g['주행km'].sum()})
share_pct = (share / share.sum() * 100).round(1)
avg = pd.DataFrame({'1건 이동거리(km)': g['이동거리_km'].mean(), '1건 점유(분)': g['점유'].mean(),
                    '1건 주행(km)': g['주행km'].mean()}).round(1)
print('비중(%)'); print(share_pct.loc[['외곽', '시내', '기타']])
print('\n1건 평균'); print(avg.loc[['외곽', '시내', '기타']])
print(f"\n외곽 1건 이동거리는 시내의 {avg.loc['외곽', '1건 이동거리(km)'] / avg.loc['시내', '1건 이동거리(km)']:.1f}배")

# 그림 1. 외곽 운행이 차지하는 비중
fig, ax = plt.subplots(figsize=(7.5, 3.2))
vals = share_pct.loc['외곽', ['건수', '차량점유(시간)', '주행거리(km)']]
labels = ['운행 건수', '차량 점유시간', '주행거리']
bars = ax.barh(labels[::-1], vals.values[::-1], color=C_OUT, height=0.55)
for b, v in zip(bars, vals.values[::-1]):
    ax.text(v + 0.5, b.get_y() + b.get_height() / 2, f'{v:.1f}%', va='center', color=INK, fontsize=11)
ax.set_xlim(0, max(vals) * 1.25); ax.xaxis.set_major_formatter(PercentFormatter(decimals=0))
ax.grid(axis='y', visible=False)
ax.set_title('외곽 12개 읍면 운행: 건수는 15%, 주행거리는 27%')
ax.set_xlabel('전체 완료 운행 대비 비중')
save(fig, 'fig02_outer_share')
