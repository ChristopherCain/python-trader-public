import { Link } from "react-router-dom";

/**
 * Top navigation bar. `crumb` optionally shows the current context
 * (e.g. a project name) to the right of the brand.
 *
 * `contained` caps the bar's contents to the shared content column so the
 * brand lines up with the page heading below it. The annotation workspace
 * leaves it off, since its three panels run edge to edge.
 */
export default function Navbar({ crumb, right, contained = false }) {
  return (
    <nav className={"app-navbar" + (contained ? " contained" : "")}>
      <div className="nav-inner">
        <Link to="/" className="brand">
          ForgoteLabeling
        </Link>
        {crumb ? <span className="crumb">/ {crumb}</span> : null}
        <span className="spacer" />
        {right}
      </div>
    </nav>
  );
}
