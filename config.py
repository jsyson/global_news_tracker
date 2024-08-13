import os
import logging
import pickle
import requests
from bs4 import BeautifulSoup
from io import StringIO
import pandas as pd


# 로깅 설정
logging.basicConfig(level=logging.DEBUG)

COMPANIES_LIST_FILE = 'companies_list.pkl'

DEFAULT_COMPANIES_SET = {'apple-store/Apple Store',
                         # 'facebook-gaming/Facebook Gaming',
                         'microsoft-azure/Microsoft Azure',
                         'google-cloud/Google Cloud',
                         'instagram/Instagram',
                         'netflix/Netflix',
                         'twitch/Twitch',
                         # 'hbo-max/HBO Max',
                         'dropbox/Dropbox',
                         'facebook/Facebook',
                         'facebook-messenger/Facebook Messenger',
                         # 'snapchat/Snapchat',
                         'amazon-web-services-aws/Amazon Web Services',
                         'itunes/iTunes',
                         't-mobile/T-Mobile',
                         'amazon-prime-instant-video/Amazon Prime Video',
                         'disney-plus/Disney+',
                         'outlook-hotmail/Outlook.com',
                         'twitter/Twitter',
                         'discord/Discord',
                         'gmail/Gmail',
                         'zoom/Zoom',
                         'tiktok/TikTok',
                         'starlink/Starlink',
                         # 'yahoo-mail/Yahoo! Mail',
                         # 'slack/Slack',
                         'verizon/Verizon Wireless',
                         'telegram/Telegram',
                         # 'whatsapp-messenger/WhatsApp',
                         'cloudflare/Cloudflare',
                         'att/AT&T',
                         'office-365/Office 365',
                         'youtube/Youtube',
                         'microsoft-teams/Microsoft Teams',
                         'roblox/Roblox',
                         'skype/Skype'
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


def get_service_chart_mapdf(service_name, need_map=True):
    # url = "https://istheservicedown.com/problems/disney-plus"
    url = "https://istheservicedown.com/problems/" + service_name

    req_ = requests.Session()
    response_ = req_.get(url,
                         headers={'User-Agent': 'Popular browser\'s user-agent', })

    soup_ = BeautifulSoup(response_.content, 'html.parser')

    # 상태
    status_ = soup_.find('p').text

    # 차트 주소
    chart_url_ = soup_.find(id="chart-img")['src']

    # map 주소
    map_df_ = None

    # map 주소를 요청할때만 가져온다.
    if need_map:
        sub_url = soup_.find(title='Live Outage Map')['href']
        if sub_url:
            map_url_ = 'https://istheservicedown.com' + sub_url

            response_ = req_.get(map_url_,
                                 headers={'User-Agent': 'Popular browser\'s user-agent', })

            soup_ = BeautifulSoup(response_.content, 'html.parser')
            table_html = soup_.find('table', class_="table table-striped table-condensed")  # , id_='status-table')
            map_df_ = pd.read_html(StringIO(str(table_html)))[0]

    return status_, chart_url_, map_df_

