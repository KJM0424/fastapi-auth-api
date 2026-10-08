# ADR 0002: 비밀번호 해싱

## 상태
채택

## 배경
PRD에 따라 비밀번호를 평문으로 저장하지 않는다. 해싱 알고리즘과 라이브러리를 정해야 한다.

## 선택지
- bcrypt
- Argon2id

## 결정
bcrypt 라이브러리를 직접 쓴다. passlib은 쓰지 않는다.
cost(반복 강도)는 기본값 12로 두고, `BCRYPT_ROUNDS` 설정으로 바꿀 수 있게 한다. 테스트에서는 4로 낮춘다.

## 이유
- bcrypt는 자료가 많아 동작을 설명하기 쉽다.
- passlib은 마지막 릴리스가 2020년 10월의 1.7.4다([PyPI](https://pypi.org/project/passlib/)).
- cost를 설정으로 두면 테스트에서 낮춰 테스트 시간을 줄일 수 있다.
- passlib 1.7.4는 bcrypt 4.1 이상에서 없어진 `bcrypt.__about__`을 읽으려다 오류 로그를 남긴다([passlib issue #190](https://foss.heptapod.net/python-libs/passlib/-/issues/190)).

## 영향
- bcrypt 5.0.0부터 72바이트를 넘는 비밀번호를 `hashpw`에 넘기면 `ValueError`가 발생한다([bcrypt CHANGELOG](https://github.com/pyca/bcrypt/blob/main/CHANGELOG.rst)). `checkpw`도 내부에서 `hashpw`를 호출하므로 같은 오류가 발생한다([bcrypt 5.0.0 소스](https://github.com/pyca/bcrypt/blob/5.0.0/src/_bcrypt/src/lib.rs#L137-L143)).
- ADR 0008에 따라 가입 단계에서 72바이트를 넘는 비밀번호를 거부한다.
- 로그인 단계에서는 72바이트를 넘는 입력을 `checkpw`에 넘기지 않고 일반 로그인 실패로 처리한다.
- 해싱과 검증 함수를 직접 감싸서 써야 한다.
