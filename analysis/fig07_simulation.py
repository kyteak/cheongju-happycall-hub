"""
그림 7. 실측 재생 시뮬레이션
  → 저장: figures/fig07_simulation.png  (보고서 '분석결과 이미지' 그림 7)

사용 데이터: 특장차 일반 호출 174,731건의 실제 접수시각·픽업·탑승시간, Hub 탑승시간(hub_effect), 동시 운행(wheelchair_busy)
처리:
  ① 호출을 접수 순서대로 재배차(가장 먼저 비는 차량)  ② 실측 평균 대기 20.1분에 맞는 차량 수 N=35 선택
  ③ Hub 연계 대상만 탑승시간을 줄여 전환율 30·50·100% 재실행  ④ 시간대별 차량 수 모형으로 강건성 확인
그림: 왼쪽 실측 vs 시뮬레이션 대기 누적분포, 오른쪽 차량 수별 평균 대기(현행 vs Hub 50%)

실행: VS Code에서 이 파일을 열고 오른쪽 위 ▷(Run Python File)  또는  터미널에서  python analysis/fig07_simulation.py
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd())
from common import *   # 데이터 위치·폰트·스타일·공통 데이터(hc, done, bnd, HUB, CORE 등)·공통 계산 함수

cand, el, per, sc = hub_effect()
sp, T0, n_min, busy, hourly, peak_h = wheelchair_busy()

sim = done[done.특장 & done.예약일반.eq('일반')].copy()
sim['t'] = ((sim['일자'] + pd.to_timedelta(sim['접수시간']) - T0) / pd.Timedelta(minutes=1)).values
sim = sim.dropna(subset=['픽업소요_분', '탑승시간_분']).sort_values('t').reset_index(drop=True)
obs_wait = sim['대기시간_분'].mean()
tt = T0 + pd.to_timedelta(sim['t'], unit='m')
sim_we, sim_h = (tt.dt.dayofweek >= 5).values, tt.dt.hour.values

def run(fa, fmax, ride):
    """fa: 호출마다 근무 중인 차량 수, fmax: 최대 차량 수"""
    t = sim['t'].values; pk = sim['픽업소요_분'].values
    free = np.zeros(fmax); w = np.empty(len(t))
    for i in range(len(t)):
        j = np.argmin(free[:fa[i]]); s = max(t[i], free[j])
        w[i] = s - t[i] + pk[i]; free[j] = s + pk[i] + ride[i]
    return w
def run_const(n, ride):
    return run(np.full(len(sim), n), n, ride)

base_ride = sim['탑승시간_분'].values
calib = {n: run_const(n, base_ride) for n in range(31, 40)}
N = min(calib, key=lambda n: abs(calib[n].mean() - obs_wait))
print(f'실측 평균 대기 {obs_wait:.1f}분 → 보정 특장차 대수 N={N} (시뮬레이션 {calib[N].mean():.1f}분, 2단계 평일 최대 동시 운행 {hourly.sum(axis=1).max():.0f}대)')

hub_ride = el[el.특장 & el.예약일반.eq('일반')].set_index('운행ID')['Hub탑승']
is_el = sim['운행ID'].isin(hub_ride.index).values
ride_hub = base_ride.copy(); ride_hub[is_el] = hub_ride.loc[sim.loc[is_el, '운행ID']].values
rng = np.random.default_rng(42); u = rng.random(len(sim))
def ride_rate(rate):
    r = base_ride.copy(); m = is_el & (u < rate); r[m] = ride_hub[m]; return r

pk_mask = (sim_h >= 7) & (sim_h <= 18)
rows = []
for lab, rate in [('현행', 0), ('Hub 연계 30%', 0.3), ('Hub 연계 50%', 0.5), ('Hub 연계 100%', 1.0)]:
    w = calib[N] if rate == 0 else run_const(N, ride_rate(rate))
    rows.append({'시나리오': lab, '평균 대기(분)': round(w.mean(), 1), '95% 대기(분)': round(np.percentile(w, 95), 1),
                 '07~19시 평균(분)': round(w[pk_mask].mean(), 1)})
simres = pd.DataFrame(rows)
simres['평균 대기 변화'] = (simres['평균 대기(분)'] / simres['평균 대기(분)'].iloc[0] - 1).map('{:+.0%}'.format)
print(simres.to_string(index=False))
print(f'Hub 연계 대상은 특장차 일반 호출의 {is_el.mean():.1%} ({is_el.sum():,}건)')

# 강건성: 시간대별 근무 차량 수 = 2단계 동시 운행 대수(평일/주말×시각) × 배율 f
allb = busy(sp)
dts = T0 + pd.to_timedelta(np.arange(n_min), unit='m')
busy_prof = pd.Series(allb).groupby([dts.dayofweek >= 5, dts.hour]).mean()
def fleet(f):
    F = np.maximum(1, np.ceil(busy_prof.values * f)).astype(int); m = dict(zip(busy_prof.index, F))
    return np.array([m[(w_, h_)] for w_, h_ in zip(sim_we, sim_h)]), F.max()
fres = {f: run(*fleet(f), base_ride).mean() for f in [1.10, 1.15, 1.20]}
fb = min(fres, key=lambda f: abs(fres[f] - obs_wait))
h0, h50 = fres[fb], run(*fleet(fb), ride_rate(0.5)).mean()
print(f'[강건성] 시간대별 차량 모형(f={fb}): 현행 {h0:.1f}분 → 전환 50% {h50:.1f}분 ({h50 / h0 - 1:+.0%})')

op_h = done[done.특장].groupby('일자')['점유'].sum().mean() / 60
saved50 = sc.query("노선.str.startswith('제안') and 전환율 == '50%' and 차량 == '특장차'", engine='python')['절감 차량시간(h/년)'].iloc[0]
print(f'특장차 전체 하루 운행 {op_h:,.0f}시간 중 전환 50% 절감 하루 {saved50 / 365:.1f}시간 ({saved50 / 365 / op_h:.1%})')

# 그림 9
curve = pd.DataFrame({'현행': {n: calib[n].mean() for n in range(N - 3, N + 3)},
                      'Hub 연계 50%': {n: run_const(n, ride_rate(0.5)).mean() for n in range(N - 3, N + 3)}})
fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.9))
ax = axes[0]
for lab, x, col, ls in [('실측', sim['대기시간_분'].values, INK2, '-'), (f'시뮬레이션 (N={N})', calib[N], C_IN, '--')]:
    xs = np.sort(np.clip(x, 0, 90)); ax.plot(xs, np.arange(1, len(xs) + 1) / len(xs), color=col, linewidth=2, linestyle=ls, label=lab)
ax.set_xlim(0, 90); ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
ax.set_xlabel('대기시간 (분, 90분 이상은 90에 합침)'); ax.set_ylabel('누적 비율')
ax.legend(loc='lower right'); ax.set_title('보정 확인: 실측과 시뮬레이션의 대기 분포')
ax = axes[1]
for lab, col in [('현행', C_IN), ('Hub 연계 50%', C_OUT)]:
    ax.plot(curve.index, curve[lab], marker='o', color=col, linewidth=2, label=lab)
ax.axhline(obs_wait, color=GRID, linewidth=1.5, zorder=0)
ax.text(curve.index.max(), obs_wait + 0.4, f'실측 평균 {obs_wait:.1f}분', fontsize=9, color=INK2, ha='right')
ax.set_xticks(curve.index); ax.set_xlabel('특장차 실효 대수 (대)'); ax.set_ylabel('평균 대기 (분)'); ax.legend(loc='upper right')
ax.set_title('Hub 연계 50%: 같은 차량으로 대기 약 1분 단축')
fig.tight_layout()
save(fig, 'fig07_simulation')
