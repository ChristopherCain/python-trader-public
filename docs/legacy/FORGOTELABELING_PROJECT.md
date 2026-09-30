# ForgoteLabeling

> AI-powered dataset annotation platform for Computer Vision.

---

# Vision

ForgoteLabeling aims to make dataset annotation fast, simple and accessible for everyone.

Instead of manually labeling thousands of images, users can upload their images, let AI generate annotations automatically, review the predictions, make corrections, and export the dataset in popular formats.

The project is designed to be lightweight, free to use, and deployable on free hosting services.

---

# Primary Goal

Provide an open-source annotation platform that anyone can use directly from a web browser.

---

# Target Users

- Machine Learning Engineers
- Data Scientists
- Kaggle Users
- Researchers
- Students
- AI Startups

---

# Core Workflow

Create Project

↓

Upload Images / Folder / ZIP

↓

AI Auto Annotation

↓

Manual Review

↓

Save Progress

↓

Export Dataset

↓

Project Automatically Removed After Expiration

---

# Supported Upload Methods

✅ Individual Images

- jpg
- jpeg
- png
- bmp
- webp

---

✅ Multiple Images

Drag & Drop

---

✅ Folder Upload

Entire image folder

---

✅ ZIP Upload

Automatic extraction

---

# AI Model

Default Model

YOLOv8n

Reason

- Small
- Fast
- Stable
- Works well on CPU
- Hugging Face friendly
- Excellent balance between speed and accuracy

Inference Device

- CPU (default)
- GPU (if available)

Confidence Threshold

User configurable

IoU Threshold

User configurable

---

# Annotation Type

Phase 1

✅ Bounding Box

Future

- Polygon
- Segmentation
- Keypoints

---

# Supported Export Formats

Phase 1

- YOLO

Phase 2

- COCO
- Pascal VOC

Phase 3

- CSV
- JSON

---

# Storage Policy

No permanent storage.

Projects are temporary.

Workflow

Upload

↓

Process

↓

Edit

↓

Export

↓

Automatic deletion after expiration.

---

# Hosting

Frontend

Cloudflare Pages

Backend

FastAPI

AI Model

Hugging Face Spaces

Database

SQLite

Storage

Temporary Local Storage

---

# UI Goals

- Fast
- Minimal
- Responsive
- Dark Mode
- Keyboard Friendly

---

# Phase 1 Features

Project Management

Image Upload

Folder Upload

ZIP Upload

YOLO Auto Annotation

Bounding Box Editor

Label Management

YOLO Export

Temporary Project Saving

---

# Future Features

Polygon Annotation

Segmentation

Dataset Statistics

Dataset Health Report

Duplicate Image Detection

Blur Detection

Class Distribution

Model Training

Team Collaboration

Authentication

Cloud Storage

---

# Deployment Philosophy

Everything should remain deployable using free hosting whenever possible.

No feature should introduce unnecessary infrastructure costs.

---

# Tech Stack

Frontend

React

Backend

FastAPI

AI

YOLOv8

Database

SQLite

Deployment

Cloudflare Pages

Hugging Face Spaces

Version Control

Git + GitHub