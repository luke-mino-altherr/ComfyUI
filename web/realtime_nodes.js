import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

let frameNumber = 0;
let currentPromptId = null;

let realtimeEnabled = false;

api.addEventListener("execution_start", (event) => {
  currentPromptId = event.detail.prompt_id;
  realtimeEnabled = false;  // Reset on new execution
  console.log("[Realtime] Execution started, prompt_id:", currentPromptId);
});

// Listen for individual node execution - the "executed" event fires per node
api.addEventListener("executed", (event) => {
  console.log("[Realtime] Node executed:", event.detail);
});

// Listen for when the whole prompt finishes
api.addEventListener("execution_cached", (event) => {
  console.log("[Realtime] Execution cached:", event.detail);
  maybeEnableRealtime(event.detail.prompt_id);
});

api.addEventListener("status", (event) => {
  // When queue becomes empty after our prompt, enable realtime (only once)
  if (!realtimeEnabled && currentPromptId && event.detail?.exec_info?.queue_remaining === 0) {
    console.log("[Realtime] Queue empty, enabling realtime mode");
    maybeEnableRealtime(currentPromptId);
  }
});

function maybeEnableRealtime(promptId) {
  if (!realtimeEnabled && api.socket && api.socket.readyState === WebSocket.OPEN && promptId === currentPromptId) {
    api.socket.send(JSON.stringify({
      type: "realtime_enable",
      data: { prompt_id: promptId }
    }));
    console.log("[Realtime] Sent realtime_enable for prompt:", promptId);
    realtimeEnabled = true;
  }
}

app.registerExtension({
  name: "Comfy.RealtimeNodes",

  async nodeCreated(node) {
    if (node.comfyClass === "RealtimeLoadImage") {
      const webcamWidget = node.addDOMWidget(
        "webcam",
        "webcam_preview",
        document.createElement("div")
      );

      const container = webcamWidget.element;
      container.style.width = "100%";
      container.style.minHeight = "200px";

      const video = document.createElement("video");
      video.style.width = "100%";
      video.autoplay = true;
      video.muted = true;
      video.playsInline = true;
      container.appendChild(video);

      const statusDiv = document.createElement("div");
      statusDiv.style.fontSize = "12px";
      statusDiv.style.color = "#888";
      statusDiv.style.marginTop = "5px";
      statusDiv.textContent = "Webcam not started";
      container.appendChild(statusDiv);

      const controlBtn = document.createElement("button");
      controlBtn.textContent = "Start Webcam";
      controlBtn.style.width = "100%";
      controlBtn.style.marginTop = "5px";
      controlBtn.style.padding = "8px";
      controlBtn.style.cursor = "pointer";
      container.appendChild(controlBtn);

      let stream = null;
      let isStreaming = false;
      let intervalId = null;
      let framesSent = 0;

      controlBtn.onclick = async () => {
        if (!isStreaming) {
          try {
            stream = await navigator.mediaDevices.getUserMedia({
              video: { width: 512, height: 512 }
            });
            video.srcObject = stream;

            intervalId = setInterval(() => {
              captureAndSendFrame(video, node, (sent) => {
                if (sent) {
                  framesSent++;
                  statusDiv.textContent = `Frames sent: ${framesSent} | Prompt: ${currentPromptId ? currentPromptId.substring(0, 8) + '...' : 'none'}`;
                } else {
                  statusDiv.textContent = `Waiting for prompt... (Queue workflow first)`;
                }
              });
            }, 1000 / 30);

            controlBtn.textContent = "Stop Webcam";
            isStreaming = true;
            statusDiv.textContent = "Webcam started, waiting for prompt...";
          } catch (err) {
            console.error("Error accessing webcam:", err);
            alert("Could not access webcam: " + err.message);
          }
        } else {
          if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
          }
          if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
          }
          video.srcObject = null;
          controlBtn.textContent = "Start Webcam";
          isStreaming = false;
          statusDiv.textContent = "Webcam stopped";
          framesSent = 0;
        }
      };

      node.onRemoved = () => {
        if (stream) {
          stream.getTracks().forEach(track => track.stop());
        }
        if (intervalId) {
          clearInterval(intervalId);
        }
      };
    }
  }
});

async function captureAndSendFrame(video, node, callback) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, 512, 512);

  canvas.toBlob(async (blob) => {
    if (!blob) {
      callback(false);
      return;
    }

    if (!currentPromptId) {
      callback(false);
      return;
    }

    const arrayBuffer = await blob.arrayBuffer();
    const binaryFrame = encodeBinaryFrame({
      prompt_id: currentPromptId,
      node_id: node.id.toString(),
      frame_number: frameNumber++,
      timestamp: Date.now(),
      width: 512,
      height: 512,
      channels: 3,
      format: 1,
      data: new Uint8Array(arrayBuffer)
    });

    if (api.socket && api.socket.readyState === WebSocket.OPEN) {
      api.socket.send(binaryFrame);
      callback(true);
    } else {
      console.warn("[Realtime] WebSocket not open");
      callback(false);
    }
  }, "image/jpeg", 0.85);
}

function encodeBinaryFrame(frameData) {
  const encoder = new TextEncoder();
  const nodeIdBytes = encoder.encode(frameData.node_id);
  const promptIdBytes = uuidToBytes(frameData.prompt_id);

  const totalSize = 4 + 16 + 4 + nodeIdBytes.length + 4 + 8 + 4 + 4 + 1 + 1 + 4 + frameData.data.length;
  const buffer = new ArrayBuffer(totalSize);
  const view = new DataView(buffer);

  let offset = 0;

  view.setUint32(offset, 5);
  offset += 4;

  new Uint8Array(buffer, offset, 16).set(promptIdBytes);
  offset += 16;

  view.setUint32(offset, nodeIdBytes.length);
  offset += 4;
  new Uint8Array(buffer, offset, nodeIdBytes.length).set(nodeIdBytes);
  offset += nodeIdBytes.length;

  view.setUint32(offset, frameData.frame_number);
  offset += 4;
  view.setFloat64(offset, frameData.timestamp);
  offset += 8;
  view.setUint32(offset, frameData.width);
  offset += 4;
  view.setUint32(offset, frameData.height);
  offset += 4;
  view.setUint8(offset, frameData.channels);
  offset += 1;
  view.setUint8(offset, frameData.format);
  offset += 1;
  view.setUint32(offset, frameData.data.length);
  offset += 4;

  new Uint8Array(buffer, offset).set(frameData.data);

  return buffer;
}

function uuidToBytes(uuid) {
  const hex = uuid.replace(/-/g, '');
  const bytes = new Uint8Array(16);
  for (let i = 0; i < 16; i++) {
    bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return bytes;
}
