# NAIA2.0 x ComfyUI-EasyUseAnima AiO Integration Plan

작성일: 2026-07-06

## 목적

NAIA2.0 Portable의 `COMFYUI` 모드에서 `ComfyUI-EasyUseAnima`의 `Anima AiO Generator`를 워크플로우 파일 지정 없이 직접 실행한다.

초기 MVP는 NAIA2.0이 이미 보유한 생성 파라미터와 확장 패널 설정만 사용해 EasyUseAnima AiO용 최소 ComfyUI API graph를 생성한다.

## 정정된 결론

설치 대상은 ComfyUI custom node가 아니라 **NAIA2.0 Portable extension**이다.

확장 설치 경로:

```text
D:\ComfyUI\NAIA-Portables\NAIA-Portable\user-data\extensions
```

이 저장소는 다음 형태의 단일 NAIA extension 패키지로 둔다.

```text
NAIA2.0-for-ComfyUI/
  extension.json
  main.py
  naia2_for_comfyui/
    __init__.py
    aio_graph.py
  tests/
```

ComfyUI 쪽 요구사항은 다음으로 제한한다.

- `ComfyUI-EasyUseAnima`가 설치되어 있어야 한다.
- ComfyUI에 `EasyUseAnimaPromptStudioAdvancedV2`, `EasyUseAnimaInput`, `EasyUseAnimaAIOGenerator`가 등록되어 있어야 한다.
- 이 MVP를 위해 ComfyUI에 `NAIA2.0-for-ComfyUI`를 설치하지 않는다.

## 확인한 NAIA Portable Extension 계약

확인 경로:

```text
D:\ComfyUI\NAIA-Portables\NAIA-Portable\resources\naia-backend
```

확인한 파일:

- `core/extension_runtime.py`
- `core/extension_install_service.py`
- `release_assets/samples/extensions/seed_fanout/extension.json`
- `release_assets/samples/extensions/seed_fanout/main.py`
- `app/web/remote/js/features/extensionsPanel.mjs`

NAIA Portable extension layout:

```text
user-data/extensions/<extension-id>/
  extension.json
  main.py
  settings.json     optional, ctx.load_settings()/save_settings()
```

`extension.json` 최소 계약:

```json
{
  "id": "naia2_easyuse_anima_aio",
  "name": "EasyUse Anima AiO",
  "version": "0.1.0",
  "naia_ext_api": 1,
  "entry": "main.py"
}
```

`main.py`는 `def register(ctx): ...`를 export한다.

이번 MVP에서 쓰는 공식 `ExtensionContext` 표면:

- `ctx.register_panel(fields, title=..., on_action=...)`
- `ctx.subscribe("generation_request_dispatched", callback)`
- `ctx.get_current_request()`
- `ctx.enqueue_generation(...)`
- `ctx.cancel_generation(request_id)`
- `ctx.load_settings(defaults)`
- `ctx.show_toast(message, level)`

내부 NAIA 모듈 import나 런타임 monkey patch는 사용하지 않는다.

## 현재 MVP 동작

### 1. Extension 패널

Settings -> Extension 승인 후 퀵 도구에 `EasyUse Anima AiO`가 표시된다.

패널 설정:

- `Use AiO workflow`
- `Override normal Generate`
- `Overwrite loaded workflow`
- `Generate AiO now`
- `UNET`
- `VAE`
- `CLIP`
- `CLIP type`

### 2. 일반 Generate override

`Override normal Generate`가 켜져 있고 현재 API 모드가 `COMFYUI`이면:

```text
NAIA normal Generate dispatch
  -> generation_request_dispatched event
  -> extension checks COMFYUI + enabled + no ext recursion
  -> if loaded custom workflow exists, require Overwrite loaded workflow
  -> cancel original queued request
  -> enqueue derived request with generated AiO API graph in params["workflow"]
  -> NAIA APIService sends that graph directly to ComfyUI /prompt
  -> NAIA reads the final image from the generated PreviewImage node in ComfyUI history
```

핵심은 `params["workflow"]`를 직접 넣는 것이다. NAIA core의 `APIService._call_comfyui_api()`는 `workflow` dict가 있으면 `ComfyUIWorkflowManager.apply_params_to_workflow()`를 우회하고 해당 graph를 그대로 전송한다.

이 방식의 장점:

- NAIA core patch가 필요 없다.
- 기존 generic/custom workflow 기능을 건드리지 않는다.
- `Overwrite loaded workflow`가 꺼져 있으면 기존 custom workflow를 보존한다.
- ComfyUI/AiO 내부 저장 경로를 건드리지 않고, 결과 저장은 NAIA의 기존 저장 설정과 경로를 사용한다.

### 3. 수동 action

`Generate AiO now`는 현재 prompt/params snapshot을 읽고 AiO graph 요청 1건을 큐에 넣는다. 이 경로는 normal Generate 버튼을 누르지 않고도 smoke test를 수행할 수 있게 한다.

## AiO 최소 Graph 계약

MVP graph는 필수 3노드만 사용한다.

```text
EasyUseAnimaPromptStudioAdvancedV2
  -> EasyUseAnimaInput
  -> EasyUseAnimaAIOGenerator
  -> PreviewImage
```

노드:

| Node id | Class id | 역할 |
| --- | --- | --- |
| `1` | `EasyUseAnimaPromptStudioAdvancedV2` | NAIA prompt/negative/resolution을 prompt data로 변환 |
| `2` | `EasyUseAnimaInput` | UNET/VAE/CLIP 리소스와 prompt data를 AiO input context로 묶음 |
| `3` | `EasyUseAnimaAIOGenerator` | txt2img sampling 실행 |
| `4` | `PreviewImage` | NAIA 결과 조회용 표준 ComfyUI image output |

필수 링크:

```text
1[0] -> 2[0]  EASYUSE_ANIMA_PROMPT_DATA
2[0] -> 3[0]  EASY_USE_ANIMA_INPUT
3[0] -> 4[0]  IMAGE
```

MVP에서 사용하는 NAIA params:

- `input` 또는 `prompt`
- `negative_prompt`
- `width`
- `height`
- `seed`
- `steps`
- `cfg_scale` 또는 `cfg`
- `sampler`
- `scheduler`
- `denoise`
- `model` 또는 `unet_name`
- `vae_name`
- `clip_name`
- `clip_type`

MVP 기본 정책:

- `sampler.backend = "comfy_ksampler"`
- Spectrum/DIT corrections disabled
- KJ SageAttention/Torch Compile disabled
- Highres/Detailer/Upscale/Postprocess disabled
- AiO 내부 save disabled
- NAIA 결과 조회는 `PreviewImage` node id `4`를 preferred output으로 사용
- 결과 저장 경로는 NAIA의 result/save pipeline 설정을 따른다.
- 메타데이터는 확장이 생성한 API graph를 `params["workflow"]`로 넘기고, NAIA result/save pipeline이 `workflow_api` 기반 PNG 메타데이터로 보강한다.
- LoRA preset/lora_stack은 MVP 제외

## 현재 제한

- 입력창에 남아 있는 ComfyUI 실행 직전 wildcard 확장은 graph 생성 이후에 일어날 수 있다. MVP는 dispatch 시점의 prompt snapshot을 사용한다.
- LoRA preset node, Spectrum, Highres, Detailer, Upscale UI는 아직 노출하지 않는다.
- ComfyUI `/object_info`에서 EasyUseAnima 필수 노드 존재 여부를 자동 검증하는 기능은 아직 없다.
- EasyUseAnima의 `generation_settings` schema/status API가 없으므로 hidden JSON은 이 저장소의 builder가 보수적으로 생성한다.

## 후속 단계

### Issue 1: Portable extension MVP

대상 repo:

- `NAIA2.0-for-ComfyUI`

작업:

- `extension.json` + `main.py` 기반 NAIA Portable extension 구조 확정
- `naia2_for_comfyui/aio_graph.py` 추가
- NAIA params 기반 최소 AiO API graph 생성
- normal Generate override와 manual action 구현
- 단위 테스트 추가
- 로컬 `user-data/extensions/naia2_easyuse_anima_aio` 설치 확인

완료 조건:

- Settings -> Extension에서 확장이 발견된다.
- 승인 후 `EasyUse Anima AiO` 도구가 표시된다.
- `Generate AiO now` 또는 normal Generate override가 `workflow` dict를 포함한 COMFYUI 요청을 큐에 넣는다.

### Issue 2: 실제 생성 smoke

대상:

- NAIA Portable
- EasyUseAnima가 설치된 ComfyUI instance

작업:

- NAIA Portable에서 extension 승인
- COMFYUI credential 확인
- `Generate AiO now`로 1장 생성
- ComfyUI history에 `EasyUseAnimaAIOGenerator` 실행 기록 확인

완료 조건:

- ComfyUI `/prompt` queue가 성공한다.
- NAIA 결과 패널에 generated AiO image가 표시된다.
- NAIA가 저장한 결과 PNG metadata에 generated AiO API workflow가 남는다.

### Issue 3: Advanced UI

작업:

- `/object_info` 기반 필수 노드 감지
- EasyUseAnima node/schema 상태 표시
- LoRA preset 관리
- Spectrum/DIT/model patch 설정
- Highres/Detailer/Upcale/Postprocess 설정
- overwrite diff summary

### Issue 4: Upstream PR 후보

MVP가 안정화된 뒤 NAIA2.0 upstream에는 다음만 부분 PR로 제안한다.

- extension API에서 ComfyUI option/object info 조회 helper
- custom workflow overwrite 상태를 extension에서 더 명확히 읽는 public helper
- ComfyUI direct workflow enqueue 관련 문서화

EasyUseAnima upstream에는 다음을 제안한다.

- `GET /easyuse_anima/aio/schema`
- `GET /easyuse_anima/aio/status`
- `generation_settings` schema/default export
- LoRA preset profile export/import helper
