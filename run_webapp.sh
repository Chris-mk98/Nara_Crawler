#!/bin/bash
# 나라장터 자동 수집 웹 서비스 실행 스크립트
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# .env 파일 확인
if [ ! -f "$ROOT/.env" ]; then
  echo "⚠️  .env 파일이 없습니다. .env.example을 복사한 뒤 설정을 입력하세요."
  echo "   cp .env.example .env"
  exit 1
fi

# 의존성 설치 (가상환경 활성화 전제)
pip install -q -r "$ROOT/requirements.txt"

echo "🚀 웹 서비스 시작: http://localhost:8000"
cd "$ROOT"
uvicorn webapp.main:app --host 0.0.0.0 --port 8000 --reload
