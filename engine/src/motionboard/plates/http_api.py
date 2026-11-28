"""HTTP plates: a generic JSON image API. The key is read at call time from a file or
environment variable named in the config, sent as a bearer header, never stored or logged.

config: {"url": "https://api.example.com/v1/images/generations",
         "body": {"model": "x", "prompt": "{prompt}", "size": "{w}x{h}"},
         "image_field": "data.0.b64_json"   (or "data.0.url"),
         "key_file": "~/.navaan-assets/meta_api_key"  or  "key_env": "NAME",
         "headers": {"X-Extra": "value"}}

References: "{ref_b64}" (base64) or "{ref}" (path) in the body takes one reference; "refs_field": "input.images"
puts every reference in a list at that dotted path, encoded per "refs_encoding": base64 (default), data_url or path.
With none of these the API takes no references, and requests with references fail unless a strategy is set.
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


def _encode(path: Path, encoding: str) -> str:
    if encoding == "path":
        return str(path)
    data = base64.b64encode(Path(path).read_bytes()).decode()
    if encoding == "data_url":
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "webp": "webp"}.get(Path(path).suffix.lower().lstrip("."), "png")
        return f"data:image/{mime};base64,{data}"
    return data


def _put(obj: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    for p in parts[:-1]:
        obj = obj.setdefault(p, {})
    obj[parts[-1]] = value


class HttpAdapter:
    kind = "http"

    def __init__(self, name: str, cfg: dict, cost: float):
        self.name, self.cfg, self.cost_per_image_usd = name, cfg, cost

    def reference_capacity(self) -> int | None:
        if self.cfg.get("refs_field"):
            return None
        body = json.dumps(self.cfg.get("body", {}))
        return 1 if ("{ref_b64}" in body or "{ref}" in body) else 0

    def request(self, req: PlateRequest) -> PlateResult:
        first = req.references[0].path if req.references else None
        body_tpl = json.dumps(self.cfg.get("body", {}))
        values = {"prompt": req.prompt, "negative": req.negative, "w": req.width, "h": req.height,
                  "seed": req.seed, "ref": str(first or ""),
                  "ref_b64": _encode(first, "base64") if first and "{ref_b64}" in body_tpl else ""}
        payload = _template(self.cfg.get("body", {"prompt": "{prompt}"}), values)
        if self.cfg.get("refs_field") and req.references:
            _put(payload, self.cfg["refs_field"],
                 [_encode(r.path, self.cfg.get("refs_encoding", "base64")) for r in req.references])
        body = json.dumps(payload).encode()
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
