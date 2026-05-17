import { Link, Route, Routes } from "react-router-dom";
import ProjectsList from "./pages/ProjectsList";
import AddProject from "./pages/AddProject";
import ProjectDetail from "./pages/ProjectDetail";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="brand">
          <span className="brand-mark">📘</span> Code Wiki
        </Link>
        <nav>
          <Link to="/new">+ New project</Link>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<ProjectsList />} />
          <Route path="/new" element={<AddProject />} />
          <Route path="/projects/:id/*" element={<ProjectDetail />} />
        </Routes>
      </main>
    </div>
  );
}
