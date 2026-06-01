# Nara_Crawler

나라장터(G2B) 입찰공고 리스트를 수집하는 크롤러입니다.

---

## G2B 작동 구조

나라장터(g2b.go.kr)는 SPA 구조로, 화면의 검색 결과는 내부 JSON API를 호출해 렌더링됩니다.  
이 크롤러는 브라우저가 하는 것과 동일한 요청 흐름을 코드로 재현합니다.

### 핵심 엔드포인트

| 역할 | 메서드 | URL |
|------|--------|-----|
| 세션 발급 | POST | `/co/coz/coza/util/getSession.do` |
| 공고 목록 조회 | POST | `/pn/pnp/pnpe/BidPbac/selectBidPbacScrollTypeList.do` |
| **Excel 다운로드** | POST | `/pn/pnp/pnpe/BidPbac/selectBidPbacListExcel.do` |

> Excel 다운로드 엔드포인트는 G2B 화면의 "Excel 다운로드" 버튼이 실제로 호출하는 URL과 동일합니다.  
> 조건에 맞는 전체 결과를 한 번에 받아올 수 있어 페이지네이션 없이 완전한 데이터를 수집합니다.

---

## 세션 메커니즘

G2B는 내부 API 호출 전에 반드시 세션이 있어야 합니다.  
세션 없이 Excel 엔드포인트를 직접 호출하면 빈 응답 또는 오류를 반환합니다.

```
[클라이언트]
    │
    ├─ POST /getSession.do  ──────────────────→  [G2B 서버]
    │       ← 200 OK (쿠키 세션 발급)                │
    │                                               │ 세션 유지
    ├─ POST /selectBidPbacListExcel.do ──────────→  │
    │       ← 200 OK (binary: .xlsx 파일)           │
    │
[파일 저장]
```

`requests.Session()`을 사용해 쿠키를 자동으로 유지하므로,  
한 번 발급된 세션은 이후 요청에 자동으로 포함됩니다.

---

## 요청 페이로드 구조

Excel 다운로드 요청 시 `dlBidPbancLstM` 객체에 검색 조건을 담아 전송합니다.

```json
{
  "dlBidPbancLstM": {
    "bidPbancNm": "소프트웨어",       // 공고명 검색어 (핵심)
    "fromBidDt": "20250501",          // 공고게시일 시작 (YYYYMMDD)
    "toBidDt":   "20250531",          // 공고게시일 종료 (YYYYMMDD)
    "bidDateType": "R",               // R = 공고게시일 기준
    "pbancKndCd": "공440002",         // 공고종류: 용역
    "prcmBsneSeCd": "0000 조070001 조070002 조070003 조070004 조070005 민079999",
    "bsneAllYn": "Y",                 // 전체 사업 포함
    "frcpYn": "Y",                    // 소기업 포함
    "rsrvYn": "Y",                    // 예약구매 포함
    "laseYn": "Y",                    // 리스 포함
    "infoSysCd": "정010029",          // 시스템 식별 코드 (고정값)
    "contxtSeCd": "콘010006",         // 컨텍스트 코드 (고정값)
    "cangParmVal": "untySrch001",     // 통합검색 모드 (고정값)
    "srchTy": "0"                     // 검색 타입 (고정값)
  }
}
```

> `infoSysCd`, `contxtSeCd`, `cangParmVal` 등 고정값은 G2B 프론트엔드가 항상 함께 전송하는 값으로,  
> 브라우저 개발자도구 Network 탭에서 확인할 수 있습니다.

---

## 전체 실행 흐름 (web_crawler.py)

```
[nara_keyword_date.xlsx]
    │  검색 기간 (C2: 시작일, C3: 종료일)
    │  키워드 목록 (B6 이하)
    ▼
read_search_conditions()
    │
    ▼ 키워드별 반복
┌─────────────────────────────────┐
│  get_session()                  │
│    └─ POST /getSession.do       │
│                                 │
│  download_excel_by_keyword()    │
│    └─ POST /selectBidPbacListExcel.do │
│    └─ 임시 파일 저장 (temp_*.xlsx)    │
└─────────────────────────────────┘
    │  키워드 수만큼 임시 파일 생성
    ▼
merge_excel_files()
    ├─ 첫 번째 파일에서 원본 스타일(A1:H5) 보존
    ├─ 전체 파일 데이터 병합
    ├─ 입찰공고번호(D열) 기준 중복 제거
    ├─ 테두리 및 열 너비 자동 조정
    └─ 검색조건 메모 시트 추가
    │
    ▼
나라장터_입찰공고_{시작일}_{종료일}_{저장시각}.xlsx
```

> 키워드마다 새 세션을 발급하는 이유:  
> 하나의 세션으로 연속 요청 시 G2B 서버에서 세션을 만료시키는 경우가 있어 안정성을 위해 매번 재발급합니다.

---

## 설치

```bash
pip install -r requirements.txt
```

---

## 실행

### 검색 조건 파일 준비

`nara_keyword_date.xlsx`를 프로젝트 루트에 생성합니다.

| 셀 | 내용 |
|----|------|
| C2 | 검색 시작일 (예: `20250501`) |
| C3 | 검색 종료일 (예: `20250531`) |
| B6~ | 키워드 목록 (한 행에 하나씩) |

### 실행

```bash
python src/web_crawler.py
```

결과 파일은 실행 위치에 `나라장터_입찰공고_{시작일}_{종료일}_{저장시각}.xlsx`로 저장됩니다.

---

## 실행 파일 빌드 (Windows)

비개발자 환경에서 Python 없이 실행할 수 있도록 단일 .exe로 패키징합니다.

```bash
pyinstaller nara_excel_post.spec
```

빌드 결과물은 `dist/` 폴더에 생성됩니다.

---

## 프로젝트 구조

```
Nara_Crawler/
├── src/
│   └── web_crawler.py          # G2B 세션 + Excel 다운로드
├── legacy/                     # 개발 과정 참고용 스크립트
│   ├── post_crawl_poc.py       # 내부 API 직접 호출 실험 코드
│   └── session_example.py      # 단일 키워드 최소 동작 예제
├── notebooks/                  # Jupyter 노트북
├── samples/                    # 샘플 데이터
├── output/                     # 크롤링 결과물 (git 미포함)
└── nara_excel_post.spec        # PyInstaller 빌드 설정
```
