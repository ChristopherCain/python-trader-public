import api, { request } from "./api";

export const getProjects = () => request(api.get("/projects"));

export const getProject = (id) => request(api.get(`/projects/${id}`));

export const createProject = (name) =>
  request(api.post("/projects", { name }));

export const updateProject = (id, data) =>
  request(api.put(`/projects/${id}`, data));

export const deleteProject = (id) => request(api.delete(`/projects/${id}`));
