"""Manual plates: the creator drops shot-NN.png into the project's inbox folder (or uploads in the Studio)."""

from pathlib import Path

from motionboard.assets import IMAGE_EXT
from motionboard.plates.adapter import Pending, PlateRequest, PlateResult


class ManualAdapter:
    kind = "manual"
    cost_per_image_usd = 0.0

    def __init__(self, name: str, cfg: dict, project: dict):
        self.name = name
        self.inbox = Path(project["folder"]) / cfg.get("watch_folder", "plates/inbox")
        self.inbox.mkdir(parents=True, exist_ok=True)

    def find(self, ord_: int) -> Path | None:
        for stem in (f"shot-{ord_:02d}", f"shot-{ord_}", f"{ord_:02d}", f"{ord_}"):
            for ext in IMAGE_EXT:
                p = self.inbox / f"{stem}{ext}"
                if p.exists():
                    return p
        return None

    def request(self, req: PlateRequest) -> PlateResult | Pending:
        p = self.find(req.shot_ord)
        return PlateResult(p) if p else Pending()
