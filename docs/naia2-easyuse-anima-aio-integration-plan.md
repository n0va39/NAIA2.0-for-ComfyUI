# NAIA2.0 x ComfyUI-EasyUseAnima AiO Integration Plan

작성일: 2026-07-06

## 목적

NAIA2.0의 ComfyUI 모드에서 `Anima AiO Generator`를 직접 제어할 수 있게 한다. 기존 "커스텀 워크플로우를 불러와 일부 노드 값을 치환"하는 방식은 유지하되, ANIMA/EasyUseAnima 전용 경로는 별도 계약으로 분리한다.

## 결론

권장 방향은 **별도 ComfyUI extension을 먼저 만들기보다, NAIA2.0의 기존 ComfyUI 기능에 `EasyUseAnima AiO` 모드를 추가하고, ComfyUI-EasyUseAnima에는 작은 공개 계약 API를 추가하는 방식**이다.

이유:

- NAIA2.0은 이미 `COMFYUI` API 모드, `ComfyUIService`, `ComfyUIWorkflowManager`, ComfyUI 파라미터 패널, `/api/comfyui/random` 원격 API를 갖고 있다.
- EasyUseAnima는 이미 `EasyUseAnimaPromptStudioAdvancedV2`, `EasyUseAnimaInput`, `EasyUseAnimaAIOGenerator`와 `generation_settings` JSON 저장 모델을 갖고 있다.
- 제3의 ComfyUI extension을 만들면 설치/버전/의존성 축이 하나 늘어난다. 현재 목표는 NAIA2.0에서 EasyUseAnima AiO를 제어하는 것이므로, 제어 UI와 요청 생성은 NAIA2.0에 두는 편이 자연스럽다.
- 다만 EasyUseAnima 내부의 숨은 JSON 구조를 NAIA2.0이 직접 하드코딩하면 깨지기 쉽다. EasyUseAnima 쪽에 스키마/기본값/노드 계약을 반환하는 읽기 전용 API를 추가해야 한다.

따라서 이 저장소(`NAIA2.0-for-ComfyUI`)는 초기에는 조율/설계/프로토타입 저장소로 쓰고, 실제 코드는 두 upstream 저장소에 나누어 PR로 반영한다.

## 확인한 현재 구조

### NAIA2.0

참조 기준:

- Repository: `DNT-LAB/NAIA2.0`
- Local reference clone: `D:\ComfyUI\custom_nodes_workplace\.tmp\naia2-ref`
- Checked commit: `1549b3b`

관련 구조:

- `core/comfyui_service.py`
  - ComfyUI `/system_stats`, `/prompt`, `/history/{prompt_id}`, `/view`를 HTTP polling 방식으로 사용한다.
  - WebSocket 진행률 대신 HTTP polling을 쓴다.
- `core/comfyui_workflow_manager.py`
  - 기본 checkpoint workflow와 ANIMA용 `UNETLoader + CLIPLoader + VAELoader + KSampler` workflow를 내부 dict로 생성한다.
  - 사용자 workflow metadata를 읽고 `validate_and_map_workflow`, `apply_params_to_workflow`로 일부 노드 입력을 치환한다.
  - `locked_unknown` workflow에서는 모델 로더를 잠그고 나머지 파라미터만 치환한다.
- `core/api_service.py`
  - `api_mode == "COMFYUI"`이면 `params["workflow"]`를 ComfyUI에 queue한다.
- `core/generation_controller.py`
  - 생성 직전 `workflow_manager.apply_params_to_workflow(params)`를 호출해 ComfyUI prompt graph를 만든다.
  - wildcard expansion은 ComfyUI workflow 생성 전에 처리된다.
- `core/remote_api_server.py`
  - `POST /api/comfyui/random`이 존재한다.
  - 응답은 `prompt`, `negative_prompt`, `width`, `height`, `remaining`, `source` 중심이다.
- `ui/interactive/comfyui_parameter_panel.py`
  - 현재 ComfyUI UI는 model, sampling mode, steps, cfg, sampler, scheduler, rescale_cfg 중심이다.
  - AiO의 highres/detailer/save/model patch 같은 설정은 없다.

현재 한계:

- workflow 치환기는 `KSampler`, `CheckpointLoaderSimple`, `UNETLoader`, `CLIPLoader`, `EmptyLatentImage` 같은 일반 노드 중심으로 설계되어 있다.
- EasyUseAnima AiO의 핵심 상태인 `generation_settings` JSON을 모른다.
- `Anima AiO Generator`는 hidden serialized widget에 설정을 저장하므로, 일반 workflow patch 방식만으로는 안전하게 제어하기 어렵다.

### ComfyUI-EasyUseAnima

참조 기준:

- Repository: `n0va39/ComfyUI-EasyUseAnima`
- Local worktree: `D:\ComfyUI\custom_nodes_workplace\worktrees\ComfyUI-EasyUseAnima\dev`
- Checked commit: `5fa0312`

관련 구조:

- `__init__.py`
  - `EasyUseAnimaPromptStudioAdvancedV2` -> display `Anima Prompt Studio Advanced v2`
  - `EasyUseAnimaInput` -> display `Easy Use Anima Input`
  - `EasyUseAnimaAIOGenerator` -> display `Anima AiO Generator`
- `nodes.py`
  - `PROMPT_DATA_TYPE = "EASYUSE_ANIMA_PROMPT_DATA"`
  - `EASY_USE_ANIMA_INPUT_TYPE = "EASY_USE_ANIMA_INPUT"`
  - `AIO_GENERATION_SETTINGS_SCHEMA = "easyuse_anima_aio_generation_settings"`
  - `AIO_GENERATION_DEFAULT_SETTINGS`에 sampler, model_patches, mod_guidance, artist_mix, highres, upscale, postprocess, detailer, save, preview 설정이 모여 있다.
  - `EasyUseAnimaInput`은 prompt data와 ANIMA 리소스 이름을 하나의 context로 묶는다.
  - `EasyUseAnimaAIOGenerator`는 `easy_use_anima_input`, hidden `generation_settings`, optional `lora_stack`을 받아 샘플링, Highres, Detailer, Upscale, Postprocess, Save를 실행한다.
- `api.py`
  - `/easyuse_anima/settings`, `/easyuse_anima/autocomplete`, `/easyuse_anima/classify_prompt`, `/easyuse_anima/translate_prompt`, LoRA profile API가 있다.
  - 아직 AiO schema/contract API는 없다.
- `docs/nodes/anima-aio-generator.en.md`
  - AiO Generator는 Prompt Studio upstream prompt data context를 받아 prompt encoding, first-pass sampling, optional Highres, optional Detailer, image saving을 한 노드에서 실행한다.
  - prompt fields는 generator UI에 두지 않고 Prompt Studio에 남긴다.

현재 장점:

- AiO 설정이 이미 versioned JSON으로 직렬화된다.
- settings normalization 함수가 있어 외부 입력을 받아도 기본값 merge와 clamp를 처리할 수 있다.
- ComfyUI `/object_info`만으로도 node class id와 input shape 일부는 확인 가능하다.

현재 한계:

- `AIO_GENERATION_DEFAULT_SETTINGS`와 normalization 결과를 외부에서 안정적으로 읽는 API가 없다.
- NAIA2.0이 이 구조를 직접 복사하면 EasyUseAnima release마다 drift가 생긴다.

## 목표 UX

NAIA2.0에서 ComfyUI 모드를 선택한 뒤, generation backend를 다음처럼 고를 수 있게 한다.

- `Generic ComfyUI Workflow`
  - 현재 기능 유지.
  - 기존 workflow import/patch 기능을 그대로 사용.
- `EasyUseAnima AiO`
  - NAIA2.0 UI에서 prompt, negative, resolution, seed, sampler, highres, detailer, save options를 설정한다.
  - NAIA2.0은 EasyUseAnima AiO prompt graph를 생성해 ComfyUI `/prompt`에 queue한다.
  - ComfyUI에는 EasyUseAnima node pack이 설치되어 있어야 한다.
  - EasyUseAnima가 없거나 버전/스키마가 맞지 않으면 구체적인 오류를 보여준다.

## 권장 아키텍처

```text
NAIA2.0
  UI: ComfyUI mode
    - Generic Workflow panel
    - EasyUseAnima AiO panel
  Core
    - ComfyUIService: existing /prompt queue, /history polling
    - EasyUseAnimaAioContractClient: /object_info + /easyuse_anima/aio/schema 조회
    - EasyUseAnimaAioWorkflowBuilder: prompt graph 생성

ComfyUI
  ComfyUI-EasyUseAnima
    - existing nodes
    - new read-only contract routes
      GET /easyuse_anima/aio/schema
      GET /easyuse_anima/aio/status
```

## EasyUseAnima 쪽 변경 제안

### 1. AiO schema/status API 추가

새 endpoint 후보:

- `GET /easyuse_anima/aio/schema`
- `GET /easyuse_anima/aio/status`

응답 예시:

```json
{
  "schema": "easyuse_anima_aio_generation_settings",
  "version": 1,
  "node_classes": {
    "prompt_studio": "EasyUseAnimaPromptStudioAdvancedV2",
    "input": "EasyUseAnimaInput",
    "generator": "EasyUseAnimaAIOGenerator",
    "lora_preset": "EasyUseAnimaLoraPreset"
  },
  "types": {
    "prompt_data": "EASYUSE_ANIMA_PROMPT_DATA",
    "easy_use_input": "EASY_USE_ANIMA_INPUT"
  },
  "defaults": {
    "generation_settings": {}
  },
  "capabilities": {
    "txt2img": true,
    "img2img": false,
    "sampler_backends": [
      "comfy_ksampler",
      "spectrum_mod_guidance_advanced",
      "spectrum_spd_speed"
    ],
    "highres": true,
    "detailer": true,
    "upscale": true,
    "postprocess": true,
    "save": true
  },
  "optional_node_packs": {
    "ComfyUI-Spectrum-KSampler": "unknown",
    "ComfyUI-Image-Saver": "unknown",
    "ComfyUI-Impact-Pack": "unknown",
    "ComfyUI-KJNodes": "unknown"
  }
}
```

원칙:

- API는 읽기 전용이다.
- defaults는 EasyUseAnima 내부 정규화 모델에서 나온다.
- NAIA2.0이 내부 Python 함수를 import하지 않는다.
- schema version이 올라가면 NAIA2.0은 호환 범위를 판단한다.

### 2. AiO graph template contract 문서화

문서 위치 후보:

- `docs/development/aio-external-control-contract.md`
- `docs/nodes/anima-aio-generator.en.md`에 "External control" 섹션 추가

문서화할 것:

- 필요한 node class ids
- required/optional inputs
- `generation_settings` JSON의 안정 필드
- unsupported mode: 현재 generator는 `txt2img`만 허용
- saved workflow 재현성 조건

### 3. regression test 추가

후보:

- `tests/test_aio_contract_api.py`
- `tests/test_aio_nodes.py`에 schema/default normalization assertion 추가

검증:

- schema endpoint가 `AIO_GENERATION_DEFAULT_SETTINGS`의 현재 schema/version을 반환한다.
- 반환 JSON이 직렬화 가능하다.
- `EasyUseAnimaAIOGenerator.INPUT_TYPES()`의 node contract와 endpoint의 node contract가 어긋나지 않는다.

## NAIA2.0 쪽 변경 제안

### 1. backend mode 분리

현재 `api_mode == "COMFYUI"` 아래에 sub-mode를 추가한다.

후보 enum:

- `comfyui_workflow_mode = "generic"`
- `comfyui_workflow_mode = "easyuse_anima_aio"`

영향 파일 후보:

- `ui/interactive/comfyui_parameter_panel.py`
- `core/generation_controller.py`
- `core/comfyui_workflow_manager.py`
- `core/api_service.py`

### 2. EasyUseAnima contract client 추가

후보 파일:

- `core/easyuse_anima_aio_contract.py`

책임:

- ComfyUI URL normalize
- `/object_info` 조회
- `/easyuse_anima/aio/schema` 조회
- node pack 설치/버전/스키마 확인
- 명확한 오류 메시지 생성

오류 예:

- `ComfyUI-EasyUseAnima is not installed or did not register EasyUseAnimaAIOGenerator.`
- `ComfyUI-EasyUseAnima AiO schema endpoint is missing. Update ComfyUI-EasyUseAnima.`
- `Unsupported EasyUseAnima AiO schema version: expected 1, got 2.`

### 3. AiO workflow builder 추가

후보 파일:

- `core/easyuse_anima_aio_workflow_builder.py`

책임:

- NAIA prompt/negative/resolution/settings를 EasyUseAnima prompt graph로 변환한다.
- 초기 MVP는 `Prompt Studio Advanced v2 -> Easy Use Anima Input -> Anima AiO Generator -> Preview/Save` 최소 graph를 만든다.
- `generation_settings`는 schema endpoint defaults를 merge해서 만든다.
- NAIA2.0 기존 generic workflow manager와 책임을 섞지 않는다.

MVP graph 방향:

```text
EasyUseAnimaPromptStudioAdvancedV2
  -> EASYUSE_ANIMA_PROMPT_DATA
EasyUseAnimaInput
  <- EASYUSE_ANIMA_PROMPT_DATA
  <- unet_name / vae_name / clip_name / clip_type
EasyUseAnimaAIOGenerator
  <- EASY_USE_ANIMA_INPUT
  <- generation_settings JSON
```

주의:

- ComfyUI prompt graph에는 UI workflow 좌표가 필요 없다. `/prompt`용 API graph만 만들면 된다.
- 저장 이미지에 workflow를 embed해야 하는 경우 UI workflow JSON 또는 `extra_pnginfo` 경로를 별도 검토해야 한다.
- `lora_stack`은 MVP에서 제외하고, 2차 PR에서 `Anima LoRA Preset` 연계로 확장한다.

### 4. UI 패널 확장

MVP에서 노출할 항목:

- EasyUseAnima install/status check
- diffusion model (`unet_name`)
- VAE (`vae_name`)
- CLIP (`clip_name`)
- CLIP type
- seed / seed after generate
- steps / cfg / sampler / scheduler / denoise
- sampler backend
- highres enable + scale/denoise/steps
- save enable + filename prefix

2차 이후:

- Spectrum advanced inputs
- DIT correction options
- Detailer face/eye/custom target tabs
- Upscale
- Postprocess final fit
- Image Saver Civitai hash rows
- LoRA stack/preset integration

### 5. 기존 custom workflow 기능 유지

`ComfyUIWorkflowManager`의 기존 generic workflow import/patch는 유지한다.

새 AiO builder는 다음 조건에서만 사용한다.

```python
if api_mode == "COMFYUI" and comfyui_workflow_mode == "easyuse_anima_aio":
    workflow = easyuse_anima_aio_builder.build(params)
else:
    workflow = comfyui_workflow_manager.apply_params_to_workflow(params)
```

## Extension 방식 판단

### 별도 ComfyUI extension으로 시작하지 않는 이유

- ComfyUI extension은 ComfyUI 내부에 설치되는 세 번째 패키지가 된다.
- 이미 EasyUseAnima가 ComfyUI node pack 역할을 한다.
- NAIA2.0의 목적은 외부 자동화/제어 UI이므로, 사용자 입력과 생성 요청의 소유권은 NAIA2.0에 두는 편이 맞다.
- EasyUseAnima 내부 기능을 또 다른 ComfyUI extension에서 감싸면 버전 호환 문제가 더 복잡해진다.

### 별도 extension을 검토할 수 있는 경우

다음 조건이 생기면 `NAIA2.0-for-ComfyUI`를 실제 extension으로 전환할 수 있다.

- NAIA2.0을 실행하지 않고도 ComfyUI 안에서 NAIA prompt generation을 직접 호출해야 한다.
- EasyUseAnima에 직접 넣기 어려운 NAIA 전용 ComfyUI node가 필요하다.
- ComfyUI Manager/Registry를 통한 별도 배포가 사용자 설치 흐름을 더 단순하게 만든다.

현재 단계에서는 이 조건이 아직 아니다.

## 이슈/PR 분할안

### Issue 1: EasyUseAnima AiO external control contract

대상 repo:

- `n0va39/ComfyUI-EasyUseAnima`

작업:

- `/easyuse_anima/aio/schema` 추가
- `/easyuse_anima/aio/status` 추가
- contract 문서 추가
- schema/default regression test 추가

완료 조건:

- ComfyUI 실행 중 endpoint가 JSON을 반환한다.
- 반환 schema/version/node class ids가 실제 node mapping과 일치한다.
- 기존 AiO UI/워크플로우 동작 변경 없음.

### Issue 2: NAIA2.0 EasyUseAnima AiO contract client

대상 repo:

- `DNT-LAB/NAIA2.0`

작업:

- ComfyUI URL 기준으로 `/object_info`, `/easyuse_anima/aio/schema`, `/easyuse_anima/aio/status` 조회
- 설치/스키마/버전 오류 메시지 정리
- headless test 추가

완료 조건:

- EasyUseAnima 설치 상태를 UI나 로그에서 명확히 구분한다.
- schema endpoint가 없을 때 generic workflow 모드는 깨지지 않는다.

### Issue 3: NAIA2.0 EasyUseAnima AiO workflow builder MVP

대상 repo:

- `DNT-LAB/NAIA2.0`

작업:

- `easyuse_anima_aio` workflow mode 추가
- MVP API graph builder 추가
- prompt/negative/resolution/sampler/highres/save 최소 매핑
- 기존 generic workflow path 유지

완료 조건:

- NAIA2.0에서 생성한 API graph가 ComfyUI `/prompt` validation을 통과한다.
- EasyUseAnima AiO Generator가 실제 queue에서 실행된다.
- generic ComfyUI workflow tests가 기존대로 통과한다.

### Issue 4: NAIA2.0 AiO UI controls

대상 repo:

- `DNT-LAB/NAIA2.0`

작업:

- ComfyUI Settings에 workflow mode selector 추가
- AiO mode일 때 AiO 기본 컨트롤 노출
- schema/status check 결과 표시
- unsupported feature는 비활성화하고 이유 표시

완료 조건:

- `Generic` 모드 UI와 기존 동작이 유지된다.
- `EasyUseAnima AiO` 모드에서 MVP graph 설정을 저장/복원할 수 있다.

### Issue 5: LoRA/detailer/upscale/save metadata 확장

대상 repo:

- 우선 `DNT-LAB/NAIA2.0`
- 필요 시 `n0va39/ComfyUI-EasyUseAnima`

작업:

- `Anima LoRA Preset` 또는 `LORA_STACK` 연결 방식 결정
- Detailer target order UI 매핑
- Upscale/Postprocess/Save Options 전체 매핑
- saved workflow 재현성 검증

완료 조건:

- AiO UI에서 설정한 고급 옵션이 generated metadata와 ComfyUI history에 일관되게 남는다.
- saved image workflow reload 재현성 확인.

## 검증 계획

### EasyUseAnima

기본 검증:

```powershell
node --check web\js\easyuse_anima_aio.js
D:\ComfyUI\ComfyUI_main\instances\ComfyUI_codex_test\.venv\Scripts\python.exe -m unittest discover -s tests
D:\ComfyUI\ComfyUI_main\instances\ComfyUI_codex_test\.venv\Scripts\python.exe -m compileall -q .
git diff --check
```

ComfyUI smoke:

```powershell
powershell -ExecutionPolicy Bypass -File D:\ComfyUI\custom_nodes_workplace\tools\codex\sync_nodepack_to_instance.ps1 -Project ComfyUI-EasyUseAnima
powershell -ExecutionPolicy Bypass -File D:\ComfyUI\custom_nodes_workplace\tools\codex\start_test_instance.ps1 -Port 8194
powershell -ExecutionPolicy Bypass -File D:\ComfyUI\custom_nodes_workplace\tools\codex\smoke_test_instance.ps1 -Port 8194
```

추가 검증:

- `GET /easyuse_anima/aio/schema`
- `GET /easyuse_anima/aio/status`
- `GET /object_info`에서 `EasyUseAnimaAIOGenerator`, `EasyUseAnimaInput`, `EasyUseAnimaPromptStudioAdvancedV2` 확인

### NAIA2.0

Headless:

```powershell
python tests/comfyui/test_workflow_compat.py
```

추가 테스트 후보:

- `tests/comfyui/test_easyuse_anima_aio_contract.py`
- `tests/comfyui/test_easyuse_anima_aio_workflow_builder.py`

Runtime smoke:

- ComfyUI test instance에 EasyUseAnima 설치
- NAIA2.0 ComfyUI URL을 test instance로 설정
- Generic workflow mode regression
- EasyUseAnima AiO mode queue validation
- 1장 생성 후 `/history/{prompt_id}` output 확인

## 주요 위험

- EasyUseAnima `generation_settings` schema가 바뀔 수 있다.
  - 대응: schema endpoint와 version gate를 둔다.
- NAIA2.0이 ComfyUI UI workflow와 API prompt graph를 혼동할 수 있다.
  - 대응: MVP는 `/prompt`용 API graph만 생성한다. workflow embed는 별도 이슈로 둔다.
- Save Options가 Image Saver backend에 의존한다.
  - 대응: MVP는 ComfyUI 기본 저장 또는 EasyUseAnima 기본 save setting으로 제한한다.
- Detailer/Impact-Pack/Spectrum/KJNodes 같은 optional node pack 상태가 환경마다 다르다.
  - 대응: status endpoint와 UI capability lock을 둔다.
- 현재 AiO Generator는 `txt2img`만 허용한다.
  - 대응: img2img/inpaint는 MVP 범위에서 제외한다.

## 다음 작업

1. 이 문서를 기준으로 EasyUseAnima Issue 1을 먼저 연다.
2. Issue 1 PR에서 schema/status API와 contract 문서를 추가한다.
3. 그 다음 NAIA2.0 Issue 2/3에서 contract client와 MVP workflow builder를 만든다.
