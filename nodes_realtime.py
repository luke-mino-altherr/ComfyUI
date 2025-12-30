"""
Realtime nodes for streaming input to ComfyUI workflows.
"""

import logging
import torch

WEB_DIRECTORY = "./web"


class RealtimeLoadImage:
    """
    Loads streaming image frames from WebSocket for realtime processing.
    
    This node maintains a frame buffer that gets updated via WebSocket
    binary messages. When executed, it returns the latest available frame.
    """

    is_realtime_node = True

    def __init__(self):
        self.current_frame = None
        self.current_mask = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 512, "min": 64, "max": 4096, "step": 64}),
                "height": ("INT", {"default": 512, "min": 64, "max": 4096, "step": 64}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "get_current_frame"
    CATEGORY = "realtime"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Always return a unique value to force re-execution
        import time
        val = time.time()
        logging.info(f"[RealtimeLoadImage] IS_CHANGED called, returning {val}")
        return val

    def get_current_frame(self, width, height):
        if self.current_frame is not None:
            logging.info(f"[RealtimeLoadImage] Returning current frame, shape: {self.current_frame.shape}")
            return (self.current_frame, self.current_mask)

        logging.info(f"[RealtimeLoadImage] No frame available, returning blank {width}x{height}")
        blank_image = torch.zeros((1, height, width, 3), dtype=torch.float32)
        blank_mask = torch.ones((1, height, width), dtype=torch.float32)
        return (blank_image, blank_mask)

    def update_frame(self, image_tensor):
        """
        Update the current frame with a new image tensor.
        
        Args:
            image_tensor: Tensor of shape (1, H, W, 3) with values in [0, 1]
        """
        logging.info(f"[RealtimeLoadImage] update_frame called, tensor shape: {image_tensor.shape}")
        self.current_frame = image_tensor
        _, h, w, _ = image_tensor.shape
        self.current_mask = torch.ones((1, h, w), dtype=torch.float32)


class RealtimeWait:
    """
    Blocking node that keeps the workflow alive for continuous realtime streaming.
    
    Place this at the end of your workflow to prevent it from completing.
    The workflow will continue running and accepting new frames indefinitely
    until cancelled or interrupted.
    
    For cloud deployments, this prevents the WebSocket connection from being
    cleaned up after prompt execution completes, allowing subsequent frame
    updates to trigger re-execution.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["infinite"],),
            },
            "optional": {
                "images": ("IMAGE",),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "wait"
    CATEGORY = "realtime"
    OUTPUT_NODE = True

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    async def wait(self, mode, images=None):
        import asyncio
        import comfy.model_management
        
        logging.info(f"[RealtimeWait] Starting wait, mode={mode}")
        
        if mode == "infinite":
            while True:
                if comfy.model_management.processing_interrupted():
                    logging.info("[RealtimeWait] Interrupt detected, exiting wait loop")
                    raise comfy.model_management.InterruptProcessingException()
                await asyncio.sleep(1.0)
        return ()


NODE_CLASS_MAPPINGS = {
    "RealtimeLoadImage": RealtimeLoadImage,
    "RealtimeWait": RealtimeWait,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RealtimeLoadImage": "Realtime Load Image",
    "RealtimeWait": "Realtime Wait",
}
