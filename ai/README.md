# EasyPick AI 로컬 모델

EasyPick AI는 외부 유료 AI API를 사용하지 않고 로컬 LLM으로 동작합니다.
기본값은 Docker Compose의 Ollama 컨테이너이고, 선택적으로 LM Studio의 로컬 OpenAI 호환 서버를 사용할 수 있습니다.

## 1. 기본 Ollama 방식

- 기본 모델: `qwen3:4b`
- EasyPick 전용 모델: `easypick-ai`
- 모델 파일은 저장소에 포함하지 않습니다.
- `ai/Modelfile`, 프롬프트 파일, 초기화 스크립트만 포함합니다.

`docker compose up -d`를 실행하면 `ollama-init` 서비스가 Ollama 서버 준비를 기다린 뒤 `qwen3:4b`를 pull하고 `easypick-ai` 모델을 생성합니다.
최초 실행은 모델 다운로드 때문에 시간이 걸릴 수 있습니다.

수동 확인:

```bash
docker exec -it easypick-ollama ollama list
```

아래 모델이 보이면 준비된 상태입니다.

```text
qwen3:4b
easypick-ai:latest
```

## 2. LM Studio 방식

LM Studio를 사용하면 Docker 안의 Ollama 대신 현재 PC에 설치된 LM Studio 모델을 사용할 수 있습니다.

설정 순서:

1. LM Studio 설치
2. LM Studio에서 사용할 모델 다운로드
3. `Developer` 또는 `Local Server` 화면에서 서버 켜기
4. 서버 주소 확인: 보통 `http://localhost:1234/v1`
5. EasyPick 관리자 페이지 접속
6. AI 서버를 `LM Studio`로 선택
7. 주소를 `http://host.docker.internal:1234/v1`로 입력
8. 모델 새로고침
9. 사용할 모델 선택
10. 연결 테스트
11. 설정 저장

Docker 컨테이너에서 호스트 PC의 LM Studio에 접근해야 하므로 Docker 실행 기준 주소는 `localhost`가 아니라 아래 주소를 사용합니다.

```text
http://host.docker.internal:1234/v1
```

백엔드를 Docker 밖에서 직접 실행할 때만 아래 주소를 씁니다.

```text
http://localhost:1234/v1
```

## 3. 추천 모델

자연스럽고 친근한 쇼핑 상담 말투를 원하면 아래 LM Studio 모델을 권장합니다.

- 권장 모델 ID: `gemma-4-e4b-uncensored-hauhaucs-aggressive`
- LM Studio 표시 이름: `Gemma 4 E4B Uncensored HauhauCS Aggressive`
- LM Studio에 표시되는 실제 모델 ID는 다운로드한 모델에 따라 달라질 수 있습니다.

모델별 참고:

- Gemma4 E4B Uncensored HauhauCS Aggressive: 현재 EasyPick에서 한국어 쇼핑 상담 말투가 가장 자연스럽게 출력되는 권장 모델입니다.
- 일반 `google/gemma-4-e4b`: 환경에 따라 답변 본문 `content`가 비고 `reasoning_content`로만 출력되는 문제가 생길 수 있습니다.
- Gemma4 E2B: 빠르고 가볍지만 긴 한국어 답변이 중간에 끊기거나 말투 제어가 약할 수 있습니다.
- Qwen 계열: 정보 정리는 괜찮지만, 쇼핑 상담원처럼 부드럽게 풀어 말하는 느낌은 모델/템플릿에 따라 약할 수 있습니다.

## 4. 프롬프트와 컨텍스트 설정

현재 백엔드는 상품 후보를 단순한 필드 목록으로 보내지 않고, 자연어 상품 카드 형태로 LLM에 전달합니다.
또한 프롬프트가 너무 길어져 컨텍스트를 넘지 않도록 글자 수 예산을 계산합니다.

관련 환경 변수:

```env
OLLAMA_NUM_CTX=8192
LMSTUDIO_CONTEXT_LENGTH=8192
AI_MAX_TOKENS=900
PROMPT_CONTEXT_BUFFER_TOKENS=1200
PROMPT_CHAR_BUDGET=0
```

의미:

- `OLLAMA_NUM_CTX`: Ollama 호출 시 사용할 컨텍스트 길이
- `LMSTUDIO_CONTEXT_LENGTH`: LM Studio 모델 로드 시 요청할 컨텍스트 길이
- `AI_MAX_TOKENS`: AI가 생성할 최대 답변 길이
- `PROMPT_CONTEXT_BUFFER_TOKENS`: 출력 여유분으로 남겨둘 토큰 수
- `PROMPT_CHAR_BUDGET`: 0이면 자동 계산, 값을 넣으면 프롬프트 글자 수 상한 직접 지정

답변이 중간에 끊기면 `AI_MAX_TOKENS`를 1200~1600 정도로 올려 테스트합니다.
GPU 메모리가 부족하거나 모델이 로드되지 않으면 `OLLAMA_NUM_CTX` 또는 `LMSTUDIO_CONTEXT_LENGTH`를 4096으로 낮춰봅니다.

## 5. 프롬프트 파일

프롬프트 파일은 아래 위치에 있습니다.

```text
ai/prompts/recommend_prompt.txt
ai/prompts/compare_prompt.txt
ai/prompts/review_summary_prompt.txt
```

현재 프롬프트는 너무 엄격한 보고서형 답변보다, 사용자의 짧은 자연어 질문을 받아주고 친근하게 설명하는 쇼핑 상담원 말투에 맞춰져 있습니다.
예를 들어 `30만원대 이어폰 있냐?`처럼 말해도 바로 거절하지 않고, DB 안의 가까운 후보를 찾아 설명하도록 구성되어 있습니다.

## 6. 모델 연결 관리

관리자 페이지에는 아래 기능이 있습니다.

- Ollama 또는 LM Studio 선택
- 각 서버 주소 입력
- 모델 목록 새로고침
- 연결 테스트
- 현재 모델 연결 끊기
- AI 서버 변경 시 기존 서버 모델 연결 정리

Ollama와 LM Studio가 동시에 큰 모델을 로드하면 GPU/메모리를 많이 사용할 수 있으므로, 서버를 바꿀 때는 모델 연결 끊기 기능을 활용하는 것이 좋습니다.
