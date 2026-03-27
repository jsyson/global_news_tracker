import streamlit as st
import logging


st.set_page_config(layout="wide", page_title='GSS')


import config


# 로깅 설정
# logging.basicConfig(level=logging.INFO)


# 세션 정보 초기화
config.init_session_state()


# # # # # # # # # # # # # # # # # # # #
# 페이지 구성
# # # # # # # # # # # # # # # # # # # #


def help_page():
    st.title('Global Service Status')
    # st.write('도움말')
    st.write('- 버전: 2026-03-27')
    st.write('- 개발: 정승용 (Feat. 김경준)')


pg = st.navigation([
    st.Page(config.DASHBOARD_US_PAGE, title='Dashboard(US)', icon="📊", default=True),
    st.Page(config.DASHBOARD_JP_PAGE, title='Dashboard(JP)', icon="📊"),
    st.Page(config.NEWSBOT_PAGE, title="News Tracker", icon='💬'),  # , url_path='news_tracker'),
    st.Page(help_page, title="Help", icon='❓')
])

pg.run()

