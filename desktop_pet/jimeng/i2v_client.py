"""即梦（火山引擎）图生视频：首尾帧一致 i2v_first_tail_v30，异步提交 + 轮询结果 + 下载。"""
import base64
import json
import time
from pathlib import Path
from typing import Optional

import requests

from desktop_pet.jimeng.client import ENDPOINT, SERVICE, _format_query, _sign_v4_request

REQ_KEY = "jimeng_i2v_first_tail_v30"
SUBMIT_ACTION = "CVSync2AsyncSubmitTask"
GET_RESULT_ACTION = "CVSync2AsyncGetResult"
VERSION = "2022-08-31"
POLL_INTERVAL = 5
DEFAULT_FRAMES = 121
DEFAULT_VIDEO_PROMPT = "旋转跳跃"


def _submit_task(
    access_key: str,
    secret_key: str,
    image_base64_list: list[str],
    prompt: str = DEFAULT_VIDEO_PROMPT,
    seed: int = -1,
    frames: int = DEFAULT_FRAMES,
) -> Optional[str]:
    """提交图生视频任务，返回 task_id。"""
    query_params = {"Action": SUBMIT_ACTION, "Version": VERSION}
    formatted_query = _format_query(query_params)
    body = {
        "req_key": REQ_KEY,
        "binary_data_base64": image_base64_list,
        "prompt": prompt,
        "seed": seed,
        "frames": frames,
    }
    req_body = json.dumps(body)
    headers = _sign_v4_request(access_key, secret_key, SERVICE, formatted_query, req_body)
    url = ENDPOINT + "?" + formatted_query
    try:
        r = requests.post(url, headers=headers, data=req_body, timeout=60)
    except Exception as e:
        import sys
        print(f"[桌宠-即梦视频] 提交任务失败: {e}", file=sys.stderr, flush=True)
        return None
    try:
        data = json.loads(r.text)
    except Exception:
        return None
    if data.get("code") != 10000 or "data" not in data:
        import sys
        print(f"[桌宠-即梦视频] 提交失败: {data.get('message', r.text[:200])}", file=sys.stderr, flush=True)
        return None
    task_id = data["data"].get("task_id")
    if not task_id:
        return None
    import sys
    print(f"[桌宠-即梦视频] 任务已提交 task_id={task_id}", file=sys.stderr, flush=True)
    return task_id


def _get_result(access_key: str, secret_key: str, task_id: str) -> Optional[str]:
    """查询任务结果，若完成返回 video_url，否则返回 None。"""
    query_params = {"Action": GET_RESULT_ACTION, "Version": VERSION}
    formatted_query = _format_query(query_params)
    body = {"req_key": REQ_KEY, "task_id": task_id}
    req_body = json.dumps(body)
    headers = _sign_v4_request(access_key, secret_key, SERVICE, formatted_query, req_body)
    url = ENDPOINT + "?" + formatted_query
    try:
        r = requests.post(url, headers=headers, data=req_body, timeout=30)
    except Exception as e:
        import sys
        print(f"[桌宠-即梦视频] 查询结果失败: {e}", file=sys.stderr, flush=True)
        return None
    try:
        data = json.loads(r.text)
    except Exception:
        return None
    if data.get("code") != 10000:
        return None
    status = data.get("data", {}).get("status")
    if status == "done":
        return data["data"].get("video_url")
    return None


def _download_video(url: str, save_path: Path) -> bool:
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        import sys
        print(f"[桌宠-即梦视频] 下载失败: {e}", file=sys.stderr, flush=True)
        return False


def generate_video_from_image(
    access_key: str,
    secret_key: str,
    image_path: str | Path,
    save_dir: str | Path,
    prompt: str = DEFAULT_VIDEO_PROMPT,
    seed: int = -1,
    frames: int = DEFAULT_FRAMES,
    poll_interval: int = POLL_INTERVAL,
) -> Optional[Path]:
    """
    用一张图做首尾帧，提交图生视频，轮询直到完成并下载到 save_dir。
    返回保存的视频路径，失败返回 None。
    """
    path = Path(image_path)
    if not path.exists():
        import sys
        print(f"[桌宠-即梦视频] 图片不存在: {path}", file=sys.stderr, flush=True)
        return None
    try:
        with open(path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        import sys
        print(f"[桌宠-即梦视频] 读取图片失败: {e}", file=sys.stderr, flush=True)
        return None
    image_base64_list = [img_b64, img_b64]

    task_id = _submit_task(access_key, secret_key, image_base64_list, prompt=prompt, seed=seed, frames=frames)
    if not task_id:
        return None

    import sys
    print("[桌宠-即梦视频] 轮询任务结果...", file=sys.stderr, flush=True)
    while True:
        video_url = _get_result(access_key, secret_key, task_id)
        if video_url:
            break
        time.sleep(poll_interval)
        print(f"[桌宠-即梦视频] 生成中，{poll_interval} 秒后重试...", file=sys.stderr, flush=True)

    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    name = path.stem + "_i2v.mp4"
    save_path = save_dir / name
    if _download_video(video_url, save_path):
        print(f"[桌宠-即梦视频] 已保存: {save_path}", file=sys.stderr, flush=True)
        return save_path
    return None
