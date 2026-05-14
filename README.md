# EasyPick AI

EasyPick AI는 캡스톤디자인 발표용으로 만든 로컬 AI 쇼핑/가격비교 웹서비스입니다.
사용자는 상품을 검색하고, 상세 정보를 확인하고, 여러 상품을 비교하고, 장바구니에 담아 주문 시뮬레이션까지 진행할 수 있습니다.
AI 기능은 외부 유료 API 없이 Docker 안의 Ollama와 `qwen3:4b` 기반 전용 모델 `easypick-ai`로 실행됩니다.
원하면 관리자 페이지에서 LM Studio의 로컬 OpenAI 호환 서버로도 바꿔 실행할 수 있습니다.
노트북 시연용 모델은 LM Studio의 `gemma-4-e2b-uncensored-hauhaucs-aggressive` 모델을 권장합니다.

처음 실행하는 팀원은 먼저 [START_HERE.md](./START_HERE.md)를 보면 됩니다.
GPU 자동 감지 실행은 [GPU_AUTO_RUN.md](./GPU_AUTO_RUN.md)를 보면 됩니다.

## 주요 기능

- 상품 검색, 카테고리/가격/브랜드/정렬 필터
- 상품 상세 페이지와 리뷰 목록
- 상품 2~3개 비교 표
- AI 상품 추천, AI 상품 비교, AI 리뷰 요약
- AI 쇼핑도우미 최근 답변 5개 유지
- AI 답변 생성 중 페이지 이동 시 상태 유지
- 장바구니, 주문서 작성, 주문 완료/주문 내역 확인
- 관리자 페이지에서 상품 추가/수정/삭제, 주문 상태 변경
- 관리자 페이지에서 Ollama/LM Studio 선택, 모델 목록 새로고침, 연결 테스트, 모델 연결 끊기
- PostgreSQL seed 데이터 자동 입력
- Ollama 컨테이너에서 `qwen3:4b` 다운로드 후 `easypick-ai` 모델 자동 생성

## 기술 스택

- Frontend: React, Vite, React Router, CSS
- Backend: FastAPI, psycopg, httpx
- Database: PostgreSQL
- Local AI: Ollama, `qwen3:4b`, `easypick-ai`, LM Studio 선택 지원
- Infra: Docker Compose

## 폴더 구조

```text
Capstone_3/
├─ frontend/              # React 쇼핑몰 UI
├─ backend/               # FastAPI REST API, DB 연결, Ollama 연동
├─ database/init.sql      # 테이블 생성, 더미 상품/리뷰/카테고리 데이터
├─ ai/
│  ├─ Modelfile           # easypick-ai 시스템 프롬프트
│  ├─ init-ollama.sh      # qwen3:4b pull 및 easypick-ai 생성 스크립트
│  └─ prompts/            # AI 추천/비교/리뷰 요약 프롬프트
├─ docker-compose.yml
├─ .env.example
├─ START_HERE.md          # 팀원용 초간단 실행 가이드
└─ README.md
```

## 실행 주소

- 프론트엔드: http://localhost:5173
- 백엔드 API: http://localhost:8000
- 백엔드 API 문서: http://localhost:8000/docs
- 관리자 페이지: http://localhost:5173/admin
- Ollama API: http://localhost:11434
- AI 모델명: `easypick-ai`

## 빠른 실행

```bash
git clone <repository-url>
cd Capstone_3
docker compose up -d --build
docker compose up ollama-init
```

Windows에서 GPU가 있으면 GPU로, 없으면 CPU로 자동 실행하고 싶을 때는 아래 파일을 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\start-easypick.ps1
```

또는 `start-easypick.bat` 파일을 더블클릭해도 됩니다.

첫 실행에서는 `qwen3:4b` 모델을 다운로드하므로 시간이 오래 걸릴 수 있습니다.
다운로드가 끝나면 브라우저에서 http://localhost:5173 으로 접속합니다.

## AI 서버 선택 구조

EasyPick은 두 가지 로컬 AI 서버를 지원합니다.

| 방식 | 용도 | 특징 |
| --- | --- | --- |
| Ollama | 기본 실행 | Docker Compose만으로 `qwen3:4b`와 `easypick-ai` 자동 준비 |
| LM Studio | 선택 실행 | 현재 PC에 설치한 LM Studio 모델을 관리자 페이지에서 선택 |

관리자 페이지의 `AI 연결 설정`에서 AI 서버를 바꿀 수 있습니다.
서버를 바꿀 때 기존에 로드된 모델 연결을 정리해 Ollama와 LM Studio가 동시에 큰 모델을 잡고 있는 상황을 줄입니다.

## 추천 LLM

현재 프로젝트에서 자연스럽고 친근한 쇼핑 상담 말투를 원하면 LM Studio의 아래 모델을 권장합니다.

- 권장 모델명: `gemma-4-e2b-uncensored-hauhaucs-aggressive`
- LM Studio 표시 이름: `Gemma 4 E2B Uncensored HauhauCS Aggressive Q2 K P`
- 실제 LM Studio 모델 ID는 다운로드한 모델에 따라 다를 수 있습니다.
- 일반 `google/gemma-4-e4b`는 환경에 따라 `content`가 비고 `reasoning_content`로 빠지는 출력 문제가 생길 수 있어 팀원 설치용 기본 권장 모델에서는 제외합니다.
- Gemma4 E2B는 빠르지만 긴 한국어 답변이 중간에 끊기거나 말투 제어가 약할 수 있습니다.
- Qwen 계열은 정보 정리는 괜찮지만, 모델에 따라 답변이 보고서처럼 딱딱해질 수 있습니다.

답변이 중간에 끊기면 `.env`에서 `AI_MAX_TOKENS=1200` 또는 `AI_MAX_TOKENS=1600`으로 올려 테스트합니다.
GPU 메모리가 부족하면 `OLLAMA_NUM_CTX` 또는 `LMSTUDIO_CONTEXT_LENGTH`를 4096으로 낮출 수 있습니다.

## LM Studio로 실행하기

Ollama 대신 LM Studio를 쓰려면 LM Studio에서 모델을 다운로드한 뒤 `Developer` 또는 `Local Server` 화면에서 서버를 켭니다.
기본 주소는 보통 `http://localhost:1234/v1`입니다.

프로젝트 루트에 `.env` 파일을 만들고 아래처럼 설정합니다.

```env
AI_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1
LMSTUDIO_MODEL=gemma-4-e2b-uncensored-hauhaucs-aggressive
LMSTUDIO_API_KEY=
LMSTUDIO_CONTEXT_LENGTH=8192
AI_MAX_TOKENS=900
PROMPT_CONTEXT_BUFFER_TOKENS=1200
PROMPT_CHAR_BUDGET=0
```

그 다음 백엔드를 다시 올립니다.

```bash
docker compose up -d --build backend
```

Docker 밖에서 백엔드를 직접 실행하는 경우에는 `LMSTUDIO_BASE_URL=http://localhost:1234/v1`을 사용하면 됩니다.
현재 연결된 AI 설정은 http://localhost:8000/api/health 에서 확인할 수 있습니다.

프롬프트가 너무 길어지는 경우에는 `PROMPT_CHAR_BUDGET`으로 직접 글자 수 상한을 줄 수 있고, GPU 메모리가 부족하면 `OLLAMA_NUM_CTX` 또는 `LMSTUDIO_CONTEXT_LENGTH`를 4096처럼 낮추면 됩니다.

관리자 페이지에서 설정하는 순서:

1. LM Studio에서 Local Server를 켭니다.
2. EasyPick 관리자 페이지로 이동합니다.
3. AI 서버를 `LM Studio`로 선택합니다.
4. 주소를 `http://host.docker.internal:1234/v1`로 입력합니다.
5. 모델 새로고침으로 LM Studio 모델 목록을 불러옵니다.
6. 사용할 모델을 선택합니다.
7. `AI 연결 테스트`를 누릅니다.
8. 정상으로 뜨면 `AI 설정 저장`을 누릅니다.

## 이번 버전에서 추가된 AI 개선점

- LM Studio 연결 지원
- 관리자 페이지 AI 서버 선택 기능
- LM Studio 모델 목록 자동 조회
- AI 연결 테스트와 모델 연결 끊기
- AI 서버 전환 시 기존 서버 모델 연결 정리
- 상품 테이블에 `상세설명`, `추천대상`, `주의사항` 컬럼 추가
- 프롬프트를 더 친근한 한국어 쇼핑 상담 말투로 개선
- 상품 후보를 자연어 상품 카드 형태로 LLM에 전달
- 컨텍스트 초과를 막기 위한 프롬프트 길이 예산 적용
- 답변 대체용 backend fallback 제거
- AI 도우미 최근 답변 5개 유지
- AI 도우미, 비교, 리뷰 요약 생성 중 페이지 이동해도 상태 유지

## 확인 명령어

```bash
docker compose ps
docker exec -it easypick-ollama ollama list
```

`ollama list` 결과에 아래 두 모델이 보이면 AI 준비가 끝난 상태입니다.

```text
qwen3:4b
easypick-ai:latest
```

## 발표 시연 흐름

1. http://localhost:5173 접속
2. 메인 검색창에 `무선청소기` 입력
3. 상품 목록에서 최고가 `200000` 입력 후 필터 적용
4. 상품 2~3개를 비교 담기
5. 비교 페이지로 이동
6. `AI 비교 설명 요청` 클릭
7. AI 도우미 페이지에서 `20만 원 이하로 자취방에서 쓸 무선청소기 추천해줘` 입력
8. 추천 상품 상세 페이지 확인
9. 장바구니 담기
10. 주문서 작성 후 결제 시뮬레이션 완료
11. 관리자 페이지에서 상품 등록 또는 주문 상태 변경 시연

## 자주 생기는 문제

### 상품 목록이 안 뜰 때

```bash
docker compose ps
```

`easypick-db`, `easypick-backend`, `easypick-frontend`가 모두 실행 중인지 확인합니다.
그 다음 브라우저에서 http://localhost:8000/api/products 를 열어 상품 JSON이 나오는지 확인합니다.

### AI가 응답하지 않을 때

```bash
docker compose up ollama-init
docker exec -it easypick-ollama ollama list
```

`easypick-ai:latest`가 없으면 모델 생성이 아직 끝나지 않은 것입니다.
처음에는 모델 다운로드 때문에 몇 분 이상 걸릴 수 있습니다.

### DB seed 데이터가 반영되지 않을 때

PostgreSQL 볼륨이 이미 만들어진 뒤에는 `database/init.sql`이 다시 자동 실행되지 않습니다.
개발 중 DB를 초기화하려면 아래 명령을 사용합니다.

```bash
docker compose down -v
docker compose up -d --build
docker compose up ollama-init
```

주의: `down -v`는 로컬 DB 데이터와 Ollama 모델 볼륨을 지웁니다. 모델도 다시 다운로드될 수 있습니다.

### 포트 충돌이 날 때

이미 5173, 8000, 5432, 11434 포트를 다른 프로그램이 쓰고 있을 수 있습니다.
기존 프로그램을 종료하거나 `docker-compose.yml`의 포트 매핑을 바꿉니다.

## API 요약

상품 API:

- `GET /api/products`
- `GET /api/products/{id}`
- `GET /api/categories`
- `GET /api/products/compare?ids=1,2,3`
- `GET /api/products/{id}/reviews`

AI API:

- `POST /api/ai/recommend`
- `POST /api/ai/compare`
- `POST /api/ai/review-summary`

장바구니/주문 API:

- `GET /api/cart?sessionId=...`
- `POST /api/cart/items`
- `PUT /api/cart/items/{id}`
- `DELETE /api/cart/items/{id}?sessionId=...`
- `POST /api/orders`
- `GET /api/orders?sessionId=...`
- `GET /api/orders/{orderNumber}`

관리자 API:

- `POST /api/admin/products`
- `PUT /api/admin/products/{id}`
- `DELETE /api/admin/products/{id}`
- `GET /api/admin/orders`
- `PATCH /api/admin/orders/{id}/status`
- `GET /api/admin/ai-settings`
- `PUT /api/admin/ai-settings`
- `GET /api/admin/ai-settings/models`
- `POST /api/admin/ai-settings/test`
- `POST /api/admin/ai-settings/unload`

## 중요한 주의사항

- OpenAI, Gemini, Claude 같은 외부 AI API를 사용하지 않습니다.
- 실제 쇼핑몰 API나 크롤링 데이터를 사용하지 않습니다.
- 상품/리뷰 데이터는 `database/init.sql`의 더미 데이터입니다.
- 모델 파일 자체는 GitHub에 올리지 않습니다. Docker 실행 시 Ollama가 자동 다운로드합니다.
- LM Studio 모델은 각자 PC의 LM Studio에서 직접 다운로드해야 합니다.
- AI는 백엔드가 DB에서 조회한 후보 상품 안에서만 답하도록 프롬프트를 구성합니다.
- AI 도우미 최근 답변과 생성 상태는 프론트 localStorage에 저장됩니다. 새로고침 중인 요청까지 완벽히 이어받는 백엔드 작업 큐는 아직 없습니다.
