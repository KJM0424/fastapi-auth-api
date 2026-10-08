# ADR 0001: 데이터베이스

## 상태
채택

## 배경
회원 정보와 리프레시 토큰을 저장할 DB가 필요하다. 하루 안에 완성하는 프로젝트라 설치와 설정 부담이 적어야 한다.

## 선택지
- SQLite + SQLAlchemy
- PostgreSQL + SQLAlchemy
- MySQL + SQLAlchemy

## 결정
SQLite와 SQLAlchemy를 쓴다.

## 이유
- SQLite는 파일 기반이라 별도 서버 설치가 필요 없다.
- SQLAlchemy를 거치면 연결 주소를 바꿔 PostgreSQL로 옮길 수 있다.

## 영향
- PostgreSQL로 옮길 가능성을 남기려면 SQLite 전용 기능에 의존하지 않아야 한다.
- 동시 쓰기가 많은 환경에는 맞지 않는다. 이 프로젝트 범위에서는 문제가 되지 않는다.
