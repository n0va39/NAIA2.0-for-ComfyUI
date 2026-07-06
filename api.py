from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

try:
    import server
    from aiohttp import web
except ImportError:
    server = None
    web = None

from .aio_graph import (
    AIO_GENERATOR_CLASS,
    INPUT_CLASS,
    PROMPT_STUDIO_CLASS,
    build_prompt_from_naia_params,
    normalize_naia_params,
)

EXTENSION_NAME = "NAIA2.0-for-ComfyUI"
NAIA_RANDOM_PATH = "/api/comfyui/random"


def _get_prompt_routes():
    if server is None:
        return None
    prompt_server = getattr(getattr(server, "PromptServer", None), "instance", None)
    return getattr(prompt_server, "routes", None)


def _json_error(message: str, status: int = 400):
    return web.json_response({"status": "error", "message": message}, status=status)


def _normalize_url(base_url: str) -> str:
    text = str(base_url or "").strip()
    if not text:
        raise ValueError("naia_url is required")
    parsed = urllib.parse.urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("naia_url must be an absolute http(s) URL")
    return text.rstrip("/")


def _post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload or {}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"NAIA request failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"NAIA request failed: {exc.reason}") from exc
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("NAIA response was not valid JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError("NAIA response must be a JSON object")
    return data


async def _request_naia_random(naia_url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    target = f"{_normalize_url(naia_url)}{NAIA_RANDOM_PATH}"
    return await asyncio.to_thread(_post_json, target, payload, timeout)


def _route_payload(params: dict[str, Any], options: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = normalize_naia_params(params)
    prompt = build_prompt_from_naia_params(normalized, options or {})
    return {
        "status": "ok",
        "extension": EXTENSION_NAME,
        "params": normalized,
        "prompt": prompt,
        "workflow": None,
    }


routes = _get_prompt_routes()

if web is not None and routes is not None:

    @routes.get("/naia2_for_comfyui/status")
    @routes.get("/api/naia2_for_comfyui/status")
    async def status_handler(request):
        return web.json_response({
            "status": "ok",
            "extension": EXTENSION_NAME,
            "mode": "generated_aio_graph_mvp",
            "required_nodes": [
                PROMPT_STUDIO_CLASS,
                INPUT_CLASS,
                AIO_GENERATOR_CLASS,
            ],
        })

    @routes.post("/naia2_for_comfyui/aio/graph")
    @routes.post("/api/naia2_for_comfyui/aio/graph")
    async def aio_graph_handler(request):
        try:
            data = await request.json()
        except Exception:
            return _json_error("Request body must be JSON")
        if not isinstance(data, dict):
            return _json_error("Request body must be a JSON object")
        params = data.get("params") or {}
        options = data.get("options") or {}
        if not isinstance(params, dict):
            return _json_error("params must be a JSON object")
        if not isinstance(options, dict):
            return _json_error("options must be a JSON object")
        payload = _route_payload(params, options)
        payload["source"] = "request_params"
        return web.json_response(payload)

    @routes.post("/naia2_for_comfyui/aio/from_naia")
    @routes.post("/api/naia2_for_comfyui/aio/from_naia")
    async def aio_from_naia_handler(request):
        try:
            data = await request.json()
        except Exception:
            return _json_error("Request body must be JSON")
        if not isinstance(data, dict):
            return _json_error("Request body must be a JSON object")
        naia_url = data.get("naia_url") or data.get("url")
        request_body = data.get("request") or {}
        options = data.get("options") or {}
        timeout = float(data.get("timeout") or 20.0)
        if not isinstance(request_body, dict):
            return _json_error("request must be a JSON object")
        if not isinstance(options, dict):
            return _json_error("options must be a JSON object")
        try:
            naia_params = await _request_naia_random(str(naia_url or ""), request_body, timeout)
            payload = _route_payload(naia_params, options)
        except ValueError as exc:
            return _json_error(str(exc))
        except RuntimeError as exc:
            return _json_error(str(exc), status=502)
        payload["source"] = "naia"
        payload["naia_url"] = _normalize_url(str(naia_url or ""))
        return web.json_response(payload)
