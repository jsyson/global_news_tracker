import config
import dashboard_dd


# 세션상태 방어 코드
config.init_session_state()


# # # # # # # # # # # # # # # # # # # #
# 웹 페이지 구성
# # # # # # # # # # # # # # # # # # # #


dashboard_dd.make_all_dashboard_tabs('JP', icon='🇯🇵')

