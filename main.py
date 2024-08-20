import streamlit as st
import logging


st.set_page_config(layout="wide")


import config


# 로깅 설정
# logging.basicConfig(level=logging.INFO)


# 세션 정보 초기화
config.init_session_state()


# # # # # # # # # # # # # # # # # # # #
# 페이지 구성
# # # # # # # # # # # # # # # # # # # #


pg = st.navigation([
    st.Page(config.DASHBOARD_PAGE, title='Dashboard', icon="🚥", default=True),
    st.Page(config.NEWSBOT_PAGE, title="News Tracker", icon='💬')  # , url_path='news_tracker'),
])

pg.run()
