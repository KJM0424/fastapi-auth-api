# AI 활용 기록

## 2026-10-08 프로젝트 초기 세팅

- 내 요청: CLAUDE.md, docs/ 기본 구조(prd.md, adr/, api-spec.md, ai-log.md), .gitignore를 만들고 git-workflow 규칙대로 커밋·push. 만들기 전에 계획부터 보여달라고 함
- AI가 한 것: 계획을 제시함. 레포에 커밋이 없어 main이 없는 상태라 "main 직접 커밋 금지" 규칙과 충돌한다고 짚고 두 안을 냄
  1. .gitignore만 main에 커밋해 main을 만들고, 나머지는 feature/project-setup 브랜치에 커밋을 나눠 PR로 올리기
  2. 초기 세팅이라는 점을 예외로 보고 전부 main에 바로 커밋하기
- 내가 고른 것: 1안. PR은 머지하지 않고 직접 확인한 뒤 머지함
- 이유: PR 과정을 직접 겪어보고, 사람이 최종 확인한 뒤 머지하는 흐름을 연습하려고
