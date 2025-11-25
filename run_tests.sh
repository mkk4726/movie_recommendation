#!/bin/bash

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🧪 Running Tests..."
echo "========================================"

# pytest 실행 (uv run을 통해 가상환경 내에서 실행)
# pyproject.toml에 설정된 옵션(-v, testpaths 등)이 자동으로 적용됩니다.
uv run pytest

# 종료 코드 확인
if [ $? -eq 0 ]; then
    echo "========================================"
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo "========================================"
    echo -e "${RED}❌ Tests failed.${NC}"
    exit 1
fi
