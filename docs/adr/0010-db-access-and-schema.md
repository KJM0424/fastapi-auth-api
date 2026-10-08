# ADR 0010: DB 접근 방식과 테이블 생성

## 상태
채택

## 배경
ADR 0001에서 SQLite와 SQLAlchemy를 쓰기로 했다. SQLAlchemy를 동기로 쓸지 비동기로 쓸지, 테이블을 어떻게 만들지 정해야 한다.

## 선택지
- DB 접근: 동기 SQLAlchemy / 비동기 SQLAlchemy
- 테이블 생성: 앱 시작 시 `Base.metadata.create_all` / Alembic 마이그레이션

## 결정
동기 SQLAlchemy를 쓴다. 테이블은 앱 시작 시 `Base.metadata.create_all`로 만든다.

## 이유
- 하루 범위에서 규모 대비 복잡도를 줄인다.
- 동기 방식은 비동기 드라이버와 세션 설정이 필요 없어 코드와 테스트가 단순하다.
- `create_all`은 별도 마이그레이션 파일 없이 모델 정의만으로 테이블을 만든다.

## 영향
- `create_all`은 없는 테이블만 만들고, 이미 있는 테이블의 컬럼 변경은 반영하지 않는다. 모델을 바꾸면 로컬 DB 파일을 지우고 다시 만든다.

## 향후 개선
- 실서비스에서는 Alembic으로 마이그레이션 관리
