import requests
import json

# 내부 API 엔드포인트 (실제는 개발자도구 > Network 탭에서 확인)
url = "https://www.g2b.go.kr/pn/pnp/pnpe/BidPbac/selectBidPbacScrollTypeList.do"  # 예시, 실제 URL 확인 필요

# 캡쳐한 payload
payload = {
    "dlBidPbancLstM": {
        "untyBidPbancNo": "",
        "bidPbancNo": "",
        "bidPbancOrd": "",
        "prcmBsneUntyNoOrd": "",
        "prcmBsneSeCd": "0000 조070001 조070002 조070003 조070004 조070005 민079999",
        "bidPbancNm": "",
        "pbancPstgDt": "",
        "ldocNoVal": "",
        "bidPrspPrce": "",
        "ctrtDmndRcptNo": "",
        "dmstcOvrsSeCd": "",
        "pbancKndCd": "공440002",
        "ctrtTyCd": "",
        "bidCtrtMthdCd": "",
        "scsbdMthdCd": "",
        "fromBidDt": "20250501",
        "toBidDt": "20250531",
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
        "cangParmVal": "",
        "currentPage": "",
        "recordCountPerPage": "10",
        "startIndex": 1,
        "endIndex": 10
    }
}

# 헤더 설정 (개발자도구에서 확인한 것과 동일하게 맞춰야 함)
headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest"
}

# 요청 보내기
response = requests.post(url, headers=headers, data=json.dumps(payload))

# 결과 출력
print("Status Code:", response.status_code)

# 응답이 JSON인 경우
try:
    data = response.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))
except ValueError:
    # JSON 파싱 실패 → HTML로 내려오는 경우
    print(response.text[:1000])  # 앞부분만 출력

