# GPU 자동 실행 안내

EasyPick AI는 기본적으로 CPU에서도 실행됩니다.
다만 NVIDIA GPU가 있는 PC에서는 Ollama가 GPU를 사용하도록 실행할 수 있습니다.

## 가장 쉬운 실행 방법

Windows에서는 프로젝트 폴더에서 아래 파일을 실행합니다.

```text
start-easypick.bat
```

또는 PowerShell에서 직접 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\start-easypick.ps1
```

이 스크립트는 자동으로 아래 작업을 수행합니다.

1. Docker Desktop 실행 여부 확인
2. `nvidia-smi` 명령어로 NVIDIA GPU 사용 가능 여부 확인
3. GPU가 있으면 `docker-compose.gpu.yml`을 함께 적용
4. GPU가 없으면 기본 CPU 모드로 실행
5. `qwen3:4b` 모델을 준비하고 `easypick-ai` 모델을 생성

## GPU가 있을 때 적용되는 설정

GPU가 감지되면 아래 Compose 파일이 추가로 적용됩니다.

```text
docker-compose.gpu.yml
```

이 파일은 Ollama 컨테이너에 다음 설정을 추가합니다.

```yaml
gpus: all
```

즉, NVIDIA GPU가 있는 PC에서는 AI 응답 속도가 더 빨라질 수 있습니다.

## GPU 사용 여부 확인

호스트 PC에서 확인:

```powershell
nvidia-smi
```

컨테이너 안에서 확인:

```powershell
docker exec -it easypick-ollama nvidia-smi
```

컨테이너 안에서도 GPU 정보가 보이면 Docker가 GPU를 정상 인식한 것입니다.

## 주의사항

- NVIDIA GPU가 없는 PC에서는 CPU 모드로 실행됩니다.
- GPU 모드는 NVIDIA 드라이버와 Docker Desktop의 WSL2 GPU 지원이 정상이어야 합니다.
- GPU 설정이 실패하면 기본 명령어로 CPU 모드 실행이 가능합니다.

CPU 모드 수동 실행:

```powershell
docker compose up -d --build
docker compose up ollama-init
```

GPU 모드 수동 실행:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up ollama-init
```
