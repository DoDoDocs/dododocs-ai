"""문서 처리 관련 코드"""
from dataclasses import dataclass, field
from typing import List, Any, Optional, Set, Dict
import asyncio
import logging
import re
import os
import time
import aiofiles

from ktb_api_client import APIClient
from ktb_prompts import *
from ktb_settings import *
from ktb_func import *
# logger 설정 추가
logger = logging.getLogger(__name__)


@dataclass
class SourceFileInfo:
    """소스 파일의 구조적 정보를 담는 데이터 클래스"""
    package: Optional[str] = None      # 패키지/네임스페이스 (예: com.example.project)
    imports: Set[str] = field(default_factory=set)  # import/using/require 문 집합
    class_name: str = ""              # 클래스/함수명
    content: str = ""                # 파일 전체 내용
    file_type: str = ""             # 파일 타입 (java, py, js 등)

    def __post_init__(self):
        """데이터 유효성 검증 및 기본값 설정"""
        if self.imports is None:
            self.imports = set()

        if self.class_name is None:
            self.class_name = ""

        if self.content is None:
            self.content = ""

        if self.file_type is None:
            self.file_type = ""

    def __str__(self) -> str:
        """사람이 읽기 쉬운 문자열 표현"""
        return (
            f"SourceFileInfo(\n"
            f"  package: {self.package}\n"
            f"  class_name: {self.class_name}\n"
            f"  file_type: {self.file_type}\n"
            f"  imports: {len(self.imports)} items\n"
            f"  content: {len(self.content)} chars\n"
            f")"
        )


class DocumentProcessor:
    """문서 생성 및 처리"""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.source_extensions = {
            '.java': 'java',
            '.py': 'py',
            '.js': 'js',
            '.ts': 'ts',
            '.cpp': 'cpp',
            '.cs': 'cs',
            '.go': 'go'
        }
        self.parsers = {
            'java': self._parse_java_file,
            'py': self._parse_python_file,
            'js': self._parse_javascript_file,
            'ts': self._parse_typescript_file,
            'cpp': self._parse_cpp_file,
            'cs': self._parse_cs_file
        }
        self.ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
        self.PARAMS = {
            "key": os.getenv("GOOGLE_API_KEY")  # 환경 변수에서 API 키 가져오기
            }
        self.HEADERS = {
            "Content-Type": "application/json",
        }

    def _parse_source_file(self, content: str, file_type: str) -> SourceFileInfo:
        """소스 파일 파싱"""
        if file_type in self.parsers:
            return self.parsers[file_type](content)
        return self._parse_generic_file(content, file_type)

    def _parse_java_file(self, content: str) -> SourceFileInfo:
        """Java 파일 파싱"""
        imports = set(re.findall(r'^import\s+[\w.*]+;', content, re.MULTILINE))
        package_match = re.search(
            r'^package\s+([\w.]+);', content, re.MULTILINE)
        class_match = re.search(r'(?:class|interface|enum)\s+(\w+)', content)

        package = package_match.group(1) if package_match else None
        class_name = class_match.group(1) if class_match else ""

        return SourceFileInfo(
            package=package,
            imports=imports,
            class_name=class_name,
            content=content,
            file_type='java'
        )

    def _parse_python_file(self, content: str) -> SourceFileInfo:
        """Python 파일 파싱"""
        imports = set(re.findall(
            r'^(?:from\s+[\w.]+\s+)?import\s+[\w.*,\s]+', content, re.MULTILINE))
        class_match = re.search(r'(?:class|def)\s+(\w+)', content)
        class_name = class_match.group(1) if class_match else ""

        return SourceFileInfo(
            package=None,
            imports=imports,
            class_name=class_name,
            content=content,
            file_type='py'
        )

    def _parse_javascript_file(self, content: str) -> SourceFileInfo:
        """JavaScript 파일 파싱"""
        imports = set(re.findall(
            r'^(?:import|require)\s+.*?;?$', content, re.MULTILINE))
        class_match = re.search(r'(?:class|function)\s+(\w+)', content)
        class_name = class_match.group(1) if class_match else ""

        return SourceFileInfo(
            package=None,
            imports=imports,
            class_name=class_name,
            content=content,
            file_type='js'
        )

    def _parse_typescript_file(self, content: str) -> SourceFileInfo:
        """TypeScript 파일 파싱"""
        imports = set(re.findall(
            r'^(?:import|require)\s+.*?;?$', content, re.MULTILINE))
        class_match = re.search(
            r'(?:class|interface|function)\s+(\w+)', content)
        class_name = class_match.group(1) if class_match else ""

        return SourceFileInfo(
            package=None,
            imports=imports,
            class_name=class_name,
            content=content,
            file_type='ts'
        )

    def _parse_cpp_file(self, content: str) -> SourceFileInfo:
        """C++ 파일 파싱"""
        imports = set(re.findall(r'#include\s+[<"].*?[>"]', content))
        class_match = re.search(
            r'(?:class|struct|void|int|bool|char|float|double)\s+(\w+)', content)
        class_name = class_match.group(1) if class_match else ""

        return SourceFileInfo(
            package=None,
            imports=imports,
            class_name=class_name,
            content=content,
            file_type='cpp'
        )

    def _parse_cs_file(self, content: str) -> SourceFileInfo:
        """C# 파일 파싱"""
        imports = set(re.findall(
            r'^using\s+([\w\.]+);', content, re.MULTILINE))
        class_match = re.search(r'(?:class|interface|struct)\s+(\w+)', content)
        class_name = class_match.group(1) if class_match else ""

        return SourceFileInfo(
            package=None,
            imports=imports,
            class_name=class_name,
            content=content,
            file_type='cs'
        )

    def _parse_generic_file(self, content: str, file_type: str) -> SourceFileInfo:
        """기본 파서"""
        return SourceFileInfo(
            package=None,
            imports=set(),
            class_name="",
            content=content,
            file_type=file_type
        )

    async def process_readme(self, repo_url: str, clone_dir: str, readme_key: str, korean: bool, blocks: List[str], metadata: dict = None, max_retries: int = 1) -> List[Any]:
        """모든 문서 처리 태스크 실행"""
        tasks = []
        start_time = time.perf_counter()

        # README 생성 태스크
        readme_task = asyncio.create_task(
            self._generate_readme(repo_url, clone_dir, korean, blocks),
            name="readme_generation"
        )
        tasks.append(readme_task)

        usage_task = asyncio.create_task(
            self._generate_usage(repo_url, clone_dir, korean),
            name="usage_generation"
        )
        tasks.append(usage_task)

        # 모든 태스크 실행 및 결과 반환
        for attempt in range(max_retries):
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                print(f"results length: {len(results)}")
                # 오류가 발생한 태스크 식별 및 재시도
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        print(
                            f"Task {tasks[i].get_name()} failed: {str(result)}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying task {tasks[i].get_name()} (attempt {
                                        attempt + 1}/{max_retries})")
                            if tasks[i].get_name() == "readme_generation":
                                tasks[i] = asyncio.create_task(
                                    self._generate_readme(
                                        repo_url, clone_dir, korean, blocks),
                                    name="readme_generation"
                                )
                            elif tasks[i].get_name() == "usage_generation":
                                tasks[i] = asyncio.create_task(
                                    self._generate_usage(
                                        repo_url, clone_dir, korean),
                                    name="usage_generation"
                                )
                            break  # 재시도 후 다시 gather 실행
                else:
                    # 모든 태스크가 성공적으로 완료된 경우
                    if len(results) > 1 and isinstance(results[0], str) and isinstance(results[1], str):
                        merged_content = self._update_readme_with_usage(
                            results[0], results[1])
                        await self._save_readme(merged_content, clone_dir, readme_key, metadata)
                    elif isinstance(results[0], str):
                        await self._save_readme(results[0], clone_dir, readme_key, metadata)

                    end_time = time.perf_counter()
                    print(f"README 및 Usage 생성 완료 처리 시간: {end_time - start_time} 초")
                    return results

            except Exception as e:
                print(f"Task execution failed: {str(e)}")
                if attempt >= max_retries - 1:
                    raise
                else:
                    logger.info(f"Retrying all tasks (attempt {
                                attempt + 1}/{max_retries})")
                    await asyncio.sleep(2 ** attempt)  # 지수 백오프

        raise Exception("All retries failed for process_readme")

    def get_optimized_source_files(self, repo_dir: str) -> Dict[str, List[SourceFileInfo]]:
        """모든 소스 파일 최적화하여 저장"""
        package_map = {}
        source_extensions = self.source_extensions
        for root, _, files in os.walk(repo_dir):
            # if any(excl in root for excl in EXCLUDE_DIRS):
            #     continue

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in source_extensions:
                    continue

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_info = self._parse_source_file(
                            content,
                            source_extensions[ext]
                        )
                        # 패키지/모듈별로 분류
                        key = file_info.package or os.path.dirname(file_path)
                        if key not in package_map:
                            package_map[key] = []
                        package_map[key].append(file_info)
                except Exception as e:
                    print(f"파일 파싱 오류 ({file_path}): {str(e)}")

        return package_map

    async def _generate_readme(self, repo_url: str, clone_dir: str, korean: bool, blocks: List[str]) -> Optional[str]:
        """README 생성"""
        readme_template = generate_readme_prompt(blocks, korean)
        start_time = time.perf_counter()
        try:
            source_files = self.get_optimized_source_files(clone_dir)
            if not source_files:
                print("소스 파일을 찾을 수 없습니다.")
                return None
            optimized_context = self._build_optimized_context(source_files)
            chunks = chunker.chunk(optimized_context)
            logger.info(f"chunks length : {len(chunks)}")
            # 청크 단위로 처리하고 결과 병합
            result = await self._process_chunks(chunks, repo_url, readme_template, korean)

            logger.info(f"README 생성 완료 처리 시간 : {
                        time.perf_counter() - start_time} 초")
            return result

        except Exception as e:
            print(f"README generation failed: {str(e)}")
            return None

    def _get_build_files(self, repo_dir: str) -> List[str]:
        """빌드 파일 목록 가져오기"""
        build_files = []

        for root, _, files in os.walk(repo_dir):
            if any(excl in root for excl in EXCLUDE_DIRS):
                continue
            # node_modules 디렉토리 체크
            if "node_modules" in root:
                continue

            for file in files:
                file_path = os.path.join(root, file)

                # 일반 빌드 파일 체크
                if file.endswith(tuple(BUILD_FILE_NAMES)) or any(name in file for name in BUILD_FILE_NAMES):
                    print(f"빌드 파일 발견: {file}")
                    build_files.append(file_path)

        if not build_files:
            print(f"빌드 파일을 찾을 수 없습니다: {repo_dir}")

        return build_files

    def _build_files_context(self, build_files: List[str], clone_dir: str) -> str:
        """빌드 파일들의 컨텍스트 구성"""
        context_parts = []
        for file_path in build_files:
            try:
                rel_path = os.path.relpath(file_path, clone_dir)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    context_parts.append(
                        f"FILE_PATH: {rel_path}\nFILE_CONTENT: {
                            content}\nFILE_END\n\n"
                    )
            except Exception as e:
                print(f"파일 읽기 오류 ({rel_path}): {str(e)}")
                continue
        return "".join(context_parts)

    async def _process_chunks(self, chunks: List[str], repo_url: str, prompt: str, korean: bool) -> Optional[str]:
        """청크 비동기 처리"""
        tasks = [
                self.process_chunk(chunk.text, repo_url, prompt)
                for chunk in chunks
            ]
        chunk_summaries = await asyncio.gather(*tasks)  # 이 부분을 블록 안으로 이동
        chunk_summaries = [s for s in chunk_summaries if s]  # None 값 필터링

        if not chunk_summaries:
            return None
        
        if len(chunk_summaries) > 1:
            start_time = time.perf_counter()
            messages = [{"role": "system", "content": prompt}]
            for summary in chunk_summaries:
                messages.append({"role": "user", "content": summary})
            if korean:
                messages.append({
                    "role": "user",
                    "content": f"Create a readme based on the previous information. MUST be in Korean. git repository url : {repo_url}"
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"Create a readme based on the previous information. git repository url : {repo_url}"
                })
            doc_response = self._get_completion(messages)
            end_time = time.perf_counter()
            print(f"README 생성 완료 처리 시간: {end_time - start_time} 초")
            return doc_response
        else:
            return chunk_summaries[0]

    async def _generate_usage(self, repo_url: str, clone_dir: str, korean: bool) -> Optional[str]:
        """Usage 생성"""
        usage_template = generate_readme_prompt(
            ["START_BLOCK"], korean)
        start_time = time.perf_counter()
        try:
            last_slash_index = repo_url.rfind('/')
            repo_url = repo_url[:last_slash_index] + ".git"

            build_files = self._get_build_files(clone_dir)
            context = self._build_files_context(build_files, clone_dir)

            chunks = chunker.chunk(context)
            print(f"Split into {len(chunks)} chunks - USAGE")
            
            result = await self._process_chunks(chunks, repo_url, usage_template, korean)
            end_time = time.perf_counter()
            print(f"USAGE 생성 완료 처리 시간: {end_time - start_time} 초")
            return result

        except Exception as e:
            print(f"Usage generation failed: {str(e)}")
            return None

    def _get_code_contents(self, files: List[str]) -> List[str]:
        """파일 내용 읽기 및 import된 클래스 내용 결합"""
        contents = []
        for file in files:
            total_code = ''
            path = os.path.dirname(file)

            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"파일 읽기 오류 ({file}): {str(e)}")
                contents.append("")
                continue

            imported_classes = self.extract_imported_classes(content)

            for class_name in imported_classes:
                class_path = class_name.replace('.', '/') + '.java'
                full_path = os.path.join(path, class_path)

                if os.path.exists(full_path):
                    try:
                        class_content = self.read_file_content(full_path)
                        total_code += f"Content of {
                            class_name} :\n{class_content}\n\n"
                        # print(f" + Content of {class_name}")
                    except Exception as e:
                        print(f"클래스 파일 읽기 오류 ({full_path}): {str(e)}")
                else:
                    logger.warning(f"클래스 파일을 찾을 수 없습니다: {full_path}")

            total_code += f"code :\n{content}"
            contents.append(total_code)
        return contents

    def _extract_filename(self, filepath: str) -> str:
        """파일 경로에서 파일명 추출"""
        return os.path.basename(filepath)

    def _build_optimized_context(self, package_map: Dict[str, List[SourceFileInfo]]) -> str:
        """최적화된 컨텍스트 생성"""
        context_parts = []

        for package, classes in package_map.items():
            # 패키지별로 공통 import문 처리
            common_imports = set.intersection(
                *[cls.imports for cls in classes])

            context_parts.append(f"\nPACKAGE: {package}")
            if common_imports:
                context_parts.append("COMMON IMPORTS:")
                context_parts.extend(sorted(common_imports))

            # 각 클래스의 고유한 내용만 포함
            for cls in classes:
                unique_imports = cls.imports - common_imports
                class_context = [
                    f"\nCLASS: {cls.class_name}",
                    "UNIQUE IMPORTS:" if unique_imports else "",
                    "\n".join(sorted(unique_imports)),
                    cls.content
                ]
                context_parts.append("\n".join(filter(None, class_context)))

        return "\n".join(context_parts)

    def _get_completion(
        self,  # self 매개변수 추가
        messages: List[Dict],
        model: Optional[str] = MODEL,
        temperature: Optional[float] = TEMPERATURE,
        seed: Optional[int] = SEED,
    ) -> str:
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "seed": seed
        }

        try:
            completion = OpenAI_client.chat.completions.create(**params)
            return completion.choices[0].message.content

        except Exception as e:
            print(f"Completion 생성 오류: {str(e)}")
            return "", None

    def _update_readme_with_usage(self, readme_content: str, usage_content: str) -> str:
        """README 내용에 Usage 내용을 병합합니다.

        Args:
            readme_content (str): 기존 README 내용
            usage_content (str): Usage 섹션 내용

        Returns:
            str: 병합된 README 내용
        """
        try:
            # 수정된 정규 표현식: Getting Started 섹션 시작부터 Motivation 섹션까지
            pattern_readme = r"(## 🚀 Getting Started.*?)(?=## 💡 Motivation|$)"
            pattern_usage = r"(## 🚀 Getting Started.*)"

            readme_match = re.search(pattern_readme, readme_content, re.DOTALL)
            usage_match = re.search(pattern_usage, usage_content, re.DOTALL)

            readme_getting_started = readme_match.group(0)
            usage_getting_started = usage_match.group(0) + "\n\n"

            # Getting Started 섹션을 usage_content의 섹션으로 교체
            new_content = readme_content.replace(
                readme_getting_started, usage_getting_started)

            return new_content

        except Exception as e:
            print(f"README 병합 중 오류: {str(e)}")
            return readme_content

    async def _save_readme(self, content: str, clone_dir: str, readme_key: str, metadata: dict = None):
        """README 파일 저장"""
        #readme_path = os.path.join(clone_dir, "README.md")
        readme_path = "./README.md"
        try:
            async with aiofiles.open(readme_path, "w", encoding="utf-8") as f:
                await f.write(remove_markdown_blocks(content))
            print(f"README가 저장되었습니다: {readme_path}")
            await upload_to_s3(BUCKET_NAME, readme_path, readme_key, metadata)
        except Exception as e:
            print(f"README 저장 중 오류: {str(e)}")

    async def process_chunk(self, chunk: str, repo_url: str, prompt: str) -> Optional[str]:
        """단일 청크 처리"""
        try:
            response = await self.api_client.generate_text_client(prompt, f"git repository url : {repo_url}\n\n" + chunk)
        except Exception as e:
            print(f"Error for chunk")
            return None

        return response


    async def generate_docs(self, directory_path: dict[str, list], 
                            output_directory: str, korean: bool, clone_dir: str):
        """문서만 생성"""
        try:
            # 한국어/영어에 따른 프롬프트 정의
            prompts = {
                'Controller': NEW_PROMPT_ARCHITECTURE_DOC_KOREAN if korean else NEW_PROMPT_ARCHITECTURE_DOC,
                'Test': NEW_PROMPT_TEST_DOC_KOREAN if korean else NEW_PROMPT_TEST_DOC
            }
            all_tasks = []
            for category, files in directory_path.items():
                # Controller와 Test 카테고리만 처리
                if category not in prompts:
                    continue

                code_contents = self._get_code_contents(files)
                all_tasks.extend([
                    (category, filename, content)
                    for filename, content in zip(files, code_contents)
                ])

            chunk_size = 30
            print("generate docs task size: ", len(all_tasks))
            for i in range(0, len(all_tasks), chunk_size):
                chunk = all_tasks[i:i + chunk_size]
                tasks = [
                    self.send_request_with_client(category, prompts[category], content, filename, clone_dir)
                    for category, filename, content in chunk
                ]
                await asyncio.gather(*tasks)
                await asyncio.sleep(1)  # 배치 간 딜레이 추가
            return output_directory

        except Exception as e:
            print(f"문서 생성 실패: {str(e)}")
            return None

    def categorize_files(self, directory):
        """각 카테고리 폴더(Service, Controller, Test) 내의 파일들을 분류"""
        categories = {
            "Controller": [],  # Controller와 RestController를 함께 처리,
            "Test": []
        }

        # 각 카테고리 폴더 확인
        for category in ["Controller", "Test"]:
            category_path = os.path.join(directory, category)
            if os.path.exists(category_path):
                for filename in os.listdir(category_path):
                    if filename.endswith(".md"):
                        categories[category].append(filename)

        return categories

    def read_file_content(self, file_path):
        with open(file_path, 'r') as file:
            return file.read()

    def extract_imported_classes(self, content):
        # Regex to find import statements
        import_pattern = r'import\s+([\w\.]+);'
        matches = re.findall(import_pattern, content)
        return matches

    async def summarize_docs_async_nogenerate(self, directory: str) -> None:
        print("SUMMARIZE_DOCS_ASYNC_with_no_generate")

        category_files = self.categorize_files(directory)
        print(category_files)

        for category in ["Controller", "Test"]:
            category_dir = os.path.join(directory, category)
            if not os.path.exists(category_dir):
                print(f"디렉토리 없음: {category_dir}")
                continue

            summary_content = ""
            for filename in category_files.get(category, []):
                file_path = os.path.join(category_dir, filename)
                try:
                    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                        content = await f.read()
                        # '## SUMMARY' 이후의 내용을 추출하는 정규 표현식
                        match = re.search(
                            r"## SUMMARY\s*(.*)", content, re.DOTALL)
                        if match:
                            summary_content += f"## {filename}\n"
                            summary_content += match.group(1).strip() + "\n\n"
                except Exception as e:
                    print(f"파일 읽기 오류: {file_path}, {str(e)}")
                    continue

            # 추출된 내용을 해당 카테고리 summary.md 파일에 저장
            output_path = os.path.join(
                directory, f"{category}_summary.md")
            try:
                async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                    await f.write(remove_markdown_blocks(summary_content))
                print(f"{category}_summary.md 파일 생성 완료: {output_path}")
            except Exception as e:
                print(f"{category}_summary.md 파일 생성 오류: {str(e)}")

    async def send_request_with_client(self, category, prompt, content, 
                                    filename, clone_dir):

        response = await self.api_client.generate_text_client(prompt, content)

                        # 파일 이름 추출
        file_name_only = os.path.basename(filename).replace(".java", ".md")
                        # 파일 이름 생성 및 저장
        md_filename = os.path.join(clone_dir, "dododocs", category, f"{file_name_only}")
        os.makedirs(os.path.dirname(md_filename), exist_ok=True)

        async with aiofiles.open(md_filename, "w", encoding="utf-8") as file:
            await file.write(remove_markdown_blocks(response))