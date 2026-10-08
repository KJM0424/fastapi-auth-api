# ADR 0002: 비밀번호 해싱

## 상태
채택

## 배경
PRD에 따라 비밀번호를 평문으로 저장하지 않는다. 해싱 알고리즘과 라이브러리를 정해야 한다.

## 선택지
- bcrypt (bcrypt 라이브러리 직접 사용)
- bcrypt (passlib 경유)
- Argon2 (argon2-cffi)

## 결정
bcrypt 라이브러리를 직접 쓴다. passlib은 쓰지 않는다.

## 이유
- bcrypt는 자료가 많아 동작을 설명하기 쉽다.
- passlib은 마지막 릴리스가 2020년 10월의 1.7.4다([PyPI](https://pypi.org/project/passlib/)).
- passlib 1.7.4는 bcrypt 4.1 이상에서 없어진 `bcrypt.__about__`을 읽으려다 오류 로그를 남긴다([passlib issue #190](https://foss.heptapod.net/python-libs/passlib/-/issues/190)).

## 영향
- bcrypt 5.0.0부터 72바이트를 넘는 비밀번호를 `hashpw`에 넘기면 `ValueError`가 발생한다([bcrypt CHANGELOG](https://github.com/pyca/bcrypt/blob/main/CHANGELOG.rst)). 입력 검증 단계에서 길이를 제한하거나 이 오류를 처리해야 한다.
- 해싱과 검증 함수를 직접 감싸서 써야 한다.
