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
        self.base_url = "http://apis.data.go.kr/1230000/ao/PubDataOpnStdService"
        self.operation_name = "getDataSetOpnStdBidPblancInfo"
        self.url = f"{self.base_url}/{self.operation_name}"
        self.service_key = service_key
        self.rows_per_page = 999  # 한 번에 가져올 최대 데이터 수
    
    def _make_request(self, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        API 요청을 보내고 응답을 반환
        
        Args:
            params (Dict[str, str]): API 요청 파라미터
            
        Returns:
            Optional[Dict[str, Any]]: API 응답 데이터 또는 None
        """
        try:
            response = requests.get(self.url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['response']['header']['resultCode'] != '00':
                raise Exception(f"API 오류: {data['response']['header']['resultMsg']}")
            
            return data
        except requests.exceptions.RequestException as e:
            print(f"API 호출 중 오류가 발생했습니다: {e}")
            return None
        except json.JSONDecodeError:
            print("JSON 형식으로 변환할 수 없습니다.")
            return None
    
    def fetch_all_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        지정된 기간의 모든 입찰 공고 데이터를 가져옴
        
        Args:
            start_date (str): 시작일 (YYYYMMDDHHMM 형식)
            end_date (str): 종료일 (YYYYMMDDHHMM 형식)
            
        Returns:
            List[Dict[str, Any]]: 전체 입찰 공고 데이터 리스트
        """
        all_results = []
        
        # 첫 번째 페이지 파라미터 설정
        params = {
            'numOfRows': str(self.rows_per_page),
            'pageNo': '1',
            'ServiceKey': self.service_key,
            'type': 'json',
            'bidNtceBgnDt': start_date,
            'bidNtceEndDt': end_date
        }
        
        print("첫 번째 페이지 데이터를 요청합니다...")
        first_page_data = self._make_request(params)
        
        if not first_page_data:
            return all_results
        
        # 전체 결과 수와 페이지 수 계산
        total_count = int(first_page_data['response']['body']['totalCount'])
        num_of_rows = int(first_page_data['response']['body']['numOfRows'])
        
        if total_count == 0:
            print("해당 기간에 조회된 입찰 공고 데이터가 없습니다.")
            return all_results
        
        # 첫 페이지 결과 저장
        if 'items' in first_page_data['response']['body'] and first_page_data['response']['body']['items']:
            items = first_page_data['response']['body']['items']
            all_results.extend(items)
            
            # 데이터 구조 디버깅 - 처음 3개 항목의 모든 필드 출력
            print("\n=== 데이터 구조 디버깅 ===")
            for i, item in enumerate(items[:3]):
                print(f"\n--- 데이터 {i+1} ---")
                for key, value in item.items():
                    print(f"{key}: {value}")
                print("-" * 50)
        
        
        # 전체 페이지 수 계산
        total_pages = math.ceil(total_count / num_of_rows)
        print(f"전체 데이터: {total_count}건, 전체 페이지: {total_pages}페이지")
        
        # 나머지 페이지 데이터 수집
        for page in range(2, total_pages + 1):
            params['pageNo'] = str(page)
            print(f"{page}/{total_pages} 페이지 데이터를 요청합니다...")
            
            page_data = self._make_request(params)
            if page_data and 'items' in page_data['response']['body']:
                all_results.extend(page_data['response']['body']['items'])
            else:
                print(f"{page} 페이지 로딩 중 문제 발생")
        
        print(f"총 {len(all_results)}개의 데이터를 수집했습니다.")
        return all_results

class BidDataFilter:
    """입찰 데이터 필터링 클래스"""
    
    @staticmethod
    def filter_by_keywords(data: List[Dict[str, Any]], 
                          keywords: List[str], 
                          target_field: str = 'bidNtceNm') -> List[Dict[str, Any]]:
        """
        여러 키워드 중 하나라도 포함된 데이터를 필터링
        
        Args:
            data (List[Dict[str, Any]]): 필터링할 데이터 리스트
            keywords (List[str]): 검색할 키워드 리스트
            target_field (str): 검색 대상 필드명
            
        Returns:
            List[Dict[str, Any]]: 필터링된 데이터 리스트
        """
        filtered_results = []
        empty_count = 0
        none_count = 0
        
        print(f"🔍 총 {len(data)}건의 데이터에서 키워드 검색 중...")
        print(f"검색 키워드: {keywords}")
        print(f"검색 대상 필드: {target_field}")
        
        for i, item in enumerate(data):
            # 검색 대상 필드값 확인
            target_value = item.get(target_field)
            
            if target_value is None:
                none_count += 1
                target_text = ""
            elif target_value == "":
                empty_count += 1
                target_text = ""
            else:
                target_text = str(target_value)
            
            # 모든 항목에 대해 상세 정보 출력 (처음 10개만)
            if i < 10:
                print(f"\n--- 데이터 {i+1} ---")
                print(f"원본 값: {repr(target_value)}")  # repr로 정확한 값 표시
                print(f"변환된 텍스트: '{target_text}'")
                
                # 항목의 모든 필드 출력
                for key, value in item.items():
                    print(f"  {key}: {repr(value)}")
                print("-" * 80)
            
            # 빈 값이면 스킵
            if not target_text.strip():
                continue
            
            # 텍스트 정규화 (공백 제거, 소문자 변환)
            normalized_text = target_text.replace(' ', '').replace('\t', '').replace('\n', '').lower()
            
            # 여러 키워드 중 하나라도 포함되는지 확인
            for keyword in keywords:
                # 키워드도 동일하게 정규화
                normalized_keyword = keyword.replace(' ', '').replace('\t', '').replace('\n', '').lower()
                
                # 원본 텍스트와 정규화된 텍스트 모두에서 검색
                if (normalized_keyword in normalized_text or 
                    keyword.lower() in target_text.lower()):
                    
                    # 매칭된 키워드 정보 추가
                    item_copy = item.copy()
                    item_copy['matched_keyword'] = keyword
                    item_copy['original_text'] = target_text  # 디버깅용
                    filtered_results.append(item_copy)
                    print(f"✅ 매칭됨: [{keyword}] {target_text}")
                    break  # 첫 번째 매칭 키워드만 기록하고 중복 방지
        
        # 결과 요약 출력
        print(f"\n📊 필터링 결과 요약:")
        print(f"  - 전체 데이터: {len(data)}건")
        print(f"  - None 값: {none_count}건")
        print(f"  - 빈 문자열: {empty_count}건")
        print(f"  - 필터링된 결과: {len(filtered_results)}건")
        
        return filtered_results
    
    @staticmethod
    def get_keyword_statistics(filtered_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        키워드별 매칭 통계 생성
        
        Args:
            filtered_data (List[Dict[str, Any]]): 필터링된 데이터
            
        Returns:
            Dict[str, int]: 키워드별 매칭 건수
        """
        keyword_stats = {}
        for item in filtered_data:
            keyword = item.get('matched_keyword', 'Unknown')
            keyword_stats[keyword] = keyword_stats.get(keyword, 0) + 1
        return keyword_stats

class ExcelExporter:
    """엑셀 파일 내보내기 클래스"""
    
    def __init__(self):
        """엑셀 내보내기 클래스 초기화"""
        pass
    
    def save_to_excel(self, 
                     filtered_data: List[Dict[str, Any]], 
                     filename: Optional[str] = None,
                     include_statistics: bool = True) -> bool:
        """
        필터링된 데이터를 엑셀 파일로 저장
        
        Args:
            filtered_data (List[Dict[str, Any]]): 저장할 데이터
            filename (Optional[str]): 파일명 (None시 자동 생성)
            include_statistics (bool): 통계 시트 포함 여부
            
        Returns:
            bool: 저장 성공 여부
        """
        if not filtered_data:
            print("저장할 데이터가 없습니다.")
            return False
        
        # 파일명 생성 및 중복 처리
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"나라장터_필터결과_{timestamp}.xlsx"
        
        # 파일명 중복 시 번호 추가
        original_filename = filename
        counter = 1
        while os.path.exists(filename):
            name, ext = os.path.splitext(original_filename)
            filename = f"{name}_{counter}{ext}"
            counter += 1
        
        # 저장 경로 확인 및 생성
        save_dir = os.path.dirname(filename) if os.path.dirname(filename) else "."
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception as e:
                print(f"디렉토리 생성 실패: {e}")
                # 현재 디렉토리에 저장 시도
                filename = os.path.basename(filename)
        
        try:
            # DataFrame 생성
            df = pd.DataFrame(filtered_data)
            
            # 주요 컬럼 순서 정렬
            important_cols = ['bidNtceNm', 'ntceInsttNm', 'dminsttNm', 'bidNtceDt', 'bidNtceUrl', 'matched_keyword']
            other_cols = [col for col in df.columns if col not in important_cols]
            column_order = [col for col in important_cols if col in df.columns] + other_cols
            df = df[column_order]
            
            # ExcelWriter로 멀티시트 저장
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # 메인 데이터 시트
                df.to_excel(writer, sheet_name='필터링_결과', index=False)
                
                # 통계 시트 (옵션)
                if include_statistics:
                    keyword_stats = BidDataFilter.get_keyword_statistics(filtered_data)
                    stats_df = pd.DataFrame(list(keyword_stats.items()), 
                                          columns=['키워드', '매칭건수'])
                    stats_df['비율(%)'] = round((stats_df['매칭건수'] / len(filtered_data)) * 100, 2)
                    stats_df.to_excel(writer, sheet_name='키워드_통계', index=False)
                
                # 워크시트 스타일링
                workbook = writer.book
                for sheet_name in workbook.sheetnames:
                    worksheet = workbook[sheet_name]
                    
                    # 헤더 스타일 적용
                    for cell in worksheet[1]:
                        cell.font = cell.font.copy(bold=True)
                    
                    # 컬럼 너비 자동 조정
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            print(f"✅ 엑셀 파일 저장 완료: {filename}")
            print(f"📊 저장된 데이터 개수: {len(filtered_data)}건")
            
            # 키워드별 통계 출력
            if include_statistics:
                keyword_stats = BidDataFilter.get_keyword_statistics(filtered_data)
                print("\n📈 키워드별 매칭 건수:")
                for keyword, count in keyword_stats.items():
                    print(f"  - {keyword}: {count}건")
            
            return True
            
        except Exception as e:
            print(f"❌ 엑셀 파일 저장 실패: {e}")
            return False

class NarajangterAnalyzer:
    """나라장터 데이터 분석 메인 클래스"""
    
    def __init__(self, service_key: str):
        """
        분석기 초기화
        
        Args:
            service_key (str): 공공데이터포털 서비스 키
        """
        self.api_client = NarajangterAPIClient(service_key)
        self.filter = BidDataFilter()
        self.excel_exporter = ExcelExporter()
    
    def analyze_and_export(self, 
                          start_date: str, 
                          end_date: str, 
                          keywords: List[str],
                          output_filename: Optional[str] = None) -> bool:
        """
        데이터 수집 -> 필터링 -> 엑셀 저장까지 전체 프로세스 실행
        
        Args:
            start_date (str): 검색 시작일 (YYYYMMDDHHMM)
            end_date (str): 검색 종료일 (YYYYMMDDHHMM)
            keywords (List[str]): 검색 키워드 리스트
            output_filename (Optional[str]): 출력 파일명
            
        Returns:
            bool: 전체 프로세스 성공 여부
        """
        try:
            print("=== 나라장터 입찰 공고 데이터 분석 시작 ===")
            print(f"검색 기간: {start_date} ~ {end_date}")
            print(f"검색 키워드: {', '.join(keywords)}")
            print()
            
            # 1. 전체 데이터 수집
            print("📡 데이터 수집 중...")
            all_data = self.api_client.fetch_all_data(start_date, end_date)
            
            if not all_data:
                print("❌ 데이터를 가져올 수 없습니다.")
                return False
            
            print(f"✅ 총 {len(all_data)}건의 데이터를 수집했습니다.")
            
            # 2. 키워드 필터링
            print("\n🔍 키워드 필터링 중...")
            
            if not keywords:
                print("⚠️  키워드가 비어있음 - 모든 데이터 반환 (디버깅 모드)")
                filtered_data = all_data
                # 디버깅용으로 matched_keyword 추가
                for item in filtered_data:
                    item['matched_keyword'] = 'ALL_DATA'
            else:
                filtered_data = self.filter.filter_by_keywords(all_data, keywords)
            
            if not filtered_data:
                print("❌ 검색 키워드에 해당하는 데이터가 없습니다.")
                return False
            
            print(f"✅ {len(filtered_data)}건의 데이터가 필터링되었습니다.")
            
            # 3. 결과 미리보기
            print("\n📋 필터링 결과 미리보기 (최대 5건):")
            for i, item in enumerate(filtered_data[:5]):
                title = item.get('bidNtceNm', 'N/A')
                keyword = item.get('matched_keyword', 'N/A')
                print(f"  {i+1}. [{keyword}] {title}")
            
            if len(filtered_data) > 5:
                print(f"  ... 외 {len(filtered_data) - 5}건")
            
            # 4. 엑셀 파일로 저장
            print("\n💾 엑셀 파일 저장 중...")
            success = self.excel_exporter.save_to_excel(filtered_data, output_filename)
            
            if success:
                print("\n🎉 전체 프로세스가 성공적으로 완료되었습니다!")
                return True
            else:
                print("\n❌ 엑셀 저장 중 문제가 발생했습니다.")
                return False
                
        except Exception as e:
            print(f"❌ 분석 중 오류 발생: {e}")
            return False

def main():
    """메인 실행 함수"""
    # 설정 값들
    SERVICE_KEY = "qPYIYI7lUydoOKfx4lfTj1Bddm3sLaMp0/sbhMz/b9aWP89T9aZZaBsIzd9yapSE/5fyXGO8Q2mpdzBlEGYj+Q=="
    START_DATE = "202505140000"
    END_DATE = "202505142359"
    
    # 여러 키워드 설정 (하나라도 포함되면 검색됨)
    # 디버깅을 위해 빈 리스트로 설정 (모든 데이터 확인)
    SEARCH_KEYWORDS = []  # 모든 데이터를 보고 싶으면 빈 리스트
    # SEARCH_KEYWORDS = ["이전가격", "세무", "회계", "재무", "세금", "부가세"]  # 실제 검색시
    
    # 분석기 생성 및 실행
    analyzer = NarajangterAnalyzer(SERVICE_KEY)
    
    result = analyzer.analyze_and_export(
        start_date=START_DATE,
        end_date=END_DATE,
        keywords=SEARCH_KEYWORDS,
        output_filename="나라장터_세무회계_검색결과.xlsx"
    )
    
    if result:
        print("\n✨ 프로그램이 성공적으로 완료되었습니다.")
    else:
        print("\n💥 프로그램 실행 중 문제가 발생했습니다.")

if __name__ == "__main__":
    main()