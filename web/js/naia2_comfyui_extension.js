import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const STORAGE_KEY = "naia2_for_comfyui.naia_url";
const DEFAULT_NAIA_URL = "http://127.0.0.1:5000";

function readNaiaUrl() {
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_NAIA_URL;
}

function writeNaiaUrl(value) {
  localStorage.setItem(STORAGE_KEY, value);
}

async function postJson(path, body) {
  const response = await api.fetchApi(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    throw new Error(data?.message || response.statusText || `HTTP ${response.status}`);
  }
  return data;
}

async function queuePromptGraph(prompt, workflow = null) {
  if (!api?.queuePrompt) {
    throw new Error("ComfyUI queuePrompt API is not available.");
  }
  return api.queuePrompt(0, { output: prompt, workflow });
}

async function queueFromNaia() {
  const currentUrl = readNaiaUrl();
  const naiaUrl = window.prompt("NAIA2.0 URL", currentUrl);
  if (!naiaUrl) {
    return null;
  }
  writeNaiaUrl(naiaUrl);
  const data = await postJson("/naia2_for_comfyui/aio/from_naia", {
    naia_url: naiaUrl,
    request: {},
    options: {},
  });
  const result = await queuePromptGraph(data.prompt, data.workflow ?? null);
  const promptId = result?.prompt_id ? `\nPrompt ID: ${result.prompt_id}` : "";
  window.alert(`Queued NAIA AiO graph.${promptId}`);
  return result;
}

async function queueFromParams(params = {}, options = {}) {
  const data = await postJson("/naia2_for_comfyui/aio/graph", { params, options });
  return queuePromptGraph(data.prompt, data.workflow ?? null);
}

function installButton() {
  if (document.getElementById("naia2-for-comfyui-aio-button")) {
    return;
  }
  const button = document.createElement("button");
  button.id = "naia2-for-comfyui-aio-button";
  button.type = "button";
  button.textContent = "NAIA AiO";
  button.title = "Queue an EasyUse Anima AiO graph from NAIA2.0 params";
  Object.assign(button.style, {
    position: "fixed",
    right: "12px",
    bottom: "12px",
    zIndex: "10000",
    padding: "8px 10px",
    borderRadius: "6px",
    border: "1px solid rgba(255,255,255,0.25)",
    background: "rgba(30,35,42,0.94)",
    color: "#f3f6f8",
    fontSize: "12px",
    lineHeight: "16px",
    cursor: "pointer",
    boxShadow: "0 2px 8px rgba(0,0,0,0.25)",
  });
  button.addEventListener("click", async () => {
    button.disabled = true;
    const originalText = button.textContent;
    button.textContent = "Queueing";
    try {
      await queueFromNaia();
    } catch (error) {
      console.error("[NAIA2.0-for-ComfyUI] queue failed", error);
      window.alert(error?.message || String(error));
    } finally {
      button.disabled = false;
      button.textContent = originalText;
    }
  });
  document.body.appendChild(button);
}

app.registerExtension({
  name: "naia2-for-comfyui.generated-aio-mvp",
  setup() {
    window.naia2ForComfyUI = {
      queueFromNaia,
      queueFromParams,
      readNaiaUrl,
      writeNaiaUrl,
    };
    installButton();
  },
});
