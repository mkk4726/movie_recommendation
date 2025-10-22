#!/bin/bash
# 메모리 디버그 모드로 Streamlit 앱 실행

echo "🐛 디버그 모드로 Streamlit 앱을 시작합니다..."
echo "메모리 사용량이 사이드바에 표시됩니다."
echo ""

# 디버그 모드 환경변수 설정
export DEBUG_MEMORY=true

# Streamlit 실행
cd "$(dirname "$0")"
streamlit run streamlit_app.py

# 스크립트 종료 시 환경변수 해제
unset DEBUG_MEMORY

