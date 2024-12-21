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


async def process_file(file_path: Path, vector_store, file_metadata, chunk_id_counter: int) -> int:
    """파일을 처리하고 벡터 스토어에 추가"""
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            doc = await file.read()
            if doc.strip():
                if file_path.suffix == '.md':
                    chunks = embedding_chunker.chunk(doc)
                    if chunks:
                        chunk_contents = [
                            chunk.text.replace('\n', ' ').strip()
                            for chunk in chunks if chunk.text.strip()
                        ]
                        if chunk_contents:
                            chunk_ids = [
                                f"{file_path}_{i}"
                                for i in range(chunk_id_counter, chunk_id_counter + len(chunk_contents))
                            ]
                            chunk_metadatas = [
                                file_metadata for _ in range(len(chunk_contents))]
                            vector_store.upsert(
                                documents=chunk_contents,
                                metadatas=chunk_metadatas,
                                ids=chunk_ids
                            )
                            # print(f"Successfully processed file: {
                            #       file_metadata["filename"]} - Added {len(chunks)} chunks")
                            return len(chunk_contents)
                else:
                    if len(tiktoken.encoding_for_model(EMBEDDING_MODEL).encode(doc)) <= 8191:
                        # print(f"file: {file_metadata["filename"]} len: {
                        #       len(tiktoken.encoding_for_model(EMBEDDING_MODEL).encode(doc))}")
                        vector_store.upsert(
                            documents=[doc.replace('\n', ' ').strip()],
                            metadatas=[file_metadata],
                            ids=[f"{file_path}"]
                        )
                        # print(f"Successfully processed file: {
                        #       file_metadata["filename"]}")
                        return 1
                    else:
                        # print(f"will chunk file: {file_metadata["filename"]} len: {
                        #       len(tiktoken.encoding_for_model(EMBEDDING_MODEL).encode(doc))}")
                        max_chunk_size = 8192
                        overlap_size = 100
                        chunks = [
                            doc[i:i + max_chunk_size]
                            for i in range(0, len(doc), max_chunk_size - overlap_size)
                        ]
                        chunk_ids = [
                            f"{file_path}_{i}"
                            for i in range(chunk_id_counter, chunk_id_counter + len(chunks))
                        ]
                        chunk_metadatas = [
                            file_metadata for _ in range(len(chunks))]
                        vector_store.upsert(
                            documents=chunks,
                            metadatas=chunk_metadatas,
                            ids=chunk_ids
                        )
                        print(f"Successfully processed file: {
                              file_metadata["filename"]} - Added {len(chunks)} chunks")
                        return len(chunks)
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error in file {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
    return 0


async def add_data_to_db(db_name: str, path: str, file_type: List[str]) -> int:
    """DB에 데이터를 추가"""
    try:
        # db_list = chroma_client.list_collections()
        # collection_names = [collection.name for collection in db_list]
        # if db_name in collection_names:
        #     chroma_client.delete_collection(db_name) -> 동시에 같은 컬렉션 생성 / 수정 시 오류 발생
        vector_store = chroma_client.get_or_create_collection(
            name=db_name,
            embedding_function=embedding_function,
            metadata=DISTANCE
        )
        repo_path = Path(path)
        total_files_processed = 0
        chunk_id_counter = 0
        for root, dirs, files in os.walk(repo_path):
            for filename in files:
                if filename == '.DS_Store':
                    continue
                if any(filename.endswith(ft) or filename == ft for ft in file_type):
                    file_path = search_file(repo_path, filename)
                    if file_path and file_path.exists() and file_path.is_file():
                        file_metadata = {
                            "filename": filename,
                            "path": str(file_path),
                            "repository": db_name
                        }
                        chunks_added = await process_file(file_path, vector_store, file_metadata, chunk_id_counter)
                        chunk_id_counter += chunks_added
                        if chunks_added > 0:
                            total_files_processed += 1
        if total_files_processed == 0:
            logger.error("No valid files were processed")
            return 0

        total_chunks = vector_store.count()
        print(f"Successfully processed {total_files_processed} files with total {
              total_chunks} chunks in {db_name}")
        return total_chunks
    except Exception as e:
        logger.error(f"Error adding data to DB: {str(e)}")
        raise
