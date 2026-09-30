import api, { request, API_BASE } from "./api";

export const getImages = (projectId) =>
  request(api.get(`/projects/${projectId}/images`));

export const uploadImages = (projectId, files, onProgress) => {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  return request(
    api.post(`/projects/${projectId}/images`, form, {
      // Do not set Content-Type manually. Axios/the browser must set
      // "multipart/form-data; boundary=..." itself; a hand-set header omits
      // the boundary and FastAPI then fails to parse the upload body.
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    })
  );
};

export const deleteImage = (projectId, imageId) =>
  request(api.delete(`/projects/${projectId}/images/${imageId}`));

// Direct URL to the raw image file (used as <img src>).
export const imageFileUrl = (projectId, imageId) =>
  `${API_BASE}/projects/${projectId}/images/${imageId}/file`;
