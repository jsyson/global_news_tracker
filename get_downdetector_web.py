# pip install selenium
# pip install webdriver-manager
# pip install undetected-chromedriver
# pip install selenium_stealth
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium_stealth import stealth
import pandas as pd
import sys
import logging
import re
import json
# import matplotlib.pyplot as plt


# 필드명
NAME = 'Name'
VALUES = "Values"
CLASS = "Class"
AREA = "Area"
CATEGORY = "Category"

# 클래스명
DANGER = "danger"
WARNING = 'warning'
SUCCESS = 'success'

# 카테고리명
TELECOM = 'telecom'
ONLINE_SERVICE = 'online-services'
SOCIAL_MEDIA = 'social-media'
FINANCE = 'finance'
GAMING = 'gaming'


# 로깅 설정
# logging.basicConfig(level=logging.INFO)


# # # # # # # # # # # # # # # # # # # #


logging.info('CHROME_DRIVER 초기화 시작')


@st.cache_resource
def get_driver():
    logging.info(f'{sys.platform=}')
    if sys.platform == 'win32' or sys.platform == 'darwin':
        # 윈도우 또는 맥일 경우
        new_driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options
        )
    else:
        # 리눅스 서버일 경우
        new_driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
            options=options,
        )

    stealth(new_driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

    return new_driver


# Selenium 설정
options = Options()
options.add_argument("start-maximized")
options.add_argument("--disable-gpu")
options.add_argument("--headless")
# options.add_argument("--headless=new")  # 최신 헤드리스 모드를 사용

options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# verify=False 관련 설정
options.add_argument('--ignore-certificate-errors')
options.add_argument('--disable-web-security')
options.add_argument('--allow-running-insecure-content')


# # # # # # # # # #
# 드라이버 초기화
# # # # # # # # # #


logging.info('CHROME_DRIVER 초기화 시작')
CHROME_DRIVER = get_driver()
logging.info('CHROME_DRIVER 초기화 완료')


# # # # # # # # # # # # # # # # # # # #


# 임팩트 클래스를 숫자 등급으로 변환
def get_impact_order(impact_class):
    if impact_class == DANGER:
        return 3
    elif impact_class == WARNING:
        return 2
    elif impact_class == SUCCESS:
        return 1
    else:
        return 0  # 예외 처리


# 다운디텍터 크롤링
@st.cache_data(show_spinner='서비스 상태 업데이트 중...')
def get_downdetector_df(url, area, service_name=None):
    global CHROME_DRIVER

    logging.info(f'다운디텍터 크롤링 시작 - {url} {area}')

    try:
        CHROME_DRIVER.get(url)
    except Exception as e:
        logging.error(f'크롬 get 에러 발생!!! - {url} - {area}')
        logging.error(f"{e}")

        logging.info('CHROME_DRIVER 초기화 시작')
        CHROME_DRIVER.quit()
        get_driver.clear()  # 캐시 삭제
        CHROME_DRIVER = get_driver()
        logging.info('CHROME_DRIVER 초기화 완료')

        logging.info('1회 재시도!!!')
        try:
            CHROME_DRIVER.get(url)
        except Exception as e:
            logging.error(f'재시도 get도 에러 발생!!! - {url} - {area}')
            logging.error(f"{e}")
            return None

    # 페이지 로딩 대기 (신규/기존 셀렉터 병합 대기)
    try:
        WebDriverWait(CHROME_DRIVER, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.block.h-full, .caption"))
        )
    except Exception as e:
        logging.warning(f"페이지 로딩 대기 타임아웃: {e}")

    logging.info(f'다운디텍터 데이터 추출 중... - {url} {area}')
    data = []

    # --- [STEP 0] 스크립트 영역 JSON 데이터 추출 (가장 정확하고 빠름) ---
    try:
        page_source = CHROME_DRIVER.page_source
        # Next.js의 스트리밍 데이터 구조에서 회사 정보 패턴 탐색
        company_pattern = r'{\\"__typename\\":\\"CompanyType\\",\\"id\\":\\"\d+\\",\\"name\\":\\"(.*?)\\",.*?\\"status\\":\\"(.*?)\\",\\"sparkline\\":\[(.*?)\].*?}'
        matches = re.finditer(company_pattern, page_source)
        
        for match in matches:
            name = match.group(1).replace('\\u0026', '&')
            status = match.group(2)
            sparkline_raw = match.group(3)
            
            # config.py의 split(', ')과 호환되도록 공백 추가
            sparkline_formatted = f"[{sparkline_raw.replace(',', ', ')}]"
            
            # 상태값 매핑
            impact_class = SUCCESS
            if status == 'danger': impact_class = DANGER
            elif status == 'warning': impact_class = WARNING
            
            data.append({NAME: name, VALUES: sparkline_formatted, CLASS: impact_class})
            
        if data:
            logging.info(f"JSON 스크립트 방식으로 {len(data)}개의 서비스 추출 성공")
    except Exception as e:
        logging.error(f"STEP 0 (JSON) 실패: {e}")

    # --- JSON 추출 실패 시 DOM 탐색 (STEP 1 & 2) ---
    if not data:
        elements = CHROME_DRIVER.find_elements(By.CSS_SELECTOR, "a.block.h-full, .caption")
        for service in elements:
            service_data = {NAME: "Unknown", VALUES: "", CLASS: SUCCESS}
            try:
                # --- [STEP 1] 신규 UI (2026년형) ---
                if "block" in service.get_attribute("class"):
                    name_el = service.find_element(By.TAG_NAME, "h2")
                    service_data[NAME] = name_el.text

                    info_container = service.find_element(By.CSS_SELECTOR, "div[role='img']")
                    status_text = info_container.get_attribute("aria-label").lower()
                    
                    # 차트 데이터 (SVG Path 대신 더미 리스트 저장 - config.py 호환용)
                    # 상세 데이터는 STEP 0 (JSON)에서 이미 추출됨.
                    service_data[VALUES] = "[0]"
                    
                    if "experiencing problems" in status_text:
                        service_data[CLASS] = DANGER
                    elif "possible problems" in status_text:
                        service_data[CLASS] = WARNING
                    else:
                        service_data[CLASS] = SUCCESS
                
                # --- [STEP 2] 기존 UI (Legacy) ---
                else:
                    name_el = service.find_element(By.TAG_NAME, "h5")
                    service_data[NAME] = name_el.text
                    sparkline = service.find_element(By.CLASS_NAME, "sparkline")
                    service_data[VALUES] = sparkline.get_attribute("data-values")
                    
                    sparkline_classes = sparkline.get_attribute("class").split()
                    for item in sparkline_classes:
                        if item in [DANGER, WARNING, SUCCESS]:
                            service_data[CLASS] = item
                            break
                
                data.append(service_data)
            except Exception:
                continue

    df_ = pd.DataFrame(data)
    if df_ is None or len(df_) == 0:
        logging.error(f"최종 추출된 데이터가 없음: {url}")
        return None

    # 중복 제거 (JSON과 DOM 방식이 섞였을 경우 대비)
    df_ = df_.drop_duplicates(subset=[NAME])

    df_sorted = df_.sort_values(by=CLASS, key=lambda x: x.map(get_impact_order), ascending=False)
    df_sorted = df_sorted.reset_index(drop=True)
    df_sorted[AREA] = area
    
    return df_sorted


# def make_plot(df_):
#     # 색상 매핑 딕셔너리
#     color_map = {DANGER: 'red', WARNING: 'orange', SUCCESS: 'green'}
#
#     # 서브플롯 그리기
#     fig, axs = plt.subplots(len(df_), figsize=(10, 8))
#
#     # 각 행에 대해 서브플롯 그리기
#     for i, row in df_.iterrows():
#         # 각 impact_class에 해당하는 색상 선택
#         color = color_map.get(row[CLASS], 'blue')  # 없는 경우 기본값으로 파란색 지정
#         data_values = [int(x) for x in row[VALUES].strip('[]').split(', ')]
#         axs[i].plot(data_values, color=color)  # 색상 적용
#         axs[i].set_title(row[NAME])
#
#     plt.tight_layout()
#     plt.show()


if __name__ == '__main__':
    # test code
    df = get_downdetector_df(url='https://downdetector.com/', area='US')
    if df is not None:
        df_sample = df.head(5).reset_index(drop=True)
        # make_plot(df_sample)
    # CHROME_DRIVER.quit()  # 테스트일 경우엔 종료해준다.
