import streamlit as st
import logging
import config
import time
import pandas as pd
import pytz
import re
from datetime import datetime
import altair as alt
import numpy as np
import base64

# 로깅 설정
# logging.basicConfig(level=logging.INFO)


# 세션상태 방어 코드
config.init_session_state()


# 리포트 차트 그리는 함수
def display_chart(chart_list, color_code, chart_height=50):
    if chart_list is None or chart_list == []:
        chart_list = [0] * 96

    chart_data = pd.DataFrame(chart_list, columns=["Report Count"]).dropna().astype('int').reset_index()
    # st.line_chart(chart_data, color=color_code, height=80)

    # Altair를 사용한 라인 차트 생성
    line_chart = alt.Chart(chart_data).mark_line().encode(
        x=alt.X('index', title=None, axis=alt.Axis(labels=False, ticks=False)),  # 축 레이블과 틱 제거
        y=alt.Y('Report Count', title=None, axis=alt.Axis(labels=False, ticks=False)),
        color=alt.value(color_code)
    ).properties(
        height=chart_height  # 차트 높이 설정
    )

    # 최대값이 0이면 이대로 뿌려주고 끝낸다.
    if chart_data['Report Count'].max() == 0:
        # 차트를 Streamlit에 표시
        st.altair_chart(line_chart, use_container_width=True)
        return

    # 최대값이 있을 경우 화면에 표시해준다.
    # 최대값 인덱스 확인
    max_index = chart_data['Report Count'].idxmax()

    color_name = 'red'
    f_size = 25
    if color_code == config.GREEN:
        color_name = 'green'
        f_size = 20
    elif color_code == config.ORANGE:
        color_name = 'orange'
        f_size = 20

    # 큰 차트에서는 숫자 크기도 키운다.
    if chart_height > 100:
        f_size *= 2

    # 최대값을 중앙에 텍스트로 표시하는 mark_text 추가
    text = (alt.Chart(chart_data).mark_text(align='center', baseline='middle', dy=-10, color=color_name, size=f_size).encode(
        x=alt.X('index', title=None),
        y=alt.Y('Report Count', title=None),
        text=alt.condition(
            alt.datum.index == max_index,  # 최대값에만 텍스트 표시
            alt.Text('Report Count:Q'),
            alt.value('')
        )
    ))

    # 차트와 텍스트를 결합하여 표시
    final_chart = line_chart + text

    # 차트를 Streamlit에 표시
    st.altair_chart(final_chart, use_container_width=True)


def click_button(area, selected_service_name):
    logging.info(f'{area} {selected_service_name} 버튼 눌림!')
    st.session_state.selected_area = area
    st.session_state.selected_service_name = selected_service_name
    st.session_state.dashboard_button_clicked = True


# 대시보드 구성 함수
def display_dashboard(area):
    # 최초 캐시 세션 생성
    if st.session_state.status_cache.get(area) is None:
        st.session_state.status_cache[area] = dict()

    target_set = st.session_state.target_service_set_dict[area]
    logging.info(f'{area} 대시보드 구성 시작: {len(target_set)}개 서비스')

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

                # print(st.session_state.companies_list_dict[area])
                if item in st.session_state.companies_list_dict[area]:
                    index_code = st.session_state.companies_list_dict[area].index(item)
                else:
                    index_code = 'None'
                    logging.error(f'{item}이 회사 목록에 없음!!!')

                unique_id = f'btn-{re.sub(r"[^a-zA-Z]", "", item).lower()}-{area.lower()}-{index_code}'
                logging.info(f'{item=} {unique_id}')

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
                if st.button(f"{item}", key=unique_id, on_click=click_button, args=(area, item,)):
                    logging.info(f'버튼 눌림!!! {area=} {item=} {unique_id=}')
                    st.session_state.selected_area = area
                    st.session_state.selected_service_name = item
                    # st.session_state.dashboard_button_clicked = True
                    st.switch_page(config.NEWSBOT_PAGE)

                if st.session_state.display_chart:
                    display_chart(chart_list, color_code)

    with st.expander('Raw Data'):
        st.write(st.session_state.status_df_dict[area])

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
# # # # # # # # # # # # # # # # # # # #


def make_all_dashboard_tabs(area, icon='', image_path=None):
    # 사이드바
    st.session_state.dashboard_auto_tab_timer = st.sidebar.number_input('페이지 자동 전환 주기(초), 0=Off',
                                                                        value=st.session_state.dashboard_auto_tab_timer,
                                                                        format='%d', min_value=0)
    st.session_state.num_dashboard_columns = st.sidebar.number_input('출력 컬럼 수',
                                                                     value=st.session_state.num_dashboard_columns,
                                                                     format='%d', min_value=1)
    st.session_state.dashboard_refresh_timer = st.sidebar.number_input('새로고침 주기(분)',
                                                                       value=st.session_state.dashboard_refresh_timer,
                                                                       format='%d', min_value=3)
    st.session_state.display_chart = st.sidebar.checkbox('리포트 차트 보기', value=st.session_state.display_chart)

    # 메인 페이지
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader(f'Global Service Status - {area} {icon}')

        # Font Awesome CSS를 HTML에 추가
        # st.markdown(
        #     """
        #     <link rel="stylesheet"
        #     href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        #     """,
        #     unsafe_allow_html=True
        # )
        # st.markdown(f'<i class="fa-solid fa-flag-usa"></i> Global Service Status Dashboard - {area}',
        #             unsafe_allow_html=True)

    with col2:
        if image_path:
            # 이미지 파일을 읽어서 Base64로 인코딩
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode()

            st.markdown(
                f"""
                <div style="text-align: right;">
                    <img src="data:image/jpeg;base64,{encoded_image}" width="50">
                </div>
                """,
                unsafe_allow_html=True
            )
            logging.info(f'{image_path} 출력 완료')

    # 탭 설정
    dashboard_tab, config_tab = st.tabs(["대시보드", "감시설정"])

    # # # # # # # # # #
    # 설정 탭
    # # # # # # # # # #

    with config_tab:
        display_config_tab(area)

    # # # # # # # # # #
    # 탭 - 대시보드
    # # # # # # # # # #

    with dashboard_tab:
        display_dashboard(area)

    # # # # # # # # # #
    # 탭 - 대시보드
    # # # # # # # # # #

    if st.session_state.dashboard_button_clicked:
        logging.info('버튼 눌림 처리!')
        st.switch_page(config.NEWSBOT_PAGE)

    # # # # # # # # # #
    # 기타 타이머 관련
    # # # # # # # # # #

    if st.session_state.dashboard_auto_tab_timer > 0:
        logging.info('자동 탭 전환 켜짐')
    elif st.session_state.dashboard_auto_tab_timer == 0:
        logging.info('자동 탭 전환 꺼짐')

    # 최종 업데이트 시각 표시
    st.sidebar.divider()

    kst = pytz.timezone('Asia/Seoul')
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
    st.sidebar.write(f'최종 업데이트 - {current_time}')
    logging.info(f'대시보드 업데이트 완료 : {current_time}')

    # 다음 업데이트 타이머 표기
    st.sidebar.divider()

    # 타이머를 표시할 위치 예약
    timer_placeholder = st.sidebar.empty()

    # 카운트다운 초 계산
    if st.session_state.refresh_timer_cache <= 0:
        st.session_state.refresh_timer_cache = st.session_state.dashboard_refresh_timer * 60
    if st.session_state.auto_tab_timer_cache <= 0:
        st.session_state.auto_tab_timer_cache = st.session_state.dashboard_auto_tab_timer

    # 타이머 실행
    while st.session_state.refresh_timer_cache >= 0:
        # 타이머 갱신
        timer_placeholder.markdown(f"⏳ Refresh까지 {st.session_state.refresh_timer_cache}초")

        # 1초 대기
        time.sleep(1)

        # 타이머 감소
        st.session_state.refresh_timer_cache -= 1
        st.session_state.auto_tab_timer_cache -= 1

        # 대시보드 전환 타이머 처리
        if st.session_state.dashboard_auto_tab_timer > 0 > st.session_state.auto_tab_timer_cache:
            if area == 'US':
                st.switch_page(config.DASHBOARD_JP_PAGE)
            elif area == 'JP':
                st.switch_page(config.DASHBOARD_US_PAGE)

    # 타이머 완료 메시지
    timer_placeholder.markdown("⏰ 카운트다운 완료! 서비스 상태 재검색!")
    st.session_state.status_cache = dict()

    logging.info('새로 고침!!!')
    config.init_status_df()  # 서비스 상태 초기화
    st.rerun()
