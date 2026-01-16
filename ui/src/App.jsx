import React, { useState, useEffect } from "react";
import Login from "./pages/Login";
import StopQueue from "./pages/StopQueue";
import Tickets from "./pages/Tickets";
import Insights from "./pages/Insights";
import Reports from "./pages/Reports";
import Assets from "./pages/Assets";
import StopPopup from "./pages/StopPopup";
import MasterDashboard from "./pages/admin/MasterDashboard";
import { getToken, parseJwt, apiGet } from "./api";

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [tab, setTab] = useState("stops");

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

    function onAuthError() {
      handleLogout();
    }
    window.addEventListener("auth:error", onAuthError);
    return () => window.removeEventListener("auth:error", onAuthError);
  }, []);

  if (!authed) return <Login onLoggedIn={() => setAuthed(true)} />;
  return (
    <div className="min-h-screen bg-gray-50 font-sans text-gray-900">
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex items-center">
          <h1 className="mr-8 text-lg font-bold text-blue-600">AssetIQ</h1>
          <div className="flex space-x-4">
            <button
              onClick={() => setTab("stops")}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${tab === "stops" ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100"}`}
            >
              Stop Queue
            </button>
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
        {tab === "stops" && <StopQueue />}
        {tab === "tickets" && <Tickets />}
        {tab === "reports" && <Reports />}
        {tab === "assets" && <Assets />}
        {tab === "insights" && <Insights />}
        {tab === "admin" && <MasterDashboard />}
      </div>
      <StopPopup />
    </div>
  );
}
