"""**PROMPTS**"""
GENERATE_DOC_PROMPT = '''Please provide comprehensive documentation for the given Service code, following these guidelines:

1. Overall Structure
- Begin with a high-level overview of the codebase structure
- Explain the purpose and function of Service code
- Describe how the different parts of the code interact with each other
- Include a Mermaid diagram showing the relationships between classes and repositories


2. Strategy Pattern Implementation
- Explain how the strategy pattern is implemented in the codebase
- Document the strategy interface and concrete strategy classes
- Describe the context class that uses the strategies
- Provide a class diagram showing:
  * Strategy interface
  * Context class
  * Relationships between components

3. Detailed Component Documentation
For each component (class, function, method), provide:

a. Classes:
- Class name and brief description of its purpose
- Explanation of class attributes
- Description of the class's role in the larger system
- Any inheritance or relationships with other classes

b. Methods and Functions:
- Name and purpose of the all method/function
- Parameters: name, type, and description of each parameter
- Return value: type and description of what is returned
- Code examples of usage

4. Implementation Flow
Include a sequence diagram showing:
- How client code interacts with the context
- How context delegates to strategy
- Strategy execution flow
- Return of results

Remember to use clear, concise language and provide context where necessary. The goal is to create documentation that helps both new and experienced developers understand and work with the code effectively. Response documentation only. Use markdown format.

Include Mermaid diagrams for:
1. Class diagram showing strategy pattern structure
2. Sequence diagram showing runtime behavior
'''

SUMMARY_PROMPT = """Please provide a concise summary of this authentication service documentation, focusing on:

1. The main purpose and core functionality of the service
2. Key components and their interactions
3. The authentication flow from client request to token generation

Please keep the summary clear and organized with bullet points where appropriate. No need to include code examples or detailed method signatures - focus on the high-level architectural overview and main concepts.
"""

#doc 번역
TRANSLATE_PROMPT = '''당신은 전문 번역가입니다. 제가 제공하는 마크다운 문서를 한국어로 번역해주세요.

번역 시 다음 지침을 반드시 따라주세요:

1. 마크다운 문법과 서식은 그대로 보존해주세요:
   - 제목 기호(#)
   - 글머리 기호(-, *, +)
   - 강조 표시(**bold**, *italic*)
   - 링크 형식([text](url))
   - 코드 블록(```)
   - 인용구(>)
   - 표 형식(|)

2. 번역 시 주의사항:
   - 전문 용어는 일반적으로 통용되는 한국어 용어를 사용해주세요
   - 코드 블록 내부의 코드와 주석을 구분하여, 코드는 그대로 두고 주석만 번역해주세요
   - URL, 이메일 주소, 변수명 등 고유 명사는 번역하지 마세요
   - 자연스러운 한국어 문장이 되도록 의역이 필요한 경우 의역을 해주세요
   - 기술 문서의 경우 한국의 기술 문서 작성 관행을 따라주세요

3. 원문의 의미와 뉘앙스를 정확하게 전달하면서도, 한국어 사용자가 이해하기 쉽게 번역해주세요.

아래 마크다운을 위 지침에 따라 한국어로 번역해주세요:

'''

PROMPT_README = f"""Please analyze the entire repository structure and generate a README.md in the following format:

# [Project Name]

## 🖼 Preview


##  Table of Contents

- [ Overview](#-overview)
- [ Analysis](#-features)
- [ Project Structure](#-project-structure)
- [ Getting Started](#-getting-started)
  - [ Prerequisites](#prerequisites)
  - [ Installation](#installation)
  - [ Usage](#usage)


## 📝 Overview
[Brief overview of the project]
- Main purpose of the project

### Main Purpose
- [Describe the primary goal and purpose of your project]
- [Explain what problem it solves]
- [Mention target users/audience]

### Key Features
- [Feature 1]
- [Feature 2]
- [Feature 3]

### Core Technology Stack
-don't have expose all sections, Skip sections if no relevant technology is used.
- Frontend: [e.g., React, Vue, Angular]
- Backend: [e.g., Node.js, Python, Java]
- Database: [e.g., PostgreSQL, MongoDB]
- Other Tools: [e.g., Docker, Redis]

## 📊 Analysis
[Key analysis findings]
- Data analysis results
- Performance metrics
- Key insights
<!-- Summary of main points from Service.md -->

## 📁 Project Structure
-don't have expose all files, expose important files with Key Features
```
[project name]
├── 📁 [folder1]
│   ├── [file1]
│   └── [file2]
├── 📁 [folder2]
│   ├── [file1]
│   └── [file2]
└── ...
```

## 🚀 Getting Started
-If there is not enough information, do not need to write it.
### Prerequisites
- Required environment setup
- Required dependencies

### Installation
```bash
# Clone the repository
git clone [repository URL]

# Install required packages
[installation commands]

# Configure environment
[configuration commands]
```

### Usage
-If there is not enough information, do not need to write it.
```bash
# How to run
[execution commands]
```
"""

PROMPT_USAGE = """Please analyze the entire build files, structure and generate in the following format:

## 🚀 Getting Started
-If there is not enough information, do not need to write it.
### Prerequisites
- Required environment setup
- Required dependencies

### Installation
```bash
# Clone the repository
git clone [repository URL]

# Install required packages
[installation commands]

# Configure environment
[configuration commands]
```

### Usage
-If there is not enough information, do not need to write it.
```bash
# How to run
[execution commands]
```

---"""

DALLE_PROMPT = '''
Draw the core features clearly. 
A simple vector logo for project.
project : '''

CHATBOT_PROMPT = """You are a helpful assistant.

When answering:
1. Only use information from the provided context and chat history
2. If the context is relevant but insufficient to fully answer the query, use information from the chat history
3. If you're unsure about the relevance of the context, explain why
4. Never make up information that's not in the context

Remember to:
- Be concise and direct
- Cite specific parts of the context when relevant
- Maintain a helpful and professional tone"""

