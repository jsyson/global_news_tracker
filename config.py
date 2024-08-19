import os
import logging
import pickle
import streamlit as st
import get_downdetector_web
import time
import pandas as pd


# 로깅 설정
logging.basicConfig(level=logging.DEBUG)


# 파일명
DASHBOARD_PAGE = 'dashboard_dd.py'
NEWSBOT_PAGE = 'news_bot_dd.py'


# 색상 코드
GREEN = '#66FF66BB'
ORANGE = '#FFCC66BB'
RED = '#FF6666BB'


COMPANIES_LIST_FILE = 'companies_list_dd.pkl'

DEFAULT_COMPANIES_SET = {
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
    'Google Drive',
    'Google Duo',
    'Google Maps',
    'Google Play',
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

}

# DEFAULT_COMPANIES_SET = {'apple-store/Apple Store',
#                          # 'facebook-gaming/Facebook Gaming',
#                          'microsoft-azure/Microsoft Azure',
#                          'google-cloud/Google Cloud',
#                          'instagram/Instagram',
#                          'netflix/Netflix',
#                          'twitch/Twitch',
#                          # 'hbo-max/HBO Max',
#                          'dropbox/Dropbox',
#                          'facebook/Facebook',
#                          'facebook-messenger/Facebook Messenger',
#                          # 'snapchat/Snapchat',
#                          'amazon-web-services-aws/Amazon Web Services',
#                          'itunes/iTunes',
#                          't-mobile/T-Mobile',
#                          'amazon-prime-instant-video/Amazon Prime Video',
#                          'disney-plus/Disney+',
#                          'outlook-hotmail/Outlook.com',
#                          'twitter/Twitter',
#                          'discord/Discord',
#                          'gmail/Gmail',
#                          'zoom/Zoom',
#                          'tiktok/TikTok',
#                          'starlink/Starlink',
#                          # 'yahoo-mail/Yahoo! Mail',
#                          # 'slack/Slack',
#                          'verizon/Verizon Wireless',
#                          'telegram/Telegram',
#                          # 'whatsapp-messenger/WhatsApp',
#                          'cloudflare/Cloudflare',
#                          'att/AT&T',
#                          'office-365/Office 365',
#                          'youtube/Youtube',
#                          'microsoft-teams/Microsoft Teams',
#                          'roblox/Roblox',
#                          'skype/Skype'
#                          }


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


def get_service_chart_mapdf(service_name=None, need_map=False):
    if 'status_df' not in st.session_state:
        st.session_state.status_df = None

    # 최초 로딩 시 또는 service_name None일 경우
    if st.session_state.status_df is None or service_name is None:
        df1 = get_downdetector_web.get_downdetector_df()  # 메인페이지를 크롤링해온다.
        time.sleep(0.1)
        df2 = get_downdetector_web.get_downdetector_df(url='https://downdetector.com/telecom/')
        time.sleep(0.1)
        df3 = get_downdetector_web.get_downdetector_df(url='https://downdetector.com/online-services/')
        time.sleep(0.1)
        df4 = get_downdetector_web.get_downdetector_df(url='https://downdetector.com/social-media/')

        st.session_state.status_df = (pd.concat([df1, df2, df3, df4], ignore_index=True)
                                      .drop_duplicates(subset=get_downdetector_web.NAME, keep='first'))

        new_list = list(st.session_state.status_df[get_downdetector_web.NAME])

        # 기존 회사 목록 불러오기
        old_list = pickle_load_cache_file(COMPANIES_LIST_FILE, list)

        st.session_state.companies_list = list(set(new_list + old_list))
        st.session_state.companies_list.sort(key=lambda x: x.lower())  # 대소문자 구분없이 abc 순으로 정렬

        logging.info('회사 목록:\n' + str(st.session_state.companies_list))
        logging.info('Total companies count: ' + str(len(st.session_state.companies_list)))

        # 합쳐진 리스트를 다시 파일로 저장
        with open(COMPANIES_LIST_FILE, 'wb') as f_:
            pickle.dump(st.session_state.companies_list, f_)
            logging.info('회사 목록 파일 저장 완료')

    # 메인페이지 크롤링 목적의 호출
    if service_name is None:
        return None, None, None

    for i, row in st.session_state.status_df.iterrows():
        if row[get_downdetector_web.NAME].upper() == service_name.upper():  # 대소문자 구분 없이 일치하는 이름을 찾는다.
            # 서비스를 찾으면 클래스, 리포트 리스트, 지도를 리턴함.
            data_values = [int(x) for x in row[get_downdetector_web.VALUES].strip('[]').split(', ')]
            return row[get_downdetector_web.CLASS], data_values, None

    # 서비스를 못찾았을 경우
    return None, None, None


# 현재 알람이 뜬 서비스 목록을 가져오는 함수
def get_current_alarm_service_list():
    get_service_chart_mapdf()  # 강제 크롤링 1회 수행.

    alarm_list = []

    for i, row in st.session_state.status_df.iterrows():
        if row[get_downdetector_web.CLASS] == get_downdetector_web.DANGER:  # Red 알람
            alarm_list.append(row[get_downdetector_web.NAME])

    return alarm_list


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

