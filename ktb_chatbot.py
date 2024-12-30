from ktb_prompts import *
from ktb_settings import *
from ktb_func import *

import os
from typing import List, Dict, Optional, Any, Generator, Union
from pathlib import Path
import logging
import tiktoken
import aiofiles

"""**FUNCTION FOR CHAT**"""
# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


def search_file(repo_path, filename):
    repo_path = Path(repo_path)

    # 경로 안의 모든 파일과 폴더를 탐색
    for file_path in repo_path.rglob(filename):
        return file_path  # 첫 번째로 찾은 파일 반환

    return None  # 파일이 없으면 None 반환


async def process_file(file_path: Path, vector_store, file_metadata) -> int:
    """파일을 처리하고 청크 데이터를 벡터 스토어에 저장"""
    total_chunks = 0
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            doc = await file.read()
            if doc.strip():
                chunks = embedding_chunker.chunk(doc)
                logger.info(f"file path : {
                            str(file_path)}, chunks size : {len(chunks)}")
                if chunks:
                    chunk_contents = [
                        str(chunk).replace('\n', ' ').strip()
                        for chunk in chunks
                    ]
                    if chunk_contents:
                        chunk_ids = [
                            f"{file_path}_{i}"
                            for i in range(len(chunk_contents))
                        ]
                        chunk_metadatas = [
                            {k: str(v)
                            for k, v in file_metadata.items()}
                            for _ in range(len(chunk_contents))
                        ]
                        vector_store.upsert(
                            documents=chunk_contents,
                            metadatas=chunk_metadatas,
                            ids=chunk_ids
                        )
                        total_chunks = len(chunk_contents)
    except Exception as e:
        logger.info(f"file path : {str(file_path)}")
        print(f"Error processing file {str(file_path)}: {str(e)}")
    return total_chunks


async def add_data_to_db(db_name: str, path: str, file_type: List[str] = None) -> int:
    """DB에 데이터를 추가"""
    try:
        vector_store = chroma_client.get_or_create_collection(
            name=db_name,
            embedding_function=embedding_func,
            metadata=DISTANCE
        )

        if not file_type:
            readme_path = os.path.join(path, "README.md")
            if not os.path.isfile(readme_path):
                print(f"README.md 파일이 존재하지 않습니다: {readme_path}")
                return 0  # 처리 실패 시 0 반환
    
            # README.md 파일 vector store에 추가
            file_metadata = {
                "filename": os.path.basename(readme_path),  # 파일명 추출
                "path": readme_path,
                "repository": db_name
            }
            with open(readme_path, "r", encoding="utf-8") as file:
                content = file.read()
    
            vector_store.upsert(
                documents=[content],  
                metadatas=[file_metadata],  
                ids=["readme"]  
            )
            logger.info(f"README.md 파일이 성공적으로 추가되었습니다: {readme_path}")
            return 1  # 처리 성공 시 1 반환

            
        repo_path = Path(path)
        total_files_processed = 0
        processed_files = set()
        all_file_paths = []

        for root, _, files in os.walk(repo_path):
            for filename in files:
                if filename == '.DS_Store':
                    continue
                if any(filename.endswith(ft) or filename == ft for ft in file_type):
                    file_path = Path(root) / filename
                    if file_path.is_file():
                        all_file_paths.append(file_path)

        batch_size = 100  # 배치 크기 설정
        for i in range(0, len(all_file_paths), batch_size):
            try:
                batch_paths = all_file_paths[i:i + batch_size]
                # tasks = []
                for file_path in batch_paths:
                    if file_path in processed_files:
                        logger.info(f"Skipping already processed file: {
                                    str(file_path)}")
                        continue
                    file_metadata = {
                        "filename": file_path.name,
                        "path": str(file_path),
                        "repository": str(db_name)
                    }
                    chunks_added = await process_file(
                        file_path, vector_store, file_metadata)
                    if chunks_added > 0:
                        total_files_processed += chunks_added
                        processed_files.add(file_path)

                logger.info(f"batch size : {len(batch_paths)}")
            except Exception as e:
                print(f"Error processing batch: {str(e)}")
                logger.info(f"batch size : {len(batch_paths)}")
                continue
        if total_files_processed == 0:
            print("No valid files were processed")
            print(f"{db_name}")
            print(f"{path}")
            return 0

        total_chunks = vector_store.count()
        logger.info(f"Successfully processed {total_files_processed} files with total {
                    total_chunks} chunks in {db_name}")
        return total_chunks
    except Exception as e:
        print(f"Error adding data to DB: {str(e)}")
        raise


def db_search(query: str, db: Any, n_results: int = 3) -> Dict[str, Any]:
    """
    Search the vector database for similar documents.

    Args:
        query (str): Search query
        db: ChromaDB collection
        n_results (int): Number of results to return
        threshold (float): Similarity threshold

    Returns:
        Dict[str, Any]: Search results including documents and metadata
    """
    try:
        results = db.query(
            query_texts=query,
            n_results=n_results,
            include=["metadatas", "documents"]
        )
        filenames = [metadata['filename'] for metadata in results['metadatas'][0]]
        logger.info(f"filenames: {filenames}")
        return results, filenames
    except Exception as e:
        print(f"Error in db_search: {e}", exc_info=True)
        raise


def _build_context(retrieved_docs: Dict[str, Any], filenames: List[str]) -> str:
    """Build context string from retrieved documents."""
    context = ""
    if retrieved_docs and filenames:
        for i in range(len(retrieved_docs['documents'][0])):
            if 'filename' in retrieved_docs['metadatas'][0][i]:
                context += f"\nFILENAME: {retrieved_docs['metadatas'][0][i]['filename']}\nFILE DOCUMENT : {
                    retrieved_docs['documents'][0][i]}\n"
    return context


def _create_prompt(query: str, source_context: str, generated_context: str, chat_history: Optional[List[dict]] = None) -> List[Dict[str, str]]:
    """Create a prompt for the LLM."""
    system_prompt = CHATBOT_PROMPT
    user_prompt = f"""
Retrieved Code Content:
{source_context}

Retrieved Document Content:
{generated_context}

User Query / Instruct: {query}
"""
    full_prompt = [{"role": "system", "content": system_prompt}]
    if chat_history:
        full_prompt.extend(chat_history)
    full_prompt.append({"role": "user", "content": user_prompt})
    return full_prompt


def generate_response(query: str, db_list: List[Any], chat_history: Optional[List[dict]] = None, augmented_query: Optional[str] = None, stream: bool = False) -> str:
    """Generate a response using LLM based on retrieved documents."""
    try:
        if augmented_query:
            retrieved_docs_source, filenames_source = db_search(
                augmented_query, db_list[0])
            retrieved_docs_generated, filenames_generated = db_search(
                augmented_query, db_list[1], n_results=2)
        else:
            retrieved_docs_source, filenames_source = db_search(
                query, db_list[0])
            retrieved_docs_generated, filenames_generated = db_search(
                query, db_list[1], n_results=2)

        source_context = _build_context(
            retrieved_docs_source, filenames_source)
        generated_context = _build_context(
            retrieved_docs_generated, filenames_generated)

        full_prompt = _create_prompt(
            query, source_context, generated_context, chat_history)

        client_gpt = get_openai_client()
        response = client_gpt.chat.completions.create(
            model=GPT_MODEL,
            messages=full_prompt,
            temperature=0.32,
            stream=False
        )

        response_content = response.choices[0].message.content
        logger.info(f"Generated response for query '{
                    query}': {response_content}")

        return response_content

    except Exception as e:
        print(f"Error in generate_response: {e}", exc_info=True)
        raise


def stream_response(query: str, db_list: List[Any], chat_history: Optional[List[dict]] = None, augmented_query: Optional[str] = None) -> Generator:
    """Generate a streaming response."""
    try:
        if augmented_query:
            retrieved_docs_source, filenames_source = db_search(
                augmented_query, db_list[0])
            retrieved_docs_generated, filenames_generated = db_search(
                augmented_query, db_list[1], n_results=2)
        else:
            retrieved_docs_source, filenames_source = db_search(
                query, db_list[0])
            retrieved_docs_generated, filenames_generated = db_search(
                query, db_list[1], n_results=2)

        source_context = _build_context(
            retrieved_docs_source, filenames_source)
        generated_context = _build_context(
            retrieved_docs_generated, filenames_generated)

        full_prompt = _create_prompt(
            query, source_context, generated_context, chat_history)

        client_gpt = get_openai_client()
        response = client_gpt.chat.completions.create(
            model=GPT_MODEL,
            messages=full_prompt,
            temperature=0.52,
            stream=True
        )

        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                yield content

    except Exception as e:
        print(f"Error in stream_response: {e}", exc_info=True)
        raise


def codebase_chat(query: str, repo_url: str, chat_history: List[dict] = None, stream: bool = False) -> Union[str, Generator]:
    """채팅 응답 생성"""
    try:
        user_name, repo_name = parse_repo_url(repo_url)
        chroma_client = get_chroma_client()
        collection_list = [
            collection.name for collection in chroma_client.list_collections()]
        if f"{user_name}_{repo_name}_source" in collection_list and f"{user_name}_{repo_name}_generated" in collection_list:
            vector_store_source = chroma_client.get_collection(
                name=f"{user_name}_{repo_name}_source",
                embedding_function=get_embedding_function()
            )
            vector_store_generated = chroma_client.get_collection(
                name=f"{user_name}_{repo_name}_generated",
                embedding_function=get_embedding_function()
            )
        else:
            error_msg = f"Collection {user_name}_{repo_name}_source or {
                user_name}_{repo_name}_generated does not exist"
            print(error_msg)
            raise Exception("Collection does not exist")
        db_list = [vector_store_source, vector_store_generated]
        if chat_history:
            total_content = ''.join([msg['content']
                                    for msg in chat_history]) + query
            total_tokens = len(tiktoken.encoding_for_model(
                GPT_MODEL).encode(total_content))
            last_message = chat_history[-1] if total_tokens > MAX_TOKEN_LENGTH else chat_history
        else:
            last_message = None

        augmented_query = query_augmentation(query, last_message)

        if stream:
            logger.info(f"Starting streaming response for query '{query}'")
            return stream_response(query, db_list, last_message, augmented_query)
        else:
            logger.info(f"Starting response generation for query '{query}'")
            return generate_response(query, db_list, last_message, augmented_query, stream)

    except Exception as e:
        print(f"Error in codebase_chat: {e}", exc_info=True)
        raise


def query_augmentation(query: str, chat_history: Optional[List[dict]] = None) -> str:
    """
    주어진 쿼리와 이전 응답을 분석하여 추가 검색이 필요한 정보를 식별하고 검색 쿼리를 생성합니다.

    Args:
        query (str): 사용자 입력 쿼리
        previous_query (str): 이전 쿼리 내용
        previous_response (str): 이전 응답 내용
    Returns:
        str: 증강된 검색 쿼리
    """
    prompt = AUGMENTATION_PROMPT

    if chat_history and len(chat_history) >= 2:
        previous_query = chat_history[-2]['content']
        previous_response = chat_history[-1]['content']
    else:
        previous_query = ""
        previous_response = ""

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Previous Query: {
            previous_query}\nPrevious Response: {previous_response}\nQuery: {query}"}
    ]
    client_gpt = get_openai_client()
    augmented_query = client_gpt.chat.completions.create(
        model=GPT_MODEL,
        messages=messages,
        temperature=0.52,
        max_tokens=150,
    )

    augmented_content = augmented_query.choices[0].message.content
    logger.info(f"Augmented query for original query '{
                query}': {augmented_content}")

    return augmented_content
