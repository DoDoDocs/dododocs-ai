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
- 프로젝트의 주요 목적은 사용자에게 기술 관련 정보를 제공하는 블로그를 만드는 것입니다.

### Main Purpose
- 사용자가 기술 블로그를 쉽게 구축할 수 있도록 돕는 것입니다.
- 블로그 포스트를 작성하고 관리하는 데 필요한 기능을 제공합니다.
- 기술 블로그를 원하는 개발자 및 기술 관련 콘텐츠 제작자를 대상으로 합니다.

### Key Features
- 서버 사이드 렌더링(SSR) 지원
- RSS 피드 생성
- 다양한 플러그인 지원 (예: KaTeX, PrismJS)

### Core Technology Stack
- Frontend: Gatsby
- Backend: Node.js
- Database: Markdown 파일 기반

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
├── 📁 static
│   ├── profile.png
│   └── ...
└── gatsby-config.js

## 🚀 Getting Started

### Prerequisites
- 지원 운영체제
  * Windows, macOS, Linux
- 필수 소프트웨어
  * Node.js
  * Gatsby CLI
- 시스템 종속성
  * 없음

### Installation
```bash
# 레포지토리 클론
git clone [repository-url]
cd Gatsby-Starter-Haon-main

# 필요한 패키지 설치
npm install

# 환경 설정
# meta-config.js 파일을 수정하여 사이트 메타데이터 설정
```

### Usage
```bash
# 실행 방법
gatsby develop
# 또는
npm start


## 💡 Motivation
- 이 프로젝트는 개인 블로그를 만들고자 하는 욕구에서 시작되었습니다.
- 기술 블로그를 통해 지식을 공유하고, 다른 개발자들과 소통하고자 합니다.

## 🎬 Demo
![Demo Video or Screenshot](path/to/demo.mp4)

## 🌐 Deployment
- Netlify 또는 Vercel과 같은 플랫폼에서 배포 가능합니다.
- 배포 단계는 다음과 같습니다:
  1. GitHub에 푸시
  2. Netlify/Vercel에서 GitHub 레포지토리 연결
  3. 자동 배포 설정

## 🤝 Contributing
- 기여 방법: 이슈를 생성하거나 풀 리퀘스트를 제출하세요.
- 코딩 표준: ESLint 및 Prettier를 사용하여 코드 스타일을 유지합니다.
- 풀 리퀘스트 프로세스: 변경 사항을 설명하는 메시지와 함께 풀 리퀘스트를 제출하세요.
- 행동 강령: 모든 기여자는 존중과 배려를 바탕으로 행동해야 합니다.

## ❓ Troubleshooting & FAQ
- 일반적인 문제: 개발 서버가 시작되지 않는 경우, 종속성을 다시 설치해 보세요.
- 자주 묻는 질문: Gatsby 관련 질문은 공식 문서를 참조하세요.
- 디버깅 팁: 콘솔 로그를 사용하여 문제를 추적하세요.

## 📈 Performance
- 성능 벤치마크: 페이지 로드 시간 및 SEO 점수
- 최적화 기법: 이미지 최적화 및 코드 스플리팅
- 확장성 고려사항: 서버리스 아키텍처를 통해 확장 가능성 확보