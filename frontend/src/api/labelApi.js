import api, { request } from "./api";

export const getLabels = (projectId) =>
  request(api.get(`/projects/${projectId}/labels`));

export const createLabel = (projectId, name, color) =>
  request(api.post(`/projects/${projectId}/labels`, { name, color }));

export const updateLabel = (projectId, labelId, data) =>
  request(api.put(`/projects/${projectId}/labels/${labelId}`, data));

export const deleteLabel = (projectId, labelId) =>
  request(api.delete(`/projects/${projectId}/labels/${labelId}`));
