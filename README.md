# fastapi-auth-api

FastAPI 기반 회원가입/로그인/JWT 인증 API

## 실행 방법
모든 명령은 프로젝트 루트에서 실행한다. `.env`와 기본 DB 파일(`app.db`) 경로가 실행 위치 기준이기 때문이다.

1. [uv](https://docs.astral.sh/uv/)를 설치한다.
2. 의존성을 설치한다.
   ```
   uv sync
   ```
3. `.env.example`을 `.env`로 복사하고 `SECRET_KEY`를 채운다.
   ```
   cp .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
4. 서버를 실행한다. API 문서는 http://127.0.0.1:8000/docs 에서 볼 수 있다.
   ```
   uv run uvicorn app.main:app --reload
   ```

## 테스트
```
uv run pytest
```

## 문서
- [PRD](docs/prd.md)
- [설계 결정(ADR)](docs/adr/)
- [API 스펙](docs/api-spec.md)
