# API 스펙

구현 전에 작성한 기준 문서다. 근거는 `docs/prd.md`와 `docs/adr/`이다.

## 공통 정보

### Base URL
`/api/v1`

### 인증 방식
- 액세스 토큰: `Authorization: Bearer <액세스 토큰>` 헤더로 보낸다(ADR 0007).
- 리프레시 토큰: 요청 본문 `{"refresh_token": "..."}`으로 보낸다(ADR 0007).
- 만료 시간: 액세스 토큰 30분, 리프레시 토큰 7일(ADR 0004).

### 공통 응답 형식
성공 시 엔드포인트별 JSON 객체를 그대로 반환한다. 감싸는 필드는 없다. 로그아웃은 본문 없이 204를 반환한다.

토큰 응답(로그인, 토큰 재발급)

| 이름 | 타입 | 설명 |
|---|---|---|
| access_token | string | 액세스 토큰 |
| refresh_token | string | 리프레시 토큰 |
| token_type | string | 항상 `"bearer"` |

사용자 응답(회원가입, 내 정보 조회)

| 이름 | 타입 | 설명 |
|---|---|---|
| id | integer | 사용자 ID |
| email | string | 이메일 |
| created_at | string | 가입 시각(ISO 8601, UTC) |

응답에 비밀번호와 비밀번호 해시는 포함하지 않는다.

### 공통 에러 형식
모든 오류는 아래 형식으로 반환한다(ADR 0009).

```json
{
  "code": "INVALID_TOKEN",
  "message": "유효하지 않은 토큰입니다"
}
```

| 이름 | 타입 | 설명 |
|---|---|---|
| code | string | 에러 코드. 전체 목록은 [에러 코드 목록](#에러-코드-목록) 참고 |
| message | string | 사람이 읽는 설명(한국어) |

## 엔드포인트

### 회원가입
- Method / URL: `POST /api/v1/auth/signup`
- 설명: 이메일과 비밀번호로 계정을 만든다.
- 인증: 필요 없음

요청

| 위치 | 이름 | 타입 | 필수 | 설명 |
|---|---|---|---|---|
| body | email | string | 예 | 이메일 형식 |
| body | password | string | 예 | 8자 이상, UTF-8 기준 72바이트 이하, 영문과 숫자 포함(ADR 0008) |

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

응답 예시 - 성공 (201)
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-10-08T09:30:00Z"
}
```

응답 예시 - 실패 (409)
```json
{
  "code": "EMAIL_ALREADY_EXISTS",
  "message": "이미 가입된 이메일입니다"
}
```

에러 코드

| 상태 코드 | 에러 코드 | 발생 조건 |
|---|---|---|
| 422 | VALIDATION_ERROR | 필드 누락, 타입 오류, 이메일 형식 오류 |
| 422 | INVALID_PASSWORD | 비밀번호가 ADR 0008 조건을 만족하지 않음 |
| 409 | EMAIL_ALREADY_EXISTS | 이미 가입된 이메일 |

### 로그인
- Method / URL: `POST /api/v1/auth/login`
- 설명: 이메일과 비밀번호가 맞으면 액세스 토큰과 리프레시 토큰을 발급한다.
- 인증: 필요 없음

요청

| 위치 | 이름 | 타입 | 필수 | 설명 |
|---|---|---|---|---|
| body | email | string | 예 | 가입한 이메일 |
| body | password | string | 예 | 비밀번호 |

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

응답 예시 - 성공 (200)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc5MTQ1MTgwMH0.GMgenLi1Jj4L3QKdr_urobte9546zZrcY2PvuwESMLY",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2giLCJqdGkiOiJkN2RlYmUyZDkyMmJiYWIwMzVlMTgwZDQ2NmQwOGZjNyIsImV4cCI6MTc5MjA1NDgwMH0.-5lcyAGBrsuXgtsyFzGjmDnnWVrmH7YbneVvVLn0KgQ",
  "token_type": "bearer"
}
```

응답 예시 - 실패 (401)
```json
{
  "code": "INVALID_CREDENTIALS",
  "message": "이메일 또는 비밀번호가 올바르지 않습니다"
}
```

에러 코드

| 상태 코드 | 에러 코드 | 발생 조건 |
|---|---|---|
| 422 | VALIDATION_ERROR | 필드 누락, 타입 오류 |
| 401 | INVALID_CREDENTIALS | 가입되지 않은 이메일, 이메일 형식 오류, 비밀번호 불일치, 72바이트를 넘는 비밀번호 |

로그인 실패는 원인과 관계없이 `INVALID_CREDENTIALS` 하나로 응답하고 메시지도 같다(ADR 0008).

### 토큰 재발급
- Method / URL: `POST /api/v1/auth/refresh`
- 설명: 유효한 리프레시 토큰으로 새 액세스 토큰과 새 리프레시 토큰을 발급한다. 요청에 쓴 리프레시 토큰은 무효화된다(ADR 0006).
- 인증: 리프레시 토큰(요청 본문)

요청

| 위치 | 이름 | 타입 | 필수 | 설명 |
|---|---|---|---|---|
| body | refresh_token | string | 예 | 로그인 또는 이전 재발급에서 받은 리프레시 토큰 |

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2giLCJqdGkiOiJkN2RlYmUyZDkyMmJiYWIwMzVlMTgwZDQ2NmQwOGZjNyIsImV4cCI6MTc5MjA1NDgwMH0.-5lcyAGBrsuXgtsyFzGjmDnnWVrmH7YbneVvVLn0KgQ"
}
```

응답 예시 - 성공 (200)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc5MTQ1MzYwMH0.9VmYk_KmbkTAZ-DFcPAk4slEkyaIxAXgS5eXPAbZlS4",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2giLCJqdGkiOiJkMmQxMDdiZWU3M2M2MGE3MWZmMzgzZDcxNjQ5ZGViYiIsImV4cCI6MTc5MjA1NjYwMH0.4UoarY09PhP2ziehqEFsYEhPn3r_239AFNi97SoJk88",
  "token_type": "bearer"
}
```

응답 예시 - 실패 (401)
```json
{
  "code": "TOKEN_EXPIRED",
  "message": "만료된 토큰입니다"
}
```

에러 코드

| 상태 코드 | 에러 코드 | 발생 조건 |
|---|---|---|
| 422 | VALIDATION_ERROR | `refresh_token` 누락, 타입 오류 |
| 401 | INVALID_TOKEN | 서명·형식 오류, 리프레시 토큰이 아님, 이미 무효화된 토큰 |
| 401 | TOKEN_EXPIRED | 만료된 리프레시 토큰 |

### 로그아웃
- Method / URL: `POST /api/v1/auth/logout`
- 설명: 리프레시 토큰을 무효화한다. 무효화된 토큰으로는 재발급할 수 없다.
- 인증: 리프레시 토큰(요청 본문)

요청

| 위치 | 이름 | 타입 | 필수 | 설명 |
|---|---|---|---|---|
| body | refresh_token | string | 예 | 무효화할 리프레시 토큰 |

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2giLCJqdGkiOiJkMmQxMDdiZWU3M2M2MGE3MWZmMzgzZDcxNjQ5ZGViYiIsImV4cCI6MTc5MjA1NjYwMH0.4UoarY09PhP2ziehqEFsYEhPn3r_239AFNi97SoJk88"
}
```

응답 예시 - 성공 (204)

본문 없음.

응답 예시 - 실패 (401)
```json
{
  "code": "INVALID_TOKEN",
  "message": "유효하지 않은 토큰입니다"
}
```

에러 코드

| 상태 코드 | 에러 코드 | 발생 조건 |
|---|---|---|
| 422 | VALIDATION_ERROR | `refresh_token` 누락, 타입 오류 |
| 401 | INVALID_TOKEN | 서명·형식 오류, 리프레시 토큰이 아님 |

로그아웃은 멱등하게 처리한다. 서명이 유효하면 아래 경우도 204를 반환한다.
- 이미 무효화된 리프레시 토큰
- 만료된 리프레시 토큰. DB에 기록이 남아 있으면 삭제한다.

### 내 정보 조회
- Method / URL: `GET /api/v1/users/me`
- 설명: 액세스 토큰의 사용자 정보를 반환한다.
- 인증: 액세스 토큰(Authorization 헤더)

요청

| 위치 | 이름 | 타입 | 필수 | 설명 |
|---|---|---|---|---|
| header | Authorization | string | 예 | `Bearer <액세스 토큰>` |

응답 예시 - 성공 (200)
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-10-08T09:30:00Z"
}
```

응답 예시 - 실패 (401)
```json
{
  "code": "UNAUTHORIZED",
  "message": "인증이 필요합니다"
}
```

에러 코드

| 상태 코드 | 에러 코드 | 발생 조건 |
|---|---|---|
| 401 | UNAUTHORIZED | Authorization 헤더 없음 |
| 401 | INVALID_TOKEN | 서명·형식 오류, 액세스 토큰이 아님 |
| 401 | TOKEN_EXPIRED | 만료된 액세스 토큰 |

## 에러 코드 목록

| 상태 코드 | 에러 코드 | 메시지 | 발생 엔드포인트 |
|---|---|---|---|
| 422 | VALIDATION_ERROR | 요청 형식이 올바르지 않습니다 | 회원가입, 로그인, 토큰 재발급, 로그아웃 |
| 422 | INVALID_PASSWORD | 비밀번호는 8자 이상, 72바이트 이하이며 영문과 숫자를 포함해야 합니다 | 회원가입 |
| 409 | EMAIL_ALREADY_EXISTS | 이미 가입된 이메일입니다 | 회원가입 |
| 401 | INVALID_CREDENTIALS | 이메일 또는 비밀번호가 올바르지 않습니다 | 로그인 |
| 401 | UNAUTHORIZED | 인증이 필요합니다 | 내 정보 조회 |
| 401 | INVALID_TOKEN | 유효하지 않은 토큰입니다 | 토큰 재발급, 로그아웃, 내 정보 조회 |
| 401 | TOKEN_EXPIRED | 만료된 토큰입니다 | 토큰 재발급, 내 정보 조회 |
| 500 | INTERNAL_ERROR | 서버 내부 오류가 발생했습니다 | 전체 |
