import logging
import requests
import pandas as pd
import pickle
import os
import time
from geopy.geocoders import Nominatim
import feedparser
from datetime import datetime, timedelta
import pytz
import re
import streamlit as st
from google.cloud import translate_v2 as translate  # pip install google-cloud-translate==2.0.1
from google.oauth2 import service_account
import config


# 로깅 설정
logging.basicConfig(level=logging.DEBUG)

GEOLOC_CACHE_FILE = 'geolocation_cache.pkl'
TRANS_CACHE_FILE = 'trans_cache.pkl'
KEY_PATH = 'key.json'


# 스레드 풀 실행자 초기화

# executor = concurrent.futures.ThreadPoolExecutor()


# Set verbose if needed
# globals.set_debug(True)


# # # # # # # # # # # #
# 세션 캐시 처리
# # # # # # # # # # # #


if "geolocations_dict" not in st.session_state:
    st.session_state.geolocations_dict = config.pickle_load_cache_file(GEOLOC_CACHE_FILE, dict)

if 'trans_text_list' not in st.session_state:
    st.session_state.trans_text_list = config.pickle_load_cache_file(TRANS_CACHE_FILE, list)

if "news_list" not in st.session_state:
    st.session_state.news_list = []

if 'service_code_name_index' not in st.session_state:
    st.session_state.service_code_name_index = None

# 서비스 인덱스를 파라미터로 받을 경우
# https://your_app.streamlit.app/?first_key=1&second_key=two
if 'service_index' in st.query_params:
    logging.info(f'{st.query_params=}')
    st.session_state.service_code_name_index = int(st.query_params["service_index"])

if 'another_service_text' not in st.session_state:
    st.session_state.another_service_text = None

if "companies_list" not in st.session_state:
    st.session_state.companies_list = config.pickle_load_cache_file(config.COMPANIES_LIST_FILE, list)


# # # # # # # # # #
# 구글 뉴스 가져오기 #
# # # # # # # # # #


def get_google_outage_news(keyword_):
    query = keyword_
    if and_keyword:
        query += ' ' + and_keyword[0]

    url = f"https://news.google.com/rss/search?q={query}+when:{search_hour}h"
    url += f'&hl=en-US&gl=US&ceid=US:en'
    url = url.replace(' ', '%20')

    title_list = []
    source_list = []
    pubtime_list = []
    link_list = []

    try:
        res = requests.get(url)  # , verify=False)
        logging.info('원본 링크: ' + url)

        if res.status_code == 200:
            datas = feedparser.parse(res.text).entries
            for data in datas:
                title = data.title
                logging.info('구글뉴스제목(원본): ' + title)

                minus_index = title.rindex(' - ')
                title = title[:minus_index].strip()

                # 기사 제목에 검색 키워드가 없으면 넘긴다.
                if keyword_.lower() not in title.lower():
                    continue

                title_list.append(title)
                source_list.append(data.source.title)
                link_list.append(data.link)

                pubtime = datetime.strptime(data.published, "%a, %d %b %Y %H:%M:%S %Z")
                # GMT+9 (Asia/Seoul)으로 변경
                gmt_plus_9 = pytz.FixedOffset(540)  # 9 hours * 60 minutes = 540 minutes
                pubtime = pubtime.replace(tzinfo=pytz.utc).astimezone(gmt_plus_9)

                pubtime_str = pubtime.strftime('%Y-%m-%d %H:%M:%S')
                pubtime_list.append(pubtime_str)

        else:
            logging.error("Google 뉴스 수집 실패! Error Code: " + str(res.status_code))
            logging.error(str(res))
            return None

    except Exception as e:
        logging.error(e)
        logging.error("Google 뉴스 RSS 피드 조회 오류 발생!")
        return None

    # 결과를 dict 형태로 저장
    result = {'제목': title_list, '언론사': source_list, '발행시간': pubtime_list, '링크': link_list}

    df = pd.DataFrame(result)
    return df


def display_news_df(ndf, keyword_):
    # st.divider()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if ndf is None or len(ndf) == 0:
        st.write(f'✅ 검색된 뉴스 없습니다. ({current_time})')
        return

    # st.write('뉴스 검색 결과')

    disp_cnt = 0
    for i, row in ndf.iterrows():
        # 이미 출력했던 뉴스라면 스킵한다.
        if row['제목'] in st.session_state.news_list:
            logging.info('뉴스 스킵!!! - ' + row['제목'])
            continue

        # 출력한 뉴스 리스트에 추가한다.
        st.session_state.news_list.append(row['제목'])
        disp_cnt += 1

        # title = row['제목'].replace(keyword_, f':yellow-background[{keyword_}]')
        # logging.info('keyword: ' + keyword_)
        # logging.info('before: ' + row['제목'])
        title = re.sub(keyword_, f':blue-background[{keyword_}]', row['제목'], flags=re.IGNORECASE)
        if and_keyword:
            title = re.sub(and_keyword[0], f':blue-background[{and_keyword[0]}]', title, flags=re.IGNORECASE)
        # logging.info('after : ' + title)

        # 제목 번역
        korean_title = translate_eng_to_kor(row['제목'])

        with st.container(border=True):
            st.markdown(f'**{title}**')
            st.caption(f'{korean_title}')
            st.markdown(f'- {row["언론사"]}, {row["발행시간"]} <a href="{row["링크"]}" target="_blank">📝</a>',
                        unsafe_allow_html=True)
        # st.write(' - 언론사: ' + row['언론사'] + '  - 발행시각: ' + row['발행시간'])

    if disp_cnt > 0:
        st.write(f'✅ 뉴스 표시 완료 ({current_time})')
    else:
        st.write(f'✅ 신규 뉴스 없습니다. ({current_time})')


def fetch_news(keyword_, infinite_loop=False):
    with st.spinner('뉴스 검색중...'):
        news_df_ = get_google_outage_news(keyword_)
        # st.write(news_df_)
        display_news_df(news_df_, keyword_)

    while infinite_loop:
        time.sleep(search_interval_min * 60)
        with st.spinner('뉴스 검색중...'):
            news_df_ = get_google_outage_news(keyword_)
            # st.write(news_df_)
            display_news_df(news_df_, keyword_)


# # # # # # # # # # # # # # #
# 영어 번역
# # # # # # # # # # # # # # #


def translate_eng_to_kor(text):
    # 캐시를 먼저 뒤져본다.
    cache_text = load_trans_cache(text)
    if cache_text:
        logging.info('trans cache hit! - ' + text + ' : ' + cache_text)
        return cache_text  # 캐시힛!

    # 캐시에 없으면 구글 api로 번역을 한다.
    if not os.path.exists(KEY_PATH):
        return ''

    credential_trans = service_account.Credentials.from_service_account_file(KEY_PATH)
    translate_client = translate.Client(credentials=credential_trans)

    result = translate_client.translate(text, target_language='ko')
    # print(names)
    translated_text = result['translatedText'].replace('&amp;', '&')

    # 캐시에 저장한다.
    save_trans_cache(text, translated_text)

    return translated_text


def save_trans_cache(eng_text, kor_text):
    if len(st.session_state.trans_text_list) >= 100:  # 100개 이하로 유지한다.
        st.session_state.trans_text_list.pop(0)

    st.session_state.trans_text_list.append((eng_text, kor_text))  # 번역 튜플을 리스트에 삽입
    # 캐시 파일에 저장
    with open(TRANS_CACHE_FILE, 'wb') as f_:
        pickle.dump(st.session_state.trans_text_list, f_)
        logging.info('번역 캐시 파일 업데이트 완료')


def load_trans_cache(eng_text):
    for e_txt, k_txt in st.session_state.trans_text_list:
        if eng_text == e_txt:
            return k_txt  # 캐시 힛
    return None


# # # # # # # # # # # # # # #
# 시간대 변환
# # # # # # # # # # # # # # #


def get_korean_time():
    # 차트 시간대 보정
    now = datetime.now() - timedelta(minutes=5)
    before_10unit_minute = int(now.minute / 10) * 10
    new_time = now.replace(minute=before_10unit_minute, second=0, microsecond=0)

    # 4시간 간격으로 이전 여섯개의 시각을 저장할 리스트
    previous_times = [new_time]

    # 4시간 간격으로 이전 시간들을 계산
    for i in range(1, 7):
        previous_time = new_time - timedelta(hours=4 * i)
        previous_times.append(previous_time)

    # 결과 출력
    logging.info(str(previous_times))

    previous_times.reverse()
    return previous_times


# # # # # # # # # #
# 위경도 받아오기
# # # # # # # # # #


def save_loc_cache(loc, lat, lon):
    st.session_state.geolocations_dict[loc] = {'lat': lat, 'lon': lon}
    # 새로운 위경도 정보를 캐시 파일에 저장
    with open(GEOLOC_CACHE_FILE, 'wb') as f_:
        pickle.dump(st.session_state.geolocations_dict, f_)
        logging.info('위경도 캐시 파일 업데이트 완료')


def load_loc_cache(loc):
    return st.session_state.geolocations_dict.get(loc)


def get_geo_location(map_df_):
    geolocator = Nominatim(user_agent="jason")
    map_df_['lat'] = None
    map_df_['lon'] = None
    map_df_['color'] = '#ff000077'  # 빨강, 살짝 투명.

    for i, row in map_df_.iterrows():
        # 세션 캐시를 먼저 살펴본다.
        cache = load_loc_cache(row['Location'])
        if cache:
            logging.info('geo cache hit! - ' + row['Location'])
            map_df_.loc[i, 'lat'] = cache['lat']
            map_df_.loc[i, 'lon'] = cache['lon']
            continue

        # 세션 캐시에 없으면 위경도 api를 써서 불러온다.
        geo = geolocator.geocode(row['Location'])

        if geo:
            map_df_.loc[i, 'lat'] = geo.latitude
            map_df_.loc[i, 'lon'] = geo.longitude
            save_loc_cache(row['Location'], geo.latitude, geo.longitude)
        else:
            # retry
            geo = geolocator.geocode(row['Location'].split(',')[0])

            if geo:
                map_df_.loc[i, 'lat'] = geo.latitude
                map_df_.loc[i, 'lon'] = geo.longitude
                save_loc_cache(row['Location'], geo.latitude, geo.longitude)
            else:
                # retry까지 실패할 경우.
                logging.error('Geo ERROR!!! :' + str(geo))

        time.sleep(0.2)
    return map_df_


def get_multiple(values_sr):
    max_report = values_sr.max()
    multiple_ = int(500000 / max_report)
    logging.info(f'{max_report=} {multiple_=}')
    return multiple_


# # # # # # # # # #
# 웹 페이지 구성
# # # # # # # # # #


st.set_page_config(layout="wide")
# st.title('뉴스 검색 봇')


# # # # # # # # # # # # # # #
# 사이드바
# # # # # # # # # # # # # # #


# st.sidebar.header('Global Service News Tracker')

service_code_name = st.sidebar.selectbox(
    "검색을 원하는 서비스는?",
    st.session_state.companies_list,
    index=st.session_state.service_code_name_index,
    placeholder="서비스 이름 선택...",
)


another_service = st.sidebar.text_input("또는 서비스명 입력", value=st.session_state.another_service_text)

search_hour = st.sidebar.number_input('최근 몇시간의 뉴스를 검색할까요?', value=1, format='%d')

and_keyword = st.sidebar.multiselect("뉴스 검색 추가 키워드", options=['outage', 'blackout', 'failure'], default=['outage'])

search_interval_min = st.sidebar.number_input('새로고침 주기(분)', value=1, format='%d')

st.sidebar.divider()
st.sidebar.write('❓ 참고사이트: https://istheservicedown.com/')


# open ai api key
# if os.environ.get("OPENAI_API_KEY"):
#     logging.info('OpenAI API key는 OS 환경변수에 저장된 key 사용합니다.')
# else:
#     os.environ["OPENAI_API_KEY"] = st.sidebar.text_input('OpenAI API Key',
#                                                          placeholder='Input your ChatGPT API key here.')

if not os.path.exists(KEY_PATH):
    uploaded_file = st.sidebar.file_uploader('API Key File', type=['json'], accept_multiple_files=False)
else:
    logging.info('API key 파일은 로컬 저장된 파일 사용합니다.')
    uploaded_file = None


# key json 파일 업로드 처리
if uploaded_file is not None:
    # 파일을 로컬에 저장
    with open(KEY_PATH, "wb") as file:
        file.write(uploaded_file.getbuffer())

    st.toast(f"API key file has been saved successfully!")


# # # # # # # # # # # # # # #
# 메인 화면
# # # # # # # # # # # # # # #


# 서비스 선택시 처리
if service_code_name and not another_service:
    # 선택된 서비스 인덱스를 세션정보에 저장.
    st.session_state.service_code_name_index = st.session_state.companies_list.index(service_code_name)
    st.session_state.another_service_text = None

    # 본문 화면 구성
    selected_code = service_code_name.split('/')[0]
    selected_name = service_code_name.split('/')[1]

    col1, col2 = st.columns(2)

    # 빈 공간을 생성하여 나중에 내용을 업데이트할 준비
    col1_placeholder = col1.empty()
    col2_placeholder = col2.empty()

    # 이 아래로는 수시로 업데이트 함.
    while True:

        with st.spinner('서비스 상태 조회중...'):
            status, chart_url, map_df = config.get_service_chart_mapdf(selected_code)

            # 상태
            if 'No problem' in status:
                color = 'green'
            elif status == 'Some problems detected':
                color = 'orange'
                st.toast(f'**{selected_name}** 서비스 문제 발생!', icon="🚨")
            else:  # 'Problems detected':
                color = 'red'
                st.toast(f'**{selected_name}** 서비스 중대 문제 발생!', icon="🚨")

        # 컬럼2 - 차트, 지도
        with col2_placeholder.container():
            # st.divider()
            st.write('📈 Live Report Chart (Last 24 hours)')

            with st.container():
                # HTML iframe 태그를 사용하여 웹사이트 임베드
                # chart_iframe_html = f"""
                # <iframe src={chart_url} width="520" height="260" frameborder="0"></iframe>
                # """

                chart_iframe_html = '''
    <style>
    .responsive-iframe-container {
        position: relative;
        width: 100%;
        height: 0;
        padding-bottom: 50%; /* 가로세로 비율 */
        margin: 0;
    }
    .responsive-iframe-container iframe {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border: 0;
    }
    </style>
''' + f'''                
    <div class="responsive-iframe-container">
        <iframe src={chart_url} allowfullscreen></iframe>
    </div>
'''
                st.markdown(chart_iframe_html, unsafe_allow_html=True)

                chart_time_items = get_korean_time()

                st.markdown(
                    """
                    <style>
                    .time-container {
                        display: flex;
                        justify-content: space-between;                                          
                        padding: 0;
                        border: 1px dotted #00008877;
                        border-radius: 20px;
                        font-family: Arial, sans-serif;
                        font-size: 10px;  /* 글씨체 크기 설정 */
                        color: #555555;  /* 글씨체 색상 설정 (연한 회색) */
                        font-weight: 300;  /* 글씨체 굵기 설정 (얇게) */
                    }
                    .time-item {
                        flex: 1;                        
                        text-align: center;                        
                        padding-right: 0;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                # 이전 시간 리스트를 HTML로 출력
                time_items = ''.join(f'<div class="time-item">{time.strftime("%H:%M")}</div>'
                                     for time in chart_time_items)

                # HTML 코드로 시간 출력
                st.markdown(
                    f"""
                    <div class="time-container">
                        {time_items}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<p style="margin: 0; padding: 0; font-size: 10px; text-align: center; font-style: italic;">'
                    '[참조] 한국 시간표. 한국은 미국보다 13시간 빠름.</p>',
                    unsafe_allow_html=True)
                st.write('')

            # st.divider()
            with st.spinner('서비스 맵 구성중...'):
                map_df = get_geo_location(map_df)

                st.write('🗺️ Live Outage Map')

                # 지도 그리기
                drawing_df = map_df.dropna()
                multiple = get_multiple(drawing_df['Reports'])

                drawing_df['Reports'] = drawing_df['Reports'] * multiple
                st.map(drawing_df,
                       latitude='lat',
                       longitude='lon',
                       size='Reports',
                       color='color')

                with st.expander('상세 보기'):
                    st.write('Locations in the past 15 days')
                    st.write(map_df[['Location', 'Reports']])

        # 컬럼1 - 뉴스
        with col1_placeholder.container():
            # st.title(selected_name)
            st.subheader(f'**{selected_name}**  👉 :{color}[{status}]')
            # st.markdown('**This is :blue-background[test].** abcd')

            st.session_state.news_list = []  # 뉴스 세션 클리어
            st.write('📰 News List')
            fetch_news(selected_name)

        # 주기적으로 페이지를 새로고침한다.
        time.sleep(search_interval_min * 60)
        st.rerun()  # 페이지를 새로 고쳐서 업데이트 적용


if another_service and not service_code_name:
    # 선택된 서비스를 세션정보에 저장.
    st.session_state.service_code_name_index = None
    st.session_state.another_service_text = another_service

    st.session_state.news_list = []  # 뉴스 세션 클리어
    st.title(another_service)
    fetch_news(another_service, infinite_loop=True)


if service_code_name and another_service:
    # 세션정보 클리어.
    st.session_state.service_code_name_index = None
    st.session_state.another_service_text = None

    st.error('하나의 서비스만 골라주세요!', icon="🚨")
    st.write(service_code_name, '  VS.  ', another_service)


# 메인 페이지 구성
# chat_placeholder = st.empty()

