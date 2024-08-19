import streamlit as st
import logging


# 로깅 설정
logging.basicConfig(level=logging.INFO)


st.set_page_config(layout="wide")


import config


# 세션 정보 초기화(공용)
if 'selected_service_name' not in st.session_state:
    st.session_state.selected_service_name = None

if 'selected_area' not in st.session_state:
    st.session_state.selected_area = None

if "companies_list_dict" not in st.session_state:
    st.session_state.companies_list_dict = config.pickle_load_cache_file(config.COMPANIES_LIST_FILE, dict)


# 세션 정보 초기화(대시보드)
if 'status_df_dict' not in st.session_state:
    st.session_state.status_df_dict = dict()

if 'target_service_set_dict' not in st.session_state:
    st.session_state.target_service_set_dict = config.DEFAULT_COMPANIES_SET_DICT

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
if "geolocations_dict" not in st.session_state:
    st.session_state.geolocations_dict = config.pickle_load_cache_file(config.GEOLOC_CACHE_FILE, dict)

if 'trans_text_list' not in st.session_state:
    st.session_state.trans_text_list = config.pickle_load_cache_file(config.TRANS_CACHE_FILE, list)

if "news_list" not in st.session_state:
    st.session_state.news_list = []

if 'search_interval_timer_cache' not in st.session_state:
    st.session_state.search_interval_timer_cache = -1

if 'search_interval_min' not in st.session_state:
    st.session_state.search_interval_min = 5


# # # # # # # # # # # # # # # # # # # #
# 페이지 구성
# # # # # # # # # # # # # # # # # # # #


pg = st.navigation([
    st.Page(config.DASHBOARD_PAGE, title='Dashboard', icon="🚥", default=True),
    st.Page(config.NEWSBOT_PAGE, title="News Tracker", icon='💬')  # , url_path='news_tracker'),
])

pg.run()
