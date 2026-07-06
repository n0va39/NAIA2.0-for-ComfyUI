# NAIA2.0 x ComfyUI-EasyUseAnima AiO Integration Plan

작성일: 2026-07-06

## 목적

NAIA2.0의 `COMFYUI` 모드에서 `ComfyUI-EasyUseAnima`의 `Anima AiO Generator`를 워크플로우 파일 지정 없이 직접 실행할 수 있게 한다.

초기 MVP는 NAIA2.0에서 이미 수집하는 생성 파라미터만 사용해 EasyUseAnima AiO용 최소 ComfyUI API graph를 생성한다.

## 정정된 결론

설치 대상은 ComfyUI custom node가 아니라 **NAIA2.0 extension**이다.

`NAIA2.0-for-ComfyUI`는 ComfyUI companion extension이 아니라, NAIA2.0에 배치하는 확장 모듈과 helper package를 제공하는 저장소로 둔다.

ComfyUI 쪽 요구사항은 다음으로 제한한다.

- `ComfyUI-EasyUseAnima`가 설치되어 있어야 한다.
- ComfyUI에 `EasyUseAnimaPromptStudioAdvancedV2`, `EasyUseAnimaInput`, `EasyUseAnimaAIOGenerator`가 등록되어 있어야 한다.
- 이 MVP를 위해 ComfyUI에 `NAIA2.0-for-ComfyUI`를 설치하지 않는다.

나중에 필요한 경우에만 별도 ComfyUI companion UI를 추가한다. 그 UI는 current workflow overwrite, LoRA preset 관리, Spectrum/Detailer 같은 고급 node-local 설정 보조에 한정한다.

## 확인한 NAIA2.0 Extension 계약

참조 기준:

- Repository: `DNT-LAB/NAIA2.0`
- 확인 커밋: `1549b3b`
- 확인 경로: `D:\ComfyUI\custom_nodes_workplace\.tmp\naia2-ref-current`

확인한 문서/코드:

- `CLAUDE.md`
- `interfaces/CLAUDE.md`
- `modules/CLAUDE.md`
- `interfaces/base_module.py`
- `interfaces/mode_aware_module.py`
- `core/middle_section_controller.py`
- `core/generation_controller.py`
- `core/comfyui_workflow_manager.py`
- `ui/interactive/comfyui_parameter_panel.py`

NAIA2.0의 확장 방식:

- `modules/*_module.py`가 자동 스캔된다.
- `BaseMiddleModule` 상속 클래스가 좌측 Middle Section 모듈로 로드된다.
- `get_parameters()` 반환값이 생성 파라미터에 병합된다.
- `ModeAwareModule`을 함께 쓰면 `NAI`, `WEBUI`, `COMFYUI` 모드별 표시/설정 저장을 제어할 수 있다.
- `COMFYUI_compatibility = True`, `NAI_compatibility = False`, `WEBUI_compatibility = False`로 COMFYUI 전용 도구를 만들 수 있다.

COMFYUI 생성 흐름:

```text
MainWindow / GenerationController
  -> main params 수집
  -> modules[*].get_parameters() 병합
  -> COMFYUI 모드면 wildcard 확장
  -> ComfyUIWorkflowManager.apply_params_to_workflow(params)
  -> params["workflow"] 설정
  -> APIService._call_comfyui_api(params)
  -> ComfyUIService.generate_image(workflow)
  -> ComfyUI /prompt
```

따라서 AiO MVP가 붙을 위치는 `modules/*_module.py`와 `ComfyUIWorkflowManager.apply_params_to_workflow()` 확장 지점이다.

## 현재 MVP 구조

이 저장소의 현재 구현 대상:

```text
NAIA2.0-for-ComfyUI/
  modules/
    easyuse_anima_aio_module.py
  naia2_for_comfyui/
    __init__.py
    aio_graph.py
  tests/
    test_aio_graph.py
    test_naia_extension_contract.py
```

설치 방식:

```text
<NAIA2.0 root>/
  modules/easyuse_anima_aio_module.py
  naia2_for_comfyui/__init__.py
  naia2_for_comfyui/aio_graph.py
```

`modules/easyuse_anima_aio_module.py` 역할:

- NAIA2.0 Middle Section에 `EasyUse Anima AiO` 모듈을 추가한다.
- COMFYUI 모드에서만 표시된다.
- 사용자가 `Use generated EasyUse Anima AiO graph`를 켜면 `workflow_type = "easyuse_anima_aio"`를 반환한다.
- UNET, VAE, CLIP, CLIP type, save 여부, filename prefix를 NAIA params에 추가한다.
- 초기 MVP에서는 `ComfyUIWorkflowManager.apply_params_to_workflow()`를 런타임 patch해서 `workflow_type == "easyuse_anima_aio"`일 때 generated AiO graph builder를 호출한다.

`naia2_for_comfyui/aio_graph.py` 역할:

- NAIA2.0 params를 EasyUseAnima AiO ComfyUI API graph로 변환한다.
- ComfyUI나 EasyUseAnima Python 내부를 import하지 않는다.
- `/prompt`에 전달 가능한 API prompt graph만 만든다.

## AiO 최소 Graph 계약

MVP graph는 필수 3노드만 사용한다.

```text
EasyUseAnimaPromptStudioAdvancedV2
  -> EasyUseAnimaInput
  -> EasyUseAnimaAIOGenerator
```

노드:

| Node id | Class id | 역할 |
| --- | --- | --- |
| `1` | `EasyUseAnimaPromptStudioAdvancedV2` | NAIA prompt/negative/resolution을 prompt data로 변환 |
| `2` | `EasyUseAnimaInput` | UNET/VAE/CLIP 리소스와 prompt data를 AiO input context로 묶음 |
| `3` | `EasyUseAnimaAIOGenerator` | txt2img sampling/save 실행 |

필수 링크:

```text
1[0] -> 2[0]  EASYUSE_ANIMA_PROMPT_DATA
2[0] -> 3[0]  EASY_USE_ANIMA_INPUT
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
- `save_enabled`
- `filename_prefix`

MVP 기본 정책:

- `sampler.backend = "comfy_ksampler"`
- Spectrum/DIT corrections disabled
- KJ SageAttention/Torch Compile disabled
- Highres/Detailer/Upscale/Postprocess disabled
- Save backend은 `comfy_save_image`
- LoRA preset/lora_stack은 MVP 제외

## 기존 Generic ComfyUI 기능과의 관계

기존 `Generic ComfyUI Workflow` 기능은 유지한다.

분기 기준:

```python
if params.get("workflow_type") == "easyuse_anima_aio":
    workflow = build_prompt_from_naia_params(params)
else:
    workflow = existing_apply_params_to_workflow(params)
```

이 분기는 현재 확장 모듈의 런타임 patch로 구현한다. 이후 NAIA2.0 upstream PR에서는 patch가 아니라 `ComfyUIWorkflowManager` 내부의 명시적 builder 분기로 옮기는 것이 맞다.

## Current Workflow Overwrite는 후순위

MVP는 current workflow overwrite를 하지 않는다.

이유:

- 실제 생성 가능 여부를 먼저 검증해야 한다.
- EasyUseAnima의 `generation_settings` schema/status API가 아직 없다.
- existing workflow patch는 hidden serialized JSON과 optional node pack 상태를 다뤄야 하므로 blast radius가 크다.

후속 단계에서만 다음을 추가한다.

- loaded workflow에서 필수 AiO node set 자동 인식
- overwrite 허용/부분 overwrite
- overwrite diff summary
- `generation_settings` schema-aware merge
- LoRA preset node/profile/lora_stack 관리
- Spectrum/DIT/model patch/Detailer/Highres 고급 설정 UI

## EasyUseAnima 쪽 후속 제안

MVP는 EasyUseAnima 변경 없이 동작해야 한다.

다만 안정화를 위해 후속 PR에서 읽기 전용 contract API를 추가하는 것이 좋다.

후보 endpoint:

- `GET /easyuse_anima/aio/schema`
- `GET /easyuse_anima/aio/status`

반환해야 할 정보:

- schema name/version
- node class ids
- socket type ids
- normalized `generation_settings` defaults
- optional node pack capability 상태
- txt2img/img2img 지원 여부

## 이슈/PR 분할안

### Issue 1: NAIA2.0 extension MVP

대상 repo:

- `NAIA2.0-for-ComfyUI`

작업:

- NAIA2.0 extension module 구조 추가
- `modules/easyuse_anima_aio_module.py` 추가
- `naia2_for_comfyui/aio_graph.py` 추가
- NAIA params 기반 최소 AiO API graph 생성
- 단위 테스트 추가

완료 조건:

- ComfyUI custom node가 아니라 NAIA2.0 `modules/` 확장으로 설치 가능하다.
- `workflow_type = "easyuse_anima_aio"`에서 generated AiO graph를 만든다.
- 기존 generic ComfyUI workflow 경로는 유지된다.

### Issue 2: NAIA2.0 local install and generation smoke

대상 repo:

- `NAIA2.0-for-ComfyUI`
- 로컬 `DNT-LAB/NAIA2.0` checkout

작업:

- 확장 파일을 NAIA2.0 root에 복사 또는 설치
- NAIA2.0 실행 후 COMFYUI 모드에서 모듈 표시 확인
- EasyUseAnima가 설치된 ComfyUI test instance에 `/prompt` queue
- 1장 생성 smoke

완료 조건:

- NAIA2.0 UI에서 `EasyUse Anima AiO` 모듈을 켤 수 있다.
- workflow 파일 지정 없이 실제 ComfyUI queue가 성공한다.
- ComfyUI history에 `EasyUseAnimaAIOGenerator` 실행 기록이 남는다.

### Issue 3: NAIA2.0 upstream native builder PR

대상 repo:

- `DNT-LAB/NAIA2.0`

작업:

- 런타임 patch를 제거하고 `ComfyUIWorkflowManager`에 명시적 AiO builder 분기 추가
- `comfyui_workflow_mode = "easyuse_anima_aio"` 또는 equivalent setting 추가
- 기본 UI/설정 저장 통합
- regression test 추가

완료 조건:

- extension 없이도 NAIA2.0 본체가 AiO builder를 이해한다.
- 기존 generic workflow tests가 유지된다.

### Issue 4: EasyUseAnima AiO external contract API

대상 repo:

- `n0va39/ComfyUI-EasyUseAnima`

작업:

- `/easyuse_anima/aio/schema`
- `/easyuse_anima/aio/status`
- contract 문서와 regression test

완료 조건:

- NAIA2.0이 내부 JSON 구조를 복사하지 않고 schema/defaults를 조회할 수 있다.

### Issue 5: Current workflow inspection and overwrite

대상 repo:

- `NAIA2.0-for-ComfyUI`
- 이후 `DNT-LAB/NAIA2.0`

작업:

- 현재 workflow에서 필수 AiO node set 인식
- overwrite 허용/부분 선택
- queue 전 diff summary
- hidden `generation_settings` merge

완료 조건:

- generated graph가 기본 경로로 유지된다.
- current workflow overwrite는 사용자가 명시적으로 켠 경우에만 적용된다.

### Issue 6: Advanced AiO controls and LoRA preset management

대상 repo:

- `NAIA2.0-for-ComfyUI`
- 필요 시 `ComfyUI-EasyUseAnima`

작업:

- Spectrum/DIT/model patch/Highres/Detailer/Upscale/Postprocess UI
- Anima LoRA Preset profile 조회/선택/저장
- `lora_stack` 연결 상태 반영

완료 조건:

- NAIA2.0 기본 UI에 없는 AiO 고급 설정을 extension에서 관리할 수 있다.

## 검증 계획

현재 저장소 static/unit:

```powershell
D:\ComfyUI\ComfyUI_main\instances\ComfyUI_codex_test\.venv\Scripts\python.exe -m unittest discover -s tests
D:\ComfyUI\ComfyUI_main\instances\ComfyUI_codex_test\.venv\Scripts\python.exe -m compileall -q .
git diff --check
```

NAIA2.0 install smoke:

```powershell
Copy-Item modules\easyuse_anima_aio_module.py <NAIA2.0>\modules\easyuse_anima_aio_module.py
Copy-Item -Recurse naia2_for_comfyui <NAIA2.0>\naia2_for_comfyui
cd <NAIA2.0>
python NAIA_cold_v4.py
```

Runtime smoke:

- NAIA2.0 `COMFYUI` 모드 선택
- `EasyUse Anima AiO` 모듈 활성화
- ComfyUI URL은 EasyUseAnima가 설치된 test instance로 지정
- workflow 파일 지정 없이 생성 실행
- ComfyUI `/history/{prompt_id}`에서 `EasyUseAnimaAIOGenerator` 실행 확인

## 현재 미확인 항목

- 실제 NAIA2.0 UI 실행 smoke는 아직 수행하지 않았다.
- 실제 ComfyUI 이미지 생성 smoke는 아직 수행하지 않았다.
- EasyUseAnima schema/status API는 아직 없다.
- 현재 런타임 patch 방식은 MVP용이다. upstream PR에서는 native builder 분기로 교체해야 한다.

## 다음 작업

1. 현재 PR을 `NAIA2.0 extension MVP`로 명확히 정리한다.
2. NAIA2.0 로컬 checkout에 확장 파일을 설치해 UI 로딩을 확인한다.
3. EasyUseAnima가 설치된 ComfyUI test instance에서 실제 1장 생성 smoke를 수행한다.
4. smoke가 성공하면 NAIA2.0 upstream PR용 native builder 설계를 분리한다.
