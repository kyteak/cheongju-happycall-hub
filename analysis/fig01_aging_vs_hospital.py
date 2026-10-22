"""
그림 1. 고령화율과 종합병원 거리 (상관계수 0.72)
  → 저장: figures/fig01_aging_vs_hospital.png  (보고서 '분석결과 이미지' 그림 1)

사용 데이터: 연령별 인구현황 엑셀, 정류장 승하차(오전 6~9시), 병원 엑셀 [청주_의료기관] 시트(종합병원 7곳), 행정동 경계
처리:
  ① 행정동별 고령화율  ② 동 고령인구를 동 안 정류장에 오전 6~9시 승차 비율로 배분
  ③ 정류장→가장 가까운 종합병원 거리(직선×1.3)의 승차량 가중평균  ④ 상관계수(베스티안 제외 값도 출력)
그림: 산점도 (x 고령화율, y 평균 거리, 원 크기 고령인구, 파랑=동 / 주황=읍면)

실행: VS Code에서 이 파일을 열고 오른쪽 위 ▷(Run Python File)  또는  터미널에서  python analysis/fig01_aging_vs_hospital.py
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd())
from common import *   # 데이터 위치·폰트·스타일·공통 데이터(hc, done, bnd, HUB, CORE 등)·공통 계산 함수

# (1) 행정동별 총인구·65세 이상 인구: 연령별 인구현황 엑셀(구별 시트, 동마다 3열씩)
sheets = pd.read_excel(DATA + '2026년 8월 연령별(만) 인구현황.xlsx', sheet_name=None, engine='calamine', header=None)
num = lambda v: 0 if pd.isna(v) else int(str(v).replace(',', ''))
rows = []
for gu, df in sheets.items():
    if gu == '청주시':
        continue
    lab = df[1].ffill()
    for c in range(6, df.shape[1], 3):          # 3열 = 인구수·구성비·성비, 6열부터 동
        name = df.iat[5, c]
        if pd.isna(name):
            continue
        tot = old = 0
        for i in range(7, len(df)):
            if df.iat[i, 2] != '계':
                continue
            l = str(lab[i]).replace(' ', ''); v = num(df.iat[i, c])
            if l == '합계':
                tot = v
            else:
                m = re.match(r'(\d+)세', l)
                if m and int(m.group(1)) >= 65:
                    old += v
        rows.append((str(name).strip(), tot, old))
pop = pd.DataFrame(rows, columns=['ADM_NM', '총인구', '고령'])
pop['ADM_NM'] = pop.ADM_NM.str.replace('.', '·', regex=False).replace({'강서제1동': '강서1동', '강서제2동': '강서2동', '탑대성동': '탑·대성동'})
pop['고령화율'] = pop['고령'] / pop['총인구'] * 100

# (2) 종합병원 7곳(상급종합 1 + 종합병원 6, 오송 베스티안병원 포함): 의료기관 시트
med = pd.read_excel(DATA + '청주_거점병원_의료접근성_분석.xlsx', sheet_name='청주_의료기관', engine='calamine')
gh = med[med['종별'].isin(['상급종합', '종합병원'])]

# (3) 고령자 위치 대리값: 동 안의 정류장마다 오전 6~9시 승차량 비율로 고령인구를 나눠 배치
am = st[st['시간대'].between(6, 8)].groupby('정류장ID', as_index=False).agg(승차=('승차', 'sum'), 위도=('위도', 'first'), 경도=('경도', 'first'))
am = gpd.sjoin(gpd.GeoDataFrame(am, geometry=gpd.points_from_xy(am.경도, am.위도), crs=4326),
               bnd[['ADM_NM', 'geometry']], how='inner', predicate='within')
am['병원거리'] = np.min([hav_km(am.위도.values, am.경도.values, la, lo) for la, lo in zip(gh['위도(Y)'], gh['경도(X)'])], axis=0) * DETOUR
wdist = am.groupby('ADM_NM').apply(lambda x: np.average(x['병원거리'], weights=x['승차']) if x['승차'].sum() > 0 else x['병원거리'].mean(),
                                   include_groups=False).rename('병원거리')
f1 = pop.merge(wdist, left_on='ADM_NM', right_index=True)
f1['읍면'] = f1.ADM_NM.str[-1].isin(['읍', '면'])
r = np.corrcoef(f1['고령화율'], f1['병원거리'])[0, 1]
print(f'{len(f1)}개 읍면동, 상관계수 r = {r:.2f}')
print(f1.sort_values('병원거리', ascending=False).head(8).round(1).to_string(index=False))
r_ex = None
gh_ex = gh[~gh['요양기관명'].str.contains('베스티안')]
d_ex = np.min([hav_km(am.위도.values, am.경도.values, la, lo) for la, lo in zip(gh_ex['위도(Y)'], gh_ex['경도(X)'])], axis=0) * DETOUR
w_ex = am.assign(d=d_ex).groupby('ADM_NM').apply(lambda x: np.average(x['d'], weights=x['승차']) if x['승차'].sum() > 0 else x['d'].mean(), include_groups=False)
r_ex = np.corrcoef(f1['고령화율'], f1.ADM_NM.map(w_ex))[0, 1]
print(f'참고: 화상 전문 베스티안병원을 빼면 r = {r_ex:.2f}, 오송읍 거리 {w_ex["오송읍"]:.1f}km')

fig, ax = plt.subplots(figsize=(8, 5))
for is_em, col, lab in [(False, C_IN, '동'), (True, C_OUT, '읍·면')]:
    s = f1[f1['읍면'] == is_em]
    ax.scatter(s['고령화율'], s['병원거리'], s=s['고령'] / 25, color=col, alpha=0.85, edgecolor='white', linewidth=0.8, label=lab)
OFF = {'현도면': (-38, -4), '북이면': (5, -14), '오송읍': (6, -12)}   # 겹치는 이름만 위치 조정
for _, rw in f1[f1['읍면']].iterrows():
    ax.annotate(rw.ADM_NM, (rw['고령화율'], rw['병원거리']), xytext=OFF.get(rw.ADM_NM, (4, 3)), textcoords='offset points', fontsize=8, color=INK2)
ax.set_xlabel('고령화율 (65세 이상 비율, %)'); ax.set_ylabel('고령자 → 가장 가까운 종합병원 평균 거리 (km)')
ax.legend(loc='upper left', title='원 크기 = 고령인구', title_fontsize=9)
ax.set_title(f'늙은 동네일수록 큰 병원이 멀다 (상관계수 {r:.2f})')
save(fig, 'fig01_aging_vs_hospital')
