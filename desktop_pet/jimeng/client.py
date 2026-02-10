"""即梦（火山引擎）图生图 3.0 智能参考 API 调用：签名与请求。

接口文档（必读）：即梦图生图3.0智能参考-接口文档
https://www.volcengine.com/docs/85621/1747301?lang=zh

请求：Action=CVProcess, Version=2022-08-31, req_key=jimeng_i2i_v30；
Body 参数：req_key、binary_data_base64（或 image）、prompt。
响应：以文档为准，本实现兼容 data 内 image/binary_data_base64/url/images 等常见返回格式。
"""
import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from desktop_pet.jimeng.prompt import JIMENG_AVATAR_PROMPT

METHOD = "POST"
HOST = "visual.volcengineapi.com"
REGION = "cn-north-1"
ENDPOINT = "https://visual.volcengineapi.com"
SERVICE = "cv"
REQ_KEY = "jimeng_i2i_v30"


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signing_key(secret_key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = _sign(secret_key.encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region_name)
    k_service = _sign(k_region, service_name)
    return _sign(k_service, "request")


def _format_query(parameters: dict) -> str:
    return "&".join(k + "=" + parameters[k] for k in sorted(parameters))


def _sign_v4_request(
    access_key: str,
    secret_key: str,
    service: str,
    req_query: str,
    req_body: str,
) -> dict:
    t = datetime.now(timezone.utc)
    current_date = t.strftime("%Y%m%dT%H%M%SZ")
    datestamp = t.strftime("%Y%m%d")
    canonical_uri = "/"
    canonical_querystring = req_query
    signed_headers = "content-type;host;x-content-sha256;x-date"
    payload_hash = hashlib.sha256(req_body.encode("utf-8")).hexdigest()
    content_type = "application/json"
    canonical_headers = (
        "content-type:" + content_type + "\n"
        "host:" + HOST + "\n"
        "x-content-sha256:" + payload_hash + "\n"
        "x-date:" + current_date + "\n"
    )
    canonical_request = (
        METHOD + "\n" + canonical_uri + "\n" + canonical_querystring + "\n"
        + canonical_headers + "\n" + signed_headers + "\n" + payload_hash
    )
    algorithm = "HMAC-SHA256"
    credential_scope = datestamp + "/" + REGION + "/" + service + "/request"
    string_to_sign = (
        algorithm + "\n" + current_date + "\n" + credential_scope + "\n"
        + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    )
    signing_key = _get_signing_key(secret_key, datestamp, REGION, service)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization_header = (
        algorithm + " Credential=" + access_key + "/" + credential_scope + ", "
        "SignedHeaders=" + signed_headers + ", Signature=" + signature
    )
    return {
        "X-Date": current_date,
        "Authorization": authorization_header,
        "X-Content-Sha256": payload_hash,
        "Content-Type": content_type,
    }


class JimengClient:
    """即梦图生图 3.0 客户端：上传宠物图片 + 固定 prompt 生成 AI 分身。"""

    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        self.access_key = access_key or os.environ.get("JIMENG_ACCESS_KEY", "").strip()
        self.secret_key = secret_key or os.environ.get("JIMENG_SECRET_KEY", "").strip()

    def image_to_image(
        self,
        image_path: str | Path,
        prompt: Optional[str] = None,
    ) -> tuple[Optional[bytes], Optional[str]]:
        """
        图生图：根据本地图片和 prompt 生成新图。
        返回 (图片二进制, None) 成功，或 (None, 错误信息) 失败。
        """
        path = Path(image_path)
        if not path.exists():
            return None, "图片文件不存在"
        try:
            with open(path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("ascii")
        except Exception as e:
            return None, f"读取图片失败: {e}"

        prompt = prompt or JIMENG_AVATAR_PROMPT
        # 与官方示例一致：binary_data_base64 为数组，并带 seed、scale
        body_params = {
            "req_key": REQ_KEY,
            "binary_data_base64": [image_b64],
            "prompt": prompt,
            "seed": -1,
            "scale": 0.5,
        }
        req_body = json.dumps(body_params)
        query_params = {"Action": "CVProcess", "Version": "2022-08-31"}
        formatted_query = _format_query(query_params)
        headers = _sign_v4_request(
            self.access_key,
            self.secret_key,
            SERVICE,
            formatted_query,
            req_body,
        )
        url = ENDPOINT + "?" + formatted_query
        import sys
        print("[桌宠-即梦] 正在请求即梦接口...", file=sys.stderr, flush=True)
        try:
            r = requests.post(url, headers=headers, data=req_body, timeout=90)
        except Exception as e:
            err = f"请求失败: {e}"
            print(f"[桌宠-即梦] {err}", file=sys.stderr, flush=True)
            return None, err
        print(f"[桌宠-即梦] 响应 HTTP {r.status_code}", file=sys.stderr, flush=True)
        resp_str = r.text.replace("\\u0026", "&")
        try:
            data = json.loads(resp_str)
        except Exception as e:
            err = f"响应非 JSON: {resp_str[:200]}"
            print(f"[桌宠-即梦] {err}", file=sys.stderr, flush=True)
            return None, err
        if r.status_code != 200:
            msg = data.get("message") or data.get("ResponseMetadata", {}).get("Error", {}).get("Message") or r.text[:200]
            err = f"HTTP {r.status_code}: {msg}"
            print(f"[桌宠-即梦] {err}", file=sys.stderr, flush=True)
            return None, err
        # 业务错误：code 非 10000/0 表示失败（文档以 10000 为成功，部分接口用 0）
        code = data.get("code") or data.get("response", {}).get("code")
        if code is not None and code not in (10000, 0, "10000", "0"):
            msg = data.get("message") or data.get("response", {}).get("message") or str(data)[:300]
            err = f"接口返回错误(code={code}): {msg}"
            print(f"[桌宠-即梦] {err}", file=sys.stderr, flush=True)
            return None, err
        # 即梦图生图3.0智能参考：响应以 data 或 result 承载结果，可能为 base64 或 URL
        image_b64_out = None
        payload = data.get("data")
        result = data.get("result")
        if isinstance(payload, dict):
            image_b64_out = (
                payload.get("image")
                or payload.get("binary_data_base64")
                or payload.get("image_url")
                or payload.get("data")
            )
            if not image_b64_out and isinstance(payload.get("images"), list) and payload["images"]:
                first_img = payload["images"][0]
                image_b64_out = first_img.get("image") or first_img.get("binary_data_base64") if isinstance(first_img, dict) else first_img
        if isinstance(payload, str):
            image_b64_out = payload
        if isinstance(payload, list) and payload:
            first = payload[0]
            image_b64_out = first.get("image") or first.get("binary_data_base64") or (first if isinstance(first, str) else None)
        if not image_b64_out and isinstance(result, dict):
            image_b64_out = result.get("image") or result.get("binary_data_base64")
            if not image_b64_out and isinstance(result.get("images"), list) and result["images"]:
                first_r = result["images"][0]
                image_b64_out = first_r.get("image") or first_r.get("binary_data_base64") if isinstance(first_r, dict) else first_r
        if not image_b64_out and isinstance(result, str):
            image_b64_out = result
        # 若返回的是图片 URL 而非 base64，则下载
        image_url = None
        if isinstance(payload, dict):
            image_url = payload.get("url") or payload.get("image_url")
        if not image_url and isinstance(payload, list) and payload and isinstance(payload[0], dict):
            image_url = payload[0].get("url") or payload[0].get("image_url")
        if not image_url and isinstance(result, dict) and result.get("images"):
            image_url = result["images"][0].get("url") or result["images"][0].get("image_url") if isinstance(result["images"][0], dict) else None
        if image_url and not image_b64_out:
            try:
                rr = requests.get(image_url, timeout=30)
                if rr.status_code == 200 and rr.content:
                    return rr.content, None
            except Exception as e:
                err = f"下载图片失败: {e}"
                print(f"[桌宠-即梦] {err}", file=sys.stderr, flush=True)
                return None, err
        if not image_b64_out:
            # 保存响应结构便于对照文档排查（脱敏 base64）
            try:
                from desktop_pet.config import DATA_DIR
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                debug_path = DATA_DIR / "jimeng_last_response.json"
                def _sanitize(obj, depth=0):
                    if depth > 5:
                        return "<max_depth>"
                    if isinstance(obj, dict):
                        return {k: _sanitize(v, depth + 1) for k, v in obj.items()}
                    if isinstance(obj, list) and obj and isinstance(obj[0], (dict, str)):
                        return [_sanitize(obj[0], depth + 1)] + (["..."] if len(obj) > 1 else [])
                    if isinstance(obj, str) and len(obj) > 300:
                        return obj[:100] + "...<len=%d>" % len(obj)
                    return obj
                summary = {"_response_keys": {"top": list(data.keys()), "data_type": type(payload).__name__}}
                if isinstance(payload, dict):
                    summary["_response_keys"]["data_keys"] = list(payload.keys())
                with open(debug_path, "w", encoding="utf-8") as f:
                    json.dump({**summary, ** _sanitize(data)}, f, ensure_ascii=False, indent=2)
                err_extra = f"\n响应结构已保存到: {debug_path}（可对照文档 1747301 检查返回字段）"
            except Exception:
                err_extra = ""
            err = (
                f"响应中未找到图片。响应摘要: {json.dumps(data, ensure_ascii=False)[:350]}"
                + err_extra
            )
            print(f"[桌宠-即梦] {err}", file=sys.stderr, flush=True)
            return None, err
        # 即梦可能返回多张图（list），取第一张解码
        if isinstance(image_b64_out, list) and image_b64_out:
            image_b64_out = image_b64_out[0]
        if not isinstance(image_b64_out, str):
            return None, f"图片数据格式异常: 期望 base64 字符串，得到 {type(image_b64_out).__name__}"
        try:
            return base64.b64decode(image_b64_out), None
        except Exception as e:
            err = f"图片 base64 解码失败: {e}"
            print(f"[桌宠-即梦] {err}", file=sys.stderr, flush=True)
            return None, err
