"""
Realtime session state management for streaming updates to ComfyUI workflows.
"""

import copy
import time


class RealtimePromptState:
    """Maintains state for a realtime-enabled workflow session."""

    def __init__(self, prompt_id: str, client_id: str):
        self.prompt_id = prompt_id
        self.client_id = client_id
        self.prompt = None
        self.pending_frame_updates = {}  # node_id → tensor
        self.target_framerate = 30
        self.last_frame_time = 0
        self.frame_count = 0
        self.dropped_frames = 0
        self.current_executing_node = None  # (node_id, class_type) of currently executing node

    def set_prompt(self, prompt: dict):
        """Store a deep copy of the prompt for realtime updates."""
        self.prompt = copy.deepcopy(prompt)

    def update_frame(self, node_id: str, tensor):
        """Queue a frame update for a specific node."""
        self.pending_frame_updates[node_id] = tensor
        self.frame_count += 1
        self.last_frame_time = time.time()

    def get_pending_frame(self, node_id: str):
        """Get and clear pending frame for a node."""
        return self.pending_frame_updates.pop(node_id, None)

    def has_pending_frames(self) -> bool:
        """Check if there are any pending frame updates."""
        return len(self.pending_frame_updates) > 0
