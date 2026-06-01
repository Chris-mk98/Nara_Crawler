import requests
import json
import math
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
import os


class NarajangterAPIClient:
    """나라장터 API 클라이언트 클래스"""

    def __init__(self, service_key: str):
        """
        API 클라이언트 초기화
        Args:
            service_key (str): 공공데이터포털에서 발급받은 서비스 키
        """
        self.base_url = "http://apis.data.go.kr/1230000/eo/BidPublicInfoService"
        self.operation_name = "getBidPblancListInfoThng"  # 표준입찰공고조회
        self.url = f"{self.base_url}/{self.operation_name}"
        self.service_key = service_key
        self.rows_per_page = 999

    def _make_request(self, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        API 요청을 보내고 응답을 반환
        """
        try:
            response = requests.get(self.url, params=params)
            response.raise_for_status()
            data = response.json()

            if data['response']['header']['resultCode'] != '00':
                raise Exception(f"API 오류: {data['response']['header']['resultMsg']}")

            return data
        except Exception as e:
            print(f"API 호출 오류: {e}")
            return None

    def fetch_all_data(
        self,
        start_date: str,
        end_date: str,
        region: Optional[str] = None,     # 지역 코드
        industry: Optional[str] = None,   # 업종 코드
        bid_type: Optional[str] = None    # 공고종류 코드
    ) -> List[Dict[str, Any]]:
        """조건에 맞는 모든 입찰공고 조회"""
        all_results = []

        # 기본 파라미터
        params = {
            'ServiceKey': self.service_key,
            'pageNo': '1',
            'numOfRows': str(self.rows_per_page),
            'type': 'json',
            'bidNtceBgnDt': start_date,
            'bidNtceEndDt': end_date
        }

        # 조건 추가
        if region:
            params['prtcptLmtRegionCd'] = region
        if industry:
            params['indstrytyLmtCd'] = industry
        if bid_type:
            params['bidClseDivCd'] = bid_type

        print("첫 페이지 요청...")
        first_page_data = self._make_request(params)
        if not first_page_data:
            return all_results

        total_count = int(first_page_data['response']['body']['totalCount'])
        num_of_rows = int(first_page_data['response']['body']['numOfRows'])
        total_pages = math.ceil(total_count / num_of_rows)

        if 'items' in first_page_data['response']['body']:
            all_results.extend(first_page_data['response']['body']['items'])

        print(f"총 {total_count}건, {total_pages} 페이지")

        # 나머지 페이지 반복
        for page in range(2, total_pages + 1):
            params['pageNo'] = str(page)
            page_data = self._make_request(params)
            if page_data and 'items' in page_data['response']['body']:
                all_results.extend(page_data['response']['body']['items'])
            else:
                print(f"{page} 페이지 로딩 중 문제 발생")

        return all_results


class BidDataFilter:
    """입찰 데이터 필터링"""

    @staticmethod
    def filter_by_keywords(
        data: List[Dict[str, Any]],
        keywords: List[str],
        target_field: str = 'bidNtceNm'
    ) -> List[Dict[str, Any]]:
        """키워드 포함 데이터만 필터링"""
        filtered_results = []

        for item in data:
            target_text = str(item.get(target_field, "")).lower()
            for keyword in keywords:
                if keyword.lower() in target_text:
                    item_copy = item.copy()
                    item_copy['matched_keyword'] = keyword
                    filtered_results.append(item_copy)
                    break
        return filtered_results

    @staticmethod
    def get_keyword_statistics(filtered_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """키워드별 매칭 통계"""
        stats = {}
        for item in filtered_data:
            kw = item.get('matched_keyword', 'Unknown')
            stats[kw] = stats.get(kw, 0) + 1
        return stats


class ExcelExporter:
    """엑셀 내보내기"""

    def save_to_excel(
        self,
        filtered_data: List[Dict[str, Any]],
        filename: Optional[str] = None,
        include_statistics: bool = True
    ) -> bool:
        if not filtered_data:
            print("저장할 데이터 없음")
            return False

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"나라장터_검색결과_{timestamp}.xlsx"

        df = pd.DataFrame(filtered_data)

        important_cols = ['bidNtceNm', 'ntceInsttNm', 'dminsttNm',
                          'bidNtceDt', 'bidNtceUrl', 'matched_keyword']
        other_cols = [c for c in df.columns if c not in important_cols]
        df = df[[c for c in important_cols if c in df.columns] + other_cols]

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="검색결과", index=False)

            if include_statistics:
                stats = BidDataFilter.get_keyword_statistics(filtered_data)
                stats_df = pd.DataFrame(list(stats.items()), columns=['키워드', '매칭건수'])
                stats_df.to_excel(writer, sheet_name="통계", index=False)

        print(f"엑셀 저장 완료: {filename}")
        return True


class NarajangterAnalyzer:
    """나라장터 분석기"""

    def __init__(self, service_key: str):
        self.api_client = NarajangterAPIClient(service_key)
        self.filter = BidDataFilter()
        self.excel = ExcelExporter()

    def analyze_and_export(
        self,
        start_date: str,
        end_date: str,
        keywords: List[str],
        region: Optional[str] = None,
        industry: Optional[str] = None,
        bid_type: Optional[str] = None,
        output_filename: Optional[str] = None
    ) -> bool:
        print(f"=== 검색: {start_date} ~ {end_date}, 키워드={keywords} ===")

        all_data = self.api_client.fetch_all_data(
            start_date, end_date, region, industry, bid_type
        )
        print(f"수집: {len(all_data)}건")

        if not all_data:
            return False

        filtered_data = self.filter.filter_by_keywords(all_data, keywords) if keywords else all_data
        print(f"필터링 후: {len(filtered_data)}건")

        return self.excel.save_to_excel(filtered_data, output_filename)


def main():
    SERVICE_KEY = "여기에_본인_서비스키_입력"
    START_DATE = "202509180000"
    END_DATE = "202509182359"

    SEARCH_KEYWORDS = ["세무", "회계", "재무"]

    analyzer = NarajangterAnalyzer(SERVICE_KEY)
    analyzer.analyze_and_export(
        start_date=START_DATE,
        end_date=END_DATE,
        keywords=SEARCH_KEYWORDS,
        region=None,      # 예: "서울"
        industry=None,    # 업종코드
        bid_type=None,    # 예: "공사", "용역", "물품"
        output_filename="나라장터_검색결과.xlsx"
    )


if __name__ == "__main__":
    main()
