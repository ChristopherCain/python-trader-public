/**
 * "About ForgoteLabeling" footer — repo and developer links.
 *
 * Rendered at the bottom of the dashboard. Kept deliberately compact: a
 * hairline rule on the page background rather than a filled panel, so it
 * reads as the end of the page instead of a separate block. Inline SVG marks
 * keep it dependency-free (no icon package) and let the glyphs inherit the
 * current text color.
 */

const REPO_URL = "https://github.com/nayonahmedjoy/ForgoteLabeling";
const LINKEDIN_URL = "https://bd.linkedin.com/in/noyonahmedml";
const FACEBOOK_URL = "https://www.facebook.com/noyonahmedml";

function GitHubIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

function LinkedInIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M3.6 5.9H.9V16h2.7V5.9ZM2.25 1.2a1.57 1.57 0 1 0 0 3.13 1.57 1.57 0 0 0 0-3.13ZM16 10.4c0-2.9-1.55-4.25-3.62-4.25-1.67 0-2.42.92-2.84 1.56V5.9H6.84c.04.76 0 10.1 0 10.1h2.7v-5.64c0-.24.02-.49.09-.66.19-.49.63-.99 1.38-.99.97 0 1.36.74 1.36 1.83V16H16v-5.6Z" />
    </svg>
  );
}

function FacebookIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M16 8.05a8 8 0 1 0-9.25 7.9v-5.59H4.72V8.05h2.03V6.3c0-2 1.2-3.11 3.02-3.11.87 0 1.79.16 1.79.16v1.97h-1.01c-.99 0-1.3.62-1.3 1.25v1.5h2.22l-.36 2.31H9.25v5.59A8 8 0 0 0 16 8.05Z" />
    </svg>
  );
}

export default function AboutSection() {
  return (
    <footer className="about">
      <div className="about-inner">
        <div className="about-col intro">
          <h2>About ForgoteLabeling</h2>
          <p>
            A lightweight tool for annotating images and exporting YOLO
            datasets. Everything is stored locally as plain files you own.
          </p>
        </div>

        <div className="about-groups">
          <div className="about-col">
            <span className="about-label">Source</span>
            <div className="about-links">
              <a
                className="about-btn"
                href={REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
              >
                <GitHubIcon />
                GitHub Repo
              </a>
            </div>
          </div>

          <div className="about-col">
            <span className="about-label">Developer</span>
            <div className="about-links">
              <a
                className="about-btn"
                href={LINKEDIN_URL}
                target="_blank"
                rel="noopener noreferrer"
              >
                <LinkedInIcon />
                LinkedIn
              </a>
              <a
                className="about-btn"
                href={FACEBOOK_URL}
                target="_blank"
                rel="noopener noreferrer"
              >
                <FacebookIcon />
                Facebook
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="about-bottom">
        <span>ForgoteLabeling — annotate images, export datasets.</span>
        <span>MIT Licensed</span>
      </div>
    </footer>
  );
}
