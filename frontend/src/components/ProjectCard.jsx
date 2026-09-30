import { useNavigate } from "react-router-dom";

import ExpiryBadge from "./ExpiryBadge";

function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function ProjectCard({ project, onDelete, onExpire }) {
  const navigate = useNavigate();

  return (
    <div className="card">
      <div className="card-head">
        <h3>{project.name || "Untitled Project"}</h3>
        <span className="badge">{project.status || "active"}</span>
      </div>

      <div className="stats">
        <span>{project.images ?? 0} images</span>
        <span>{project.annotations ?? 0} boxes</span>
      </div>

      <div className="created">
        <span className="created-date">
          Created {formatDate(project.created_at)}
        </span>
        {/* Renders nothing unless the server gave this project a deadline,
            so self-hosted cards look exactly as they did in v1.0.0. */}
        <ExpiryBadge seconds={project.seconds_remaining} onExpire={onExpire} />
      </div>

      <div className="card-actions">
        <button
          className="primary small"
          onClick={() => navigate(`/project/${project.id}`)}
        >
          Open Project
        </button>
        <button
          className="danger-ghost small"
          onClick={() => onDelete(project)}
          title="Delete project"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
