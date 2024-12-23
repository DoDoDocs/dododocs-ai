from ktb_prompts import *
from ktb_settings import *
from ktb_func import *

import os
from typing import List, Dict, Any
from pathlib import Path
import logging
import tiktoken
import aiofiles

"""**FUNCTION FOR CHAT**"""
# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


async def process_file(file_path: Path, vector_store, file_metadata) -> List[Dict[str, Any]]:
    """파일을 처리하고 청크 데이터를 반환"""
    chunk_data_list = []
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            doc = await file.read()
            if doc.strip():
                chunks = embedding_chunker.chunk(doc)

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
                        for i in range(len(chunk_contents)):
                            chunk_data_list.append({
                                "document": chunk_contents[i],
                                "metadata": chunk_metadatas[i],
                                "id": chunk_ids[i]
                            })
    except UnicodeDecodeError as e:
        print(f"Unicode decode error in file {
              str(file_path)}: {str(e)}")
    except Exception as e:
        print(f"Error processing file {
              str(file_path)}: {str(e)}")
    return chunk_data_list


# async def add_data_to_db(db_name: str, path: str, file_type: List[str]) -> int:
#     """DB에 데이터를 추가"""
#     try:
#         vector_store = chroma_client.get_or_create_collection(
#             name=db_name,
#             embedding_function=embedding_function,
#             metadata=DISTANCE
#         )
#         repo_path = Path(path)
#         total_files_processed = 0
#         processed_files = set()
#         logger.info(f"repo_path: {repo_path}")

#         async def process_file(file_path: Path, vector_store, file_metadata) -> int:
#             """파일을 처리하고 벡터 스토어에 추가, 이미 처리된 파일은 건너뜁니다."""
#             if file_path in processed_files:
#                 logger.info(f"Skipping already processed file: {
#                             str(file_path)}")
#                 return 0
#             try:
#                 async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
#                     doc = await file.read()
#                     if doc.strip():
#                         chunks = embedding_chunker.chunk(doc)
#                         logger.info(f"file path : {
#                                     str(file_path)}, chunks size : {len(chunks)}")
#                         if chunks:
#                             chunk_contents = [
#                                 str(chunk.text).replace('\n', ' ').strip()
#                                 for chunk in chunks if chunk.text
#                             ]
#                             if chunk_contents:
#                                 chunk_ids = [
#                                     f"{file_path}_{i}"
#                                     for i in range(len(chunk_contents))
#                                 ]
#                                 chunk_metadatas = [
#                                     {k: str(v)
#                                      for k, v in file_metadata.items()}
#                                     for _ in range(len(chunk_contents))
#                                 ]
#                                 vector_store.upsert(
#                                     documents=chunk_contents,
#                                     metadatas=chunk_metadatas,
#                                     ids=chunk_ids
#                                 )
#                                 processed_files.add(file_path)
#                                 return len(chunk_contents)

#             except UnicodeDecodeError as e:
#                 logger.error(f"Unicode decode error in file {
#                              str(file_path)}: {str(e)}")
#             except Exception as e:
#                 logger.error(f"Error processing file {
#                              str(file_path)}: {str(e)}")
#             return 0

#         for root, _, files in os.walk(repo_path):
#             for filename in files:
#                 if filename == '.DS_Store':
#                     continue
#                 if any(filename.endswith(ft) or filename == ft for ft in file_type):
#                     file_path = Path(root) / filename
#                     if file_path.is_file():
#                         file_metadata = {
#                             "filename": filename,
#                             "path": str(file_path),
#                             "repository": str(db_name) if not isinstance(db_name, str) else db_name
#                         }
#                         chunks_added = await process_file(
#                             file_path, vector_store, file_metadata)
#                         if chunks_added > 0:
#                             total_files_processed += chunks_added

#         if total_files_processed == 0:
#             logger.error("No valid files were processed")
#             return 0

#         total_chunks = vector_store.count()
#         print(f"Successfully processed {total_files_processed} files with total {
#               total_chunks} chunks in {db_name}")
#         return total_chunks
#     except Exception as e:
#         logger.error(f"Error adding data to DB: {str(e)}")
#         raise


async def add_data_to_db(db_name: str, path: str, file_type: List[str]) -> int:
    """DB에 데이터를 추가"""
    try:
        vector_store = chroma_client.get_or_create_collection(
            name=db_name,
            embedding_function=embedding_func,
            metadata=DISTANCE
        )
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

        batch_size = 30  # 배치 크기 설정
        for i in range(0, len(all_file_paths), batch_size):
            try:
                batch_paths = all_file_paths[i:i + batch_size]
                batch_chunk_data = []
                for file_path in batch_paths:
                    if file_path in processed_files:
                        print(f"Skipping already processed file: {
                              str(file_path)}")
                        continue
                    file_metadata = {
                        "filename": file_path.name,
                        "path": str(file_path),
                        "repository": str(db_name)
                    }
                    chunk_data_list = await process_file(
                        file_path, vector_store, file_metadata)
                    if chunk_data_list:
                        batch_chunk_data.extend(chunk_data_list)
                        processed_files.add(file_path)
                if batch_chunk_data:
                    documents = [item["document"] for item in batch_chunk_data]
                    metadatas = [item["metadata"] for item in batch_chunk_data]
                    ids = [item["id"] for item in batch_chunk_data]
                    vector_store.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    total_files_processed += len(batch_chunk_data)
            except Exception as e:
                logger.error(f"Error processing batch: {str(e)}")
                continue

        if total_files_processed == 0:
            print("No valid files were processed")
            print(f"{db_name}")
            print(f"{path}")
            return 0

        total_chunks = vector_store.count()
        print(f"Successfully processed {total_files_processed} files with total {
              total_chunks} chunks in {db_name}")
        return total_chunks
    except Exception as e:
        logger.error(f"Error adding data to DB: {str(e)}")
        raise
