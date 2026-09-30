import { Routes, Route } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import Project from "./pages/Project";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/project/:id" element={<Project />} />
    </Routes>
  );
}

export default App;