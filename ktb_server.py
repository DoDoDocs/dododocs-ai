import logging
import time
from fastapi import FastAPI, HTTPException, status 
import uvicorn
from ktb_src import *  # 전체 경로를 명시
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import shutil

# 로깅 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

app = FastAPI()

class DocRequest(BaseModel):
    git_path: str
    s3_path: str

class ChatRequest(BaseModel):
    git_path: str
    query: str
    chat_history: Optional[List[Dict[str, Any]]] = None


@app.post("/generate_doc")
async def generate_doc(request: DocRequest):
    """Git 저장소에서 서비스 코드를 분석하여 문서 생성"""
    clone_dir = None
    repo_path = None
    try:
        start_time = time.perf_counter()
        clone_dir, output_directory, repo_name = parse_repo_url(request.git_path)
        print("start")
        repo_path = repo_name+".zip"
        try:
            download_zip_from_s3(bucket_name, request.s3_path, repo_path)
            extract_zip(repo_path, clone_dir)
        except Exception as s3_error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"S3 작업 실패: {str(s3_error)}"
            )

        java_files = file_list(clone_dir)
        directory_path = check_service_annotation(java_files)

        if directory_path:
            try:
                await generate_docs_async(directory_path, output_directory)
                logger.info("문서 생성 완료")
                
                await summarize_docs_async(output_directory)
                logger.info("문서 요약 완료")
            except Exception as doc_error:
                logger.error(f"문서 생성 중 오류 발생: {str(doc_error)}")
                # 문서 생성 실패해도 계속 진행

        try:
            readme_content = await generate_readme(request.git_path, clone_dir, max_tokens=MAX_TOKEN_LENGTH)
            usage_content = await generate_usage(request.git_path, clone_dir, max_tokens=MAX_TOKEN_LENGTH)
            final_content = update_readme_with_usage(readme_content, usage_content)
            
            readme_file_path = os.path.join(clone_dir, "README.md")
            
            if final_content:
                try:
                    with open(readme_file_path, "w", encoding="utf-8") as f:
                        f.write(final_content)
                    logger.info("README.md 생성 완료")
                except IOError as io_error:
                    logger.error(f"README.md 파일 쓰기 실패: {str(io_error)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="README 파일 생성 실패"
                    )
            else:
                logger.warning("README 내용이 비어있습니다")
        except Exception as readme_error:
            logger.error(f"README 생성 중 오류 발생: {str(readme_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"README 생성 실패: {str(readme_error)}"
            )

        try:
            description = read_description_from_readme(readme_file_path)
            image_url, image_path = generate_image(description, clone_dir)
            update_readme_with_image(file_path=readme_file_path)
            logger.info("이미지 생성 및 README 업데이트 완료")
        except Exception as image_error:
            logger.error(f"이미지 생성 중 오류 발생: {str(image_error)}")
            # 이미지 생성 실패해도 계속 진행
            image_url = None
            image_path = None

        if directory_path:
            try:
                doc_count = add_data_to_db(repo_name, output_directory)
                logger.info(f"DB에 {doc_count}개의 청크 추가 완료")
            except Exception as db_error:
                logger.error(f"DB 추가 중 오류 발생: {str(db_error)}")
                # DB 추가 실패해도 계속 진행

        end_time = time.perf_counter()
        print(f"전체 처리 시간: {end_time - start_time} 초")

        upload_key = output_directory.rstrip('/').lstrip('./')+".zip"

        create_zip(clone_dir, repo_name+".zip")
        upload_zip_to_s3(bucket_name, repo_name+".zip", repo_name+".zip")

        url = get_presigned_url(bucket_name, "README_test.md.zip")

        return { 
            "status": "success",
            "message": f"Documentation generated successfully for {repo_name}",
            "image_url": image_url,
            "url": url,
            "upload_key": upload_key
        }

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error in document generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
    finally:
        # cleanup 로직을 finally 블록으로 이동
        try:
            if repo_path and os.path.exists(repo_path):
                os.remove(repo_path)
                print(f"repo_path 파일이 삭제되었습니다: {repo_path}")

            if clone_dir and os.path.exists(clone_dir):
                shutil.rmtree(clone_dir)
                print(f"clone_dir 디렉토리가 삭제되었습니다: {clone_dir}")

            if clone_dir:
                user_path = os.path.join('.', clone_dir.split('/')[1])
                if os.path.exists(user_path):
                    shutil.rmtree(user_path)
                    print(f"user_path 디렉토리가 삭제되었습니다: {user_path}")

        except Exception as cleanup_error:
            logger.error(f"Cleanup failed: {str(cleanup_error)}")
    
    

@app.post("/chat")
async def chat(request: ChatRequest):
    """사용자 쿼리에 대한 응답 생성"""
    try:
        if not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty"
            )

        response = codebase_chat(request.query, request.git_path, request.chat_history)
        
        return StreamingResponse(
            response, 
            media_type="text/plain",
            headers={
                "X-Error-Message": "None"
            }
        )

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        # 에러가 발생해도 스트리밍 응답을 보내되, 에러 메시지를 포함
        async def error_stream():
            yield f"Error occurred: {str(e)}"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/plain",
            headers={
                "X-Error-Message": str(e)
            }
        )

if __name__ == "__main__":
    try:
        # 초기 설정
        port = int(os.getenv("PORT", 8000))
        logger.info("Initializing test repository...")

        # FastAPI 서버 실행
        logger.info("Starting FastAPI server...")
        uvicorn.run(
            "ktb_server:app",
            host="0.0.0.0",
            port=port,
            reload=False,  # 개발 환경에서 코드 변경 시 자동 재시작
            reload_dirs=["ktb_final_project"],
            workers=4     # 워커 프로세스 수
        )

    except Exception as e:
        logger.error(f"Server initialization failed: {str(e)}")
        raise