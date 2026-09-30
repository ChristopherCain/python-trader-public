# ForgoteLabeling API Specification

> REST API contract.

---

# Base URL

/api/v1

---

# Response Format

Every endpoint returns the same structure.

Success

{
    "success": true,
    "message": "",
    "data": {}
}

Error

{
    "success": false,
    "message": "",
    "error": {}
}

---

# Project Endpoints

Create Project

POST

/projects

---

List Projects

GET

/projects

---

Get Project

GET

/projects/{project_id}

---

Delete Project

DELETE

/projects/{project_id}

---

# Upload Endpoints

Upload Images

POST

/upload

Supported

- Image
- Multiple Images
- Folder
- ZIP

---

List Uploaded Images

GET

/projects/{project_id}/images

---

Delete Image

DELETE

/projects/{project_id}/images/{image_id}

---

# AI Endpoints

Run Auto Annotation

POST

/projects/{project_id}/predict

---

# Annotation Endpoints

Get Annotation

GET

/annotations/{image_id}

---

Update Annotation

PUT

/annotations/{image_id}

---

Delete Annotation

DELETE

/annotations/{image_id}

---

# Label Endpoints

Create Label

POST

/labels

---

List Labels

GET

/labels

---

Delete Label

DELETE

/labels/{label_id}

---

# Export Endpoints

Export YOLO

POST

/export/yolo

---

Export COCO

POST

/export/coco

Future Version

---

Export Pascal VOC

POST

/export/voc

Future Version

---

# Health Endpoints

Health Check

GET

/health

---

Version

GET

/version