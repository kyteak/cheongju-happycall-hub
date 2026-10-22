"""
그림 4. 외곽–주요 정류장–충북대병원 저상노선 후보 7개
  → 저장: figures/fig04_lowfloor_routes.png  (보고서 '분석결과 이미지' 그림 4)

사용 데이터: 정류장 좌표·이용량, 읍면 Hub, 주요 정류장 권역, 행정동 경계, 보고서 7장 노선표
처리:
  노선표 순서대로 정류장 좌표를 직선 연결, 노선 길이 출력.
  아래쪽 [참고]는 보고서 2장 노선 설계 규칙(그리디 삽입) 구현으로 결과만 출력
그림: 지도 위 노선 A~G, 원 크기=권역 이용량, 네모=Hub, 별=충북대병원

실행: VS Code에서 이 파일을 열고 오른쪽 위 ▷(Run Python File)  또는  터미널에서  python analysis/fig04_lowfloor_routes.py
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd())
from common import *   # 데이터 위치·폰트·스타일·공통 데이터(hc, done, bnd, HUB, CORE 등)·공통 계산 함수

# 노선 그리기에 쓸 점 좌표: 읍면 Hub 정류장, 주요 정류장 권역 대표 정류장, 충북대병원 정류장
name_xy = st.groupby('정류장명').agg(위도=('위도', 'mean'), 경도=('경도', 'mean'), 이용=('승차', 'sum'))
P = {r.읍면: (r.위도, r.경도) for r in HUB.itertuples()}
for k in KW:
    P[k] = tuple(name_xy.loc[k, ['위도', '경도']])
P['충북대병원'] = P['충북대학교병원']
SHORT = {'용암효성': '용암효성아파트', '현대3차': '현대3차아파트', '분평휴먼시아': '분평휴먼시아2단지아파트', '마로니에공원': '마로니에공원',
         '문화제조창': '문화제조창.시청제2임시청사', '청주대': '청주대학교.뉴시스', '도청': '도청.그림책정원1937', '사직사거리': '사직사거리.시립미술관.교육도서관',
         '산업단지입구': '산업단지입구', '사창사거리': '사창사거리', '시외버스터미널': '시외버스터미널'}

# 보고서 7장 표의 최종 노선 7개 (읍면 Hub → 주요 정류장 권역 → 충북대병원)
ROUTES = {
    'A': ['미원면', '낭성면', '가덕면', '남일면', '용암효성', '현대3차', '분평휴먼시아', '충북대병원'],
    'B': ['북이면', '내수읍', '마로니에공원', '문화제조창', '청주대', '도청', '사직사거리', '충북대병원'],
    'C': ['현도면', '남이면', '충북대병원'],
    'D': ['문의면', '분평휴먼시아', '충북대병원'],
    'E': ['오창읍', '산업단지입구', '사창사거리', '충북대병원'],
    'F': ['강내면', '시외버스터미널', '산업단지입구', '사창사거리', '충북대병원'],
    'G': ['옥산면', '시외버스터미널', '산업단지입구', '사창사거리', '충북대병원'],
}
xy = lambda k: P[SHORT.get(k, k)]
def length(seq):
    return sum(hav_km(*xy(a), *xy(b)) for a, b in zip(seq[:-1], seq[1:])) * DETOUR
for k, seq in ROUTES.items():
    print(k, f'{length(seq):.1f}km', ' → '.join(seq))

PAL = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6']
fig, ax = plt.subplots(figsize=(8, 8))
bnd.plot(ax=ax, color=np.where(bnd['구분'] == '읍면', '#f3efe6', '#ffffff'), edgecolor=GRID, linewidth=0.6)
for (k, seq), col in zip(ROUTES.items(), PAL):
    pts = [xy(s) for s in seq]
    ax.plot([p_[1] for p_ in pts], [p_[0] for p_ in pts], color=col, linewidth=2.2, zorder=2)
    ax.text(pts[0][1], pts[0][0] + 0.008, k, color=col, fontsize=12, fontweight='bold', ha='center', zorder=4)
kw_pts = name_xy.loc[[k for k in KW if k not in ('충북대학교병원',)]]
ax.scatter(kw_pts['경도'], kw_pts['위도'], s=kw_pts['이용'] / kw_pts['이용'].max() * 250 + 20, facecolor='white', edgecolor=INK2, linewidth=1, zorder=3, label='주요 정류장 권역 (원 크기 = 이용량)')
ax.scatter(HUB['경도'], HUB['위도'], marker='s', s=40, color=INK2, edgecolor='white', zorder=3, label='읍면 Hub 정류장')
ax.scatter(*P['충북대병원'][::-1], marker='*', s=260, color='#e34948', edgecolor='white', zorder=5, label='충북대학교병원')
for r_ in HUB.itertuples():
    ax.annotate(r_.읍면, (r_.경도, r_.위도), xytext=(5, -10), textcoords='offset points', fontsize=8, color=INK2)
ax.legend(loc='lower left', fontsize=9); ax.set_axis_off()
ax.set_title('외곽 읍면 → 주요 정류장 → 충북대병원을 잇는 저상노선 후보 7개')
save(fig, 'fig04_lowfloor_routes')

# %% [참고] 노선 설계 규칙(그리디 삽입) ─ 그림 없이 결과만 출력
# 참고: 보고서 2장에 적힌 노선 설계 규칙(그리디 삽입)을 코드로 구현
# 1) 충북대병원에서 먼 읍면부터 노선을 시작하고, 다른 읍면을 넣어도 노선 길이가 25% 넘게 늘지 않으면 함께 묶는다
# 2) 마지막 읍면 뒤 ~ 병원 앞 구간에, 추가 우회 1.5km 이내로 들를 수 있는 주요 정류장 권역을 이용량 큰 순서로 넣는다
KWSHARE = dict(zip(KW, [14.3, 7.0, 6.4, 3.2, 2.4, 1.8, 1.2, 1.2, 1.2, 1.1, 1.0, 1.0, 1.0, 0.9, 0.7]))   # 보고서 5장 권역 이용 비중(%)
dd = lambda a, b: hav_km(*P[a], *P[b]) * DETOUR
L = lambda r_: sum(dd(a, b) for a, b in zip(r_[:-1], r_[1:]))
order = sorted(HUB['읍면'], key=lambda h: -dd(h, '충북대병원'))
routes, used = [], set()
for h in order:
    if h in used:
        continue
    r_ = [h, '충북대병원']; used.add(h)
    for g_ in order:
        if g_ in used:
            continue
        best = min((r_[:i] + [g_] + r_[i:] for i in range(1, len(r_))), key=L)
        if L(best) <= 1.25 * L(r_):
            r_ = best; used.add(g_)
    routes.append(r_)
cand = [k for k in sorted(KW, key=lambda k: -KWSHARE[k]) if k not in ('충북대학교병원', '오창프라자', '오송역')]
for r_ in routes:
    for k in cand:
        last = max(i for i, x in enumerate(r_) if x in set(HUB['읍면']))
        best = min((r_[:i] + [k] + r_[i:] for i in range(last + 1, len(r_))), key=L)
        if L(best) - L(r_) <= 1.5:
            r_[:] = best
for r_ in routes:
    print(f'{L(r_):.1f}km', ' → '.join(r_))
print('※ 이 규칙만으로는 B·C·E·F·G가 보고서와 같고, A·D는 남일·가덕면 묶음이 달라진다(보고서 노선은 팀의 앞선 단계 코드 결과).')
