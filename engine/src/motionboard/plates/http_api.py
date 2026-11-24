"""HTTP plates: a generic JSON image API. The key is read at call time from a file or
environment variable named in the config, sent as a bearer header, never stored or logged.

config: {"url": "https://api.example.com/v1/images/generations",
         "body": {"model": "x", "prompt": "{prompt}", "size": "{w}x{h}"},
         "image_field": "data.0.b64_json"   (or "data.0.url"),
         "key_file": "~/.navaan-assets/meta_api_key"  or  "key_env": "NAME",
         "headers": {"X-Extra": "value"}}
"""

import base64
import json
import os
import urllib.request
from pathlib import Path

from motionboard.plates.adapter import PlateRequest, PlateResult
from motionboard.report import MbError


def _template(obj, values: dict):
    if isinstance(obj, str):
        return obj.format(**values)
    if isinstance(obj, dict):
        return {k: _template(v, values) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_template(v, values) for v in obj]
    return obj


def _dig(obj, path: str):
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


def _key(cfg: dict) -> str | None:
    if cfg.get("key_file"):
        p = Path(cfg["key_file"]).expanduser()
        if not p.is_file():
            raise MbError("INVALID_INPUT", f"key file not found: {p}")
        return p.read_text().strip()
    if cfg.get("key_env"):
        v = os.environ.get(cfg["key_env"])
        if not v:
            raise MbError("INVALID_INPUT", f"environment variable {cfg['key_env']} is not set")
        return v
    return None


class HttpAdapter:
    kind = "http"

    def __init__(self, name: str, cfg: dict, cost: float):
        self.name, self.cfg, self.cost_per_image_usd = name, cfg, cost

    def request(self, req: PlateRequest) -> PlateResult:
        values = {"prompt": req.prompt, "negative": req.negative, "w": req.width, "h": req.height,
                  "seed": req.seed}
        body = json.dumps(_template(self.cfg.get("body", {"prompt": "{prompt}"}), values)).encode()
        headers = {"Content-Type": "application/json", **self.cfg.get("headers", {})}
        key = _key(self.cfg)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        http_req = urllib.request.Request(self.cfg["url"], data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(http_req, timeout=self.cfg.get("timeout", 180)) as resp:
                data = json.loads(resp.read())
        except Exception as e:  # never echo headers
            raise MbError("INTERNAL", f"image API request failed: {type(e).__name__}: {getattr(e, 'reason', e)}") from e
        try:
            value = _dig(data, self.cfg.get("image_field", "data.0.b64_json"))
        except (KeyError, IndexError, TypeError) as e:
            raise MbError("INTERNAL", f"image not found in API response at {self.cfg.get('image_field')}") from e
        if isinstance(value, str) and value.startswith("http"):
            with urllib.request.urlopen(value, timeout=120) as r:
                req.out.write_bytes(r.read())
        else:
            req.out.write_bytes(base64.b64decode(value))
        return PlateResult(req.out, self.cost_per_image_usd)
