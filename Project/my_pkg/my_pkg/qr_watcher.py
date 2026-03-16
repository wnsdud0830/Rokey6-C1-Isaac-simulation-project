import os
import time
import json
from collections import deque, Counter

import cv2
import numpy as np

import sys
import cv2

info = cv2.getBuildInformation()
for line in info.splitlines():
    if "QUIRC" in line.upper() or "QR" in line.upper():
        print("[ENV]", line)
QR_IMAGE_PATH = "/tmp/isaac_qr_input.png"
QR_RESULT_PATH = "/tmp/qr_result.json"

POLL_INTERVAL_SEC = 0.10

# 새 이미지 하나가 들어왔을 때, 최대 이 시간 동안 반복 판독
DETECT_WINDOW_SEC = 2.0

# 같은 결과가 연속 몇 프레임 나오면 확정할지
CONSECUTIVE_CONFIRM_COUNT = 5

# 최근 프레임 deque 길이
RECENT_TYPES_MAXLEN = 12

# crop/재탐색용 확장 픽셀
ROI_PAD = 24

LAST_MTIME = None


def safe_remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"[QR_WATCHER] removed: {path}")
    except Exception as e:
        print(f"[QR_WATCHER] remove warning for {path}: {e}")


def parse_detected_type(text: str):
    if text is None:
        return None
    t = str(text).strip().upper()
    if not t:
        return None

    if t == "MEDICINE_A" or t.endswith("_A"):
        return "A"
    if t == "MEDICINE_B" or t.endswith("_B"):
        return "B"
    if t == "MEDICINE_C" or t.endswith("_C"):
        return "C"
    return None


def save_result(ok: bool, detected_type=None, raw_text=None, message="", recent_types=None):
    payload = {
        "ok": bool(ok),
        "detected_type": detected_type,
        "raw_text": raw_text,
        "message": message,
        "recent_types": recent_types or [],
        "timestamp": time.time(),
    }

    tmp_path = QR_RESULT_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, QR_RESULT_PATH)


def try_decode_direct(detector, img):
    try:
        text, _, _ = detector.detectAndDecode(img)
        if text:
            return text
    except Exception:
        pass
    return None


def try_decode_multi(detector, img):
    try:
        ok, decoded_info, _, _ = detector.detectAndDecodeMulti(img)
        if ok and decoded_info:
            for t in decoded_info:
                if t:
                    return t
    except Exception:
        pass
    return None


def try_decode_variants(detector, img_bgr):
    text = try_decode_direct(detector, img_bgr)
    if text:
        return text

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    text = try_decode_direct(detector, gray)
    if text:
        return text

    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    text = try_decode_direct(detector, th)
    if text:
        return text

    ad = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        5,
    )
    text = try_decode_direct(detector, ad)
    if text:
        return text

    text = try_decode_multi(detector, img_bgr)
    if text:
        return text

    return None


def try_decode_roi_search(detector, img_bgr):
    try:
        ok, pts = detector.detect(img_bgr)
    except Exception:
        ok, pts = False, None

    if not ok or pts is None:
        return None

    pts = np.array(pts, dtype=np.float32).reshape(-1, 2)

    x_min = max(int(np.min(pts[:, 0])) - ROI_PAD, 0)
    y_min = max(int(np.min(pts[:, 1])) - ROI_PAD, 0)
    x_max = min(int(np.max(pts[:, 0])) + ROI_PAD, img_bgr.shape[1] - 1)
    y_max = min(int(np.max(pts[:, 1])) + ROI_PAD, img_bgr.shape[0] - 1)

    roi = img_bgr[y_min:y_max, x_min:x_max]
    if roi.size == 0:
        return None

    for scale in [2, 3, 4, 5]:
        up = cv2.resize(
            roi,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

        text = try_decode_variants(detector, up)
        if text:
            return text

    return None


def decode_once(img_bgr):
    detector = cv2.QRCodeDetector()

    text = try_decode_variants(detector, img_bgr)
    if text:
        return text

    text = try_decode_roi_search(detector, img_bgr)
    if text:
        return text

    return None


def confirm_from_recent(recent_types):
    if not recent_types:
        return None

    last = recent_types[-1]
    if last is not None:
        count = 0
        for t in reversed(recent_types):
            if t == last:
                count += 1
            else:
                break
        if count >= CONSECUTIVE_CONFIRM_COUNT:
            return last

    valid = [t for t in recent_types if t in ["A", "B", "C"]]
    if not valid:
        return None

    c = Counter(valid)
    top_type, top_count = c.most_common(1)[0]
    if top_count >= CONSECUTIVE_CONFIRM_COUNT:
        return top_type

    return None


def handle_new_image():
    print("[QR_WATCHER] new image detected")

    recent_types = deque(maxlen=RECENT_TYPES_MAXLEN)
    last_text = None

    start = time.monotonic()
    frame_idx = 0

    try:
        while time.monotonic() - start <= DETECT_WINDOW_SEC:
            img_bgr = cv2.imread(QR_IMAGE_PATH, cv2.IMREAD_COLOR)
            if img_bgr is None:
                time.sleep(POLL_INTERVAL_SEC)
                continue

            frame_idx += 1
            text = decode_once(img_bgr)
            last_text = text
            detected_type = parse_detected_type(text)

            recent_types.append(detected_type)

            print(
                f"[QR_WATCHER] frame={frame_idx}, raw={text}, type={detected_type}, recent={list(recent_types)}"
            )

            confirmed = confirm_from_recent(recent_types)
            if confirmed is not None:
                save_result(
                    True,
                    detected_type=confirmed,
                    raw_text=last_text,
                    message=f"confirmed by repeated detection within {DETECT_WINDOW_SEC:.1f}s",
                    recent_types=list(recent_types),
                )
                print(f"[QR_WATCHER] CONFIRMED type={confirmed}")
                return

            time.sleep(POLL_INTERVAL_SEC)

        save_result(
            False,
            detected_type=None,
            raw_text=last_text,
            message=f"QR decode failed after repeated search for {DETECT_WINDOW_SEC:.1f}s",
            recent_types=list(recent_types),
        )
        print("[QR_WATCHER] decode failed after repeated search window")

    finally:
        safe_remove(QR_IMAGE_PATH)


def main():
    global LAST_MTIME

    print("[QR_WATCHER] started")
    print(f"[QR_WATCHER] image path  = {QR_IMAGE_PATH}")
    print(f"[QR_WATCHER] result path = {QR_RESULT_PATH}")

    while True:
        try:
            if not os.path.exists(QR_IMAGE_PATH):
                time.sleep(POLL_INTERVAL_SEC)
                continue

            mtime = os.path.getmtime(QR_IMAGE_PATH)
            if LAST_MTIME is not None and mtime == LAST_MTIME:
                time.sleep(POLL_INTERVAL_SEC)
                continue

            LAST_MTIME = mtime
            handle_new_image()

        except Exception as e:
            save_result(False, None, None, f"{type(e).__name__}: {e}", [])
            print(f"[QR_WATCHER] ERROR: {type(e).__name__}: {e}")
            safe_remove(QR_IMAGE_PATH)

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
