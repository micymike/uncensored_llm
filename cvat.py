import cv2
import numpy as np
from collections import defaultdict, Counter
from ultralytics import YOLO
from cvat_sdk import make_client
from cvat_sdk.api_client import models
from tqdm import tqdm

# --- CONFIG ---
CVAT_HOST = "app.cvat.ai"
USERNAME   = "monick"
PASSWORD   = "Donotlogout@anytim1"
TASK_ID    = 2116064

NEAR_LABEL_NAME = "near-side team"
FAR_LABEL_NAME  = "far-side team"
BALL_LABEL_NAME = "ball"

COURT_TOP_Y    = 0.25
COURT_BOTTOM_Y = 0.98
NET_LINE_Y     = 0.52

CONF_THRESHOLD       = 0.4
BALL_CONF_THRESHOLD  = 0.55
KEYFRAME_INTERVAL    = 5
MIN_TRACK_FRAMES     = 8
BOX_TIGHTEN          = 0.96
BOX_PAD_PX           = 6
EMA_ALPHA_PLAYER     = 0.6
EMA_ALPHA_BALL       = 0.8
MOVE_THRESHOLD       = 3.0

# --- HELPERS ---

def clamp_box(x1, y1, x2, y2, w, h):
    return max(0, x1), max(0, y1), min(w, x2), min(h, y2)

def adjust_box(x1, y1, x2, y2, w, h):
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    bw = (x2 - x1) * BOX_TIGHTEN
    bh = (y2 - y1) * BOX_TIGHTEN

    x1n = cx - bw/2 - BOX_PAD_PX
    y1n = cy - bh/2 - BOX_PAD_PX
    x2n = cx + bw/2 + BOX_PAD_PX
    y2n = cy + bh/2 + BOX_PAD_PX

    return clamp_box(x1n, y1n, x2n, y2n, w, h)

def ema_smooth(prev, curr, alpha):
    if prev is None:
        return curr
    return tuple(alpha * c + (1 - alpha) * p for p, c in zip(prev, curr))

def box_moved(prev, curr):
    if prev is None:
        return True
    px = (prev[0] + prev[2]) / 2
    py = (prev[1] + prev[3]) / 2
    cx = (curr[0] + curr[2]) / 2
    cy = (curr[1] + curr[3]) / 2
    return ((px - cx)**2 + (py - cy)**2) ** 0.5 > MOVE_THRESHOLD

def majority_label(votes):
    return Counter(votes).most_common(1)[0][0]

# --- MAIN ---

def run_tracks_pipeline():
    with make_client(host=CVAT_HOST, credentials=(USERNAME, PASSWORD)) as client:
        task = client.tasks.retrieve(TASK_ID)
        labels = task.get_labels()

        near_id = next(l.id for l in labels if l.name == NEAR_LABEL_NAME)
        far_id  = next(l.id for l in labels if l.name == FAR_LABEL_NAME)
        ball_id = next(l.id for l in labels if l.name == BALL_LABEL_NAME)

        print("⚠️ Resetting annotations...")
        task.update_annotations(models.PatchedLabeledDataRequest(shapes=[], tracks=[], tags=[]))

        model = YOLO("yolov8m.pt")

        meta = task.get_meta()
        frame_count = meta.size
        h, w = meta.frames[0].height, meta.frames[0].width

        track_shapes = defaultdict(list)
        track_votes  = defaultdict(list)
        track_count  = defaultdict(int)
        track_ema    = {}
        last_kf      = {}

        print("Processing frames...")

        for frame_idx in tqdm(range(frame_count)):
            frame_data = task.get_frame(frame_idx)
            frame = cv2.imdecode(np.frombuffer(frame_data.read(), np.uint8), cv2.IMREAD_COLOR)

            results = model.track(
                frame, persist=True,
                classes=[0, 32],
                conf=CONF_THRESHOLD,
                tracker="bytetrack.yaml",
                verbose=False
            )

            seen = set()

            if results[0].boxes.id is None:
                continue

            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids   = results[0].boxes.id.cpu().numpy().astype(int)
            cls   = results[0].boxes.cls.cpu().numpy().astype(int)
            confs = results[0].boxes.conf.cpu().numpy()

            for box, obj_id, obj_cls, conf in zip(boxes, ids, cls, confs):
                x1, y1, x2, y2 = box
                cy = (y1 + y2) / 2 / h

                if not (COURT_TOP_Y <= cy <= COURT_BOTTOM_Y):
                    continue

                if obj_cls == 32 and conf < BALL_CONF_THRESHOLD:
                    continue
                if obj_cls == 0 and conf < CONF_THRESHOLD:
                    continue

                seen.add(obj_id)

                label = near_id if (obj_cls == 0 and cy > NET_LINE_Y) else (far_id if obj_cls == 0 else ball_id)

                track_votes[obj_id].append(label)
                track_count[obj_id] += 1

                alpha = EMA_ALPHA_BALL if obj_cls == 32 else EMA_ALPHA_PLAYER
                adjusted = adjust_box(x1, y1, x2, y2, w, h)
                smooth = ema_smooth(track_ema.get(obj_id), adjusted, alpha)
                track_ema[obj_id] = smooth

                is_kf = (frame_idx % KEYFRAME_INTERVAL == 0) and box_moved(last_kf.get(obj_id), smooth)

                if is_kf:
                    last_kf[obj_id] = smooth
                    shape = models.TrackedShapeRequest(
                        type="rectangle",
                        frame=frame_idx,
                        points=list(map(float, smooth)),
                        outside=False,
                        keyframe=True,
                    )
                    track_shapes[obj_id].append(shape)

            # handle disappear
            for obj_id in set(track_shapes.keys()) - seen:
                shapes = track_shapes[obj_id]
                if shapes and not shapes[-1].outside:
                    track_shapes[obj_id].append(
                        models.TrackedShapeRequest(
                            type="rectangle",
                            frame=frame_idx,
                            points=shapes[-1].points,
                            outside=True,
                            keyframe=True,
                        )
                    )

        # --- BUILD TRACKS ---
        tracks = []

        for obj_id, shapes in track_shapes.items():
            if track_count[obj_id] < MIN_TRACK_FRAMES or len(shapes) < 2:
                continue

            # sort + deduplicate
            shapes = sorted(shapes, key=lambda s: s.frame)
            uniq = {}
            for s in shapes:
                uniq[s.frame] = s
            shapes = list(uniq.values())

            label = majority_label(track_votes[obj_id])
            start = min(s.frame for s in shapes)

            track = models.LabeledTrackRequest(
                frame=start,
                label_id=label,
                group=int(obj_id),
                shapes=shapes,
                attributes=[],
                source="manual"
            )

            tracks.append(track)

        print(f"Uploading {len(tracks)} tracks...")

        if tracks:
            task.update_annotations(models.PatchedLabeledDataRequest(tracks=tracks))
            print("✅ Done. CVAT ready.")
        else:
            print("❌ No tracks created.")


if __name__ == "__main__":
    run_tracks_pipeline()