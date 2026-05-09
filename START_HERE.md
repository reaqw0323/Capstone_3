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
- 리뷰 확인
- 여러 상품 비교
- AI에게 상품 추천 요청
- AI에게 비교 설명 요청
- AI 리뷰 요약 요청
- 장바구니 담기
- 주문서 작성과 결제 시뮬레이션
- 관리자 페이지에서 상품 등록/수정/삭제

AI는 외부 유료 API를 사용하지 않습니다.
Docker 안에서 Ollama가 실행되고, `qwen3:4b` 모델을 다운로드한 뒤 `easypick-ai`라는 EasyPick 전용 모델을 만들어 사용합니다.

## 2. 실행 전에 설치해야 하는 것

팀원 PC에 아래 프로그램이 설치되어 있어야 합니다.

1. Git
2. Docker Desktop
3. Docker Compose

Windows에서는 보통 Docker Desktop만 설치하면 Docker Compose도 같이 설치됩니다.
Docker Desktop 설치 후에는 PC를 한 번 재부팅하는 것이 좋습니다.

## 3. 프로젝트 다운로드

GitHub에 올라간 프로젝트를 받을 폴더에서 터미널을 엽니다.
Windows라면 PowerShell을 사용하면 됩니다.

```powershell
git clone <GitHub 저장소 주소>
cd shopsense
```

저장소 폴더 이름을 `easypick`으로 바꿨다면 아래처럼 이동합니다.

```powershell
cd easypick
```

중요한 점: 명령어는 `docker-compose.yml` 파일이 있는 폴더에서 실행해야 합니다.

## 4. 사이트 실행

아래 명령어를 순서대로 실행합니다.

```powershell
docker compose up -d --build
```

이 명령은 다음 서비스를 실행합니다.

- PostgreSQL DB
- FastAPI 백엔드
- React 프론트엔드
- Ollama AI 서버

그 다음 AI 모델을 준비합니다.

```powershell
docker compose up ollama-init
```

처음 실행할 때는 `qwen3:4b` 모델을 다운로드합니다.
모델 크기가 크기 때문에 인터넷 속도에 따라 몇 분 이상 걸릴 수 있습니다.
중간에 멈춘 것처럼 보여도 로그가 계속 진행 중이면 기다리면 됩니다.

## 5. 브라우저에서 접속

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

## 6. 정상 실행 확인

터미널에서 아래 명령어를 실행합니다.

```powershell
docker compose ps
```

아래 컨테이너들이 `Up` 상태이면 정상입니다.

- `easypick-db`
- `easypick-ollama`
- `easypick-backend`
- `easypick-frontend`

AI 모델까지 확인하려면 아래 명령어를 실행합니다.

```powershell
docker exec -it easypick-ollama ollama list
```

아래 두 줄이 보이면 AI 준비가 완료된 것입니다.

```text
qwen3:4b
easypick-ai:latest
```

## 7. 발표 시연 추천 순서

1. 메인 페이지 접속: http://localhost:5173
2. 검색창에 `무선청소기` 입력
3. 상품 목록에서 최고가를 `200000`으로 입력
4. 상품 2개 또는 3개를 `비교 담기`
5. 비교 페이지로 이동
6. `AI 비교 설명 요청` 버튼 클릭
7. AI 도우미 페이지로 이동
8. `20만 원 이하로 자취방에서 쓸 무선청소기 추천해줘` 입력
9. AI 추천 결과에서 관련 상품 확인
10. 상품 상세 페이지로 이동
11. 장바구니 담기
12. 주문서 작성 후 결제 시뮬레이션 완료
13. 관리자 페이지에서 새 상품 등록 또는 주문 상태 변경

## 8. 자주 발생하는 문제 해결

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

대부분 `easypick-ai` 모델 생성이 아직 안 끝난 경우입니다.

```powershell
docker compose up ollama-init
docker exec -it easypick-ollama ollama list
```

`easypick-ai:latest`가 보이면 다시 사이트에서 AI 기능을 눌러봅니다.

### 포트 충돌이 나는 경우

다른 프로그램이 아래 포트를 쓰고 있을 수 있습니다.

- 프론트엔드: 5173
- 백엔드: 8000
- DB: 5432
- Ollama: 11434

기존 프로그램을 종료하거나 `docker-compose.yml`에서 포트 번호를 바꿔야 합니다.

### Docker가 너무 느리거나 멈추는 경우

Docker Desktop 설정에서 메모리를 최소 8GB 정도로 올리는 것을 권장합니다.
특히 AI 모델을 실행하기 때문에 메모리가 부족하면 응답이 느릴 수 있습니다.

## 9. 종료 방법

사이트를 끄려면 프로젝트 폴더에서 아래 명령어를 실행합니다.

```powershell
docker compose down
```

DB 데이터까지 완전히 지우고 처음 상태로 되돌리려면 아래 명령어를 사용합니다.

```powershell
docker compose down -v
```

## 10. 기억할 점

- 모델 파일 자체는 GitHub에 올라가지 않습니다.
- `docker compose up ollama-init`이 모델을 자동으로 다운로드하고 `easypick-ai`를 만듭니다.
- 외부 AI API 키는 필요 없습니다.
- 상품 데이터는 `database/init.sql`에 있습니다.
- 새 상품은 사이트의 관리자 페이지에서도 추가할 수 있습니다.
