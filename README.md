# LEVER Xpert API

광고 운영 자동화 솔루션 LEVER Xpert의 백엔드 API 서버입니다.

## 프로젝트 개요

LEVER Xpert는 디지털 마케팅 광고 캠페인을 효율적으로 관리하고 운영할 수 있는 통합 솔루션입니다. 다양한 광고 플랫폼(Google Ads, Facebook, Naver, Kakao)의 데이터를 수집하고 분석하여 광고 성과를 최적화합니다.

## 주요 기능

- **사용자 인증**: JWT 기반 인증 시스템
- **캠페인 관리**: 광고 캠페인 CRUD 및 일괄 업데이트
- **성과 분석**: 캠페인 메트릭스 조회 및 집계
- **데이터 파이프라인**: Apache Airflow 연동을 통한 데이터 동기화
- **캐싱**: Redis(MemoryDB) 기반 캐싱으로 성능 최적화
- **관리자 기능**: 사용자 관리 및 시스템 모니터링

## 기술 스택

- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL (AWS RDS)
- **Cache**: Redis (AWS MemoryDB)
- **Data Pipeline**: Apache Airflow
- **Authentication**: JWT (python-jose)
- **Cloud**: AWS (Lambda, ECS, RDS, MemoryDB)

## 프로젝트 구조

```
src/
├── main.py              # FastAPI 애플리케이션 진입점
├── config.py            # 환경 설정
├── database.py          # 데이터베이스 연결
├── models.py            # SQLAlchemy 모델
├── schemas.py           # Pydantic 스키마
├── auth.py              # 인증 관련 유틸리티
├── cache.py             # Redis 캐시 서비스
├── requirements.txt     # 의존성 목록
├── routers/
│   ├── auth_router.py      # 인증 API
│   ├── campaign_router.py  # 캠페인 API
│   ├── pipeline_router.py  # 파이프라인 API
│   └── admin_router.py     # 관리자 API
└── services/
    ├── campaign_service.py  # 캠페인 비즈니스 로직
    └── pipeline_service.py  # 파이프라인 비즈니스 로직
```

## 실행 방법

### 환경 변수 설정

`.env` 파일을 생성하고 다음 환경 변수를 설정합니다:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/lever_xpert
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-here
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=ap-northeast-2
AIRFLOW_BASE_URL=http://localhost:8080
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=admin
DEBUG=false
```

### 로컬 실행

```bash
# 의존성 설치
pip install -r src/requirements.txt

# 서버 실행
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker 실행

```bash
docker build -t lever-xpert-api .
docker run -p 8000:8000 --env-file .env lever-xpert-api
```

## API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 주요 API 엔드포인트

### 인증
- `POST /auth/register` - 회원가입
- `POST /auth/login` - 로그인
- `GET /auth/me` - 현재 사용자 정보
- `POST /auth/password-reset` - 비밀번호 재설정 요청

### 캠페인
- `GET /campaigns` - 캠페인 목록 조회
- `POST /campaigns` - 캠페인 생성
- `GET /campaigns/{id}` - 캠페인 상세 조회
- `PUT /campaigns/{id}` - 캠페인 수정
- `DELETE /campaigns/{id}` - 캠페인 삭제
- `POST /campaigns/bulk-update` - 일괄 업데이트
- `GET /campaigns/{id}/metrics` - 성과 메트릭스 조회

### 파이프라인
- `POST /pipelines/jobs` - 파이프라인 작업 생성
- `POST /pipelines/jobs/{id}/trigger` - 작업 실행
- `GET /pipelines/jobs/{id}` - 작업 상태 조회
- `POST /pipelines/sync/{platform}` - 플랫폼 데이터 동기화

### 관리자
- `GET /admin/users` - 사용자 목록
- `GET /admin/stats` - 시스템 통계
- `POST /admin/cache/clear` - 캐시 삭제

## 코드 리뷰 과제

이 프로젝트는 코드 리뷰 평가를 위한 과제입니다. 코드를 검토하고 발견한 버그, 보안 취약점, 성능 이슈, 아키텍처 문제 등을 리포트해 주세요.

### 평가 기준

1. **버그 식별 능력**: 코드 내 숨겨진 버그를 찾아내는 능력
2. **보안 인식**: 보안 취약점을 발견하고 설명하는 능력
3. **코드 품질 분석**: 코드 스타일, 패턴, 아키텍처 개선점 제안
4. **실무 적용 능력**: 실제 운영 환경에서 발생할 수 있는 문제 예측

### 제출 형식

발견한 이슈를 다음 형식으로 정리해 주세요:

```
## [심각도] 이슈 제목

**파일**: 파일 경로
**라인**: 라인 번호

**설명**:
이슈에 대한 상세 설명

**수정 방안**:
권장하는 수정 방법
```

심각도는 Critical, Major, Minor 중 하나를 선택해 주세요.
