
# 완전한 Selenium 접근 방법
# pip install selenium 필요

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import json
import time
import pandas as pd

def get_g2b_data_selenium():
    """Selenium으로 나라장터 데이터 수집"""

    # Chrome 옵션 설정
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # 백그라운드 실행 (디버깅시 주석처리)
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        print("1. 나라장터 입찰공고 페이지 접속...")
        driver.get('https://www.g2b.go.kr/ep/tbid/tbidList.do')

        # 페이지 로딩 완료 대기
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "search_form"))
        )

        print("2. 검색 조건 설정...")

        # 검색어 입력 (예: 인공지능)
        try:
            search_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "bidPbancNm"))
            )
            search_input.clear()
            search_input.send_keys("인공지능")
            print("   검색어 입력 완료")
        except:
            print("   검색어 입력란을 찾을 수 없습니다.")

        # 날짜 설정
        try:
            from_date = driver.find_element(By.NAME, "fromBidDt")
            to_date = driver.find_element(By.NAME, "toBidDt")

            from_date.clear()
            from_date.send_keys("2024-12-01")

            to_date.clear()
            to_date.send_keys("2024-12-31")
            print("   날짜 설정 완료")
        except:
            print("   날짜 입력란을 찾을 수 없습니다.")

        # 검색 버튼 클릭
        try:
            search_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "btn_search"))
            )
            search_btn.click()
            print("3. 검색 실행...")

            # 결과 로딩 대기
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "search_result"))
            )

        except Exception as e:
            print(f"   검색 버튼 클릭 실패: {e}")
            return False

        print("4. 결과 데이터 추출...")

        # 결과 테이블에서 데이터 추출
        results = []
        try:
            # 결과 행들 찾기
            rows = driver.find_elements(By.CSS_SELECTOR, "table.search_result tbody tr")

            for i, row in enumerate(rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:  # 충분한 열이 있는 경우만
                        result_data = {
                            'index': i + 1,
                            'bid_name': cells[1].text.strip(),
                            'organization': cells[2].text.strip(),
                            'announcement_date': cells[3].text.strip(),
                            'bid_method': cells[4].text.strip(),
                            'status': cells[5].text.strip() if len(cells) > 5 else ''
                        }
                        results.append(result_data)

                        # 첫 번째 결과 미리보기
                        if i == 0:
                            print("   첫 번째 결과:")
                            for key, value in result_data.items():
                                print(f"     {key}: {value}")

                except Exception as e:
                    print(f"   행 {i+1} 처리 오류: {e}")
                    continue

            print(f"   총 {len(results)}개 결과 추출")

            # JSON 저장
            with open('g2b_selenium_results.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            # Excel 저장
            if results:
                df = pd.DataFrame(results)
                df.to_excel('g2b_selenium_results.xlsx', index=False)
                print("   결과를 Excel 파일로도 저장했습니다.")

            return len(results) > 0

        except Exception as e:
            print(f"   데이터 추출 오류: {e}")
            return False

    except Exception as e:
        print(f"Selenium 실행 오류: {e}")
        return False

    finally:
        print("5. 브라우저 종료...")
        driver.quit()

# 실행
if __name__ == "__main__":
    success = get_g2b_data_selenium()
    if success:
        print("\n✓ Selenium을 통한 데이터 수집 성공!")
    else:
        print("\n✗ 데이터 수집 실패")
