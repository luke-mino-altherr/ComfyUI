# Realtime Webcam Processing MVP

This example demonstrates real-time webcam frame processing through ComfyUI workflows.

## Setup

1. Start ComfyUI:
   ```bash
   python main.py
   ```

2. Open ComfyUI in your browser (usually http://localhost:8188)

## Loading the Workflow

1. Load the workflow file: `realtime_webcam_upscale.json`
   - Drag and drop the file onto the ComfyUI canvas, OR
   - Use "Load" button and select the file

## Workflow Overview

The workflow contains:
- **Realtime Load Image**: Receives streaming webcam frames via WebSocket
- **Image Scale**: Upscales the 512x512 input to 1024x1024 using Lanczos
- **Preview Image**: Shows the processed result
- **Realtime Wait**: Keeps the workflow running indefinitely

## Using the Webcam

1. After loading the workflow, you'll see a "Realtime Load Image" node with a webcam preview widget

2. Queue the workflow (press Q or click "Queue Prompt")

3. Enable realtime mode by sending via WebSocket:
   ```json
   {
     "type": "realtime_enable",
     "data": { "prompt_id": "<your-prompt-id>" }
   }
   ```

4. Click **"Start Webcam"** button in the RealtimeLoadImage node

5. Grant camera permission when prompted

6. You should see:
   - Live webcam preview in the node
   - Processed/upscaled images appearing in the Preview Image node

7. Click **"Stop Webcam"** to stop streaming

## Expected Behavior

- Webcam frames are captured at ~30fps
- Frames are sent to the server via WebSocket binary messages
- Server processes each frame through the workflow
- Upscaled images appear in the preview

## Troubleshooting

### No webcam access
- Make sure you're using HTTPS or localhost
- Check browser permissions
- Try a different browser

### No output appearing
- Ensure the workflow is queued and running
- Check browser console for errors
- Verify WebSocket connection is active

### Low framerate
- This is expected for MVP - full optimization comes later
- GPU processing may introduce latency

## Technical Details

- Input resolution: 512x512 (configurable in node settings)
- Output resolution: 1024x1024 (2x upscale)
- Frame format: JPEG at 85% quality
- Target framerate: 30fps (may be lower depending on processing)
