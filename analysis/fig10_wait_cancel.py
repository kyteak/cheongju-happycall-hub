"""
그림 10. 차종별 평균 대기와 접수 시각별 취소율
  → 저장: figures/fig10_wait_cancel.png  (보고서 '분석결과 이미지' 그림 10)

사용 데이터: 대기 = 완료된 일반 호출의 접수→승차, 취소율 = 전체 호출(hc)
처리:
  특장차 vs 일반차량 평균 대기(+39%), 접수 시각별 취소 비율
그림: 왼쪽 막대(차종별 대기), 오른쪽 선(시각별 취소율, 16~19시 강조)

실행: VS Code에서 이 파일을 열고 오른쪽 위 ▷(Run Python File)  또는  터미널에서  python analysis/fig10_wait_cancel.py
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd())
from common import *   # 데이터 위치·폰트·스타일·공통 데이터(hc, done, bnd, HUB, CORE 등)·공통 계산 함수

# 차종별 대기(일반 호출) / 접수 시각별 취소율(전체 호출)
nd = done[done.예약일반.eq('일반')]
wait = nd.groupby('차종')['대기시간_분'].agg(['mean', 'median', 'size']).round(1).sort_values('mean', ascending=False)
print(wait)
wt_sp = nd.loc[nd.특장, '대기시간_분'].mean(); wt_ns = nd.loc[~nd.특장, '대기시간_분'].mean()
print(f'전체 {nd.대기시간_분.mean():.1f}분 / 특장차 {wt_sp:.1f}분 / 그 외 {wt_ns:.1f}분 → {wt_sp / wt_ns - 1:.0%} 김')
cancel_h = hc.groupby('접수시')['취소'].mean() * 100
print(f"16~19시 취소율 {hc[hc.접수시.between(16, 18)].취소.mean():.1%} (2026년만 {hc[y26 & hc.접수시.between(16, 18)].취소.mean():.1%})")

fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw={'width_ratios': [1, 1.4]})
ax = axes[0]
w = pd.Series({'특장차(휠체어)': wt_sp, '그 외 차량': wt_ns})
bars = ax.bar(w.index, w.values, color=[C_OUT, C_IN], width=0.55)
for b, v in zip(bars, w.values):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.4, f'{v:.1f}분', ha='center', color=INK)
ax.set_ylim(0, w.max() * 1.25); ax.set_ylabel('평균 대기 (분, 일반 호출)'); ax.grid(axis='x', visible=False)
ax.set_title('특장차 이용자가 39% 더 기다린다')
ax = axes[1]
ax.plot(cancel_h.index, cancel_h.values, color=C_IN, linewidth=2)
ax.axvspan(15.5, 18.5, color=C_OUT, alpha=0.12, linewidth=0)
ax.text(17, cancel_h.max() * 1.02, '16~19시', ha='center', color=C_OUT, fontsize=10)
ax.set_xticks(range(0, 24, 3)); ax.set_xlabel('호출 접수 시각 (시)')
ax.yaxis.set_major_formatter(PercentFormatter(decimals=0)); ax.set_ylim(0, cancel_h.max() * 1.15)
ax.set_title('저녁 16~19시 호출 5건 중 1건이 취소된다')
fig.tight_layout()
save(fig, 'fig10_wait_cancel')
