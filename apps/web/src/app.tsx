import { NavLink, Route, Routes } from "react-router-dom";
import { LandingPage } from "./pages/landing-page";
import { RegisterPage } from "./pages/register-page";
import { AuthenticatePage } from "./pages/authenticate-page";
import { AdminPage } from "./pages/admin-page";
import { ProfilePage } from "./pages/profile-page";
import { HelpPage } from "./pages/help-page";

const navigation = [
  { to: "/", label: "Overview" },
  { to: "/register", label: "Register" },
  { to: "/authenticate", label: "Authenticate" },
  { to: "/admin", label: "Admin" },
  { to: "/profile", label: "Profile" },
  { to: "/help", label: "Help" }
];

export function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brandmark">
          <span className="brandmark__glyph">DS</span>
          <span>
            <strong>DeepShield Guardian</strong>
            <small>Deepfake-resistant face authentication</small>
          </span>
        </NavLink>

        <nav className="topbar__nav">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              className={({ isActive }) => (isActive ? "nav-pill nav-pill--active" : "nav-pill")}
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="page-shell">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/authenticate" element={<AuthenticatePage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/help" element={<HelpPage />} />
        </Routes>
      </main>
    </div>
  );
}

