# NAIA2.0 x ComfyUI-EasyUseAnima AiO Integration Plan

작성일: 2026-07-06

## 목적

NAIA2.0의 ComfyUI 모드에서 `Anima AiO Generator`를 직접 제어할 수 있게 한다. 기존 "커스텀 워크플로우를 불러와 일부 노드 값을 치환"하는 방식은 유지하되, ANIMA/EasyUseAnima 전용 경로는 별도 계약으로 분리한다.

## 결론

권장 방향은 **NAIA2.0의 기존 ComfyUI 기능에 `EasyUseAnima AiO` 모드를 추가하고, 별도 ComfyUI companion extension으로 필요한 UI를 제공하며, ComfyUI-EasyUseAnima에는 작은 공개 계약 API를 추가하는 방식**이다.

이유:

- NAIA2.0은 이미 `COMFYUI` API 모드, `ComfyUIService`, `ComfyUIWorkflowManager`, ComfyUI 파라미터 패널, `/api/comfyui/random` 원격 API를 갖고 있다.
- EasyUseAnima는 이미 `EasyUseAnimaPromptStudioAdvancedV2`, `EasyUseAnimaInput`, `EasyUseAnimaAIOGenerator`와 `generation_settings` JSON 저장 모델을 갖고 있다.
- 별도 extension은 생성 로직을 복제하지 않고, ComfyUI 안에서 필요한 조작 UI만 제공한다. 예: target node set 선택, overwrite 매핑, LoRA preset 관리, 현재 workflow 상태 표시.
- 다만 EasyUseAnima 내부의 숨은 JSON 구조를 NAIA2.0이 직접 하드코딩하면 깨지기 쉽다. EasyUseAnima 쪽에 스키마/기본값/노드 계약을 반환하는 읽기 전용 API를 추가해야 한다.

따라서 이 저장소(`NAIA2.0-for-ComfyUI`)는 초기 조율/설계 저장소이면서, 이후 ComfyUI companion extension 후보가 된다. 실제 코드는 세 갈래로 나눈다: NAIA2.0의 ComfyUI 전용 도구, EasyUseAnima의 공개 계약 API, `NAIA2.0-for-ComfyUI` companion extension UI.

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

NAIA2.0에서 ComfyUI 모드를 선택한 뒤, `COMFYUI 전용 도구` 항목에서 generation backend를 다음처럼 고를 수 있게 한다.

- `Generic ComfyUI Workflow`
  - 현재 기능 유지.
  - 기존 workflow import/patch 기능을 그대로 사용.
- `EasyUseAnima AiO`
  - NAIA2.0 UI에서 prompt, negative, resolution, seed, sampler, highres, detailer, save options를 설정한다.
  - NAIA2.0은 EasyUseAnima AiO prompt graph를 생성해 ComfyUI `/prompt`에 queue한다.
  - 사용자가 ComfyUI workflow 덮어쓰기를 허용하면, 현재 workflow 안의 필수 EasyUseAnima 노드를 자동 인식하고 NAIA2.0에서 치환할 params를 선택할 수 있게 한다.
  - ComfyUI에는 EasyUseAnima node pack이 설치되어 있어야 한다.
  - EasyUseAnima가 없거나 버전/스키마가 맞지 않으면 구체적인 오류를 보여준다.

## 권장 아키텍처

```text
NAIA2.0
  UI: ComfyUI mode
    - COMFYUI 전용 도구
      - Generic Workflow panel
      - EasyUseAnima AiO control panel
      - overwrite selection panel
  Core
    - ComfyUIService: existing /prompt queue, /history polling
    - EasyUseAnimaAioContractClient: /object_info + /easyuse_anima/aio/schema 조회
    - EasyUseAnimaAioWorkflowInspector: loaded workflow에서 필수 노드 자동 인식
    - EasyUseAnimaAioWorkflowBuilder: prompt graph 생성

ComfyUI
  NAIA2.0-for-ComfyUI companion extension
    - frontend panel / menu / node selection UI
    - overwrite mapping UI
    - LoRA preset management UI
    - calls NAIA2.0 remote API and EasyUseAnima public routes
  ComfyUI-EasyUseAnima
    - existing nodes
    - new read-only contract routes
      GET /easyuse_anima/aio/schema
      GET /easyuse_anima/aio/status
```

## ComfyUI 전용 도구 동작

`EasyUseAnima AiO`는 일반 API 모드가 아니라 NAIA2.0의 ComfyUI 전용 도구 항목으로 추가한다. 이 항목은 기존 ComfyUI mode 위에서 동작하며, 현재 선택된 workflow를 다음 두 경로 중 하나로 처리한다.

### 1. 기존 workflow 기반 제어

사용자가 ComfyUI workflow를 불러온 상태에서 `EasyUseAnima AiO`를 선택하면 NAIA2.0은 workflow를 먼저 검사한다.

필수 노드:

- `EasyUseAnimaPromptStudioAdvancedV2`
- `EasyUseAnimaInput`
- `EasyUseAnimaAIOGenerator`

선택 노드:

- `EasyUseAnimaLoraPreset`
- `EasyUseAnimaWildcard`
- `EasyUseAnimaPromptDataUnpack`

인식 기준:

- `/object_info`로 EasyUseAnima node class가 설치되어 있는지 확인한다.
- loaded workflow prompt graph에서 class id를 찾는다.
- API graph와 UI workflow metadata가 모두 있을 때는 API graph를 우선한다.
- 여러 후보가 있으면 사용자가 target node set을 선택하게 한다.
- 필수 노드가 빠졌거나 연결이 불완전하면 자동 치환을 막고, 누락 노드와 필요한 연결을 표시한다.

### 2. 새 AiO graph 생성

불러온 workflow가 없거나 필수 노드가 없을 때는 NAIA2.0이 최소 AiO API graph를 생성한다.

```text
Prompt Studio Advanced v2 -> Easy Use Anima Input -> Anima AiO Generator
```

이 경로는 "새 graph 생성"으로 표시하고, 기존 workflow overwrite와 구분한다.

## 덮어쓰기 정책

자동 인식은 읽기 전용으로 먼저 수행한다. 실제 workflow 값 변경은 사용자가 `ComfyUI overwrite 허용`을 켠 경우에만 한다.

덮어쓰기 허용 시 NAIA2.0에서 선택 가능한 params:

- prompt source
  - positive prompt
  - negative prompt
  - prompt data field text
  - width / height
- resource selection
  - `unet_name`
  - `vae_name`
  - `clip_name`
  - `clip_type`
- sampler
  - seed
  - seed after generate
  - backend
  - steps
  - cfg
  - sampler
  - scheduler
  - denoise
- stage options
  - highres enable/settings
  - detailer enable/order/basic target settings
  - upscale enable/settings
  - postprocess fit settings
- save options
  - save enable
  - backend
  - filename prefix
  - embed workflow
- optional integrations
  - lora preset selection
  - wildcard seed/mode

덮어쓰기 금지 시:

- NAIA2.0은 필수 노드와 현재 값을 읽고 상태만 보여준다.
- queue에는 원본 workflow 값을 그대로 사용한다.
- NAIA2.0 params UI는 비활성화하거나 preview-only 상태로 표시한다.

부분 덮어쓰기:

- 사용자가 체크한 params만 치환한다.
- 체크하지 않은 params는 loaded workflow 값을 보존한다.
- 치환 전후 diff summary를 queue 직전에 보여준다.
- hidden serialized widget인 `generation_settings`는 schema defaults와 현재 workflow 값을 merge한 뒤, 선택된 필드만 갱신한다.

금지:

- 필수 노드가 인식되지 않았는데 NAIA2.0 params를 임의 graph 위치에 주입하지 않는다.
- class id가 같더라도 연결이 불완전하면 silent fallback하지 않는다.
- schema version mismatch 상태에서 `generation_settings` 내부 필드를 직접 수정하지 않는다.

## Companion Extension UI

`NAIA2.0-for-ComfyUI`는 별도 ComfyUI extension으로 발전시켜, ComfyUI 안에서 필요한 UI를 제공한다. 이 extension은 EasyUseAnima의 node execution을 대체하지 않고, NAIA2.0과 EasyUseAnima 사이의 제어 UI만 맡는다.

주요 역할:

- 현재 workflow에서 EasyUseAnima AiO 필수 노드 자동 탐지 결과를 표시한다.
- 여러 `Prompt Studio Advanced v2` / `Easy Use Anima Input` / `Anima AiO Generator` 후보가 있을 때 target set을 선택한다.
- `ComfyUI overwrite 허용`과 항목별 overwrite checkbox를 제공한다.
- overwrite diff summary를 queue 전에 보여준다.
- LoRA preset을 조회, 선택, 저장, 복구한다.
- `Anima LoRA Preset` node와 `lora_stack` 연결 상태를 표시한다.
- NAIA2.0 remote API 연결 상태와 EasyUseAnima schema/status를 동시에 보여준다.

초기 UI 위치 후보:

- ComfyUI top menu: `NAIA2.0`
- right sidebar/panel: `NAIA AiO Control`
- selected AiO node context menu: `Use with NAIA2.0`

초기 extension 구조 후보:

```text
NAIA2.0-for-ComfyUI/
  __init__.py
  pyproject.toml
  api.py
  web/
    js/
      naia2_comfyui_extension.js
      naia2_aio_panel.js
      naia2_lora_preset_panel.js
```

초기 API 후보:

- `GET /naia2_for_comfyui/status`
- `POST /naia2_for_comfyui/workflow/inspect`
- `POST /naia2_for_comfyui/workflow/overwrite_plan`

원칙:

- extension은 NAIA2.0이 꺼져 있어도 ComfyUI workflow 검사와 EasyUseAnima schema/status 표시는 가능해야 한다.
- NAIA2.0 remote API가 연결되어 있을 때만 prompt/random generation과 NAIA params sync를 활성화한다.
- LoRA preset 파일 쓰기는 EasyUseAnima의 기존 profile API를 우선 사용한다. 별도 파일 포맷을 만들지 않는다.
- EasyUseAnima 내부 Python 함수를 직접 import하지 않는다. 공개 route와 `/object_info`를 사용한다.

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

### 4. NAIA2.0 UI 패널 확장

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
- companion extension connection status

2차 이후:

- Spectrum advanced inputs
- DIT correction options
- Detailer face/eye/custom target tabs
- Upscale
- Postprocess final fit
- Image Saver Civitai hash rows
- LoRA stack/preset integration

NAIA2.0 쪽 UI는 생성 params와 remote API 상태에 집중한다. ComfyUI graph target 선택, overwrite diff, LoRA preset 관리처럼 workflow graph와 강하게 연결된 UI는 companion extension에 둔다.

### 5. 기존 custom workflow 기능 유지

`ComfyUIWorkflowManager`의 기존 generic workflow import/patch는 유지한다.

새 AiO builder는 다음 조건에서만 사용한다.

```python
if api_mode == "COMFYUI" and comfyui_workflow_mode == "easyuse_anima_aio":
    workflow = easyuse_anima_aio_builder.build(params)
else:
    workflow = comfyui_workflow_manager.apply_params_to_workflow(params)
```

## Extension 역할 판단

별도 extension은 필요하다. 단, 역할은 **생성 로직 구현**이 아니라 **ComfyUI 안의 제어 UI와 workflow inspection 보조**로 제한한다.

extension에 둔다:

- ComfyUI 화면 안의 `NAIA AiO Control` 패널
- target AiO node set 선택
- overwrite 허용/부분 overwrite UI
- queue 전 overwrite diff
- LoRA preset 관리 UI
- EasyUseAnima schema/status 표시
- NAIA2.0 remote API 연결 상태 표시

extension에 두지 않는다:

- EasyUseAnima AiO sampling/detailer/save 실행 로직 복제
- EasyUseAnima `generation_settings` schema의 독자 포크
- NAIA2.0 prompt generation pipeline 복제
- EasyUseAnima profile 파일 포맷 재정의

이렇게 나누면 설치 축은 하나 늘어나지만, ComfyUI 내부 사용자가 필요한 조작 UI를 얻고, 실제 생성 계약은 EasyUseAnima와 NAIA2.0의 공개 API에 남는다.

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
- companion extension connection status 표시
- unsupported feature는 비활성화하고 이유 표시

완료 조건:

- `Generic` 모드 UI와 기존 동작이 유지된다.
- `EasyUseAnima AiO` 모드에서 MVP graph 설정을 저장/복원할 수 있다.

### Issue 5: NAIA2.0-for-ComfyUI companion extension MVP

대상 repo:

- `NAIA2.0-for-ComfyUI`

작업:

- ComfyUI extension scaffold 추가
- `NAIA AiO Control` panel 추가
- `/object_info`와 EasyUseAnima schema/status 기반 필수 노드 자동 인식
- target node set 선택 UI
- overwrite 허용/부분 overwrite UI
- queue 전 overwrite diff summary
- NAIA2.0 remote API 연결 상태 표시

완료 조건:

- EasyUseAnima 필수 노드가 있는 workflow에서 target set이 자동 감지된다.
- 여러 후보가 있을 때 사용자가 target set을 선택할 수 있다.
- overwrite off 상태에서는 workflow 값이 변경되지 않는다.
- overwrite on 상태에서 선택한 항목만 overwrite plan에 포함된다.

### Issue 6: Companion extension LoRA preset management

대상 repo:

- `NAIA2.0-for-ComfyUI`
- 필요 시 `n0va39/ComfyUI-EasyUseAnima`

작업:

- EasyUseAnima LoRA profile API 조회/저장 UI
- workflow 안의 `Anima LoRA Preset` node 인식
- preset 선택 시 target node의 serialized profile state 갱신 plan 생성
- missing LoRA fix/recovery UI 연결
- `lora_stack` 연결 상태 표시

완료 조건:

- LoRA preset 변경이 사용자가 허용한 target node에만 적용된다.
- profile save/load가 EasyUseAnima 기존 profile API와 호환된다.
- 없는 LoRA는 기존 EasyUseAnima fix/recovery 흐름을 사용한다.

### Issue 7: Detailer/upscale/save metadata 확장

대상 repo:

- `DNT-LAB/NAIA2.0`
- `NAIA2.0-for-ComfyUI`
- 필요 시 `n0va39/ComfyUI-EasyUseAnima`

작업:

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

### NAIA2.0-for-ComfyUI companion extension

Static:

```powershell
node --check web\js\naia2_comfyui_extension.js
node --check web\js\naia2_aio_panel.js
node --check web\js\naia2_lora_preset_panel.js
D:\ComfyUI\ComfyUI_main\instances\ComfyUI_codex_test\.venv\Scripts\python.exe -m compileall -q .
git diff --check
```

Runtime smoke:

- ComfyUI test instance에 extension 설치
- EasyUseAnima 설치 여부별 status 표시 확인
- workflow에 필수 AiO 노드가 있을 때 target node set 자동 인식 확인
- overwrite off 상태에서 plan이 read-only로 남는지 확인
- overwrite on + 일부 항목 선택 시 선택 항목만 overwrite plan에 포함되는지 확인
- LoRA profile list/load/save가 EasyUseAnima API와 호환되는지 확인

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
3. `NAIA2.0-for-ComfyUI`에서 companion extension MVP scaffold를 만든다.
4. 그 다음 NAIA2.0 Issue 2/3에서 contract client와 MVP workflow builder를 만든다.
5. companion extension에서 LoRA preset 관리 UI를 확장한다.
