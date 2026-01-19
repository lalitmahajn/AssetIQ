import { lazy, Suspense, useEffect, useState } from "react";
import { apiGet, getToken, parseJwt } from "./api";
import Login from "./pages/Login";

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
  const [tab, setTab] = useState(() => localStorage.getItem("activeTab") || "stops");
  const [config, setConfig] = useState({ stopQueueVisible: true, autoLogoutMinutes: 30 });

  useEffect(() => {
    localStorage.setItem("activeTab", tab);
  }, [tab]);

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
  }

  async function fetchConfig() {
    try {
      const data = await apiGet("/master/config");
      setConfig(data);
      // If we are on stops tab but it's now hidden, move to tickets
      if (data.stopQueueVisible === false && tab === "stops") {
        setTab("tickets");
      }
    } catch (e) {
      console.error("Failed to fetch config", e);
    }
  }

  useEffect(() => {
    async function fetchSiteCode() {
      try {
        const data = await apiGet("/readyz");
        if (data && data.site_code) {
          document.title = `AssetIQ - ${data.site_code}`;
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

  if (!authed) return <Login onLoggedIn={() => setAuthed(true)} />;
  return (
    <div className="min-h-screen bg-gray-50 font-sans text-gray-900">
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex items-center">
          <h1 className="mr-8 text-lg font-bold text-blue-600">AssetIQ</h1>
          <div className="flex space-x-4">
            {config.stopQueueVisible !== false && (
              <button
                onClick={() => setTab("stops")}
                className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${tab === "stops" ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100"}`}
              >
                Stop Queue
              </button>
            )}
            <button
              onClick={() => setTab("tickets")}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${tab === "tickets" ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100"}`}
            >
              Tickets
            </button>
            <button
              onClick={() => setTab("reports")}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${tab === "reports" ? "bg-green-100 text-green-700" : "text-gray-600 hover:bg-gray-100"}`}
            >
              Reports
            </button>
            <button
              onClick={() => setTab("assets")}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${tab === "assets" ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100"}`}
            >
              Assets
            </button>
            <button
              onClick={() => setTab("insights")}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${tab === "insights" ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100"}`}
            >
              Insights
            </button>
            <button
              onClick={() => setTab("admin")}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${tab === "admin" ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-gray-100"}`}
            >
              Admin
            </button>
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
          {tab === "stops" && <StopQueue />}
          {tab === "tickets" && <Tickets />}
          {tab === "reports" && <Reports />}
          {tab === "assets" && <Assets />}
          {tab === "insights" && <Insights />}
          {tab === "admin" && <MasterDashboard />}
        </Suspense>
      </div>
      <Suspense fallback={null}>
        <StopPopup />
      </Suspense>
    </div>
  );
}
