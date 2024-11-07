from ktb_prompts import *
from ktb_settings import *
from ktb_docs import *

import re
import os
from typing import List, Dict, Optional, Tuple, Any, Generator
import asyncio
import aiohttp
import tiktoken
from PIL import Image
import requests
import io
import aiofiles
from concurrent.futures import ProcessPoolExecutor

"""**async gpt**"""
async def generate_text_async(session, prompt, contents):
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        json_data = get_json_data(chat_format(prompt, contents))

        async with session.post("https://api.openai.com/v1/chat/completions", json=json_data, headers=headers) as response:
            response_data = await response.json()
            
            if 'error' in response_data:
                print("API 오류:", response_data['error'])
                return None
                
            return response_data['choices'][0]['message']['content']

    except Exception as e:
        print(f"Error summarizing text: {e}")
        return None


async def generate_docs_async(directory_path, output_directory):
    """파일을 카테고리별로 비동기로 요약"""
    service_code_contents = get_code_extention(directory_path)  # 파일 이름과 내용의 리스트를 가져온다고 가정
    async with aiohttp.ClientSession() as session:
        # 각 파일 내용을 비동기로 요약 생성
        tasks = [
            generate_text_async(session, GENERATE_DOC_PROMPT, code_content) 
            for code_content in service_code_contents
        ]

        summaries = await asyncio.gather(*tasks)  # 모든 작업이 완료될 때까지 기다림

        # 파일명과 요약을 쌍으로 묶어 반복
        for filename, summary in zip(directory_path, summaries):
            # 파일명에서 카테고리 결정
            if "Service" in filename:
                category = "Service"
            elif "RestController" in filename:
                category = "RestController"
            elif "Controller" in filename:
                category = "Controller"
            else:
                category = "Others"
            
            # 카테고리 폴더 경로 생성
            category_dir = os.path.join(output_directory, category)
            os.makedirs(category_dir, exist_ok=True)
            
            # 출력 파일 경로 설정
            output_file_name = os.path.join(category_dir, extract_filename(filename).replace('.java', '.md'))
            
            # 파일 저장
            with open(output_file_name, "w", encoding="utf-8") as file:
                file.write(summary)

    return None


def categorize_files(directory):
    """각 카테고리 폴더(Service, Controller, RestController) 내의 파일들을 분류"""
    categories = {
        "Service": [],
        "Controller": [],
        "RestController": []
    }
    
    # 각 카테고리 폴더 확인
    for category in categories.keys():
        category_path = os.path.join(directory, category)
        if os.path.exists(category_path):
            for filename in os.listdir(category_path):
                if filename.endswith(".md"):
                    categories[category].append(filename)
    
    return categories


def find_file_in_directory(directory: str, target_filename: str) -> str:
    """디렉토리를 재귀적으로 검색하여 파일의 전체 경로를 반환"""
    for root, _, files in os.walk(directory):
        if target_filename in files:
            return os.path.join(root, target_filename)
    return None


async def summarize_docs(files, directory, session):
    if not files:  # 빈 리스트 체크
        print(f"No {directory} provided to process")
        return {}
    tasks = []
    
    for filename in files:
        # 전체 파일 경로 구성
        file_path = os.path.join(directory, filename)
        
        try:        
            # 파일이 실제로 존재하고 디렉토리가 아닌지 확인
            if not os.path.isfile(file_path):
                print(f"Skipping directory or non-existent file: {file_path}")
                continue
                
            async with aiofiles.open(file_path, "r", encoding="utf-8") as file:
                text = await file.read()
                tasks.append((filename, generate_text_async(session, SUMMARY_PROMPT, text)))
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            continue
    
    if not tasks:
        print(f"No valid files found in directory: {directory}")
        return {}
    
    try:
        # Run tasks and gather results
        results = await asyncio.gather(*[task[1] for task in tasks])
        
        # Build summaries dictionary for the category
        summaries = {tasks[i][0]: results[i] for i in range(len(tasks)) if results[i] is not None}
        return summaries
    except Exception as e:
        print(f"Error processing tasks: {e}")
        return {}

def summarize_category(files, category, directory):
    # 각 프로세스에서 별도의 aiohttp.ClientSession 생성
    async def run():
        async with aiohttp.ClientSession() as session:
            return await summarize_docs(files, os.path.join(directory, category), session)
    
    return asyncio.run(run())


async def summarize_docs_async(directory):
    category_files = categorize_files(directory)
    summaries = { "Service": {}, "Controller": {}, "RestController": {} }
    
    # ProcessPoolExecutor를 사용하여 멀티프로세싱 적용
    with ProcessPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                executor,
                summarize_category,  # 각 카테고리 요약을 별도의 프로세스에서 실행
                files, category, directory
            )
            for category, files in category_files.items()
        ]
        
        results = await asyncio.gather(*tasks)

        # 결과를 summaries에 저장
        for category, result in zip(category_files.keys(), results):
            summaries[category] = result

    # Write summaries to markdown files asynchronously
    for category, summary_dict in summaries.items():
        output_path = os.path.join(directory, f"{category}_summary.md")
        
        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(f"# {category} Files Summary\n\n")
            for filename, summary in summary_dict.items():
                if summary is not None:
                    await f.write(f"## {filename}\n{summary}\n\n")
        
        print(f"{output_path} file created successfully.")
    
    return None


"""GENERATE README"""
def count_tokens(text: str) -> int:
    """텍스트의 토큰 수를 계산합니다."""
    encoding = tiktoken.encoding_for_model(MODEL)

    # 모든 특수 토큰을 허용
    return len(encoding.encode(text, disallowed_special=()))


def split_context(text: str, max_tokens: int) -> List[str]:
    """텍스트를 최대 토큰 수에 맞춰 분할합니다."""
    encoding = tiktoken.encoding_for_model(MODEL)
    # 모든 특수 토큰을 허용
    tokens = encoding.encode(text, disallowed_special=())

    chunks = []
    current_chunk = []
    current_length = 0

    for token in tokens:
        if current_length + 1 > max_tokens:
            chunks.append(encoding.decode(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(token)
        current_length += 1

    if current_chunk:
        chunks.append(encoding.decode(current_chunk))

    return chunks


def get_source_files(repo_dir: str) -> List[str]:
    """Finds and returns source code build files in the given repository directory."""
    source_files = []
    
    for root, dirs, files in os.walk(repo_dir):
        # Exclude specified directories from the search
        dirs[:] = [d for d in dirs if not any(excl in d for excl in exclude_dirs)]
        
        # Check for specific file names
        for file in files:
            # 파일명이 exclude_dirs에 포함된 문자열을 가지고 있지 않고,
            # build_file_names 중 하나와 일치하는 경우만 포함
            if (not any(excl in file for excl in exclude_dirs) and 
                any(name in file for name in build_file_names)):
                source_files.append(os.path.join(root, file))
    
    return source_files

async def summarize_chunks_batched(chunks, summary_prompt, session, max_tokens_per_batch=1500000):
    all_summaries = []
    batch = []
    batch_token_count = 0
    print("len chunks : ",len(chunks))

    for chunk in chunks:
        chunk_tokens = count_tokens(chunk)
        print("chunk_tokens : ", chunk_tokens)
        if batch_token_count + chunk_tokens > max_tokens_per_batch:
            # Process the current batch if adding this chunk would exceed the limit
            print("tokens : ", batch_token_count)
            batch_summaries = await asyncio.gather(
                *[generate_text_async(session, summary_prompt, c) for c in batch]
            )
            all_summaries.extend(batch_summaries)
            print("배치 처리 완료. 1분 대기 중...")
            await asyncio.sleep(40)
            batch = []  # Reset the batch
            batch_token_count = 0

        batch.append(chunk)
        batch_token_count += chunk_tokens

    # Process any remaining chunks in the last batch
    if batch:
        batch_summaries = await asyncio.gather(
            *[generate_text_async(session, summary_prompt, c) for c in batch]
        )
        all_summaries.extend(batch_summaries)

    return all_summaries


async def generate_readme(repo_url: str, clone_dir: str, max_tokens: int = MAX_TOKEN_LENGTH) -> Optional[str]:
    """Git 저장소를 분석하여 README.md를 생성합니다."""
    try:
        source_files = get_source_files(clone_dir)

        # 소스 코드 컨텍스트 구성
        context = ""
        for file_path in source_files:
            rel_path = os.path.relpath(file_path, clone_dir)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 파일 구분자를 명확하게 하여 특수 문자 충돌 방지
                    context += f"\n\nFILE_START: {rel_path}\n{content}\nFILE_END\n"
            except Exception as e:
                print(f"파일 읽기 오류 ({rel_path}): {str(e)}")
                continue

        token_count = count_tokens(context)
        print(f"Total src files tokens: {token_count}")
        messages = [{"role": "system", "content": PROMPT_README}]

        if token_count > max_tokens:
            chunks = split_context(context, max_tokens)
            print(f"Split into {len(chunks)} chunks")
            
            # aiohttp 세션 생성 및 전달
            async with aiohttp.ClientSession() as session:
                chunk_summaries = await summarize_chunks_batched(chunks, PROMPT_README, session)
                print("chunk_summaries length: ", len(chunk_summaries))
                for i, chunk_summary in enumerate(chunk_summaries, 1):
                    messages.append({"role": "user", "content": chunk_summary})
                    print(f"### 파트 {i} 분석, 길이 : {len(chunk_summary)} 토큰")
                messages.append({"role": "user", "content": f"Create a readme based on the previous conversation history. git repository url : {repo_url}"})
                DOC_RESPONSE, _ = get_completion(messages)
                return DOC_RESPONSE
        else:
            messages.append({"role": "user", "content": context})
            messages.append({"role": "user", "content": f"git repository url : {repo_url}"})
            DOC_RESPONSE, _ = get_completion(
                  messages
                  )
            return DOC_RESPONSE

    except Exception as e:
        print(f"README 생성 중 오류 발생: {str(e)}")
        return None


def get_build_files(repo_dir: str) -> List[str]:
    """Finds and returns source code build files in the given repository directory."""
    source_files = []
    
    for root, dirs, files in os.walk(repo_dir):
        # Exclude specified directories from the search
        dirs[:] = [d for d in dirs if not any(excl in d for excl in exclude_dirs)]
        
        # Check for specific file names
        for file in files:
            # 파일명이 exclude_dirs에 포함된 문자열을 가지고 있지 않고,
            # build_file_names 중 하나와 일치하는 경우만 포함
            if (not any(excl in file for excl in exclude_dirs) and 
                any(name in file for name in build_file_names)):
                source_files.append(os.path.join(root, file))
    
    return source_files


def update_readme_with_usage(readme_content: str, usage_content: str) -> str:
    try:
        # usage_content에서 Getting Started 이후 내용만 추출
        usage_match = re.search(r"## 🚀 Getting Started\n([\s\S]*$)", usage_content)
        if usage_match:
            usage_after_started = usage_match.group(1)  # Getting Started 이후 내용만 가져오기
            
            # readme_content에서 Getting Started 이후 내용 교체
            pattern = r"(## 🚀 Getting Started\n)([\s\S]*$)"
            new_content = re.sub(pattern, 
                               r"\1" + usage_after_started,
                               readme_content)
            print("USAGE가 성공적으로 생성되었습니다.")
            return new_content
    except Exception as e:
        print(f"오류 발생: {e}")
    return readme_content  # 실패 시 원본 반환


async def generate_usage(repo_url: str, clone_dir: str, max_tokens: int = MAX_TOKEN_LENGTH) -> Optional[str]:
    """Git 저장소를 분석하여 README.md를 생성합니다."""
    try:
        source_files = get_build_files(clone_dir)
        # 소스 코드 컨텍스트 구성
        context = ""
        for file_path in source_files:
            rel_path = os.path.relpath(file_path, clone_dir)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 파일 구분자를 명확하게 하여 특수 문자 충돌 방지
                    context += f"\n\nFILE_START: {rel_path}\n{content}\nFILE_END\n"
            except Exception as e:
                print(f"파일 읽기 오류 ({rel_path}): {str(e)}")
                continue

        token_count = count_tokens(context)
        print(f"Total build files tokens: {token_count}")
        messages = [{"role": "system", "content": PROMPT_USAGE}]

        if token_count > max_tokens:
            chunks = split_context(context, max_tokens)
            print(f"Split into {len(chunks)} chunks")
            
            # aiohttp 세션 생성 및 전달
            async with aiohttp.ClientSession() as session:
                chunk_summaries = await summarize_chunks_batched(chunks, PROMPT_USAGE, session)
                for i, chunk_summary in enumerate(chunk_summaries, 1):
                    messages.append({"role": "user", "content": chunk_summary})
                    print(f"### 파트 {i} 분석, 길이 : {len(chunk_summary)} 토큰")
                messages.append({"role": "user", "content": f"Create a readme based on the previous conversation history. git repository url : {repo_url}"})
                DOC_RESPONSE, _ = get_completion(messages)
                return DOC_RESPONSE    
        else:
            messages.append({"role": "user", "content": context})
            messages.append({"role": "user", "content": f"git repo url : {repo_url}"})
            DOC_RESPONSE, _ = get_completion(
                  messages
                  )
            return DOC_RESPONSE

    except Exception as e:
        print(f"USAGE 생성 중 오류 발생: {str(e)}")
        return None


def read_description_from_readme(file_path="README.md"):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            # Description 섹션을 정규 표현식으로 추출
            description_match = re.search(r"Overview\n(.*?)(### Main Purpose)", content, re.S)

            if description_match:
                return description_match.group(1).strip()
            else:
                raise ValueError("Could not find 'Overview' or 'Core Technology Stack' sections in the README.md")
    except FileNotFoundError:
        raise FileNotFoundError(f"File '{file_path}' does not exist.")

# OpenAI API를 사용해 DALL-E로 이미지 생성
def generate_image(description, clone_dir, new_size=(400, 400)):
    response = client_gpt.images.generate(
      model="dall-e-3",
      prompt=DALLE_PROMPT+description,
      size="1024x1024",
      quality="standard",
      n=1,
    )
    image_url = response.data[0].url
    image_data = requests.get(image_url).content
    
    img = Image.open(io.BytesIO(image_data))
    resized_img = img.resize(new_size)

    resized_img.save(clone_dir+"/"+"generated_image.png")

    return image_url, clone_dir+"/"+"generated_image.png"


def update_readme_with_image(file_path="README.md", image_path="./generated_image.png"):
    with open(file_path, "r+", encoding="utf-8") as file:
        content = file.read()

        # 'Preview' 섹션 뒤에 이미지를 삽입
        new_content = re.sub(r"(Preview\n)(.*?)(##|$)",
                             f"Preview\n\n<img src='{image_path}' width='400' height='400'/>\n\n\\3",
                             content, flags=re.S)

        # 파일에 변경 사항 쓰기
        file.seek(0)
        file.write(new_content)
        file.truncate()
