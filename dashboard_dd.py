import streamlit as st
import logging
import config
import time
import pandas as pd
import re


# 로깅 설정
logging.basicConfig(level=logging.INFO)


# 대시보드 구성 함수
def display_dashboard(area):
    # 최초 캐시 세션 생성
    if st.session_state.status_cache.get(area) is None:
        st.session_state.status_cache[area] = dict()

    target_set = st.session_state.target_service_set_dict[area]
    logging.info(f'{area} 대시보드 구성 목록:\n{target_set}\n')

    # 현재 알람 크롤링 + 레드 알람 목록 가져옴.
    alarm_list = config.get_current_alarm_service_list(area=area)
    alarm_list.sort(key=lambda x: x.lower())  # abc 순으로 정렬

    target_list = list(target_set)
    target_list_filtered = [item for item in target_list if item not in alarm_list]
    target_list_filtered.sort(key=lambda x: x.lower())  # abc 순으로 정렬

    all_target_list = alarm_list + target_list_filtered

    dashboard_columns = st.columns(st.session_state.num_dashboard_columns)

    for idx, item in enumerate(all_target_list):
        col = dashboard_columns[idx % st.session_state.num_dashboard_columns]  # 순서대로 컬럼에 아이템 배치
        # logging.info(f'{area} 컬럼{idx} : {item=}')

        with col:
            if item in st.session_state.status_cache[area]:
                # cache hit
                status, chart_list = st.session_state.status_cache[area][item]
            else:
                # cache miss
                # with st.spinner('서비스 상태 조회중...'):
                status, chart_list, _ = config.get_service_chart_mapdf(area=area, service_name=item)
                st.session_state.status_cache[area][item] = (status, chart_list)

            with st.container():
                # 상태
                _, color_code, _ = config.get_status_color(item, status)

                unique_id = f'button-after-{re.sub(r"[^a-zA-Z]", "", item)}-{area}'

                st.markdown(f'<style>.element-container:has(#{unique_id})'
                            ' + div button '
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

                st.markdown(f'<span id="{unique_id}"></span>', unsafe_allow_html=True)
                if st.button(f"{item}", key=unique_id):  # {status}
                    st.session_state.selected_area = area
                    st.session_state.selected_service_name = item
                    logging.info(f'버튼 눌림!!! {area=} {item=}')
                    st.switch_page(config.NEWSBOT_PAGE)

                if st.session_state.display_chart and chart_list:
                    # logging.info(f'{area} {item} 차트 출력함.')
                    chart_data = pd.DataFrame(chart_list, columns=["Report Count"])
                    st.line_chart(chart_data, color=color_code, height=80)

                elif st.session_state.display_chart and chart_list is None:
                    # logging.info(f'{area} {item} 차트 없음.')
                    chart_data = pd.DataFrame([0] * 96, columns=["Report Count"])
                    st.line_chart(chart_data, color=color_code, height=80)

    logging.info(f'{area} 대시보드 구성 완료.\n')


def display_config_tab(area):
    # 최초 리스트 생성
    if st.session_state.companies_list_dict.get(area) is None:
        st.session_state.companies_list_dict[area] = list()

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

        for idx, item in enumerate(sorted(st.session_state.companies_list_dict[area], key=str.lower)):
            col = columns[idx % num_columns]  # 순서대로 컬럼에 아이템 배치

            if item in st.session_state.target_service_set_dict[area]:
                if col.checkbox(item[:12], value=True, help=item, key=item + ' ' + area):
                    st.session_state.target_service_set_dict[area].add(item)
            else:
                if col.checkbox(item[:12], help=item, key=item + ' ' + area):
                    st.session_state.target_service_set_dict[area].add(item)


# # # # # # # # # # # # # # # # # # # #


# 웹 페이지 구성
st.set_page_config(layout="wide")
# st.title('Global IT Dashboard')


# 사이드바
st.session_state.display_chart = st.sidebar.checkbox('리포트 차트 보기', value=st.session_state.display_chart)
st.session_state.num_dashboard_columns = st.sidebar.number_input('출력 컬럼 수',
                                                                 value=st.session_state.num_dashboard_columns,
                                                                 format='%d')
st.session_state.dashboard_refresh_timer = st.sidebar.number_input('새로고침 주기(분)',
                                                                   value=st.session_state.dashboard_refresh_timer,
                                                                   format='%d')


# 메인 페이지
st.subheader('Global Service Status')
dashboard_us_tab, dashboard_jp_tab, config_us_tab, config_jp_tab = st.tabs(["대시보드(US)", "대시보드(JP)",
                                                                            "감시설정(US)", "감시설정(JP)"])


# # # # # # # # # #
# 탭3 - 설정 탭(미국)
# # # # # # # # # #


with config_us_tab:
    display_config_tab('US')


# # # # # # # # # #
# 탭4 - 설정 탭(일본)
# # # # # # # # # #


with config_jp_tab:
    display_config_tab('JP')


# # # # # # # # # #
# 탭1 - 대시보드 미국
# # # # # # # # # #


with dashboard_us_tab:
    display_dashboard('US')


# # # # # # # # # #
# 탭2 - 대시보드 일본
# # # # # # # # # #


with dashboard_jp_tab:
    display_dashboard('JP')


# 사이드바에 타이머 표기
st.sidebar.divider()

# 타이머를 표시할 위치 예약
timer_placeholder = st.sidebar.empty()

# 카운트다운 초 계산
if st.session_state.refresh_timer_cache <= 0:
    st.session_state.refresh_timer_cache = st.session_state.dashboard_refresh_timer * 60

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
config.init_status_df()  # 서비스 상태 초기화
st.rerun()

