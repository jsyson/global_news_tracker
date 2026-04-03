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
def display_chart(chart_list, color_code, chart_height=50, label_tick=False):
    if chart_list is None or chart_list == []:
        chart_list = [0] * 96

    chart_data = pd.DataFrame(chart_list, columns=["Report Count"]).dropna().astype('int').reset_index()
    chart_data['Time'] = chart_data['index'].apply(lambda x: ((x - 96) * 15) / 60)
    # st.line_chart(chart_data, color=color_code, height=80)

    # Altair를 사용한 라인 차트 생성
    line_chart = alt.Chart(chart_data).mark_line().encode(
        x=alt.X('Time', title=None, axis=alt.Axis(labels=label_tick, ticks=label_tick)),
        y=alt.Y('Report Count', title=None, axis=alt.Axis(labels=label_tick, ticks=label_tick)),
        color=alt.value(color_code)
    ).properties(
        height=chart_height,
        width='container'
    )

    # 최대값이 0이면 이대로 뿌려주고 끝낸다.
    if chart_data['Report Count'].max() == 0:
        # 설정을 여기서 적용하여 단일 차트로 표시
        st.altair_chart(line_chart.configure_view(strokeWidth=0).configure_axis(grid=False), width='stretch')
        return

    # 최대값이 있을 경우 화면에 표시해준다.
    # 최대값 인덱스 확인
    max_index = chart_data['Report Count'].idxmax()

    color_name = 'red'
    f_size = 20
    if color_code == config.GREEN:
        color_name = 'green'
        f_size = 18
    elif color_code == config.ORANGE:
        color_name = 'orange'
        f_size = 19

    # 큰 차트에서는 숫자 크기도 키운다.
    if chart_height > 100:
        f_size *= 2

    # 최대값을 중앙에 텍스트로 표시하는 mark_text 추가
    text = (alt.Chart(chart_data).mark_text(align='center', baseline='middle', dy=-10, color=color_name, size=f_size).encode(
        x=alt.X('Time', title=None),
        y=alt.Y('Report Count', title=None),
        text=alt.condition(
            alt.datum.index == max_index,  # 최대값에만 텍스트 표시
            alt.Text('Report Count:Q'),
            alt.value('')
        )
    ))

    # 차트와 텍스트를 결합하여 표시
    final_chart = (line_chart + text).configure_view(
        strokeWidth=0
    ).configure_axis(
        grid=False
    )

    # 차트를 Streamlit에 표시
    st.altair_chart(final_chart, width='stretch')


def click_button(area, selected_service_name):
    logging.info(f'{area} {selected_service_name} 버튼 눌림!')
    st.session_state.selected_area = area
    st.session_state.selected_service_name = selected_service_name
    st.session_state.dashboard_button_clicked = True


# 대시보드 구성 함수
def display_dashboard(area):
    # 세션 상태 방어 코드 강제 실행
    config.init_session_state()

    # 최초 캐시 세션 생성
    if st.session_state.status_cache.get(area) is None:
        st.session_state.status_cache[area] = dict()

    if area not in st.session_state.target_service_set_dict:
        logging.error(f"target_service_set_dict에 {area} 키가 없음! 초기값으로 복구 시도.")
        st.session_state.target_service_set_dict[area] = config.DEFAULT_COMPANIES_SET_DICT.get(area, set())

    target_set = st.session_state.target_service_set_dict[area]
    logging.info(f'{area} 대시보드 구성 시작: {len(target_set)}개 서비스')

    # 현재 알람 크롤링 + 레드 알람 목록 가져옴.
    alarm_list = config.get_current_alarm_service_list(area=area)
    alarm_list.sort(key=lambda x: x.lower())  # DANGER 서비스들끼리 abc 순 정렬

    # 나머지 서비스들에 대한 정렬 기준 설정 (차트 데이터 보유 여부)
    status_df = st.session_state.status_df_dict.get(area)

    def get_non_alarm_sort_key(name):
        if status_df is not None:
            # 대소문자 구분 없이(upper) Name 컬럼에서 해당 서비스 검색
            match = status_df[status_df[config.get_downdetector_web.NAME].str.upper() == name.upper()]
            if not match.empty:
                val = match.iloc[0][config.get_downdetector_web.VALUES]
                # 차트 데이터 유무 판별 ( [0], [], 빈값 등은 데이터 없음으로 간주 )
                if val and val not in ["[0]", "[]", ""]:
                    return (0, name.lower())  # 1순위: 데이터 있음
                return (1, name.lower())      # 2순위: 데이터 없음
        return (2, name.lower())              # 3순위: 정보 없음

    target_list = list(target_set)
    # 대소문자 구분 없이 알람 목록에 있는지 확인
    alarm_list_upper = [a.upper() for a in alarm_list]
    target_list_filtered = [item for item in target_list if item.upper() not in alarm_list_upper]
    
    # 차트 데이터 유무에 따른 정렬 적용
    target_list_filtered.sort(key=get_non_alarm_sort_key)

    # 전체 리스트 합칠 때 중복 발생 방지
    all_target_list = alarm_list + target_list_filtered
    
    seen = set()
    unique_all_target_list = []
    for x in all_target_list:
        if x.upper() not in seen:
            unique_all_target_list.append(x)
            seen.add(x.upper())

    dashboard_columns = st.columns(st.session_state.num_dashboard_columns)

    for idx, item in enumerate(unique_all_target_list):
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
                # 상태 및 색상 결정
                _, color_code, _ = config.get_status_color(item, status)

                # 차트 데이터 유무 판별
                has_chart_data = False
                if chart_list is not None and len(chart_list) > 0:
                    if max(chart_list) > 0:
                        has_chart_data = True
                
                is_success = (status == config.get_downdetector_web.SUCCESS or status is None)
                if not has_chart_data and is_success:
                    color_code = '#E0E0E0BB'

                if item in st.session_state.companies_list_dict[area]:
                    index_code = st.session_state.companies_list_dict[area].index(item)
                else:
                    index_code = 'None'

                # ID 생성 (알파벳/숫자 포함하도록 수정하여 GTA 5 등 대응)
                safe_name = re.sub(r"[^a-zA-Z0-9]", "", item).lower()
                unique_id = f'btn-{safe_name}-{area.lower()}-{index_code}'
                news_count = st.session_state.news_count_cache.get(area, {}).get(item, 0)

                # 서비스명 길이에 따른 다이나믹 폰트 크기 결정
                name_len = len(item)
                if name_len < 11:
                    f_size = "17px"
                elif name_len < 17:
                    f_size = "15px"
                else:
                    f_size = "13px"

                # 1. 초소형 카드 스타일 및 간격 제거
                st.markdown(f"""
                    <style>
                    /* 컨테이너 간격 강제 제거 */
                    [data-testid="stVerticalBlock"] > div:has(#{unique_id}) {{
                        gap: 0px !important;
                        margin-bottom: -15px !important;
                    }}
                    .service-card-{unique_id} {{
                        /* height: 120px; */ 
                        display: flex;
                        flex-direction: column;
                        padding: 0px;
                        overflow: visible;
                    }}
                    /* 버튼 스타일: 높이 절대 고정 및 텍스트 클램핑 */
                    .element-container:has(#{unique_id}) + div button {{
                        background-color: {color_code} !important;
                        border-radius: 4px !important;
                        height: 48px !important;
                        min-height: 48px !important;
                        max-height: 48px !important;
                        padding: 2px 4px !important;
                        transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                        border: none !important;
                        overflow: hidden !important;
                        display: flex !important;
                        align-items: center !important;
                        justify-content: center !important;
                    }}
                    /* 버튼 내부 텍스트 타겟팅 및 줄 제한 */
                    .element-container:has(#{unique_id}) + div button p {{
                        font-size: {f_size} !important;
                        font-weight: 400 !important;
                        color: #111 !important;
                        line-height: 1.1 !important;
                        margin: 0 !important;
                        padding: 0 !important;
                        display: -webkit-box !important;
                        -webkit-line-clamp: 2 !important; /* 최대 2줄 고정 */
                        -webkit-box-orient: vertical !important;
                        text-overflow: ellipsis !important;
                        overflow: hidden !important;
                        word-break: break-word !important;
                    }}
                    .element-container:has(#{unique_id}) + div button:hover {{
                        transform: translateY(-5px) scale(1.03);
                        box-shadow: 0 10px 20px rgba(0,0,0,0.15);
                        filter: brightness(1.08);
                        z-index: 100;
                    }}
                    /* 배지 컨테이너의 수직 여백 및 공간 강제 제거 */
                    [data-testid="stElementContainer"]:has(#badge-wrapper-{unique_id}) {{
                        height: 0px !important;
                        min-height: 0px !important;
                        margin-top: -16px !important; /* Streamlit 기본 gap 상쇄 */
                        margin-bottom: 0px !important;
                        padding: 0px !important;
                        z-index: 999 !important;
                    }}
                    </style>
                    <div class="service-card-{unique_id}">
                """, unsafe_allow_html=True)

                # 2. 버튼 출력 (앵커 span은 공간 차지 않게 처리)
                st.markdown(f'<span id="{unique_id}" style="display:none;"></span>', unsafe_allow_html=True)
                if st.button(f"{item}", key=unique_id, on_click=click_button, args=(area, item,), use_container_width=True):
                    st.session_state.selected_area = area
                    st.session_state.selected_service_name = item
                    st.switch_page(config.NEWSBOT_PAGE)

                # 뉴스 배지 (상대적 위치로 복구하되 공간은 0으로)
                if news_count > 0:
                    st.markdown(f"""
                        <div id="badge-wrapper-{unique_id}" style="position: relative; height: 0px; top: -58px; pointer-events: none; overflow: visible;">
                            <div style="position: absolute; right: -6px; top: 0px; 
                                        background: #1E1E1E;
                                        color: #FF4B4B; 
                                        border-radius: 10px; 
                                        min-width: 18px; height: 18px; padding: 0 5px;
                                        display: flex; align-items: center; justify-content: center; 
                                        font-size: 10px; font-weight: 900;
                                        border: 1.5px solid #FF4B4B;
                                        box-shadow: 0 0 10px rgba(255, 75, 75, 0.4);
                                        z-index: 1000;">
                                {news_count}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                # 3. 차트 출력 (높이 60px 고정)
                if st.session_state.display_chart:
                    display_chart(chart_list, color_code)  # , chart_height=60)
                else:
                    st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

    with st.expander('Raw Data'):
        if area in st.session_state.status_df_dict:
            st.write(st.session_state.status_df_dict[area])
        else:
            st.write(f"{area} 전체 크롤링 실패!")

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
    st.session_state.dashboard_auto_tab_timer = st.sidebar.number_input('페이지 전환/뉴스 검색 주기(초), 0=Off',
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
        st.caption("Ver 2.0")

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

    # 뉴스 수동 새로고침 버튼
    if st.sidebar.button('뉴스 강제 새로고침'):
        config.background_news_search()
        st.rerun()

    # 타이머 실행
    while st.session_state.refresh_timer_cache >= 0:
        # 타이머 갱신 (통합 타이머 하나만 표시)
        timer_placeholder.markdown(f"⏳ 다음 갱신/전환까지 **{st.session_state.auto_tab_timer_cache}**초")

        # 1초 대기
        time.sleep(1)

        # 타이머 감소
        st.session_state.refresh_timer_cache -= 1
        st.session_state.auto_tab_timer_cache -= 1

        # 대시보드 전환 및 뉴스 검색 트리거 (전환 주기 도달 시)
        if st.session_state.dashboard_auto_tab_timer > 0 and st.session_state.auto_tab_timer_cache <= 0:
            logging.info(f'화면 전환 및 뉴스 검색 시작: {area} -> Next')
            
            # 뉴스 검색 트리거
            config.background_news_search()
            
            # 타이머 리셋
            st.session_state.auto_tab_timer_cache = st.session_state.dashboard_auto_tab_timer
            
            # 페이지 전환
            if area == 'US':
                st.switch_page(config.DASHBOARD_JP_PAGE)
            elif area == 'JP':
                st.switch_page(config.DASHBOARD_US_PAGE)
            break

        # 서비스 전체 데이터 리프레시 주기 도달 시
        if st.session_state.refresh_timer_cache < 0:
            logging.info('서비스 데이터 리프레시 주기 도달')
            break

    # 타이머 완료 메시지
    timer_placeholder.markdown("⏰ 카운트다운 완료! 서비스 상태 재검색!")
    st.session_state.status_cache = dict()

    logging.info('새로 고침!!!')
    config.init_status_df()  # 서비스 상태 초기화
    st.rerun()
