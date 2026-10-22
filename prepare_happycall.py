"""
해피콜 정보공개청구 원자료(월별 .xls 13개) → 분석용 CSV 하나로 정리

실행:  python prepare_happycall.py
입력:  data/정보공개청구_17770333_.zip  (또는 data/happycall_raw/ 폴더 안의 .xls 파일들)
       data/교통분석_데이터/cheongju_grid_100m.geojson  (행정동 코드 연결용)
출력:  data/cheongju_happycall_2025-10_2026-10.csv
"""
import sys, zipfile, glob
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd

BASE = Path(__file__).resolve().parent
RAW_ZIP = BASE / 'data' / '정보공개청구_17770333_.zip'
RAW_DIR = BASE / 'data' / 'happycall_raw'
OUT = BASE / 'data' / 'cheongju_happycall_2025-10_2026-10.csv'
_main_zip = BASE / 'data' / '교통분석_데이터.zip'
if _main_zip.exists() and not (BASE / 'data' / '교통분석_데이터').exists():
    zipfile.ZipFile(_main_zip).extractall(BASE / 'data')        # 격자 지도가 든 공모전 데이터 zip 풀기
GEO = next((p for p in [BASE / 'data' / '교통분석_데이터' / 'cheongju_grid_100m.geojson', BASE / 'data' / 'cheongju_grid_100m.geojson'] if p.exists()), None)

# 1) 원자료 풀기 (zip 안 한글 파일명이 cp949로 저장된 경우까지 처리)
if not RAW_DIR.exists() and RAW_ZIP.exists():
    RAW_DIR.mkdir(parents=True)
    with zipfile.ZipFile(RAW_ZIP) as z:
        for i in z.infolist():
            if i.is_dir() or not i.filename.lower().endswith('.xls'):
                continue
            name = i.filename if i.flag_bits & 0x800 else i.filename.encode('cp437').decode('cp949', 'ignore')
            (RAW_DIR / Path(name).name).write_bytes(z.read(i))
files = sorted(glob.glob(str(RAW_DIR / '*.xls')))
if not files or GEO is None:
    sys.exit('data/에 정보공개청구 zip과 격자 지도(geojson)를 넣어 주세요. data/README.md 참고')

# 2) 13개 파일 합치기 (각 파일 3행째가 머리글)
d = pd.concat([pd.read_excel(f, engine='calamine', header=2).assign(원본파일=Path(f).name) for f in files], ignore_index=True)
print(f'원자료 {len(files)}개 파일, {len(d):,}건')

# 3) 행정동 코드: 격자 지도의 행정동 경계 43개(ADM_CD, ADM_NM)
bnd = gpd.read_file(GEO)
bnd = bnd[bnd.ADM_CD.notna()]
code = dict(zip(bnd.ADM_NM, bnd.ADM_CD))
kind = {n: ('읍' if n.endswith('읍') else '면' if n.endswith('면') else '동') for n in code}

d = d.rename(columns={'예약/일반': '예약일반', '주중/주말': '주중주말', '운행거리(웹)': '운행거리_웹_m',
                      '픽업거리(m)': '픽업거리_m', '이동거리(m)': '이동거리_m',
                      '목적지 도시': '목적지도시', '목적지 시군구': '목적지시군구', '목적지 읍면동': '목적지읍면동'})
d['일자'] = pd.to_datetime(d['일자']).dt.normalize()
for p in ['출발', '목적지']:
    c, g, e = f'{p}도시', f'{p}시군구', f'{p}읍면동'
    m = d[c] == '충청북도'
    d.loc[m, c] = d.loc[m, g]                                  # '충청북도/충주시' → 도시=충주시
    d[c] = d[c].replace({'세종시': '세종특별자치시'})
    d[e] = d[e].str.replace('.', '·', regex=False).replace({'탑대성동': '탑·대성동'})   # 격자 지도 표기로 통일
    inc = d[c] == '청주시'
    d[f'{p}_ADM_CD'] = np.where(inc, d[e].map(code), None)
    d[f'{p}_읍면동구분'] = np.where(inc, d[e].map(kind), None)

# 4) 시각 → 분 단위 소요시간 (자정 넘김은 24시간 보정)
def mins(s):
    return s.map(lambda t: t.hour * 60 + t.minute + t.second / 60 if hasattr(t, 'hour') else np.nan)
T = {c: mins(d[f'{c}시간']) for c in ['접수', '배차', '승차', '하차']}
gap = lambda a, b: (T[b] - T[a]) % 1440
normal = d['예약일반'] == '일반'
d['배차소요_분'] = np.where(normal, gap('접수', '배차'), np.nan)
d['대기시간_분'] = np.where(normal, gap('접수', '승차'), np.nan)     # 일반 호출만 (예약은 접수일이 다름)
d['픽업소요_분'] = gap('배차', '승차')
d['탑승시간_분'] = gap('승차', '하차')
d['차량점유_분'] = gap('배차', '하차')
lim = {'배차소요_분': 360, '대기시간_분': 360, '픽업소요_분': 240, '탑승시간_분': 300, '차량점유_분': 480}
flag = pd.Series(False, index=d.index)
for c, l in lim.items():
    bad = d[c] > l; flag |= bad; d.loc[bad, c] = np.nan
d['시간이상치'] = flag
for c in lim:
    d[c] = d[c].round(1)
d['운행거리이상치'] = d['운행거리_웹_m'] > 300_000
d.loc[d['운행거리이상치'], '운행거리_웹_m'] = np.nan
d['이동거리_km'] = (d['이동거리_m'] / 1000).round(3)
d['픽업거리_km'] = (d['픽업거리_m'] / 1000).round(3)

# 5) 분석용 표시 열
d['운행완료'] = d['배차결과'].eq('고객하차')
d['취소'] = d['배차결과'].str.contains('취소|고객없음')
d['연월'] = d['일자'].dt.strftime('%Y-%m')
d['요일'] = d['일자'].dt.dayofweek.map(dict(enumerate('월화수목금토일')))
d['접수시'] = T['접수'].floordiv(60).astype(int)
d['시외운행'] = (d['출발도시'].notna() & d['출발도시'].ne('청주시')) | (d['목적지도시'].notna() & d['목적지도시'].ne('청주시'))
d['외곽출발'] = d['출발_읍면동구분'].isin(['읍', '면'])
d['중복의심'] = d.drop(columns='원본파일').duplicated(keep='first')
for c in ['접수', '배차', '승차', '하차']:
    d[f'{c}시간'] = d[f'{c}시간'].map(lambda t: t.strftime('%H:%M:%S') if hasattr(t, 'hour') else None)

d = d.sort_values(['일자', '접수시간']).reset_index(drop=True)
d.insert(0, '운행ID', np.arange(1, len(d) + 1))
cols = ['운행ID', '일자', '연월', '요일', '주중주말', '접수시', '차량종류', '예약일반', '배차결과', '운행완료', '취소',
        '접수시간', '배차시간', '승차시간', '하차시간', '배차소요_분', '대기시간_분', '픽업소요_분', '탑승시간_분', '차량점유_분',
        '픽업거리_m', '이동거리_m', '픽업거리_km', '이동거리_km', '운행거리_웹_m',
        '출발도시', '출발시군구', '출발읍면동', '출발_ADM_CD', '출발_읍면동구분', '외곽출발',
        '목적지도시', '목적지시군구', '목적지읍면동', '목적지_ADM_CD', '목적지_읍면동구분', '시외운행',
        '시간이상치', '운행거리이상치', '중복의심', '원본파일']
d[cols].to_csv(OUT, index=False, encoding='utf-8-sig', date_format='%Y-%m-%d')
print(f'저장: {OUT.relative_to(BASE)}  ({len(d):,}건, 완료 {int(d.운행완료.sum()):,}건, 이상치 {int(d.시간이상치.sum()):,}건, 중복 의심 {int(d.중복의심.sum()):,}건)')
