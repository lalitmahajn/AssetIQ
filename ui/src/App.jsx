import { lazy, Suspense, useEffect, useState } from "react";
import { Routes, Route, Navigate, NavLink, useLocation, useNavigate } from "react-router-dom";
import { apiGet, getToken, parseJwt } from "./api";
import Login from "./pages/Login";
import ProtectedRoute from "./components/ProtectedRoute";

// Lazy load heavy page components
const Assets = lazy(() => import("./pages/Assets"));
const Insights = lazy(() => import("./pages/Insights"));
const Reports = lazy(() => import("./pages/Reports"));
const StopQueue = lazy(() => import("./pages/StopQueue"));
const Tickets = lazy(() => import("./pages/Tickets"));
const MasterDashboard = lazy(() => import("./pages/admin/MasterDashboard"));
const StopPopup = lazy(() => import("./pages/StopPopup"));

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [config, setConfig] = useState({
    plantName: "Loading...",
    stopQueueVisible: true,
    autoLogoutMinutes: 30
  });
  const location = useLocation();
  const navigate = useNavigate();

  // Derive roles from token for display
  const token = getToken();
  let userRoles = [];
  if (token) {
    const payload = parseJwt(token);
    if (payload && payload.roles) {
      userRoles = typeof payload.roles === 'string' ? payload.roles.split(',') : payload.roles;
    }
  }

  function handleLogout() {
    localStorage.removeItem("token");
    setAuthed(false);
    navigate("/login");
  }

  async function fetchConfig() {
    try {
      const data = await apiGet("/master/config");
      setConfig(prev => ({ ...prev, ...data }));
    } catch (e) {
      console.error("Failed to fetch config", e);
    }
  }

  useEffect(() => {
    async function fetchSiteCode() {
      try {
        const data = await apiGet("/readyz");
        if (data && data.plant_display_name) {
          document.title = `${data.plant_display_name} | AssetIQ`;
          setConfig(prev => ({ ...prev, plantName: data.plant_display_name }));
        }
      } catch (e) {
        console.error("Failed to fetch site code", e);
      }
    }
    fetchSiteCode();

    if (authed) {
      fetchConfig();
    }

    const onAuthError = () => handleLogout();
    const onConfigUpdated = () => fetchConfig();

    window.addEventListener("auth:error", onAuthError);
    window.addEventListener("config:updated", onConfigUpdated);

    return () => {
      window.removeEventListener("auth:error", onAuthError);
      window.removeEventListener("config:updated", onConfigUpdated);
    };
  }, [authed]);

  // AUTO-LOGOUT LOGIC
  useEffect(() => {
    if (!authed) return;

    let timer;
    const resetTimer = () => {
      clearTimeout(timer);
      const ms = (config.autoLogoutMinutes || 30) * 60 * 1000;
      timer = setTimeout(() => {
        alert("You have been logged out due to inactivity.");
        handleLogout();
      }, ms);
    };

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    events.forEach(name => window.addEventListener(name, resetTimer));
    resetTimer();

    return () => {
      clearTimeout(timer);
      events.forEach(name => window.removeEventListener(name, resetTimer));
    };
  }, [authed, config.autoLogoutMinutes]);

  const navItemClass = ({ isActive }) =>
    `rounded-md px-3 py-1 text-sm font-medium transition-colors ${isActive ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100"}`;

  const navReportClass = ({ isActive }) =>
    `rounded-md px-3 py-1 text-sm font-medium transition-colors ${isActive ? "bg-green-100 text-green-700" : "text-gray-600 hover:bg-gray-100"}`;

  const navAdminClass = ({ isActive }) =>
    `rounded-md px-3 py-1 text-sm font-medium transition-colors ${isActive ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-gray-100"}`;

  // If not authed and not on login page, redirect to login
  if (location.pathname === "/login") {
    if (authed) return <Navigate to="/" replace />;
    return <Login onLoggedIn={() => setAuthed(true)} />;
  }

  // Layout for authenticated users
  return (
    <div className="min-h-screen bg-gray-50 font-sans text-gray-900">
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex items-center">
          <div className="mr-8 flex flex-col">
            <h1 className="text-lg font-black text-blue-600 leading-none">AssetIQ</h1>
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">{config.plantName || "Plant"}</span>
          </div>
          <div className="flex space-x-4">
            {config.stopQueueVisible !== false && (
              <NavLink to="/stops" className={navItemClass}>
                Stop Queue
              </NavLink>
            )}
            <NavLink to="/tickets" className={navItemClass}>
              Tickets
            </NavLink>
            <NavLink to="/reports" className={navReportClass}>
              Reports
            </NavLink>
            <NavLink to="/assets" className={navItemClass}>
              Assets
            </NavLink>
            <NavLink to="/insights" className={navItemClass}>
              Insights
            </NavLink>
            <NavLink to="/admin" className={navAdminClass}>
              Admin
            </NavLink>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {userRoles.length > 0 && (
            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded font-medium border border-gray-200">
              {userRoles.map(r => r.toUpperCase()).join(" / ")}
            </span>
          )}
          <button
            onClick={handleLogout}
            className="text-sm text-gray-500 hover:text-red-600 transition-colors"
          >
            Logout
          </button>
        </div>
      </div>

      <div className="p-4">
        <Suspense fallback={<div className="p-20 text-center text-gray-400">Loading module...</div>}>
          <Routes>
            <Route path="/" element={<Navigate to="/stops" replace />} />

            <Route path="/stops" element={
              <ProtectedRoute><StopQueue /></ProtectedRoute>
            } />

            <Route path="/tickets" element={
              <ProtectedRoute><Tickets plantName={config.plantName} /></ProtectedRoute>
            } />

            <Route path="/reports" element={
              <ProtectedRoute><Reports /></ProtectedRoute>
            } />

            <Route path="/assets" element={
              <ProtectedRoute><Assets /></ProtectedRoute>
            } />

            <Route path="/insights" element={
              <ProtectedRoute><Insights plantName={config.plantName} /></ProtectedRoute>
            } />

            <Route path="/admin/*" element={
              <ProtectedRoute><MasterDashboard /></ProtectedRoute>
            } />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </div>

      <Suspense fallback={null}>
        <StopPopup />
      </Suspense>
    </div>
  );
}
