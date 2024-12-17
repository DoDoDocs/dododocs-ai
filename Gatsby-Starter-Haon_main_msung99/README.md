# Gatsby-Starter-Haon

## Table of Contents

[ 📝 Overview](#📝-overview)  
[ 📁 Project Structure](#📁-project-structure)  
[ 🚀 Getting Started](#🚀-getting-started)  
[ 💡 Motivation](#💡-motivation)  
[ 🎬 Demo](#🎬-demo)  
[ 🌐 Deployment](#🌐-deployment)  
[ 🤝 Contributing](#🤝-contributing)  
[ ❓ Troubleshooting & FAQ](#❓-troubleshooting-&-faq)  
[ 📈 Performance](#📈-performance)  

## 📝 Overview
이 프로젝트는 Gatsby를 사용하여 기술 블로그 테마를 구현한 것입니다.  
- 블로그 포스트를 작성하고 관리할 수 있는 기능을 제공합니다.

### Main Purpose
- 이 프로젝트의 주요 목표는 사용자가 쉽게 블로그를 작성하고 관리할 수 있도록 하는 것입니다.
- 기술 블로그를 운영하고자 하는 사용자에게 적합합니다.

### Key Features
- 서버 사이드 렌더링(SSR) 지원
- RSS 피드 생성
- 다양한 플러그인 지원 (예: KaTeX, PrismJS)

### Core Technology Stack
- Frontend: Gatsby
- Backend: 없음 (정적 사이트 생성)
- Database: 없음 (Markdown 파일 사용)
- Others: KaTeX, PrismJS

## 📁 Project Structure
[Gatsby-Starter-Haon]
├── 📁 src
│   ├── 📁 templates
│   │   ├── Post.jsx
│   │   ├── tag.jsx
│   │   └── series.jsx
│   ├── 📁 contents
│   │   ├── 📁 posts
│   │   └── ...
│   └── ...
├── gatsby-config.js
├── gatsby-ssr.js
└── gatsby-browser.js

## 🚀 Getting Started

### Prerequisites
- Supported Operating Systems
  * Windows, macOS, Linux
- Required Software
  * Runtime environment: Node.js
  * Version requirements: Node.js 최신 버전
  * Package managers: npm
- System Dependencies
  * 없음

### Installation
```bash
# Clone the repository
git clone [repository-url]
cd Gatsby-Starter-Haon-main

# Install required packages
npm install

# Configure environments
# 환경 설정은 meta-config.js 파일을 통해 가능합니다.
```

### Usage
```bash
# How to run
gatsby develop
# 또는
npm start


## 💡 Motivation
- 이 프로젝트는 개인 블로그를 운영하고자 하는 욕구에서 시작되었습니다.
- 기술 블로그를 통해 지식을 공유하고, 다른 개발자들과 소통하고자 합니다.

## 🎬 Demo
![Demo Video or Screenshot](path/to/demo.mp4)

## 🌐 Deployment
- Netlify를 사용하여 배포할 수 있습니다.
- 배포 단계는 다음과 같습니다:
  1. Netlify 계정 생성
  2. GitHub 레포지토리와 연결
  3. 배포 설정 완료 후 자동 배포

## 🤝 Contributing
- 기여 방법은 GitHub에서 이슈를 생성하거나 Pull Request를 통해 가능합니다.
- 코드 표준은 ESLint를 사용하여 유지합니다.
- Pull Request 프로세스는 다음과 같습니다:
  1. 포크 후 브랜치 생성
  2. 변경 사항 커밋
  3. Pull Request 제출

## ❓ Troubleshooting & FAQ
- 일반적인 문제:
  * 개발 서버가 시작되지 않음: Node.js와 npm이 올바르게 설치되었는지 확인하세요.
- 자주 묻는 질문:
  * Markdown 파일은 어디에 저장되나요? → `src/contents/posts` 폴더에 저장됩니다.
- 디버깅 팁:
  * 콘솔에서 오류 메시지를 확인하고, 관련 문서를 참조하세요.

## 📈 Performance
- 성능 벤치마크는 필요에 따라 추가할 수 있습니다.
- 최적화 기법으로는 이미지 최적화 및 코드 스플리팅을 사용할 수 있습니다.
- 확장성 고려 사항으로는 Gatsby의 정적 사이트 생성 기능을 활용하여 트래픽 증가에 대응할 수 있습니다.