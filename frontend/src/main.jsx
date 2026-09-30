import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

// Global styles. Vite only applies CSS that is imported from JS (or linked in
// index.html) — without this import index.css never loads, so the overlay
// rules (.bbox-image pointer-events:none, .bbox-canvas absolute/crosshair)
// don't apply: the <img> stays draggable (ghost) and the canvas isn't on top.
import "./index.css";

import App from "./App";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);