import streamlit as st
import logging
import requests
from bs4 import BeautifulSoup
import pickle
import config


# 로깅 설정
logging.basicConfig(level=logging.DEBUG)


# # # # # # # # # # # # # # # # # # # #
# 회사 목록 받아오기 (skip)
# # # # # # # # # # # # # # # # # # # #


# if 'companies_loaded' not in st.session_state:
#     st.session_state.companies_loaded = False
#
#
# if not st.session_state.companies_loaded:
#     logging.info('최초 접속이므로 회사 정보 웹로딩 시작...')
#
#     req = requests.Session()
#     response = req.get('https://istheservicedown.com/companies',
#                        headers={'User-Agent': 'Popular browser\'s user-agent'})
#
#     soup = BeautifulSoup(response.content, 'html.parser')
#
#     companies_html_list = soup.find_all('a', class_='b-lazy-bg')
#     companies_list = []
#
#     for company in companies_html_list:
#         code = company['href'].split('/')[-1]
#         name = company.h3.text
#         code_name = code + '/' + name
#         logging.debug(code_name)
#         companies_list.append(code_name)
#
#     logging.info('Total companies count:' + str(len(companies_list)))
#
#     # 파일 저장
#     with open(config.COMPANIES_LIST_FILE, 'wb') as f_:
#         pickle.dump(companies_list, f_)
#         logging.info('회사 목록 파일 저장 완료')
#
#     st.session_state.companies_loaded = True
#
# else:
#     logging.info('회사 정보 웹로딩 스킵!')


# # # # # # # # # # # # # # # # # # # #
# 페이지 구성
# # # # # # # # # # # # # # # # # # # #


pg = st.navigation([
    st.Page(config.DASHBOARD_PAGE, title='Dashboard', icon="🚥", default=True),
    st.Page(config.NEWSBOT_PAGE, title="News Tracker", icon='💬', url_path='news_tracker'),
])

pg.run()
