# Python 3.12 이미지를 기반으로 설정
FROM python:3.12

# 작업 디렉토리 설정
WORKDIR /mnt

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir google-generativeai --verbose
# 애플리케이션 코드 복사
COPY . .


ENV IS_DOCKER=true

# 포트 노출
EXPOSE 8000

# 실행 명령어
CMD ["python", "flask_chat.py"]
