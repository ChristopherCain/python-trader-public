<div align="center">

# ForgoteLabeling

**A lightweight image annotation tool for building computer-vision datasets.**

Create a project, upload images, define labels, draw bounding boxes, and export straight to YOLO format — with everything stored locally as plain files you own.

[![License: MIT](https://img.shields.io/badge/License-MIT-000000.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)

</div>

---

## 🚀 Live Demo

Try it in your browser — no install required: **[Try ForgoteLabeling](https://forgotelabeling-frontend.onrender.com/)**

> The public demo runs on free-tier hosting with **anonymous, temporary** projects — no sign-up and no accounts. Anyone with the link can create a project, upload images, annotate, and export YOLO. Projects are therefore **not private**, and **every project is permanently deleted 30 hours after it is created** — images, annotations, and labels included. **Export your dataset before the deadline**; see [Public projects are temporary](#-public-projects-are-temporary--30-hours-then-permanently-deleted). For real work, self-host with the [Local Development](#local-development) steps below, where your data stays on your own disk permanently.

_Deploying your own copy? Replace the URL above with your Cloudflare Pages address — see [Public Deployment](#public-deployment)._

## Why ForgoteLabeling

Most annotation tools ask you to stand up a database, sign into an account, or push your images to someone else's cloud before you can draw a single box. ForgoteLabeling does none of that.

It runs entirely on your machine. Every project is a plain folder on disk — images, labels, and annotations are readable JSON you can inspect, back up, diff, or delete with ordinary tools. There is no database to migrate and no account to create. Start the two processes, open the browser, and label.

## Features

- **Projects** — create, browse, and delete isolated annotation projects.
- **Image upload** — multi-file upload with per-file validation (`.jpg`, `.jpeg`, `.png`, `.webp`).
- **Labels** — named, color-coded classes with a deterministic order that defines the YOLO class index.
- **Bounding-box editor** — draw, move, resize, select, and delete boxes on a canvas overlay.
- **Keyboard-first workflow** — `←` / `→` to move between images, `Delete` to remove the selected box.
- **Durable persistence** — annotations are written atomically and survive reloads and restarts.
- **YOLO export** — a zipped dataset with `images/`, `labels/`, `data.yaml`, and a deterministic train/val split, ready for training.
- **COCO export** — the same dataset as `annotations/instances.json` in standard COCO detection format.
- **Honest reporting** — boxes that can't be exported are listed in `unlabeled.txt` rather than silently dropped.

## Tech Stack

| Layer    | Choice                              |
| -------- | ----------------------------------- |
| Frontend | React 19, Vite, React Router, Axios |
| Backend  | FastAPI, Pydantic v2, Uvicorn       |
| Storage  | JSON files on disk (no database)    |
| Export   | YOLO + COCO                         |
| Testing  | pytest + Starlette `TestClient`     |

## Requirements

- **Python** 3.10 or newer
- **Node.js** 18 or newer
- No database, no external services

## Local Development

This is the self-hosted path: two local processes, all data on your own disk, no external services. It is byte-for-byte the v1.0.0 workflow and the default when `STORAGE_BACKEND` is unset.

Clone the repository:

```bash
git clone https://github.com/nayonahmedjoy/ForgoteLabeling.git
cd ForgoteLabeling
```

### 1. Backend

The backend has no `__init__.py` files and relies on namespace packages, so it **must** be started from the `backend/` directory.

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install fastapi uvicorn pydantic pydantic-settings python-multipart pillow
uvicorn app.main:app --reload --port 8000
```

The API is now at **http://localhost:8000** (interactive docs at `/docs`).

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

> CORS is restricted to the Vite dev origins (`5173` and `4173` on `localhost` and `127.0.0.1`). If you serve the frontend from somewhere else, set the `FRONTEND_ORIGIN` environment variable (it is appended to the allowed origins) rather than editing `backend/app/core/config.py`. The frontend picks up the backend URL from `VITE_API_BASE_URL`; when unset it defaults to `http://127.0.0.1:8000`. See `backend/.env.example` and `frontend/.env.example`.

## Usage

1. **Create a project** from the dashboard.
2. **Upload images** using the panel on the left.
3. **Add labels** on the right — each gets a color, and their order fixes the YOLO class index.
4. **Select a label**, then drag on the image to draw a box. Drag inside a box to move it, or grab a corner to resize.
5. **Navigate** with `←` / `→`; press `Delete` to remove the selected box.
6. **Export YOLO** or **Export COCO** from the top bar to download the finished dataset.

Annotations save as you work — there is no save button.

## Export Format

### YOLO

`Export YOLO` downloads a zip laid out as:

```
dataset/
├── images/          # your images, copied as-is
├── labels/          # one .txt per image, matched by filename stem
├── data.yaml        # Ultralytics dataset config (path/train/val/nc/names)
├── train.txt        # 80% of the images, one relative path per line
├── val.txt          # the remaining 20%
├── classes.txt      # class names, one per line, in index order
└── unlabeled.txt    # only written when some boxes could not be exported
```

Each line in a label file is a normalized, center-anchored box:

```
<class_index> <x_center> <y_center> <width> <height>
```

All four coordinates are floats in `0..1` relative to the image dimensions, which is the standard YOLO convention.

A box is omitted only when it has no label or points at a label that no longer exists. Those cases are counted per image in `unlabeled.txt`, so an incomplete dataset is always visible rather than silent. Images with no boxes still get an empty label file, as YOLO expects.

### COCO

`Export COCO` downloads a zip laid out as:

```
dataset/
├── images/                    # your images, copied as-is
└── annotations/
    └── instances.json         # standard COCO detection annotations
```

`instances.json` holds the usual three arrays. Each image carries `id`, `file_name`, `width`, and `height`; each annotation carries `id`, `image_id`, `category_id`, `bbox`, `area`, and `iscrowd`; categories come from the project's labels, numbered from `1` (COCO reserves `0`). Unlike YOLO, `bbox` is `[x, y, width, height]` in **absolute pixels** with `(x, y)` at the top-left corner, so the stored normalized boxes are scaled by each image's own dimensions.

## Project Structure

```
ForgoteLabeling/
├── backend/
│   ├── app/
│   │   ├── api/routes.py        # every HTTP endpoint
│   │   ├── core/                # config, storage helpers, logging
│   │   ├── models/              # Pydantic models
│   │   ├── services/            # project / upload / label / annotation / export
│   │   └── main.py              # app setup, CORS, error handlers
│   ├── tests/                   # pytest regression suite
│   └── uploads/                 # project data (created at runtime)
├── frontend/
│   └── src/
│       ├── api/                 # thin API client per resource
│       ├── components/          # Navbar, ImageViewer, LabelPanel, dialogs…
│       └── pages/               # Dashboard, Project workspace
└── docs/                        # architecture and API notes
```

### How Storage Works

Each project is a UUID-named folder under `backend/uploads/`:

```
uploads/<project_id>/
├── metadata.json                # project record
├── images.json                  # image index (source of truth)
├── labels.json                  # label definitions, in order
├── annotations/annotations.json # every bounding box
└── images/                      # the uploaded files
```

Writes go through an atomic temp-file-and-replace helper, so an interrupted save can't leave a half-written file behind.

## API Overview

All responses use a consistent envelope: `{ success, message, data }` on success and `{ success, message, error }` on failure.

| Method   | Endpoint                                         | Purpose                 |
| -------- | ------------------------------------------------ | ----------------------- |
| `GET`    | `/health`                                        | Health check            |
| `POST`   | `/projects`                                      | Create a project        |
| `GET`    | `/projects`                                      | List projects           |
| `GET`    | `/projects/{pid}`                                | Get one project         |
| `DELETE` | `/projects/{pid}`                                | Delete a project        |
| `POST`   | `/projects/{pid}/images`                         | Upload images           |
| `GET`    | `/projects/{pid}/images`                         | List images             |
| `GET`    | `/projects/{pid}/images/{iid}/file`              | Serve an image          |
| `DELETE` | `/projects/{pid}/images/{iid}`                   | Delete an image         |
| `GET`    | `/projects/{pid}/labels`                         | List labels             |
| `POST`   | `/projects/{pid}/labels`                         | Create a label          |
| `DELETE` | `/projects/{pid}/labels/{lid}`                   | Delete an unused label  |
| `GET`    | `/projects/{pid}/images/{iid}/annotations`       | List boxes for an image |
| `POST`   | `/projects/{pid}/images/{iid}/annotations`       | Create a box            |
| `PUT`    | `/projects/{pid}/images/{iid}/annotations/{aid}` | Update a box            |
| `DELETE` | `/projects/{pid}/images/{iid}/annotations/{aid}` | Delete a box            |
| `GET`    | `/projects/{pid}/export/yolo`                    | Download the dataset    |

Deleting a label that annotations still reference returns `409` with the reference count, so boxes are never silently orphaned.

## Testing

```bash
cd backend
pip install pytest httpx
pytest
```

The suite runs against a temporary directory, so it never touches your real `uploads/` data. It covers the project/image/label/annotation lifecycle, persistence across restarts, and byte-level assertions on the YOLO export.

## Public Deployment

The same codebase can run as a zero-install public demo on **$0 free tiers**, without changing the local workflow. It splits across three services:

| Piece                   | Host                        | Role                                                     |
| ----------------------- | --------------------------- | -------------------------------------------------------- |
| Frontend (static SPA)   | **Cloudflare Pages**        | Serves the built React app at `https://<name>.pages.dev` |
| Backend (FastAPI)       | **Render** (free web tier)  | The REST API, run with `uvicorn`                         |
| Persistent data         | **Supabase Storage**        | JSON documents + uploaded image blobs                    |

**Why object storage instead of the server disk?** Render's free instance has only an *ephemeral* disk that is wiped on every restart and deploy. So in public mode, persistence is delegated to Supabase Storage through a small storage abstraction. The selection is made entirely by one environment variable:

- `STORAGE_BACKEND=local` (default) — JSON + images on the local filesystem. This is the self-hosted / v1.0.0 path and is completely unchanged.
- `STORAGE_BACKEND=cloud` — the same logical data model (Project / Image / Label / Annotation) stored as Supabase objects. Only this mode enables the abuse limits and cleanup described below.

### Backend environment variables (Render)

| Variable               | Required          | Purpose                                                        |
| ---------------------- | ----------------- | -------------------------------------------------------------- |
| `STORAGE_BACKEND`      | yes (`cloud`)     | Selects the cloud backend                                      |
| `SUPABASE_URL`         | yes               | Supabase project URL (e.g. `https://abc.supabase.co`)          |
| `SUPABASE_SERVICE_KEY` | yes (**secret**)  | `service_role` key — server-side only, never sent to browsers  |
| `SUPABASE_BUCKET`      | yes               | Storage bucket name (create it in the Supabase dashboard)      |
| `FRONTEND_ORIGIN`      | yes               | Your Pages URL, added to CORS (e.g. `https://x.pages.dev`)     |
| `MAINTENANCE_TOKEN`    | optional          | Shared secret enabling the cleanup endpoint (see below)        |
| `PROJECT_TTL_HOURS`    | optional (`30`)   | Lifetime of a public project in hours; `0` disables expiry     |
| `MAX_UPLOAD_BYTES` / `MAX_IMAGES_PER_PROJECT` / `MAX_PROJECT_BYTES` | optional | Abuse limits (sensible defaults) |

Secrets are read from the environment only — nothing sensitive is committed. `render.yaml` at the repo root declares the service (build with `pip install -r backend/requirements-prod.txt`, a slim runtime that omits the heavy unused AI libraries) and marks secret values as dashboard-entered.

### Frontend environment variable (Cloudflare Pages)

| Variable             | Purpose                                                  |
| -------------------- | -------------------------------------------------------- |
| `VITE_API_BASE_URL`  | Your Render backend URL (e.g. `https://x.onrender.com`)  |

Build command `npm run build`, output directory `dist`. SPA deep links are handled by `frontend/public/_redirects` (`/* /index.html 200`), which Cloudflare Pages copies to the site root.

### Deploy outline

1. **Supabase** — create a project and a private Storage bucket; copy the project URL and `service_role` key.
2. **Render** — new Web Service from this repo (it picks up `render.yaml`); set the backend env vars above.
3. **Cloudflare Pages** — connect the repo, set the frontend build settings and `VITE_API_BASE_URL`, deploy; then set `FRONTEND_ORIGIN` on Render to the resulting `*.pages.dev` URL.

### Anonymous, temporary, and self-limiting

Public projects have **no authentication** by design — they are anonymous and shared by link. To keep a free deployment sustainable, cloud mode enforces upload size, image-count, and per-project byte limits, and validates image content (not just the extension).

### ⏳ Public projects are temporary — 30 hours, then permanently deleted

> **This applies only to the public demo.** A self-hosted instance (`STORAGE_BACKEND` unset or `local`) never expires anything and never deletes your data.

Every project created on the public deployment is **permanently deleted exactly 30 hours after it was created**. This is deliberate: the demo runs entirely on free-tier infrastructure with a small shared storage quota, so it cannot host datasets indefinitely.

When a project expires, everything belonging to it is removed from Supabase Storage — the uploaded images, the annotations, the label definitions, the project metadata, and every generated index document. Nothing is archived, hidden, or recoverable; expiry is a real deletion, not a flag. Once the sweep has run there is no way to restore the project, and its link will return "not found".

**Export your YOLO dataset before the deadline.** The 30-hour clock starts at creation and cannot be extended, paused, or reset — reopening or editing a project does not buy more time. Each project card and the project page show the remaining lifetime (for example `Expires in 29h 42m`), and the indicator becomes more prominent as the deadline approaches. Use **Export YOLO** or **Export COCO** to download your dataset; the downloaded zip is yours permanently and is unaffected by expiry.

The deadline is enforced by the server, not the browser. The expiry timestamp is generated server-side at creation time (`expires_at = created_at + PROJECT_TTL_HOURS`), stored in the project metadata, and never accepted from a client — so a modified request or a wrong system clock cannot extend a project's life. Past the deadline the project stops being listed and every project-scoped endpoint (open, images, labels, annotations, export) responds `404`, whether or not the cleanup sweep has run yet.

**The public deployment is not intended for permanent dataset hosting.** For long-term work, run ForgoteLabeling locally as described in [Local Development](#local-development) — the local path stores everything on your own disk with no time limit.

Deletion itself is performed by a token-guarded sweep endpoint, intended for a free external cron:

```
POST /maintenance/cleanup     header: X-Maintenance-Token: <MAINTENANCE_TOKEN>
```

It is safe to call repeatedly and is idempotent: it deletes each expired project's objects under that project's own storage prefix only, removes `metadata.json` last so an interrupted run retries cleanly, and reports `{"checked", "deleted", "failed"}`. The endpoint returns `404` unless both `STORAGE_BACKEND=cloud` and `MAINTENANCE_TOKEN` are set, so a self-hosted instance never exposes it and never auto-deletes your data.

## Roadmap

Built and working today: the full manual annotation loop described above.

Under consideration:

- Pascal VOC export
- Zoom and pan in the editor
- Undo / redo
- Optional AI-assisted pre-labeling (the `/predict` endpoint is currently an honest `501` stub)

## V1.0.0

**v1.0.0 is the frozen stable baseline**: the local, self-hosted tool described in [Local Development](#local-development) — projects as plain folders, JSON + image files on your own disk, no database, no accounts, no network. That release is the reference behavior, and it stays intact.

The public deployment support (Cloudflare Pages + Render + Supabase, selected via `STORAGE_BACKEND=cloud`) is an **additive layer on top of v1.0.0**, not a rewrite of it. When `STORAGE_BACKEND` is unset or `local`, the code path, the on-disk layout, the API responses, and the YOLO export are all unchanged from v1.0.0 — the cloud abstraction and every abuse limit are inert. The regression suite runs entirely in local mode, so the baseline behavior is what the tests pin down.

## Contributing

Issues and pull requests are welcome. Please run the backend test suite before opening a PR, and keep changes focused — small, reviewable diffs get merged faster.

## License

Released under the [MIT License](LICENSE).

## Developer

Built by **Noyon Ahmed**.

[LinkedIn](https://bd.linkedin.com/in/noyonahmedml) · [Facebook](https://www.facebook.com/noyonahmedml) · [Repository](https://github.com/nayonahmedjoy/ForgoteLabeling)
