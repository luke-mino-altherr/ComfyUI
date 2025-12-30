"""
Binary protocol utilities for realtime frame streaming.

Frame format:
    [4B: event_type]
    [16B: prompt_id (UUID bytes)]
    [4B: node_id_len]
    [NB: node_id string]
    [4B: frame_num]
    [8B: timestamp]
    [4B: width]
    [4B: height]
    [1B: channels]
    [1B: format (1=JPEG)]
    [4B: data_len]
    [NB: image_data]
"""

import struct
import uuid
from io import BytesIO

import numpy as np
import torch
from PIL import Image

from protocol import BinaryEventTypes


def decode_realtime_frame(data: bytes) -> dict:
    """
    Parse a binary WebSocket message into frame metadata and image data.
    
    Args:
        data: Raw binary data from WebSocket
        
    Returns:
        Dictionary with frame metadata and raw image bytes
    """
    offset = 0

    event_type = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4

    prompt_id_bytes = data[offset:offset + 16]
    prompt_id = str(uuid.UUID(bytes=prompt_id_bytes))
    offset += 16

    node_id_len = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4

    node_id = data[offset:offset + node_id_len].decode("utf-8")
    offset += node_id_len

    frame_num = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4

    timestamp = struct.unpack(">d", data[offset:offset + 8])[0]
    offset += 8

    width = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4

    height = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4

    channels = struct.unpack("B", data[offset:offset + 1])[0]
    offset += 1

    format_type = struct.unpack("B", data[offset:offset + 1])[0]
    offset += 1

    data_len = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4

    image_data = data[offset:offset + data_len]

    return {
        "event_type": event_type,
        "prompt_id": prompt_id,
        "node_id": node_id,
        "frame_num": frame_num,
        "timestamp": timestamp,
        "width": width,
        "height": height,
        "channels": channels,
        "format": format_type,
        "image_data": image_data,
    }


def frame_to_tensor(frame_data: dict) -> torch.Tensor:
    """
    Convert decoded frame data to a PyTorch tensor.
    
    Args:
        frame_data: Dictionary from decode_realtime_frame()
        
    Returns:
        Tensor of shape (1, H, W, 3) with values in [0, 1]
    """
    image_bytes = frame_data["image_data"]
    image = Image.open(BytesIO(image_bytes))

    if image.mode != "RGB":
        image = image.convert("RGB")

    np_array = np.array(image).astype(np.float32) / 255.0

    tensor = torch.from_numpy(np_array)

    tensor = tensor.unsqueeze(0)

    return tensor


def encode_realtime_frame(
    prompt_id: str,
    node_id: str,
    frame_num: int,
    timestamp: float,
    width: int,
    height: int,
    channels: int,
    format_type: int,
    image_data: bytes,
) -> bytes:
    """
    Encode frame data into binary format for WebSocket transmission.
    
    This is primarily for testing/debugging from Python clients.
    """
    prompt_uuid = uuid.UUID(prompt_id)

    node_id_bytes = node_id.encode("utf-8")

    data = bytearray()
    data.extend(struct.pack(">I", BinaryEventTypes.REALTIME_FRAME))
    data.extend(prompt_uuid.bytes)
    data.extend(struct.pack(">I", len(node_id_bytes)))
    data.extend(node_id_bytes)
    data.extend(struct.pack(">I", frame_num))
    data.extend(struct.pack(">d", timestamp))
    data.extend(struct.pack(">I", width))
    data.extend(struct.pack(">I", height))
    data.extend(struct.pack("B", channels))
    data.extend(struct.pack("B", format_type))
    data.extend(struct.pack(">I", len(image_data)))
    data.extend(image_data)

    return bytes(data)
