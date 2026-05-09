# EasyPick AI 로컬 모델

EasyPick AI는 외부 유료 AI API를 사용하지 않고 Docker Compose의 Ollama 컨테이너에서 실행됩니다.

- 기본 모델: `qwen3:4b`
- EasyPick 전용 모델: `easypick-ai`
- 모델 파일은 저장소에 포함하지 않습니다.
- `ai/Modelfile`, 프롬프트 파일, 초기화 스크립트만 포함합니다.

`docker compose up -d`를 실행하면 `ollama-init` 서비스가 Ollama 서버 준비를 기다린 뒤 `qwen3:4b`를 pull하고 `easypick-ai` 모델을 생성합니다. 최초 실행은 모델 다운로드 때문에 시간이 걸릴 수 있습니다.
