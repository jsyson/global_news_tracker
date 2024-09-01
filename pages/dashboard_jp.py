import config
import dashboard_dd
import streamlit as st
import logging


# 세션상태 방어 코드
config.init_session_state()


# # # # # # # # # # # # # # # # # # # #
# 웹 페이지 구성
# # # # # # # # # # # # # # # # # # # #


if st.session_state.dashboard_button_clicked:
    logging.info('버튼 눌림 처리!')
    st.switch_page(config.NEWSBOT_PAGE)


dashboard_dd.make_all_dashboard_tabs('JP', icon='', image_path='./images/flag_jp.jpg')

