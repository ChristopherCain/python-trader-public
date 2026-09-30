import api, { request } from "./api";

export const getAnnotations = (projectId, imageId) =>
  request(api.get(`/projects/${projectId}/images/${imageId}/annotations`));

export const createAnnotation = (projectId, imageId, annotation) =>
  request(
    api.post(`/projects/${projectId}/images/${imageId}/annotations`, annotation)
  );

export const updateAnnotation = (projectId, imageId, annotationId, data) =>
  request(
    api.put(
      `/projects/${projectId}/images/${imageId}/annotations/${annotationId}`,
      data
    )
  );

export const deleteAnnotation = (projectId, imageId, annotationId) =>
  request(
    api.delete(
      `/projects/${projectId}/images/${imageId}/annotations/${annotationId}`
    )
  );
