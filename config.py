import os
import logging
import pickle
import streamlit as st
import time
import pandas as pd
from datetime import datetime
import pytz
import feedparser
import requests
import re


import threading


# 한국 시간대를 사용하여 시간 생성
class KSTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        kst = pytz.timezone('Asia/Seoul')
        # record.created를 변경하지 않고, 변환된 시간을 생성
        created_time = datetime.fromtimestamp(record.created, kst)
        if datefmt:
            return created_time.strftime(datefmt)
        else:
            return created_time.strftime('%Y-%m-%d %H:%M:%S')


# 로그 포맷 설정 (한국 시간대 포함)
log_format = '%(asctime)s - %(levelname)s : %(message)s'

# 로깅 설정
# 로그 핸들러 설정
handler = logging.StreamHandler()
handler.setFormatter(KSTFormatter(log_format))

# 기본 로거 설정
logging.basicConfig(level=logging.INFO, handlers=[handler])


# # # # # # # # # # # # # # # # # # # #


import get_downdetector_web


# 파일명 등 각종 설정
AREA_LIST = ['US', 'JP']

DASHBOARD_US_PAGE = 'pages/dashboard_us.py'
DASHBOARD_JP_PAGE = 'pages/dashboard_jp.py'
NEWSBOT_PAGE = 'pages/news_bot_dd.py'

GEOLOC_CACHE_FILE = 'geolocation_cache.pkl'
TRANS_CACHE_FILE = 'trans_cache.pkl'
KEY_PATH = 'key.json'

COMPANIES_LIST_FILE = 'companies_list_dd.pkl'


# 색상 코드
GREEN = '#66FF66BB'
ORANGE = '#FFCC66BB'
RED = '#FF6666BB'


DEFAULT_COMPANIES_SET_DICT = {
    'US': {
        'Amazon',
        'Amazon Web Services',
        'Amazon Prime Video',
        'Anthropic',
        'AT&T',
        'Cloudflare',
        'Discord',
        'Disney+',
        'Facebook',

        'Gmail',
        'Google Gemini',
        'Google',
        # 'Google Calendar',
        'Google Cloud',
        'Google Drive',
        # 'Google Duo',
        'Google Maps',
        # 'Google Meet',
        'Google Play',
        # 'Google Public DNS',
        # 'Google Workspace',

        'Grok',

        'iCloud',
        'Instagram',
        # 'Line',
        'Microsoft 365',
        # 'Minecraft',
        'Microsoft Azure',
        'Microsoft Teams',
        'Netflix',
        'OpenAI',
        # 'Paramount+',
        'Paypal',
        # 'Roblox',
        # 'Snapchat',
        # 'Spotify',
        'Starlink',
        'T-Mobile',
        'TikTok',
        # 'Twitch',
        'Verizon',
        # 'Whatsapp',
        'X (Twitter)',
        'Yahoo',
        'Yahoo Mail',
        'YouTube',
        # 'Zoom',
    },

    'JP': {
        'Akamai',
        'Amazon',
        'Amazon Web Services',

        'App Store',
        'Apple Store',
        'Cloudflare',
        'Dropbox',
        'Facebook',

        'Gmail',
        'Google Gemini',
        'Google',
        # 'Google Calendar',
        'Google Cloud',
        'Google Drive',
        # 'Google Duo',
        'Google Maps',
        'Google Meet',
        'Google Play',
        # 'Google Public DNS',
        # 'Google Workspace',

        'Grok',

        'iCloud',
        'Instagram',
        'Line',
        'Microsoft 365',
        'Microsoft Azure',
        'Microsoft Teams',
        'Netflix',
        'NTT Docomo',
        'OpenAI',
        'SoftBank',
        'TikTok',
        # 'Whatsapp',
        'X (Twitter)',
        'Yahoo',
        'Yahoo Mail',
        'YouTube',
        'Zoom',
    }
}


# # # # # # # # # # # # # # #
# 전체 세션 정보 초기화
# # # # # # # # # # # # # # #


def init_session_state():
    # 세션 정보 초기화(공용)
    if 'selected_service_name' not in st.session_state:
        st.session_state.selected_service_name = None

    if 'selected_area' not in st.session_state:
        st.session_state.selected_area = None

    if "companies_list_dict" not in st.session_state:
        st.session_state.companies_list_dict = pickle_load_cache_file(COMPANIES_LIST_FILE, dict)

    # 세션 정보 초기화(대시보드)
    if 'dashboard_button_clicked' not in st.session_state:
        st.session_state.dashboard_button_clicked = False

    if 'dashboard_auto_tab_timer' not in st.session_state:
        st.session_state.dashboard_auto_tab_timer = 180 # 기본 3분으로 연장

    if 'auto_tab_timer_cache' not in st.session_state:

        st.session_state.auto_tab_timer_cache = -1

    if 'status_df_dict' not in st.session_state:
        st.session_state.status_df_dict = dict()

    if 'target_service_set_dict' not in st.session_state:
        st.session_state.target_service_set_dict = DEFAULT_COMPANIES_SET_DICT

    if 'status_cache' not in st.session_state:
        st.session_state.status_cache = dict()

    if 'dashboard_refresh_timer' not in st.session_state:
        st.session_state.dashboard_refresh_timer = 5

    if 'refresh_timer_cache' not in st.session_state:
        st.session_state.refresh_timer_cache = -1

    if 'num_dashboard_columns' not in st.session_state:
        st.session_state.num_dashboard_columns = 8

    if 'display_chart' not in st.session_state:
        st.session_state.display_chart = True

    # 세션 정보 초기화(뉴스)
    if 'news_count_cache' not in st.session_state:
        st.session_state.news_count_cache = dict()  # {area: {service_name: count}}

    if "geolocations_dict" not in st.session_state:
        st.session_state.geolocations_dict = pickle_load_cache_file(GEOLOC_CACHE_FILE, dict)

    if 'trans_text_list' not in st.session_state:
        st.session_state.trans_text_list = pickle_load_cache_file(TRANS_CACHE_FILE, list)

    if "news_list" not in st.session_state:
        st.session_state.news_list = []

    if 'search_interval_timer_cache' not in st.session_state:
        st.session_state.search_interval_timer_cache = -1

    if 'search_interval_min' not in st.session_state:
        st.session_state.search_interval_min = 5

    if 'search_hour' not in st.session_state:
        st.session_state.search_hour = 1

    if 'news_and_keywords' not in st.session_state:
        st.session_state.news_and_keywords = ['outage']

    if 'news_data_cache' not in st.session_state:
        st.session_state.news_data_cache = dict()  # {area: {service_name: df}}

    # 크롤링 제어 플래그
    if 'refresh_done_dict' not in st.session_state:
        st.session_state.refresh_done_dict = {area: False for area in AREA_LIST}

    if 'crawl_fail_count' not in st.session_state:
        st.session_state.crawl_fail_count = {area: 0 for area in AREA_LIST}


# # # # # # # # # # # # # # #
# 피클 파일 로딩 함수
# # # # # # # # # # # # # # #


def pickle_load_cache_file(filename, default_type):
    if os.path.exists(filename):
        # 캐시 파일이 있으면 불러온다.
        with open(filename, 'rb') as pickle_f:
            loaded_object = pickle.load(pickle_f)
            logging.info('피클 캐시 파일 로딩 완료 : ' + filename)
            return loaded_object

    logging.info('피클 파일 없음! : ' + filename)
    return default_type()


# # # # # # # # # # # # # # #
# 서비스의 현재 상태 받아오기
# # # # # # # # # # # # # # #


def get_service_chart_df_by_url_list(area):
    if area is None:
        logging.info(f'{area=} 크롤링 미실행!')
        return None

    logging.info(f'===== {area} 전체 크롤링 시작 =====')

    if area.upper() == 'JP':
        postfix = 'jp'
    else:
        postfix = 'com'

    categories_list = [
        'None',
        # get_downdetector_web.TELECOM,
        # get_downdetector_web.ONLINE_SERVICE,
        # get_downdetector_web.SOCIAL_MEDIA,
        # get_downdetector_web.FINANCE,
        # get_downdetector_web.GAMING,
    ]

    # url_list = [  # f'https://downdetector.{postfix}/',
    #             f'https://downdetector.{postfix}/telecom/',
    #             f'https://downdetector.{postfix}/online-services/',
    #             f'https://downdetector.{postfix}/social-media/',
    #             f'https://downdetector.{postfix}/finance/',
    #             f'https://downdetector.{postfix}/gaming/',
    #             ]

    df_list = []
    for category_item in categories_list:
        if category_item != 'None':
            url_item = f'https://downdetector.{postfix}/{category_item}/'
        else:
            url_item = f'https://downdetector.{postfix}/'
        df_ = get_downdetector_web.get_downdetector_df(url=url_item, area=area)
        if df_ is not None:
            df_[get_downdetector_web.CATEGORY] = category_item  # 종류 구분을 첨부해준다.
            df_list.append(df_)
        time.sleep(1)  # guard time

    if len(df_list) == 0:
        logging.error(f'===== {area} 전체 크롤링 실패!!! =====')
        return None

    total_df = (pd.concat(df_list, ignore_index=True)
                .drop_duplicates(subset=get_downdetector_web.NAME, keep='first'))

    logging.info(f'===== {area} 전체 크롤링 및 df 변환 완료 =====')
    return total_df


def refresh_status_and_save_companies(area):
    # 세션상태 방어 코드
    init_session_state()

    # 이번 회차에서 이미 시도했다면 중단
    if st.session_state.refresh_done_dict.get(area, False):
        return

    # 상태 받아오기 (하나라도 성공하면 DataFrame, 모두 실패하면 None 리턴)
    new_status_df = get_service_chart_df_by_url_list(area)

    # 시도 완료 플래그 설정 (실패하더라도 이번 루프에선 다시 안함)
    st.session_state.refresh_done_dict[area] = True

    # 일부라도 크롤링에 성공했다면 데이터 업데이트
    if new_status_df is not None and len(new_status_df) > 0:
        st.session_state.status_df_dict[area] = new_status_df
        st.session_state.crawl_fail_count[area] = 0 # 성공 시 카운트 초기화
        logging.info(f"{area} 일부 또는 전체 서비스 크롤링 성공 - 데이터 업데이트 완료")
    else:
        # 모든 서비스 크롤링에 실패했을 경우
        st.session_state.crawl_fail_count[area] += 1 # 실패 카운트 증가
        logging.error(f"{area} 모든 서비스 크롤링 실패! (누적 {st.session_state.crawl_fail_count[area]}회)")
        
        if st.session_state.status_df_dict.get(area) is not None and len(st.session_state.status_df_dict[area]) > 0:
            logging.error(f"{area} 이전 성공 데이터 유지")
        else:
            logging.error(f"{area} 모든 서비스 크롤링 실패! (최초 실행 실패 - 데이터 없음)")
            # 최초 실행 시 실패했다면 루프 방지를 위해 빈 DF라도 넣어줌
            st.session_state.status_df_dict[area] = pd.DataFrame(columns=[get_downdetector_web.NAME, 
                                                                         get_downdetector_web.CLASS, 
                                                                         get_downdetector_web.VALUES, 
                                                                         get_downdetector_web.AREA])
        return 

    logging.info(f"{area} 현재 사용 데이터 길이: {len(st.session_state.status_df_dict[area])}")

    # 회사 목록 파일 업데이트
    new_list = list(st.session_state.status_df_dict[area][get_downdetector_web.NAME])

    # 기존 회사 목록 불러오기
    # companies_list = pickle_load_cache_file(COMPANIES_LIST_FILE, dict)

    # 신규 목록 합치기
    st.session_state.companies_list_dict[area] = list(set(st.session_state.companies_list_dict.get(area, [])
                                                          + new_list))
    st.session_state.companies_list_dict[area].sort(key=lambda x: x.lower())  # 대소문자 구분없이 abc 순으로 정렬

    # logging.info(f'{area} 회사 목록:\n{st.session_state.companies_list_dict[area][:5]} ...')
    logging.info(f'{area} Total services count: {len(st.session_state.companies_list_dict[area])}')

    # 합쳐진 리스트를 다시 파일로 저장
    with open(COMPANIES_LIST_FILE, 'wb') as f_:
        pickle.dump(st.session_state.companies_list_dict, f_)
        logging.info(f'{area} 회사 목록 업데이트 & 파일 저장 완료')


def get_service_chart_mapdf(area, service_name=None, need_map=False):
    # 세션상태 방어 코드
    init_session_state()

    # 이번 회차에 아직 크롤링 안했거나 최초 로딩인 경우
    if not st.session_state.refresh_done_dict.get(area, False) or service_name is None:
        logging.info(f'크롤링 필요 감지 - 시작 {area=} {service_name=}')
        refresh_status_and_save_companies(area)

    # 단순 크롤링 목적의 호출일 경우
    if service_name is None:
        logging.info(f'크롤링 종료 - {area=}')
        return None, None, None

    # 데이터가 아예 없는 경우 (최초 실행 실패 등)
    if st.session_state.status_df_dict.get(area) is None:
        logging.error(f'데이터 없음!!! {area=} {service_name=}')
        return None, None, None

    for i, row in st.session_state.status_df_dict[area].iterrows():
        if row[get_downdetector_web.NAME].upper() == service_name.upper() \
                and row[get_downdetector_web.AREA].upper() == area.upper():  # 대소문자 구분 없이 이름/지역 일치 찾음.
            # 서비스를 찾으면 클래스, 리포트 리스트, 지도를 리턴함.
            if row[get_downdetector_web.VALUES] is None or row[get_downdetector_web.VALUES] == "":
                logging.info(f'{area} {service_name} 의 data_values 없음!')
                data_values = None
            else:
                try:
                    data_values = [int(x) for x in row[get_downdetector_web.VALUES].strip('[]').split(', ')]
                except:
                    data_values = None
            return row[get_downdetector_web.CLASS], data_values, None

    # 서비스를 못찾았을 경우
    return None, None, None


# 현재 알람이 뜬 서비스 목록을 가져오는 함수
def get_current_alarm_service_list(area):
    # 세션상태 방어 코드
    init_session_state()

    if st.session_state.status_df_dict.get(area) is None:
        logging.info('현재 알람 상태 없어서 크롤링 시작')
        get_service_chart_mapdf(area)  # 현재 값이 없을 경우 강제 크롤링 1회 수행.

    if st.session_state.status_df_dict.get(area) is None or len(st.session_state.status_df_dict[area]) == 0:
        # 데이터가 아예 없을 경우.
        return []

    alarm_list = []
    for i, row in st.session_state.status_df_dict[area].iterrows():
        # 해당 지역의 Red 알람이면서 게임/금융 알람이 아닌 것.
        if row[get_downdetector_web.CLASS] == get_downdetector_web.DANGER \
                and row[get_downdetector_web.AREA].upper() == area.upper() \
                and row[get_downdetector_web.CATEGORY] != get_downdetector_web.GAMING \
                and row[get_downdetector_web.CATEGORY] != get_downdetector_web.FINANCE:
            alarm_list.append(row[get_downdetector_web.NAME])

    logging.info(f'{area}의 Red 알람 서비스 목록: {alarm_list}')

    return alarm_list


def init_status_df():
    logging.info('status_df_dict 플래그 초기화! (데이터 유지)')
    # 데이터를 삭제하지 않고 플래그만 초기화하여 다음 루프에서 새로고침 유도
    for area in st.session_state.refresh_done_dict:
        st.session_state.refresh_done_dict[area] = False
    
    get_downdetector_web.get_downdetector_df.clear()


def get_status_color(name, status):
    if status is None or status == get_downdetector_web.SUCCESS:
        color = 'green'
        color_code = GREEN
        icon = '☻'
    elif status == get_downdetector_web.WARNING:
        color = 'orange'
        color_code = ORANGE
        icon = '☁︎'
        # st.toast(f'**{name}** 서비스 문제 발생!', icon="🔔")
    else:  # get_downdetector_web.DANGER:
        color = 'red'
        color_code = RED
        icon = '☠︎'
        # st.toast(f'**{name}** 서비스 문제 발생!', icon="🚨")

    return color, color_code, icon


# # # # # # # # # # # # # # #
# 뉴스 검색 관련 공용 함수
# # # # # # # # # # # # # # #


def get_google_news(keyword, search_hour=1, add_keywords=[]):
    query = keyword

    # 추가 조건 (outage 등)
    if add_keywords:
        query += ' ' + ' '.join(add_keywords)
    
    logging.info(f"뉴스 검색중 : {query} ({search_hour}h)")

    url = f"https://news.google.com/rss/search?q={query}"
    if search_hour > 0:
        url += f"+when:{search_hour}h"
    url += f'&hl=en-US&gl=US&ceid=US:en'
    url = url.replace(' ', '%20')

    title_list = []
    source_list = []
    pubtime_list = []
    link_list = []

    # 실제 브라우저처럼 보이기 위한 헤더 추가
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }

    try:
        # 타임아웃을 15초로 연장
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            datas = feedparser.parse(res.text).entries
            for data in datas:
                title = data.title
                if ' - ' in title:
                    minus_index = title.rindex(' - ')
                    title = title[:minus_index].strip()

                # 기사 제목에 검색 키워드 검사 (공백 무시 비교로 매칭률 향상)
                # clean_keyword = keyword.lower().replace(" ", "")
                # clean_title = title.lower().replace(" ", "")
                #
                # if clean_keyword not in clean_title:
                #     continue

                title_list.append(title)
                source_list.append(data.source.title)
                link_list.append(data.link)

                pubtime = datetime.strptime(data.published, "%a, %d %b %Y %H:%M:%S %Z")
                kst = pytz.timezone('Asia/Seoul')
                pubtime = pubtime.replace(tzinfo=pytz.utc).astimezone(kst)
                pubtime_list.append(pubtime.strftime('%Y-%m-%d %H:%M:%S'))
        else:
            logging.error(f"구글 뉴스 응답 에러: {res.status_code}")

    except Exception as e:
        logging.error(f"뉴스 검색 오류 ({keyword}): {e}")
    
    result = {'제목': title_list, '언론사': source_list, '발행시간': pubtime_list, '링크': link_list}
    return pd.DataFrame(result)


def _news_search_task(area_list, news_count_cache, news_data_cache, target_service_set_dict, status_df_dict, search_hour, add_keywords):
    logging.info("===== [Thread] 백그라운드 뉴스 검색 시작 =====")
    
    search_targets_set = set()
    
    for area in area_list:
        monitored_set = target_service_set_dict.get(area, set())
        if area in status_df_dict:
            df = status_df_dict[area]
            if not df.empty:
                # 1. DANGER 등급인 모든 서비스 (목록 포함 여부 무관) 추출
                dangers = df[df[get_downdetector_web.CLASS] == get_downdetector_web.DANGER][get_downdetector_web.NAME].tolist()
                search_targets_set.update(dangers)
                
                # 2. 사전에 설정한 감시 목록 서비스 중 WARNING 등급인 서비스 추출
                warnings = df[df[get_downdetector_web.CLASS] == get_downdetector_web.WARNING][get_downdetector_web.NAME].tolist()
                monitored_warnings = [w for w in warnings if w in monitored_set]
                search_targets_set.update(monitored_warnings)
    
    # 리스트로 변환
    search_targets = list(search_targets_set)
    
    if not search_targets:
        logging.info("검색 조건(Danger 전체 또는 감시 중인 Warning)에 맞는 서비스가 없어 뉴스 검색을 건너뜁니다.")
        return

    logging.info(f"뉴스 검색 대상 확정 (총 {len(search_targets)}개): {search_targets}")

    # 3. 검색 수행
    temp_results = {}
    for service_name in search_targets:
        try:
            df = get_google_news(service_name, search_hour, add_keywords)
            temp_results[service_name] = df
            time.sleep(1.5) # 구글 차단 방지용 간격
        except Exception as e:
            logging.error(f"뉴스 검색 에러 ({service_name}): {e}")
            time.sleep(3.0)

    # 4. 결과 배분
    for area in area_list:
        if area not in news_count_cache: news_count_cache[area] = dict()
        if area not in news_data_cache: news_data_cache[area] = dict()
            
        for service_name, df in temp_results.items():
            news_count_cache[area][service_name] = len(df)
            news_data_cache[area][service_name] = df

    logging.info(f"===== [Thread] 뉴스 검색 완료 (대상: {len(search_targets)}개) =====")


def background_news_search():
    # 세션 상태 방어
    init_session_state()
    
    # 별도 스레드에서 실행
    thread = threading.Thread(
        target=_news_search_task,
        args=(
            AREA_LIST,
            st.session_state.news_count_cache,
            st.session_state.news_data_cache,
            st.session_state.target_service_set_dict,
            st.session_state.status_df_dict,
            st.session_state.search_hour,
            st.session_state.news_and_keywords
        ),
        daemon=True
    )
    thread.start()

