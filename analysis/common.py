"""
공통 설정·데이터 준비 ─ 그림 파일(fig01~fig10)이 맨 위에서 `from common import *`로 불러 씁니다.
직접 고칠 필요는 없습니다.

들어 있는 것
  · 데이터 위치(data/), 한글 폰트, 그림 스타일, 그림 저장 함수 save(), 거리 함수 hav_km()
  · 공통 데이터: hc(해피콜 전체), done(완료 운행 383,964건), bnd(행정동 경계), st(정류장 승하차),
                 stops(정류장 좌표), HUB(읍면 Hub 12곳), KW(주요 정류장 권역 15곳), hos(종합병원), CORE(핵심 목적지 동 18곳)
  · 여러 그림이 함께 쓰는 계산 함수
      outer_destinations()  외곽→시내 도착 동 집계        (그림 3, 8)
      hub_effect()          Hub 연계 반사실 계산·시나리오 (그림 5, 7)
      wheelchair_busy()     특장차 동시 운행 대수         (그림 6, 7)
  · 처음 실행할 때 준비한 데이터를 data/_cache/에 저장해 두고, 다음부터는 바로 읽어 와 빨라집니다.
"""
import os, sys, re, zipfile, heapq, platform, pickle
from pathlib import Path

# 그림을 화면에도 띄울지: 그림 파일 하나만 실행하면 창으로 표시, run_all.py로 한꺼번에 돌리면 파일로만 저장
SHOW = os.environ.get('HC_NO_SHOW') != '1'
if platform.system() == 'Linux' and not os.environ.get('DISPLAY') and 'ipykernel' not in sys.modules:
    SHOW = False
import matplotlib
if not SHOW:
    matplotlib.use('Agg')
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter, FuncFormatter
from matplotlib.patches import Patch
from matplotlib import font_manager

# ── 데이터 위치 ─────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent          # 프로젝트 폴더 (analysis/의 한 단계 위)
_zip = BASE / 'data' / '교통분석_데이터.zip'
if _zip.exists() and not (BASE / 'data' / '교통분석_데이터').exists():
    zipfile.ZipFile(_zip).extractall(BASE / 'data')     # zip만 넣어 둔 경우 자동으로 풂
_dd = next((d for d in [BASE / 'data' / '교통분석_데이터', BASE / 'data'] if (d / 'cheongju_happycall_2025-10_2026-10.csv').exists()), None)
if _dd is None:
    sys.exit('data 폴더에 교통분석_데이터.zip(또는 압축 푼 파일들)을 넣은 뒤 다시 실행하세요. 자세한 내용은 data/README.md')
DATA = str(_dd) + os.sep
FIG_DIR = BASE / 'figures'; FIG_DIR.mkdir(exist_ok=True)
OUT_DIR = BASE / 'outputs'; OUT_DIR.mkdir(exist_ok=True)
CACHE_DIR = BASE / 'data' / '_cache'; CACHE_DIR.mkdir(exist_ok=True)

# ── 한글 폰트 (Windows 맑은 고딕 → macOS 애플고딕 → 나눔고딕 → Noto CJK) ──
_have = {f.name for f in font_manager.fontManager.ttflist}
_kfont = next((f for f in ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'Noto Sans CJK KR', 'Noto Sans CJK JP'] if f in _have), None)
if _kfont:
    plt.rcParams['font.family'] = _kfont
else:
    try:
        import koreanize_matplotlib  # noqa: F401
    except ImportError:
        print('한글 폰트를 찾지 못했습니다. pip install koreanize-matplotlib 후 다시 실행하세요.')

# ── 그림 스타일 (외곽=주황, 시내·비교=파랑, 보조=회색) ──
C_OUT, C_IN, C_GRAY = '#eb6834', '#2a78d6', '#b4b2a9'
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e6e5e0'
plt.rcParams.update({
    'axes.unicode_minus': False, 'figure.dpi': 110, 'savefig.dpi': 200, 'savefig.bbox': 'tight',
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': GRID,
    'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK,
    'axes.titlesize': 13, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
    'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.8, 'axes.axisbelow': True,
    'legend.frameon': False,
})

def save(fig, name):
    """그림을 figures/<name>.png로 저장하고, 단독 실행이면 창으로도 보여 줌"""
    fig.savefig(FIG_DIR / f'{name}.png')
    print(f'  → figures/{name}.png 저장')
    plt.show() if SHOW else plt.close(fig)

def hav_km(lat1, lon1, lat2, lon2):
    """두 좌표 사이 직선거리(km)"""
    p = np.pi / 180
    a = np.sin((lat2 - lat1) * p / 2) ** 2 + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))
DETOUR = 1.3   # 직선거리 → 도로거리 우회계수


# ════════════════════════════════════════════════════════════
# 공통 데이터 준비 ① 해피콜 운행기록  ② 행정동 경계·정류장·Hub·종합병원
#   ① 차종 재분류(2025년 G1 특장차·G2 임차택시 / 2026년 G1·G2 특장차 / G3 바우처택시 / G5 자가용),
#     외곽 12개 읍면 출발·도착 표시, 예약 운행 점유 보정, done = 완료 & 이상치 제외(383,964건)
#   ② 정류장·종합병원을 행정동 경계에 연결, 읍면 Hub 12곳·주요 정류장 권역 15곳·핵심 목적지 동(CORE) 지정
# ════════════════════════════════════════════════════════════
def _prepare():
    hc = pd.read_csv(DATA + 'cheongju_happycall_2025-10_2026-10.csv',
                     dtype={'출발_ADM_CD': str, '목적지_ADM_CD': str}, low_memory=False)
    hc['일자'] = pd.to_datetime(hc['일자'])
    y26 = hc['일자'] >= '2026-01-01'
    hc['차종'] = np.select(
        [hc.차량종류.eq('G1'), hc.차량종류.eq('G2') & y26, hc.차량종류.eq('G2') & ~y26, hc.차량종류.eq('G3'), hc.차량종류.eq('G5')],
        ['특장차', '특장차', '임차택시', '바우처택시', '자가용승용차'], '기타')
    hc['특장'] = hc['차종'].eq('특장차')

    OUTER12 = ['오창읍', '내수읍', '옥산면', '남이면', '강내면', '미원면', '남일면', '북이면', '문의면', '가덕면', '현도면', '낭성면']
    in_cj_o, in_cj_d = hc.출발도시.eq('청주시'), hc.목적지도시.eq('청주시')
    hc['o12'] = in_cj_o & hc.출발읍면동.isin(OUTER12)
    hc['d12'] = in_cj_d & hc.목적지읍면동.isin(OUTER12)
    hc['구간'] = np.select([hc.o12 | hc.d12,
                           hc.출발_읍면동구분.eq('동') & hc.목적지_읍면동구분.eq('동')],
                          ['외곽', '시내'], '기타')

    # 예약 운행의 점유·픽업 보정
    normal = hc.예약일반.eq('일반')
    med_pick = hc[normal].groupby('차종')['픽업소요_분'].median()
    hc['픽업'] = np.where(normal, hc['픽업소요_분'], hc['차종'].map(med_pick))
    hc['점유'] = np.where(normal, hc['차량점유_분'], hc['탑승시간_분'] + hc['픽업'])
    hc['주행km'] = hc['픽업거리_km'] + hc['이동거리_km']

    done = hc[hc.운행완료 & ~hc.시간이상치].copy()
    print(f'전체 {len(hc):,}건 / 완료(이상치 제외) {len(done):,}건')
    print(done.groupby('차종').size().rename('완료 건수').to_frame().T)

    # 행정동 경계, 정류장·병원 → 행정동 연결
    geo = gpd.read_file(DATA + 'cheongju_grid_100m.geojson')
    bnd = geo[geo.ADM_CD.notna()][['ADM_CD', 'ADM_NM', 'geometry']].reset_index(drop=True)
    bnd['구분'] = np.where(bnd.ADM_NM.str[-1].isin(['읍', '면']), '읍면', '동')

    st = pd.read_csv(DATA + '청주_정류장_월별_시간대별_승하차_.csv', encoding='cp949')
    stops = st.groupby(['정류장ID', '정류장명'], as_index=False).agg(위도=('위도', 'first'), 경도=('경도', 'first'))
    stops = gpd.sjoin(gpd.GeoDataFrame(stops, geometry=gpd.points_from_xy(stops.경도, stops.위도), crs=4326),
                      bnd[['ADM_NM', 'geometry']], how='left', predicate='within').drop(columns='index_right')

    # 보고서 3장의 읍면 Hub(환승 정류장)와 고령자→Hub 도로환산거리(km)
    HUB = pd.DataFrame([
        ('오창읍', '오창프라자', 2.1), ('내수읍', '내수삼일아파트', 2.3), ('옥산면', '형제빌라', 1.9),
        ('남이면', '남이면행정복지센터', 4.3), ('강내면', '월곡초등학교', 1.8), ('미원면', '미원우체국', 0.5),
        ('남일면', '고은리', 2.8), ('북이면', '장재', 2.4), ('문의면', '문의초등학교입구', 2.4),
        ('가덕면', '청주운전면허시험장', 3.6), ('현도면', '우록1리', 2.4), ('낭성면', '낭성면행정복지센터', 3.8)],
        columns=['읍면', 'Hub정류장', 'Hub거리_km'])
    # 보고서 6장: 현행 노선으로 충북대병원까지 1회 환승이 확인된 읍면
    NOW_LINKED = ['가덕면', '낭성면', '문의면', '내수읍', '강내면', '남이면', '오창읍']
    HUB['현행노선연결'] = HUB.읍면.isin(NOW_LINKED)
    hub_pts = stops[stops.정류장명.isin(HUB.Hub정류장)].drop_duplicates('정류장명')
    HUB = HUB.merge(hub_pts[['정류장명', '위도', '경도', 'ADM_NM']].rename(columns={'정류장명': 'Hub정류장', 'ADM_NM': 'Hub소재동'}), on='Hub정류장', how='left')

    # 보고서 5장의 주요 정류장 권역 15곳(대표 정류장)
    KW = ['도청.그림책정원1937', '시외버스터미널', '사창사거리', '청주대학교.뉴시스', '분평휴먼시아2단지아파트',
          '문화제조창.시청제2임시청사', '사직사거리.시립미술관.교육도서관', '마로니에공원', '산업단지입구',
          '현대3차아파트', '오창프라자', '용암효성아파트', '오송역', '충북대학교병원', '시청신청사예정지']
    kw_dong = set(stops[stops.정류장명.isin(KW)].ADM_NM)

    hos = pd.read_excel(DATA + '청주_거점병원_의료접근성_분석.xlsx', sheet_name='종합병원_기준점', engine='calamine').dropna(subset=['경도(X)'])
    hos = gpd.sjoin(gpd.GeoDataFrame(hos, geometry=gpd.points_from_xy(hos['경도(X)'], hos['위도(Y)']), crs=4326),
                    bnd[['ADM_NM', 'geometry']], how='left', predicate='within')
    hos_dong = set(hos.ADM_NM)

    # 핵심 목적지 동 = 주요 정류장 권역 또는 종합병원이 있는 '동' (저상버스로 닿기 쉬운 시내 거점)
    CORE = sorted(d for d in kw_dong | hos_dong if bnd.set_index('ADM_NM').loc[d, '구분'] == '동')
    print('핵심 목적지 동', len(CORE), '곳:', ', '.join(CORE))
    print('종합병원 소재 동:', dict(zip(hos['종합병원급 의료기관'].str[-8:], hos.ADM_NM)))
    print(HUB[['읍면', 'Hub정류장', 'Hub소재동', 'Hub거리_km', '현행노선연결']].to_string(index=False))
    print('주의: 가덕면 Hub(청주운전면허시험장)는 행정구역상 남일면에 있음 → 보고서에 명시하거나 가덕면 안 정류장으로 교체 검토')
    return dict(hc=hc, y26=y26, OUTER12=OUTER12, done=done, bnd=bnd, st=st, stops=stops, HUB=HUB,
                NOW_LINKED=NOW_LINKED, KW=KW, hos=hos, CORE=CORE)

_src = [DATA + f for f in ['cheongju_happycall_2025-10_2026-10.csv', 'cheongju_grid_100m.geojson',
                           '청주_정류장_월별_시간대별_승하차_.csv', '청주_거점병원_의료접근성_분석.xlsx']]
_key = [(os.path.basename(f), os.path.getsize(f), int(os.path.getmtime(f))) for f in _src]
_cache = CACHE_DIR / 'common.pkl'
_d = None
if _cache.exists():
    try:
        with open(_cache, 'rb') as fh:
            _k, _d = pickle.load(fh)
        if _k != _key:
            _d = None
    except Exception:
        _d = None
if _d is None:
    print('공통 데이터를 준비합니다 (처음 한 번만 30초 안팎 걸림)...')
    _d = _prepare()
    with open(_cache, 'wb') as fh:
        pickle.dump((_key, _d), fh)
globals().update(_d)
hc, y26, OUTER12, done, bnd, st, stops, HUB, NOW_LINKED, KW, hos, CORE = (_d[k] for k in
    ['hc', 'y26', 'OUTER12', 'done', 'bnd', 'st', 'stops', 'HUB', 'NOW_LINKED', 'KW', 'hos', 'CORE'])


# ════════════════════════════════════════════════════════════
# 여러 그림이 함께 쓰는 계산
# ════════════════════════════════════════════════════════════
def outer_destinations():
    """[그림 3·8] 외곽 12개 읍면 출발 → 시내(동) 도착 운행의 도착 동별 건수.
    반환: out(대상 운행), dest(동별 건수), core_share(핵심 목적지 동 비율)"""
    out = done[done.o12 & done.목적지_읍면동구분.eq('동')]
    dest = out.목적지읍면동.value_counts()
    core_share = out.목적지읍면동.isin(CORE).mean()
    print(f'외곽→시내(동) 완료 운행 {len(out):,}건 (하루 약 {len(out) / 365:.0f}건), 핵심 목적지 동 비율 {core_share:.1%}')
    print(f"그중 성화·개신·죽림동(충북대병원) {dest.get('성화·개신·죽림동', 0):,}건")
    print(dest.head(10))
    print('참고: 1위 율량·사천동은 보고서의 주요 정류장 권역·종합병원 소재 동이 아니어서 핵심 목적지에서 빠짐 (권역에 포함하면 Hub 대상이 늘어남)')
    return out, dest, core_share


def hub_effect():
    """[그림 5·7, 보고서 결과표] Hub 연계 반사실 계산.
    대상: 외곽 12개 읍면 ↔ 핵심 목적지 동 운행 중 Hub 거리 ≤ 실제 이동거리 × 70%
    운행마다 Hub 탑승시간 = 실제 탑승시간 × Hub거리 ÷ 실제 이동거리
    반환: cand(후보), el(대상 30,125건), per(읍면별 평균), sc(노선 범위 × 전환율 × 차종 시나리오 표)"""
    hubkm = HUB.set_index('읍면')['Hub거리_km']; linked = HUB.set_index('읍면')['현행노선연결']
    go = done.o12 & done.목적지읍면동.isin(CORE)
    back = done.d12 & done.출발읍면동.isin(CORE)
    cand = done[go | back].copy()
    cand['방향'] = np.where(go[go | back], '외곽→시내', '시내→외곽')
    cand['읍면'] = np.where(cand.방향.eq('외곽→시내'), cand.출발읍면동, cand.목적지읍면동)
    cand['Hub거리'] = cand.읍면.map(hubkm)
    cand['적용'] = cand.Hub거리 <= 0.7 * cand.이동거리_km
    cand['현행연결'] = cand.읍면.map(linked)
    el = cand[cand.적용 & cand.탑승시간_분.notna()].copy()
    el['Hub탑승'] = el.탑승시간_분 * el.Hub거리 / el.이동거리_km
    el['절감분'] = el.탑승시간_분 - el.Hub탑승
    el['절감km'] = el.이동거리_km - el.Hub거리
    el['Hub점유'] = el.점유 - el.절감분
    print(f'후보 {len(cand):,}건 중 70% 규칙 통과 {len(el):,}건 (외곽→시내 {el.방향.eq("외곽→시내").sum():,}, 시내→외곽 {el.방향.eq("시내→외곽").sum():,})')
    print(f'1건당 점유 {el.점유.mean():.1f}분 → {el.Hub점유.mean():.1f}분 ({el.절감분.mean():.1f}분, {el.절감분.sum() / el.점유.sum():.0%} 절감), 주행 {el.절감km.mean():.1f}km 절감')

    per = el[el.방향.eq('외곽→시내')].groupby('읍면').agg(
        연간건수=('운행ID', 'size'), 현재점유=('점유', 'mean'), Hub점유=('Hub점유', 'mean'),
        절감분=('절감분', 'mean'), 특장비율=('특장', 'mean')).round(1).sort_values('현재점유')
    per['현행노선연결'] = per.index.map(linked)
    print(per)
    # 관찰: 모든 읍면에서 시내→외곽 운행이 외곽→시내의 약 2배다. 시내→외곽 호출은 10~11시, 15시에 몰려 병원 진료 뒤 귀가로 보인다.
    # (가는 길은 가족 차량·예약 등 다른 수단을 쓰고 귀가할 때 해피콜을 부르는 경우가 많을 수 있음 → 공단 확인 권장)
    print(pd.crosstab(cand.읍면, cand.방향))

    # 시나리오별 연간 효과
    rows = []
    avg_occ_sp = done.loc[done.특장, '점유'].mean(); avg_occ_ns = done.loc[~done.특장, '점유'].mean()
    for net, sel in [('현행 노선(7개 읍면)', el.현행연결), ('제안 노선(12개 읍면)', pd.Series(True, index=el.index))]:
        e = el[sel]
        for rate in [0.1, 0.3, 0.5]:
            for grp, mask, occ in [('특장차', e.특장, avg_occ_sp), ('그 외 차량', ~e.특장, avg_occ_ns)]:
                h = e.loc[mask, '절감분'].sum() * rate / 60
                rows.append({'노선': net, '전환율': f'{rate:.0%}', '차량': grp, '대상(건/년)': int(mask.sum()),
                             '절감 차량시간(h/년)': round(h), '추가 처리 가능(건/년)': round(h * 60 / occ),
                             '절감 주행(km/년)': round(e.loc[mask, '절감km'].sum() * rate)})
    sc = pd.DataFrame(rows)
    print(sc.to_string(index=False))
    return cand, el, per, sc


def wheelchair_busy():
    """[그림 6·7] 특장차 운행마다 [배차, 하차] 구간을 1분 단위로 쌓아 동시 운행 대수를 구함.
    반환: sp(특장차 완료 운행), T0(기준 시각), n_min(분 개수), busy(구간→분별 대수 함수),
          hourly(평일 시각별 평균: 외곽 / 그 외), peak_h(가장 바쁜 시각)"""
    # 특장차 동시 운행 대수 (1분 해상도) – 평일 시간대별 평균
    sp = done[done.특장].copy()
    start = sp['일자'] + pd.to_timedelta(sp['배차시간'])
    # 예약 운행은 승차 시각에서 픽업 중앙값만큼 앞당겨 시작으로 봄
    start = np.where(sp.예약일반.eq('일반'), start,
                     sp['일자'] + pd.to_timedelta(sp['승차시간']) - pd.to_timedelta(sp['픽업'], unit='m'))
    sp['t0'] = pd.to_datetime(start); sp['t1'] = sp['t0'] + pd.to_timedelta(sp['점유'], unit='m')
    sp = sp.dropna(subset=['t0', 't1'])
    T0 = hc['일자'].min(); n_min = int((hc['일자'].max() + pd.Timedelta(days=2) - T0) / pd.Timedelta(minutes=1))
    def busy(df):
        a = ((df.t0 - T0) / pd.Timedelta(minutes=1)).astype(int).clip(0, n_min - 1).values
        b = ((df.t1 - T0) / pd.Timedelta(minutes=1)).astype(int).clip(0, n_min - 1).values
        arr = np.zeros(n_min + 1); np.add.at(arr, a, 1); np.add.at(arr, b, -1)
        return np.cumsum(arr)[:n_min]
    idx = T0 + pd.to_timedelta(np.arange(n_min), unit='m')
    prof = pd.DataFrame({'외곽': busy(sp[sp.구간.eq('외곽')]), '그 외': busy(sp[~sp.구간.eq('외곽')])}, index=idx)
    prof = prof[(prof.index.dayofweek < 5) & (prof.index < hc['일자'].max() + pd.Timedelta(days=1))]
    hourly = prof.groupby(prof.index.hour).mean()
    peak_h = hourly.sum(axis=1).idxmax()
    print(f'평일 특장차 동시 운행 최대 {hourly.sum(axis=1).max():.1f}대 ({peak_h}시), 그중 외곽 {hourly.loc[peak_h, "외곽"]:.1f}대')
    print(f'평일 07~19시 외곽 운행이 묶은 특장차 평균 {hourly.loc[7:18, "외곽"].mean():.1f}대')
    return sp, T0, n_min, busy, hourly, peak_h
