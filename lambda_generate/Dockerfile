# AWS Lambda Python 3.12 베이스 이미지 사용
FROM public.ecr.aws/lambda/python:3.12

# 작업 디렉토리 설정 (기본적으로 /var/task)
WORKDIR /var/task

# requirements.txt 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# Lambda 핸들러 지정
# CMD 형식: ["파일명.함수명"]
CMD ["lambda_generate.lambda_handler"]
