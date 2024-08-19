# pip install selenium
# pip install webdriver-manager
# pip install undetected-chromedriver
# pip install selenium_stealth

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
import pandas as pd
import logging
import matplotlib.pyplot as plt


# 필드명
NAME = 'Name'
VALUES = "Values"
CLASS = "Class"
AREA = "Area"

# 클래스명
DANGER = "danger"
WARNING = 'warning'
SUCCESS = 'success'

# 로깅 설정
logging.basicConfig(level=logging.INFO)


# # # # # # # # # # # # # # # # # # # #

logging.info('CHROME_DRIVER 초기화 시작')

# Selenium 설정
options = Options()
# options.add_argument("--headless")
options.add_argument("start-maximized")
options.add_argument("--headless")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# verify=False 관련 설정
options.add_argument('--ignore-certificate-errors')
options.add_argument('--disable-web-security')
options.add_argument('--allow-running-insecure-content')

# 드라이버 설정
CHROME_DRIVER = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

stealth(CHROME_DRIVER,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )

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
def get_downdetector_df(url, area, service_name=None):
    logging.info(f'다운디텍터 크롤링 시작 - {url} {area}')

    # if service_name:
    # https://downdetector.com/status/{service_name}/

    CHROME_DRIVER.get(url)

    # 페이지 로딩 대기
    WebDriverWait(CHROME_DRIVER, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".caption")))

    logging.info(f'다운디텍터 크롤링 완료 - {url} {area}')

    # 서비스명, data-values, 영향도 클래스 추출
    services = CHROME_DRIVER.find_elements(By.CSS_SELECTOR, ".caption")
    data = []

    for service in services:
        try:
            name = service.find_element(By.TAG_NAME, "h5").text
            data_values = service.find_element(By.CLASS_NAME, "sparkline").get_attribute("data-values")
            sparkline_classes = service.find_element(By.CLASS_NAME, "sparkline").get_attribute("class").split()
            impact_class = SUCCESS
            for item in sparkline_classes:
                if item in [DANGER, WARNING, SUCCESS]:
                    impact_class = item
                    break

            data.append({NAME: name, VALUES: data_values, CLASS: impact_class})

        except Exception as e:
            logging.error(f"Error extracting data for a service: {e}\n{url} - {area}")

    # 브라우저 종료
    # driver.quit()

    df_ = pd.DataFrame(data)
    df_sorted = df_.sort_values(by=CLASS, key=lambda x: x.map(get_impact_order), ascending=False)
    df_sorted = df_sorted.reset_index(drop=True)
    df_sorted[AREA] = area  # 지역 컬럼 추가

    # for debug
    logging.info(str(df_sorted))

    # log_str = f'\n---------- {url} ----------\n'
    # for i, row in df_sorted.iterrows():
    #     log_str += f'{row[NAME]}\t{row[AREA]}\t{row[CLASS]}\t{row[VALUES]}\n'
    # log_str += '------------------------------\n\n'
    # logging.info(log_str)

    return df_sorted


def make_plot(df_):
    # 색상 매핑 딕셔너리
    color_map = {DANGER: 'red', WARNING: 'orange', SUCCESS: 'green'}

    # 서브플롯 그리기
    fig, axs = plt.subplots(len(df_), figsize=(10, 8))

    # 각 행에 대해 서브플롯 그리기
    for i, row in df_.iterrows():
        # 각 impact_class에 해당하는 색상 선택
        color = color_map.get(row[CLASS], 'blue')  # 없는 경우 기본값으로 파란색 지정
        data_values = [int(x) for x in row[VALUES].strip('[]').split(', ')]
        axs[i].plot(data_values, color=color)  # 색상 적용
        axs[i].set_title(row[NAME])

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    # test code
    df = get_downdetector_df(url='https://downdetector.com/telecom/', area='US')
    df_sample = df.head(5).reset_index(drop=True)
    make_plot(df_sample)
    CHROME_DRIVER.quit()  # 테스트일 경우엔 종료해준다.

