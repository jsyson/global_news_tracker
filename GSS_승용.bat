@echo off
c:
cd \global_news_tracker

call C:\ProgramData\miniconda3\Scripts\activate.bat

call conda activate gss
streamlit run main.py

pause
