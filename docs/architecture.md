# ForgoteLabeling Architecture

> System architecture and technical design document.

---

# Overview

ForgoteLabeling is an AI-powered dataset annotation platform for Computer Vision.

The platform allows users to upload images, folders, or ZIP archives, automatically generate object detection annotations using YOLOv8, manually review the predictions, and export the final dataset in standard annotation formats.

The system is designed around a simple service-oriented architecture that is lightweight, modular, and deployable on free cloud platforms.

---

# Design Principles

- Keep everything simple.
- Avoid unnecessary dependencies.
- Keep the backend modular.
- Separate business logic from API routes.
- Temporary project storage only.
- Free deployment should always remain possible.

---

# High-Level Architecture

User

↓

React Frontend

↓

FastAPI Backend

↓

Services Layer

↓

YOLOv8 + SQLite + File Storage

---

# Component Overview

## Frontend

Responsible for

- User Interface
- Image Viewer
- Annotation Editor
- Project Management
- Export Requests

---

## Backend

Responsible for

- REST API
- File Upload
- Project Management
- Annotation Management
- Export Pipeline

---

## AI Module

Responsible for

- Loading YOLOv8
- Running inference
- Returning bounding boxes

The AI module should never communicate directly with the frontend.

---

## Database

SQLite stores only metadata.

It does NOT store images.

Examples

- Project information
- Image metadata
- Labels
- Bounding boxes

---

## File Storage

Images remain inside the project workspace.

Example

uploads/

    project_id/

        image1.jpg

        image2.jpg

Projects are temporary.

---

# Project Lifecycle

Create Project

↓

Upload Images

↓

Generate Predictions

↓

Manual Review

↓

Export Dataset

↓

Delete Project

---

# Data Flow

User

↓

Frontend

↓

Backend API

↓

Upload Service

↓

AI Service

↓

Annotation Service

↓

Export Service

↓

Response

---

# Core Modules

Project Service

Responsible for creating and managing projects.

---

Upload Service

Responsible for validating uploads.

Supported

- Image
- Folder
- ZIP

---

AI Service

Responsible for YOLO inference.

Input

Images

Output

Bounding Boxes

---

Annotation Service

Responsible for

- Create
- Update
- Delete
- Review

annotations.

---

Export Service

Responsible for generating

- YOLO
- COCO
- Pascal VOC

datasets.

---

# Database Entities

Project

Stores project information.

Image

Stores image metadata.

Label

Stores class names.

Annotation

Stores bounding boxes.

---

# Temporary Storage Policy

Projects are stored only while users are working.

Expired projects should be removed automatically.

No permanent storage.

---

# Future Expansion

Future versions may include

- Segmentation
- Polygon Annotation
- Team Collaboration
- Authentication
- Cloud Storage
- Custom YOLO Models