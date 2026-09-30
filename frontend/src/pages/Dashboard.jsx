import { useEffect, useState } from "react";

import Navbar from "../components/Navbar";
import ProjectCard from "../components/ProjectCard";
import CreateProjectModal from "../components/CreateProjectModal";
import ConfirmDialog from "../components/ConfirmDialog";
import AboutSection from "../components/AboutSection";
import {
  getProjects,
  createProject,
  deleteProject,
} from "../api/projectApi";
import { getConfig } from "../api/configApi";

export default function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  // The project awaiting delete confirmation (null = dialog closed).
  const [pendingDelete, setPendingDelete] = useState(null);
  // Deployment mode, asked of the backend: on the public deployment projects
  // are temporary, self-hosted they are permanent. Defaults to "permanent" so a
  // failed/older /config call never invents a warning that isn't true.
  const [config, setConfig] = useState({
    temporary_projects: false,
    project_ttl_hours: null,
  });

  useEffect(() => {
    loadProjects();
    // Config failure is non-fatal: the app works, it just shows no TTL notice.
    getConfig()
      .then((data) => {
        if (data && typeof data === "object") setConfig(data);
      })
      .catch(() => {});
  }, []);

  async function loadProjects() {
    setLoading(true);
    setError("");
    try {
      const data = await getProjects();
      setProjects(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Failed to load projects.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(name) {
    const project = await createProject(name);
    // Optimistically prepend, then refresh from server for accurate counts.
    setProjects((prev) => [project, ...prev]);
  }

  async function handleDelete(project) {
    // Opens the in-app confirmation; the actual delete runs in confirmDelete.
    setPendingDelete(project);
  }

  async function confirmDelete() {
    const project = pendingDelete;
    if (!project) return;
    try {
      await deleteProject(project.id);
      setProjects((prev) => prev.filter((p) => p.id !== project.id));
      setPendingDelete(null);
    } catch (err) {
      setError(err.message || "Failed to delete project.");
      setPendingDelete(null);
    }
  }

  return (
    <>
      <Navbar
        contained
        right={
          <button className="primary" onClick={() => setShowModal(true)}>
            + Create Project
          </button>
        }
      />

      <div className="page">
        <div className="page-head">
          <div className="titles">
            <h1>Projects</h1>
            {!loading && !error && projects.length > 0 ? (
              <span className="page-sub">
                {projects.length} {projects.length === 1 ? "project" : "projects"}
              </span>
            ) : null}
          </div>
        </div>
        {loading ? (
          <div className="state">
            <span className="spin" /> Loading projects…
          </div>
        ) : error ? (
          <div className="state error">
            {error}
            <div style={{ marginTop: 12 }}>
              <button onClick={loadProjects}>Retry</button>
            </div>
          </div>
        ) : projects.length === 0 ? (
          <div className="empty">
            <h2>No projects yet.</h2>
            <p>Create your first dataset annotation project.</p>
            <button className="primary" onClick={() => setShowModal(true)}>
              + Create Project
            </button>
          </div>
        ) : (
          <div className="project-grid">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onDelete={handleDelete}
                // A finished countdown proves nothing on its own — re-ask the
                // server, which is the only authority on what still exists.
                onExpire={loadProjects}
              />
            ))}
          </div>
        )}
      </div>

      {showModal ? (
        <CreateProjectModal
          onClose={() => setShowModal(false)}
          onCreate={handleCreate}
          temporary={!!config.temporary_projects}
          ttlHours={config.project_ttl_hours}
        />
      ) : null}

      {pendingDelete ? (
        <ConfirmDialog
          title="Delete project"
          message="This will permanently remove"
          highlight={`“${pendingDelete.name || "Untitled Project"}”`}
          note="along with its images and annotations. This cannot be undone."
          confirmText="Delete project"
          onConfirm={confirmDelete}
          onCancel={() => setPendingDelete(null)}
        />
      ) : null}

      <AboutSection />
    </>
  );
}
