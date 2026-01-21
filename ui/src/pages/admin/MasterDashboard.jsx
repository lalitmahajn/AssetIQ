import { useState } from "react";
import { getRoles } from "../../api";
import PLCConfiguration from "../PLCConfiguration";
import AssetManager from "./AssetManager";
import AuditLogViewer from "./AuditLogViewer";
import MastersManager from "./MastersManager";
import StationConfig from "./StationConfig";
import SuggestionsReview from "./SuggestionsReview";
import UserList from "./UserList";

export default function MasterDashboard() {
    const roles = getRoles();
    const isAdmin = roles.includes("admin");
    const isSupervisor = roles.includes("supervisor");

    // Define tabs with permissions
    const allTabs = [
        { id: "users", label: "User Management", allowed: isAdmin },
        { id: "assets", label: "Asset Hierarchy", allowed: true },
        { id: "masters", label: "Dynamic Masters", allowed: isAdmin || isSupervisor },
        { id: "learning", label: "Self-Learning", allowed: isAdmin || isSupervisor },
        { id: "audit", label: "Audit Logs", allowed: isAdmin },
        { id: "stations", label: "Station Config", allowed: isAdmin },
        { id: "plc", label: "PLC Configuration", allowed: isAdmin },
    ];

    const visibleTabs = allTabs.filter(t => t.allowed);
    const [tab, setTab] = useState(visibleTabs[0]?.id || "");

    if (visibleTabs.length === 0) {
        return (
            <div className="p-10 text-center">
                <h2 className="text-xl font-bold text-red-600">Access Denied</h2>
                <p className="text-gray-500">You do not have permission to view this area.</p>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-800">Master Management</h2>
                <p className="text-gray-500">Configure global settings, users, and standard lists.</p>
            </div>

            <div className="flex border-b mb-6 overflow-x-auto">
                {visibleTabs.map(t => (
                    <button
                        key={t.id}
                        onClick={() => setTab(t.id)}
                        className={`px-6 py-3 font-medium text-sm transition-colors border-b-2 whitespace-nowrap ${tab === t.id ? "border-blue-600 text-blue-600 bg-blue-50" : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50"}`}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            <div className="min-h-[400px]">
                {tab === "users" && <UserList />}
                {tab === "assets" && <AssetManager />}
                {tab === "masters" && <MastersManager />}
                {tab === "learning" && <SuggestionsReview />}
                {tab === "audit" && <AuditLogViewer />}
                {tab === "audit" && <AuditLogViewer />}
                {tab === "stations" && <StationConfig />}
                {tab === "plc" && <PLCConfiguration />}
            </div>
        </div>
    );
}
