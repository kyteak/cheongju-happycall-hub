"""
그림 1~10을 한 번에 만들고, 보고서 본문 수치를 outputs/report_numbers.csv로 저장합니다.
실행:  python run_all.py
그림 하나만 보고 싶으면 analysis/ 폴더의 그림 파일(fig01~fig10)을 하나씩 실행하세요.
"""
import os, sys, runpy
from pathlib import Path
os.environ['HC_NO_SHOW'] = '1'                       # 한꺼번에 돌릴 때는 창을 띄우지 않고 파일로만 저장
A = Path(__file__).resolve().parent / 'analysis'
sys.path.insert(0, str(A))

FIGS = ['fig01_aging_vs_hospital', 'fig02_outer_share', 'fig03_destination_map', 'fig04_lowfloor_routes',
        'fig05_hub_occupancy', 'fig06_wheelchair_busy', 'fig07_simulation', 'fig08_outer_destinations',
        'fig09_trip_distance', 'fig10_wait_cancel']
res = {}
for f in FIGS:
    print(f'\n========== {f} ==========')
    res[f] = runpy.run_path(str(A / f'{f}.py'), run_name='__main__')

# ── 보고서 본문 수치 ────────────────────────────────────────
from common import *                                  # hc, done 등
g1, g2, g3, g5, g7, g10 = (res[k] for k in ['fig01_aging_vs_hospital', 'fig02_outer_share', 'fig03_destination_map',
                                            'fig05_hub_occupancy', 'fig07_simulation', 'fig10_wait_cancel'])
sc, el, simres = g5['sc'], g5['el'], g7['simres']
LPG_KG_PER_L = 1.798                                   # 2025 국가 온실가스 인벤토리 LPG 배출계수(kgCO2e/L)
KM_PER_L = {'특장차': 7.0, '그 외 차량': 9.0}          # 특장차 7km/L, 일반차량 9km/L (가정)
co2 = sc[sc.노선.str.startswith('제안')].copy()
co2['절감 CO2(t/년)'] = co2['절감 주행(km/년)'] / co2.차량.map(KM_PER_L) * LPG_KG_PER_L / 1000
co2_tab = co2.pivot(index='전환율', columns='차량', values='절감 CO2(t/년)').round(1)
co2_tab['합계'] = co2_tab.sum(axis=1)
print('\n제안 노선 기준 연간 CO2 절감(t)'); print(co2_tab)

wk = hc[hc['일자'].dt.dayofweek < 5]; ndays = wk['일자'].nunique(); sp_wk = wk[wk.특장]
ev = pd.DataFrame({'호출(하루 평균)': sp_wk.groupby('접수시').size() / ndays,
                   '취소율': sp_wk.groupby('접수시')['취소'].mean(),
                   '평균 대기(분)': sp_wk[sp_wk.운행완료 & sp_wk.예약일반.eq('일반')].groupby('접수시')['대기시간_분'].mean()}).loc[[15, 17]]
f1 = g1['f1']; r_fig1 = np.corrcoef(f1['고령화율'], f1['병원거리'])[0, 1]
sc50 = sc.query("노선.str.startswith('제안') and 전환율 == '50%'", engine='python').set_index('차량')
now50 = sc.query("노선.str.startswith('현행') and 전환율 == '50%'", engine='python')['절감 차량시간(h/년)'].sum()
saved_total = sc50['절감 차량시간(h/년)'].sum(); km50 = sc50['절감 주행(km/년)'].sum()
share_pct, avg, nd = g2['share_pct'], g2['avg'], g10['nd']
nums = [
    ('완료 운행(이상치 제외)', f'{len(done):,}건'),
    ('외곽 비중: 건수 / 차량점유 / 주행거리', ' / '.join(f'{v:.1f}%' for v in share_pct.loc['외곽', ['건수', '차량점유(시간)', '주행거리(km)']])),
    ('1건 이동거리: 외곽 / 시내', f"{avg.loc['외곽', '1건 이동거리(km)']}km / {avg.loc['시내', '1건 이동거리(km)']}km"),
    ('평균 대기: 전체 / 특장차 / 일반차량', f"{nd.대기시간_분.mean():.1f} / {g10['wt_sp']:.1f} / {g10['wt_ns']:.1f}분"),
    ('16~19시 취소율', f"{hc[hc.접수시.between(16, 18)].취소.mean():.1%}"),
    ('고령화율–종합병원 거리 상관계수 (베스티안 제외 시)', f"{r_fig1:.2f} ({g1['r_ex']:.2f})"),
    ('외곽→시내 운행 / 핵심 목적지 동 비율', f"{len(g3['out']):,}건 / {g3['core_share']:.1%}"),
    ('Hub 연계 대상 / 1건 점유 현재→Hub', f'{len(el):,}건 / {el.점유.mean():.1f}분 → {el.Hub점유.mean():.1f}분'),
    ('연간 절감 차량시간(제안, 50%): 특장차 / 일반차량 / 합계', f"{sc50.loc['특장차', '절감 차량시간(h/년)']:,} / {sc50.loc['그 외 차량', '절감 차량시간(h/년)']:,} / {saved_total:,}시간"),
    ('일반차량 몫 / 현행 노선 7개 읍면 몫', f"{sc50.loc['그 외 차량', '절감 차량시간(h/년)'] / saved_total:.0%} / {now50 / saved_total:.0%}"),
    ('추가 처리 가능(제안, 50%)', f"{sc50['추가 처리 가능(건/년)'].sum():,}건"),
    ('특장차 평균 대기 현행→50% (95% 대기)', f"{simres.iloc[0]['평균 대기(분)']} → {simres.iloc[2]['평균 대기(분)']}분 ({simres.iloc[0]['95% 대기(분)']} → {simres.iloc[2]['95% 대기(분)']}분)"),
    ('절감 주행 / 탄소(제안, 50%)', f"{km50:,}km / {co2_tab.loc['50%', '합계']:.1f}t"),
    ('평일 특장차 15시대→17시대: 호출 / 취소율 / 대기', f"{ev.iloc[0, 0]:.0f}→{ev.iloc[1, 0]:.0f}건 / {ev.iloc[0, 1]:.0%}→{ev.iloc[1, 1]:.0%} / {ev.iloc[0, 2]:.0f}→{ev.iloc[1, 2]:.0f}분"),
]
summary = pd.DataFrame(nums, columns=['항목', '값'])
summary.to_csv(OUT_DIR / 'report_numbers.csv', index=False, encoding='utf-8-sig')
print('\n' + summary.to_string(index=False))
print('  → outputs/report_numbers.csv 저장')
