# Global News Tracker

## 개요
Downdetector와 Google News를 기반으로 글로벌 서비스들의 장애 현황과 관련 뉴스를 추적하는 대시보드입니다.

## 설치
프로젝트 실행에 필요한 라이브러리들을 설치합니다.

```bash
pip install -r requirements.txt
```

## 실행
아래 명령어를 사용하여 Streamlit 대시보드를 실행합니다.

```bash
streamlit run main.py
```

## 프로젝트 구조
- `main.py`: Streamlit 앱의 메인 실행 파일
- `pages/`: 대시보드의 각 페이지 구성
- `config.py`: 각종 운용자 설정
- `dashboard_dd.py`: 대시보드 화면 구성
- `get_downdetector_web.py`: 웹사이트 크롤링 
- `requirements.txt`: 프로젝트에 필요한 Python 라이브러리 목록
