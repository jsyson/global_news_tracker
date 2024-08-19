import os
import logging
import pickle
import streamlit as st
import get_downdetector_web
import time
import pandas as pd


# 로깅 설정
logging.basicConfig(level=logging.INFO)


# 파일명
DASHBOARD_PAGE = 'dashboard_dd.py'
NEWSBOT_PAGE = 'news_bot_dd.py'

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
        'AT&T',
        'Cloudflare',
        'Discord',
        'Disney+',
        'Facebook',

        'Gmail',
        'Google',
        'Google Calendar',
        'Google Cloud',
        'Google Drive',
        'Google Duo',
        'Google Maps',
        'Google Meet',
        'Google Play',
        'Google Public DNS',
        'Google Workspace',

        'iCloud',
        'Instagram',
        'Line',
        'Microsoft 365',
        'Minecraft',
        'Netflix',
        'OpenAI',
        'Paramount+',
        'Paypal',
        'Roblox',
        'Snapchat',
        'Spotify',
        'Starlink',
        'T-Mobile',
        'TikTok',
        'Twitch',
        'Verizon',
        'Whatsapp',
        'X (Twitter)',
        'Yahoo',
        'Yahoo Mail',
        'Youtube',
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
        'Google',
        'Google Calendar',
        'Google Cloud',
        'Google Drive',
        'Google Duo',
        'Google Maps',
        'Google Meet',
        'Google Play',
        'Google Public DNS',
        'Google Workspace',

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
        'Whatsapp',
        'X (Twitter)',
        'Yahoo',
        'Yahoo Mail',
        'Youtube',
        'Zoom',
    }
}


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
    logging.info(f'===== {area} 전체 크롤링 시작 =====')

    if area.upper() == 'JP':
        postfix = 'jp'
    else:
        postfix = 'com'

    url_list = [f'https://downdetector.{postfix}/',
                f'https://downdetector.{postfix}/telecom/',
                f'https://downdetector.{postfix}/online-services/',
                f'https://downdetector.{postfix}/social-media/'
                ]

    df_list = []
    for url_item in url_list:
        df_ = get_downdetector_web.get_downdetector_df(url=url_item, area=area)
        if df_ is not None:
            df_list.append(df_)
        time.sleep(1)  # guard time

    if len(df_list) == 0:
        logging.info(f'===== {area} 전체 크롤링 실패!!! =====')
        return None

    total_df = (pd.concat(df_list, ignore_index=True)
                .drop_duplicates(subset=get_downdetector_web.NAME, keep='first'))

    logging.info(f'===== {area} 전체 크롤링 및 df 변환 완료 =====')
    return total_df


def refresh_status_and_save_companies(area):
    # 상태 받아오기
    st.session_state.status_df_dict[area] = get_service_chart_df_by_url_list(area)

    if st.session_state.status_df_dict[area] is None:
        return

    # 회사 목록 파일 업데이트
    new_list = list(st.session_state.status_df_dict[area][get_downdetector_web.NAME])

    # 기존 회사 목록 불러오기
    companies_list = pickle_load_cache_file(COMPANIES_LIST_FILE, dict)

    # 신규 목록 합치기
    companies_list[area] = list(set(companies_list.get(area, []) + new_list))
    companies_list[area].sort(key=lambda x: x.lower())  # 대소문자 구분없이 abc 순으로 정렬

    logging.info(f'{area} 회사 목록:\n' + str(companies_list[area]))
    logging.info(f'{area} Total companies count: ' + str(len(companies_list[area])))

    # 합쳐진 리스트를 다시 파일로 저장
    with open(COMPANIES_LIST_FILE, 'wb') as f_:
        pickle.dump(companies_list, f_)
        logging.info(f'{area} 회사 목록 업데이트 & 파일 저장 완료')


def get_service_chart_mapdf(area, service_name=None, need_map=False):
    # 최초 로딩 시 또는 service_name None일 경우
    if st.session_state.status_df_dict.get(area) is None or service_name is None:
        refresh_status_and_save_companies(area)

    # 크롤링에 실패했을 경우 또는 단순 크롤링 목적의 호출일 경우
    if st.session_state.status_df_dict.get(area) is None or service_name is None:
        return None, None, None

    for i, row in st.session_state.status_df_dict[area].iterrows():
        if row[get_downdetector_web.NAME].upper() == service_name.upper() \
                and row[get_downdetector_web.AREA].upper() == area.upper():  # 대소문자 구분 없이 이름/지역 일치 찾음.
            # 서비스를 찾으면 클래스, 리포트 리스트, 지도를 리턴함.
            data_values = [int(x) for x in row[get_downdetector_web.VALUES].strip('[]').split(', ')]
            return row[get_downdetector_web.CLASS], data_values, None

    # 서비스를 못찾았을 경우
    return None, None, None


# 현재 알람이 뜬 서비스 목록을 가져오는 함수
def get_current_alarm_service_list(area):
    if st.session_state.status_df_dict.get(area) is None:
        get_service_chart_mapdf(area)  # 현재 값이 없을 경우 강제 크롤링 1회 수행.

    alarm_list = []

    for i, row in st.session_state.status_df_dict[area].iterrows():
        if row[get_downdetector_web.CLASS] == get_downdetector_web.DANGER \
                and row[get_downdetector_web.AREA].upper() == area.upper():  # 해당 지역의 Red 알람
            alarm_list.append(row[get_downdetector_web.NAME])

    return alarm_list


def init_status_df():
    logging.info('status_df_dict 초기화!')
    st.session_state.status_df_dict = dict()


def get_status_color(name, status):
    if status is None or status == get_downdetector_web.SUCCESS:
        color = 'green'
        color_code = GREEN
        icon = '☻'
    elif status == get_downdetector_web.WARNING:
        color = 'orange'
        color_code = ORANGE
        icon = '☁︎'
        st.toast(f'**{name}** 서비스 문제 발생!', icon="🔔")
    else:  # get_downdetector_web.DANGER:
        color = 'red'
        color_code = RED
        icon = '☠︎'
        st.toast(f'**{name}** 서비스 중대 문제 발생!', icon="🚨")

    return color, color_code, icon

