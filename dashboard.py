import streamlit as st
import logging
import config
import time


# 로깅 설정
logging.basicConfig(level=logging.DEBUG)


# 세션 정보 초기화
if "companies_list" not in st.session_state:
    st.session_state.companies_list = config.pickle_load_cache_file(config.COMPANIES_LIST_FILE, list)

if 'target_service_list' not in st.session_state:
    st.session_state.target_service_set = config.DEFAULT_COMPANIES_SET

if 'service_code_name_index' not in st.session_state:
    st.session_state.service_code_name_index = None

if 'status_cache' not in st.session_state:
    st.session_state.status_cache = dict()

if 'refresh_timer_cache' not in st.session_state:
    st.session_state.refresh_timer_cache = -1

if 'num_dashboard_columns' not in st.session_state:
    st.session_state.num_dashboard_columns = 5


# 서비스명으로 풀 코드 찾아주는 함수
def find_full_code_by_name(name):
    for item_ in st.session_state.companies_list:
        if name == item_.split('/')[1]:
            return item_
    return None


# 웹 페이지 구성
st.set_page_config(layout="wide")
# st.title('Global IT Dashboard')


# 사이드바
st.session_state.display_chart = st.sidebar.checkbox('리포트 차트 보기', value=False)
st.session_state.num_dashboard_columns = st.sidebar.number_input('출력 컬럼 수',
                                                                 value=st.session_state.num_dashboard_columns,
                                                                 format='%d')
refresh_timer = st.sidebar.number_input('새로고침 주기(분)', value=1, format='%d')


# 메인 페이지
st.subheader('Global Service Status  🇺🇸')
dashboard_tab, config_tab = st.tabs(["대시보드", "감시 설정", ])


# # # # # # # # # #
# 탭2 - 설정 탭
# # # # # # # # # #


with config_tab:
    st.write("감시할 서비스들을 고르세요.")

    # 수직 스크롤바 컨테이너 생성을 위한 css 코드 추가
    st.markdown(
        """
        <style>
        .scrollable-container {
            max-height: 300px;  /* 스크롤이 생길 최대 높이 */
            overflow-y: scroll; /* Y축 스크롤바를 강제 */
            border:1px solid #7777;
            margin:10px
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 컨테이너 생성
    with st.container(height=500):
        num_columns = 5
        columns = st.columns(num_columns)
        config_list = [x.split('/')[1] for x in st.session_state.companies_list]  # 서비스 이름만 잘라낸다.

        for idx, item in enumerate(sorted(config_list, key=str.lower)):
            col = columns[idx % num_columns]  # 순서대로 컬럼에 아이템 배치

            if find_full_code_by_name(item) in st.session_state.target_service_set:
                if col.checkbox(item[:15], value=True, help=item):
                    st.session_state.target_service_set.add(find_full_code_by_name(item))
            else:
                if col.checkbox(item[:15], help=item):
                    st.session_state.target_service_set.add(find_full_code_by_name(item))


# # # # # # # # # #
# 탭1 - 대시보드 탭
# # # # # # # # # #


with dashboard_tab:
    logging.info(f'대시보드 구성 목록:\n{st.session_state.target_service_set}\n')

    target_list = list(st.session_state.target_service_set)
    target_list.sort(key=lambda x: x.split('/')[1].lower())  # abc 순으로 정렬

    # num_dashboard_columns = st.session_state.num_dashboard_columns
    dashboard_columns = st.columns(st.session_state.num_dashboard_columns)

    for idx, item in enumerate(target_list):
        col = dashboard_columns[idx % st.session_state.num_dashboard_columns]  # 순서대로 컬럼에 아이템 배치

        selected_code = item.split('/')[0]
        selected_name = item.split('/')[1]

        # 링크를 만들때 st.session_state.service_code_name_index 를 사용
        # https://your_app.streamlit.app/?first_key=1&second_key=two
        logging.info(f'컬럼{col} : {selected_name=}')

        with col:
            if selected_code in st.session_state.status_cache:
                status, chart_url = st.session_state.status_cache[selected_code]
            else:
                # with st.spinner('서비스 상태 조회중...'):
                status, chart_url, _ = config.get_service_chart_mapdf(selected_code, need_map=False)
                st.session_state.status_cache[selected_code] = (status, chart_url)

            with st.container():
                # 상태
                if 'No problem' in status:
                    color = '#66FF6680'  # 'green'
                    status = '☻'
                elif status == 'Some problems detected':
                    color = '#FFCC6680'  # 'orange'
                    status = '☁︎'
                    st.toast(f'**{selected_name}** 서비스 문제 발생!', icon="🚨")
                else:  # 'Problems detected':
                    color = '#FF666680'  # 'red'
                    status = '☠︎'
                    st.toast(f'**{selected_name}** 서비스 중대 문제 발생!', icon="🚨")

                # st.write(f'<a href="{hyperlink}">**{selected_name}**  👉 :{color}[{status}]</a>',
                #          unsafe_allow_html=True)
                service_code_name_index = st.session_state.companies_list.index(item)

                st.markdown(f'<style>.element-container:has(#button-after{service_code_name_index}) + div button '
                            """{
                    font-size: 3px;   /* 글자 크기 */
                    line-height: 1;
                    padding: 0px 10px; /* 버튼 안쪽 여백 (위/아래, 좌/우) */
                    margin: 0;       /* 버튼 바깥쪽 여백 */
                    border: 0px solid #ccc; /* 테두리 설정 */"""
                            f'background-color: {color}; /* 배경색 설정 */\n'
                            """
                    text-align: center;/* 텍스트 가운데 정렬 */
                    border-radius: 10px; /* 모서리 둥글게 */
                 }</style>""", unsafe_allow_html=True)

                st.markdown(f'<span id="button-after{service_code_name_index}"></span>', unsafe_allow_html=True)
                if st.button(f"{selected_name}", ):  # {status}
                    st.session_state.service_code_name_index = service_code_name_index
                    logging.info(f'버튼 눌림!!! {service_code_name_index=}')
                    st.switch_page('news_bot.py')

                if st.session_state.display_chart:
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


# 사이드바에 타이머 표기
st.sidebar.divider()

# 타이머를 표시할 위치 예약
timer_placeholder = st.sidebar.empty()

# 카운트다운 초 계산
if st.session_state.refresh_timer_cache <= 0:
    st.session_state.refresh_timer_cache = refresh_timer * 60

# 타이머 실행
while st.session_state.refresh_timer_cache >= 0:
    # 타이머 갱신
    timer_placeholder.markdown(f"⏳ Refresh까지 {st.session_state.refresh_timer_cache}초")

    # 1초 대기
    time.sleep(1)

    # 타이머 감소
    st.session_state.refresh_timer_cache -= 1

# 타이머 완료 메시지
timer_placeholder.markdown("## ⏰ 타이머 완료!")
st.session_state.status_cache = dict()
logging.info('새로 고침!!!')
st.rerun()

