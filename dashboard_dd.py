import streamlit as st
import logging
import config
import time
import pandas as pd


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


# 웹 페이지 구성
st.set_page_config(layout="wide")
# st.title('Global IT Dashboard')


# 사이드바
st.session_state.display_chart = st.sidebar.checkbox('리포트 차트 보기', value=True)
st.session_state.num_dashboard_columns = st.sidebar.number_input('출력 컬럼 수',
                                                                 value=st.session_state.num_dashboard_columns,
                                                                 format='%d')
refresh_timer = st.sidebar.number_input('새로고침 주기(분)', value=1, format='%d')


# 메인 페이지
st.subheader('Global Service Status - US')
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
        # config_list = [x.split('/')[1] for x in st.session_state.companies_list]  # 서비스 이름만 잘라낸다.

        for idx, item in enumerate(sorted(st.session_state.companies_list, key=str.lower)):
            col = columns[idx % num_columns]  # 순서대로 컬럼에 아이템 배치

            if item in st.session_state.target_service_set:
                if col.checkbox(item[:15], value=True, help=item):
                    st.session_state.target_service_set.add(item)
            else:
                if col.checkbox(item[:15], help=item):
                    st.session_state.target_service_set.add(item)


# # # # # # # # # #
# 탭1 - 대시보드 탭
# # # # # # # # # #


with dashboard_tab:
    logging.info(f'대시보드 구성 목록:\n{st.session_state.target_service_set}\n')

    # 현재 알람 크롤링 + 레드 알람 목록 가져옴.
    alarm_list = config.get_current_alarm_service_list()
    alarm_list.sort(key=lambda x: x.lower())  # abc 순으로 정렬

    target_list = list(st.session_state.target_service_set)
    target_list_filtered = [item for item in target_list if item not in alarm_list]
    target_list_filtered.sort(key=lambda x: x.lower())  # abc 순으로 정렬

    all_target_list = alarm_list + target_list_filtered

    # num_dashboard_columns = st.session_state.num_dashboard_columns
    dashboard_columns = st.columns(st.session_state.num_dashboard_columns)

    for idx, item in enumerate(all_target_list):
        col = dashboard_columns[idx % st.session_state.num_dashboard_columns]  # 순서대로 컬럼에 아이템 배치

        # selected_code = item.split('/')[0]
        # selected_name = item.split('/')[1]

        # 링크를 만들때 st.session_state.service_code_name_index 를 사용
        # https://your_app.streamlit.app/?first_key=1&second_key=two
        logging.info(f'컬럼{col} : {item=}')

        with col:
            if item in st.session_state.status_cache:
                status, chart_list = st.session_state.status_cache[item]
            else:
                # with st.spinner('서비스 상태 조회중...'):
                status, chart_list, _ = config.get_service_chart_mapdf(item, need_map=False)
                st.session_state.status_cache[item] = (status, chart_list)

            with st.container():
                # 상태
                _, color_code, _ = config.get_status_color(item, status)
                service_code_name_index = st.session_state.companies_list.index(item)

                st.markdown(f'<style>.element-container:has(#button-after{service_code_name_index}) + div button '
                            """{
                    font-size: 3px;   /* 글자 크기 */
                    line-height: 1;
                    padding: 0px 10px; /* 버튼 안쪽 여백 (위/아래, 좌/우) */
                    margin: 0;       /* 버튼 바깥쪽 여백 */
                    border: 0px solid #ccc; /* 테두리 설정 */"""
                            f'background-color: {color_code}; /* 배경색 설정 */\n'
                            """
                    text-align: center;/* 텍스트 가운데 정렬 */
                    border-radius: 10px; /* 모서리 둥글게 */
                    width: 100%; /* 버튼의 너비를 100%로 설정 */
                    height: 100%;
                 }</style>""", unsafe_allow_html=True)

                st.markdown(f'<span id="button-after{service_code_name_index}"></span>', unsafe_allow_html=True)
                if st.button(f"{item}", ):  # {status}
                    st.session_state.service_code_name_index = service_code_name_index
                    logging.info(f'버튼 눌림!!! {service_code_name_index=}')
                    st.switch_page(config.NEWSBOT_PAGE)

                if st.session_state.display_chart and chart_list:
                    logging.info(f'{item} 차트 출력함.')
                    chart_data = pd.DataFrame(chart_list, columns=["Report Count"])
                    st.line_chart(chart_data, color=color_code, height=100)

                elif st.session_state.display_chart and chart_list is None:
                    logging.info(f'{item} 차트 없음.')
                    chart_data = pd.DataFrame([0] * 96, columns=["Report Count"])
                    st.line_chart(chart_data, color=color_code, height=100)


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
timer_placeholder.markdown("⏰ 카운트다운 완료! 서비스 상태 재검색!")
st.session_state.status_cache = dict()

logging.info('새로 고침!!!')
# config.get_service_chart_mapdf(None)  # 서비스 상태 크롤링
st.rerun()

