# 처음 실행 가이드

이 문서는 EasyPick AI를 처음 받은 팀원이 그대로 따라 해서 사이트를 실행할 수 있도록 만든 안내서입니다.
프로젝트를 실행할 때는 이 파일부터 보면 됩니다.

## 1. 이 사이트가 뭔가요?

EasyPick AI는 자체 상품 DB를 기반으로 동작하는 쇼핑몰/가격비교 웹사이트입니다.
실제 쿠팡, 다나와, 네이버쇼핑 API를 쓰지 않고, 프로젝트 안의 더미 상품 데이터로만 작동합니다.

사용자는 다음 기능을 시연할 수 있습니다.

- 상품 검색
- 카테고리, 가격대, 브랜드 필터
- 상품 상세 정보 확인
- 상세설명, 추천대상, 주의사항 확인
- 리뷰 확인
- 여러 상품 비교
- AI에게 상품 추천 요청
- AI에게 비교 설명 요청
- AI 리뷰 요약 요청
- 장바구니 담기
- 주문서 작성과 결제 시뮬레이션
- 관리자 페이지에서 상품 등록/수정/삭제
- 관리자 페이지에서 AI 서버를 Ollama 또는 LM Studio로 선택

AI는 외부 유료 API를 사용하지 않습니다.
기본 실행은 Docker 안의 Ollama가 `qwen3:4b`를 다운로드하고 `easypick-ai` 모델을 만들어 사용합니다.
원하면 관리자 페이지에서 LM Studio의 로컬 서버(`http://localhost:1234/v1`)로 바꿔 사용할 수 있습니다.

## 2. 실행 전에 설치해야 하는 것

팀원 PC에 아래 프로그램이 설치되어 있어야 합니다.

1. Git
2. Docker Desktop
3. Docker Compose
4. 선택 사항: LM Studio

Windows에서는 보통 Docker Desktop만 설치하면 Docker Compose도 같이 설치됩니다.
Docker Desktop 설치 후에는 PC를 한 번 재부팅하는 것이 좋습니다.

LM Studio는 필수는 아닙니다.
기본 Ollama 방식만 쓸 팀원은 Git과 Docker Desktop만 준비하면 됩니다.

## 3. 프로젝트 다운로드

GitHub에 올라간 프로젝트를 받을 폴더에서 터미널을 엽니다.
Windows라면 PowerShell을 사용하면 됩니다.

```powershell
git clone https://github.com/reaqw0323/Capstone_3.git
cd Capstone_3
```

압축 파일로 받은 경우에는 압축을 풀고 `docker-compose.yml` 파일이 있는 폴더로 이동합니다.
중요한 점: 명령어는 반드시 `docker-compose.yml` 파일이 있는 폴더에서 실행해야 합니다.

## 4. 기본 실행: Ollama 사용

Windows에서 가장 쉽게 실행하려면 아래 파일을 더블클릭합니다.

```text
start-easypick.bat
```

이 파일은 NVIDIA GPU가 있으면 GPU 모드로, GPU가 없으면 CPU 모드로 자동 실행합니다.

PowerShell에서 직접 실행하려면 아래 명령어를 사용합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\start-easypick.ps1
```

수동으로 실행하고 싶다면 아래 명령어를 순서대로 실행합니다.

```powershell
docker compose up -d --build
docker compose up ollama-init
```

이 명령은 다음 서비스를 실행합니다.

- PostgreSQL DB
- FastAPI 백엔드
- React 프론트엔드
- Ollama AI 서버

처음 실행할 때는 `qwen3:4b` 모델을 다운로드하고 `easypick-ai` 모델을 생성합니다.
모델 크기가 크기 때문에 인터넷 속도에 따라 몇 분 이상 걸릴 수 있습니다.
중간에 멈춘 것처럼 보여도 로그가 계속 진행 중이면 기다리면 됩니다.

## 5. 선택 실행: LM Studio 사용

LM Studio를 쓰면 Docker의 Ollama 대신, 현재 PC에 설치된 LM Studio 모델을 EasyPick에서 사용할 수 있습니다.
특히 노트북 시연에서는 `gemma-4-e2b-uncensored-hauhaucs-aggressive` 모델을 권장합니다.

권장 모델:

- 모델 ID: `gemma-4-e2b-uncensored-hauhaucs-aggressive`
- LM Studio 표시 이름: `Gemma 4 E2B Uncensored HauhauCS Aggressive Q2 K P`
- LM Studio에 표시되는 실제 모델 ID는 설치한 모델에 따라 다를 수 있습니다.

참고:

- 일반 `google/gemma-4-e4b`는 환경에 따라 답변 본문 대신 reasoning 영역으로 출력이 빠지는 문제가 생길 수 있어 팀원 설치용 기본 권장 모델에서는 제외합니다.
- Gemma4 E2B 같은 더 작은 모델은 빠르지만 긴 한국어 답변이 중간에 끊기거나 말투 제어가 약할 수 있습니다.
- Qwen 계열은 정보 정리는 괜찮지만 쇼핑 상담원처럼 자연스럽게 말하는 느낌은 모델에 따라 약할 수 있습니다.
- 답변이 자주 끊기면 `.env`의 `AI_MAX_TOKENS` 값을 1200~1600 정도로 올려 테스트할 수 있습니다.

LM Studio 설정 순서:

1. LM Studio를 설치합니다.
2. LM Studio에서 사용할 모델을 다운로드합니다.
3. 왼쪽 메뉴의 `Developer` 또는 `Local Server` 화면으로 이동합니다.
4. Local Server를 켭니다.
5. 기본 주소가 `http://localhost:1234/v1`인지 확인합니다.
6. EasyPick 사이트의 관리자 페이지로 이동합니다.
7. `AI 연결 설정`에서 AI 서버를 `LM Studio`로 선택합니다.
8. LM Studio 주소를 `http://host.docker.internal:1234/v1`로 입력합니다.
9. 모델 새로고침 버튼으로 LM Studio 모델 목록을 불러옵니다.
10. 사용할 모델을 선택하고 `AI 연결 테스트`를 누릅니다.
11. 정상으로 뜨면 `AI 설정 저장`을 누릅니다.

Docker 컨테이너 안의 백엔드에서 내 PC의 LM Studio로 접근해야 하므로, Docker 실행 기준 주소는 아래처럼 씁니다.

```text
http://host.docker.internal:1234/v1
```

백엔드를 Docker 밖에서 직접 실행하는 경우에는 아래 주소를 씁니다.

```text
http://localhost:1234/v1
```

프로젝트 루트에 `.env` 파일을 만들면 기본값을 직접 지정할 수 있습니다.

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

`.env`를 수정했다면 백엔드를 다시 올립니다.

```powershell
docker compose up -d --build backend
```

## 6. 브라우저에서 접속

모든 실행이 끝나면 브라우저에서 아래 주소를 엽니다.

```text
http://localhost:5173
```

관리자 페이지는 아래 주소입니다.

```text
http://localhost:5173/admin
```

백엔드 API 문서는 아래 주소입니다.

```text
http://localhost:8000/docs
```

현재 연결된 AI 서버와 모델은 아래 주소에서 확인할 수 있습니다.

```text
http://localhost:8000/api/health
```

## 7. 정상 실행 확인

터미널에서 아래 명령어를 실행합니다.

```powershell
docker compose ps
```

아래 컨테이너들이 `Up` 상태이면 정상입니다.

- `easypick-db`
- `easypick-ollama`
- `easypick-backend`
- `easypick-frontend`

Ollama 모델까지 확인하려면 아래 명령어를 실행합니다.

```powershell
docker exec -it easypick-ollama ollama list
```

아래 두 줄이 보이면 Ollama 준비가 완료된 것입니다.

```text
qwen3:4b
easypick-ai:latest
```

LM Studio를 사용하는 경우에는 관리자 페이지에서 모델 목록 새로고침과 연결 테스트로 확인합니다.

## 8. 이번 버전에서 추가된 AI 관련 기능

이번 버전에는 AI 사용 편의성을 위해 아래 기능이 추가되어 있습니다.

- 관리자 페이지에서 Ollama와 LM Studio 선택 가능
- LM Studio 주소 입력 가능
- LM Studio에 설치된 모델 목록 자동 불러오기
- AI 연결 테스트 기능
- 현재 모델 연결 끊기 기능
- AI 서버를 바꿀 때 기존 서버 모델 연결 정리
- 상품 DB 컬럼 `상세설명`, `추천대상`, `주의사항` 추가
- AI 프롬프트가 딱딱한 규칙 위주에서 자연어 쇼핑 상담 말투로 개선
- 상품 후보를 기계적인 필드 나열이 아니라 자연어 상품 카드 형태로 LLM에 전달
- 프롬프트가 너무 길어지지 않도록 컨텍스트 예산 계산 적용
- AI 쇼핑도우미 최근 답변 5개 유지
- AI 쇼핑도우미, 비교, 리뷰 요약 생성 중 다른 페이지로 이동해도 상태 유지
- 백엔드 fallback 답변 대체 제거

주의:

- 앱 내부에서 다른 페이지로 이동하는 동안에는 생성 중 상태가 유지됩니다.
- 브라우저 새로고침이나 탭 닫기 중 생성 중이던 요청까지 이어받으려면 백엔드 작업 ID 방식이 추가로 필요합니다.

## 9. 발표 시연 추천 순서

1. 메인 페이지 접속: http://localhost:5173
2. 검색창에 `무선청소기` 입력
3. 상품 목록에서 최고가를 `200000`으로 입력
4. 상품 2개 또는 3개를 `비교 담기`
5. 비교 페이지로 이동
6. `AI 비교 설명 요청` 버튼 클릭
7. 비교 설명 생성 중 상품 목록이나 상세 페이지로 이동했다가 다시 비교 페이지로 돌아와 상태 유지 확인
8. AI 도우미 페이지로 이동
9. `30만원대 이어폰 있냐?` 또는 `20만 원 이하로 자취방에서 쓸 무선청소기 추천해줘` 입력
10. 최근 질문/답변이 5개까지 유지되는지 확인
11. 상품 상세 페이지로 이동
12. AI 리뷰 요약 요청 후 다른 페이지로 갔다가 돌아와 상태 유지 확인
13. 장바구니 담기
14. 주문서 작성 후 결제 시뮬레이션 완료
15. 관리자 페이지에서 상품 등록, AI 서버 변경, 모델 연결 테스트 시연

## 10. 자주 발생하는 문제 해결

### 상품 목록이 안 뜨는 경우

먼저 백엔드가 상품 데이터를 주는지 확인합니다.

```text
http://localhost:8000/api/products
```

상품 JSON이 보이면 DB와 백엔드는 정상입니다.
사이트 화면만 이상하면 브라우저에서 `Ctrl + F5`로 강력 새로고침합니다.

상품 JSON도 안 보이면 아래 명령어로 컨테이너 상태를 확인합니다.

```powershell
docker compose ps
```

DB를 완전히 초기화해야 할 때는 아래 명령어를 사용합니다.

```powershell
docker compose down -v
docker compose up -d --build
docker compose up ollama-init
```

주의: `down -v`는 DB 데이터와 Ollama 모델 볼륨도 지웁니다. 모델 다운로드를 다시 해야 할 수 있습니다.

### AI가 답변하지 않는 경우

Ollama 사용 중이면 대부분 `easypick-ai` 모델 생성이 아직 안 끝난 경우입니다.

```powershell
docker compose up ollama-init
docker exec -it easypick-ollama ollama list
```

`easypick-ai:latest`가 보이면 다시 사이트에서 AI 기능을 눌러봅니다.

LM Studio 사용 중이면 아래를 확인합니다.

- LM Studio 앱이 켜져 있는지 확인
- Local Server가 켜져 있는지 확인
- LM Studio 주소가 `http://host.docker.internal:1234/v1`인지 확인
- 관리자 페이지에서 모델 목록 새로고침
- 관리자 페이지에서 AI 연결 테스트 실행
- Ollama와 LM Studio가 동시에 큰 모델을 로드하고 있으면 한쪽 모델 연결 끊기

### AI 답변이 중간에 끊기는 경우

대부분 출력 길이 제한 또는 모델 크기 문제입니다.

- `.env`에서 `AI_MAX_TOKENS=1200` 또는 `AI_MAX_TOKENS=1600`으로 올려봅니다.
- Gemma4 E2B처럼 작은 모델은 긴 한국어 답변이 중간에 끊길 수 있습니다.
- 노트북 시연에서는 `gemma-4-e2b-uncensored-hauhaucs-aggressive` 모델을 권장합니다.
- GPU 메모리가 부족하면 `LMSTUDIO_CONTEXT_LENGTH` 또는 `OLLAMA_NUM_CTX`를 4096으로 낮춰봅니다.

### GPU를 안 쓰는 경우

Ollama는 GPU 모드로 실행되어야 GPU를 사용합니다.
Windows에서는 `start-easypick.bat` 또는 `start-easypick.ps1`을 사용하면 NVIDIA GPU를 감지해 GPU compose 파일을 같이 적용합니다.
자세한 내용은 [GPU_AUTO_RUN.md](./GPU_AUTO_RUN.md)를 확인합니다.

### 포트 충돌이 나는 경우

다른 프로그램이 아래 포트를 쓰고 있을 수 있습니다.

- 프론트엔드: 5173
- 백엔드: 8000
- DB: 5432
- Ollama: 11434
- LM Studio: 1234

기존 프로그램을 종료하거나 `docker-compose.yml`에서 포트 번호를 바꿔야 합니다.

### Docker가 너무 느리거나 멈추는 경우

Docker Desktop 설정에서 메모리를 최소 8GB 정도로 올리는 것을 권장합니다.
특히 AI 모델을 실행하기 때문에 메모리가 부족하면 응답이 느릴 수 있습니다.

## 11. 종료 방법

사이트를 끄려면 프로젝트 폴더에서 아래 명령어를 실행합니다.

```powershell
docker compose down
```

DB 데이터까지 완전히 지우고 처음 상태로 되돌리려면 아래 명령어를 사용합니다.

```powershell
docker compose down -v
```

## 12. 기억할 점

- 모델 파일 자체는 GitHub에 올라가지 않습니다.
- `docker compose up ollama-init`이 Ollama 모델을 자동으로 다운로드하고 `easypick-ai`를 만듭니다.
- LM Studio 모델은 각자 PC의 LM Studio에서 직접 다운로드해야 합니다.
- 외부 AI API 키는 필요 없습니다.
- 상품 데이터는 `database/init.sql`에 있습니다.
- 새 상품은 사이트의 관리자 페이지에서도 추가할 수 있습니다.
- 관리자 페이지에서 AI 서버를 변경하면 현재 연결된 모델 상태를 정리한 뒤 새 설정을 저장합니다.
