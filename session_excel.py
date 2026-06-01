import requests
import json

# ==========================
# 1️⃣ 세션 생성
# ==========================
session = requests.Session()
base_url = "https://www.g2b.go.kr"

# 세션 발급 요청 (getSession.do)
session_headers = {
    "Accept": "application/json",
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": "https://www.g2b.go.kr/",
    "Origin": "https://www.g2b.go.kr",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
}

print("⏳ 세션 발급 중...")
session_response = session.post(f"{base_url}/co/coz/coza/util/getSession.do", headers=session_headers)
if session_response.status_code == 200:
    print("✅ 세션 발급 성공")
else:
    print("❌ 세션 발급 실패:", session_response.status_code)
    exit(1)

# ==========================
# 2️⃣ Excel 다운로드 요청
# ==========================
excel_url = f"{base_url}/pn/pnp/pnpe/BidPbac/selectBidPbacListExcel.do"

payload = {
    "dlBidPbancLstM": {
        "untyBidPbancNo": "",
        "bidPbancNo": "",
        "bidPbancOrd": "",
        "prcmBsneUntyNoOrd": "",
        "prcmBsneSeCd": "0000 조070001 조070002 조070003 조070004 조070005 민079999",
        "bidPbancNm": "이전가격", ## 검색단어
        "pbancPstgDt": "",
        "ldocNoVal": "",
        "bidPrspPrce": "",
        "ctrtDmndRcptNo": "",
        "dmstcOvrsSeCd": "",
        "pbancKndCd": "공440002",
        "ctrtTyCd": "",
        "bidCtrtMthdCd": "",
        "scsbdMthdCd": "",
        "fromBidDt": "20250514", ## 공고게시일자 기준 시작일자
        "toBidDt": "20250515", ## 공고게시일자 기준 종료일자
        "minBidPrspPrce": "",
        "maxBidPrspPrce": "",
        "bsneAllYn": "Y",
        "frcpYn": "Y",
        "rsrvYn": "Y",
        "laseYn": "Y",
        "untyGrpGb": "",
        "dmstNm": "",
        "pbancPicNm": "",
        "odnLmtLgdngCd": "",
        "odnLmtLgdngNm": "",
        "intpCd": "",
        "intpNm": "",
        "dtlsPrnmNo": "",
        "dtlsPrnmNm": "",
        "slprRcptDdlnYn": "",
        "lcrtTyCd": "",
        "isMas": "",
        "isElpdt": "",
        "oderInstUntyGrpNo": "",
        "instSearchRangeYn": "",
        "esdacYn": "",
        "infoSysCd": "정010029",
        "contxtSeCd": "콘010006",
        "bidDateType": "R",
        "brcoOrgnCd": "",
        "deptOrgnCd": "",
        "isShop": "",
        "srchTy": "0",
        "cangParmVal": "untySrch001",
        "currentPage": "",
        "recordCountPerPage": "10",
        "startIndex": 1,
        "endIndex": 10,
        "excelHeaderText": ""
    }
}

excel_headers = {
    "Accept": "*/*",
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": "https://www.g2b.go.kr/",
    "Origin": "https://www.g2b.go.kr",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
}

print("⏳ Excel 다운로드 중...")
response = session.post(excel_url, headers=excel_headers, json=payload)

if response.status_code == 200:
    with open("bid_list.xlsx", "wb") as f:
        f.write(response.content)
    print("✅ Excel 파일 저장 완료: bid_list.xlsx")
else:
    print("❌ Excel 다운로드 실패:", response.status_code)
    print(response.text)
