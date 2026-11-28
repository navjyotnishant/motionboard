"""Handoff plates: requests wait in plate_request; the mb-cinematographer skill makes the images with
whatever MCP image tool the creator has (for example Muse) and calls `mb plate fulfil`."""

from motionboard.plates.adapter import Pending, PlateRequest


class HandoffAdapter:
    kind = "handoff"

    def __init__(self, name: str, cfg: dict, cost: float):
        self.name, self.cfg, self.cost_per_image_usd = name, cfg, cost

    def request(self, req: PlateRequest) -> Pending:
        return Pending()

    def reference_capacity(self) -> int | None:
        return None  # every reference is listed for the agent that makes the image
