import React, { useState, useEffect } from "react";
import { apiGet, apiPost } from "../../api";

export default function SuggestionsReview() {
    const [suggestions, setSuggestions] = useState([]);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState("STOP_REASON"); // STOP_REASON | DEPARTMENT

    const TABS = [
        { id: "STOP_REASON", label: "Stop Reasons", desc: "For machine stops" },
        { id: "RESOLUTION_REASON", label: "Resolution Reasons", desc: "For ticket closure" },
        { id: "DEPARTMENT", label: "Departments", desc: "For ticket assignment" },
    ];

    // Modal State
    const [showModal, setShowModal] = useState(false);
    const [targetId, setTargetId] = useState(null);
    const [newName, setNewName] = useState("");
    const [newCode, setNewCode] = useState("");
    const [isCodeManual, setIsCodeManual] = useState(false);

    useEffect(() => {
        loadSuggestions();
    }, [activeTab]);

    async function loadSuggestions() {
        setLoading(true);
        try {
            const res = await apiGet(`/suggestions/list?status=pending&type_code=${activeTab}`);
            setSuggestions(res || []);
        } finally {
            setLoading(false);
        }
    }

    function openApproveModal(s) {
        setTargetId(s.id);
        const name = s.suggested_name;
        setNewName(name);
        // Clean initial code guess
        setNewCode(name.toUpperCase().replace(/\s+/g, "_").replace(/[^A-Z0-9_]/g, ""));
        setIsCodeManual(false);
        setShowModal(true);
    }

    async function handleConfirmApprove() {
        if (!targetId || !newCode) return;
        try {
            await apiPost("/suggestions/approve", {
                suggestion_id: targetId,
                item_code: newCode
            });
            setShowModal(false);
            loadSuggestions();
        } catch (err) {
            alert("Error approving suggestion: " + err.message);
        }
    }

    return (
        <div className="max-w-6xl mx-auto">
            {/* APPROVE MODAL */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4">
                        <h3 className="text-lg font-bold text-gray-900 mb-4">
                            Approve Suggestion
                        </h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Option Name *</label>
                                <input
                                    autoFocus
                                    className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="Enter option name..."
                                    value={newName}
                                    onChange={e => {
                                        const val = e.target.value;
                                        setNewName(val);
                                        if (!isCodeManual) {
                                            setNewCode(val.toUpperCase().replace(/\s+/g, "_").replace(/[^A-Z0-9_]/g, ""));
                                        }
                                    }}
                                    onKeyDown={e => { if (e.key === "Enter") handleConfirmApprove(); }}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Code (auto-generated)</label>
                                <input
                                    className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm font-mono bg-gray-50"
                                    placeholder="AUTO_GENERATED"
                                    value={newCode}
                                    onChange={e => {
                                        setNewCode(e.target.value.toUpperCase().replace(/\s+/g, "_"));
                                        setIsCodeManual(true);
                                    }}
                                />
                            </div>
                        </div>
                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => setShowModal(false)}
                                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleConfirmApprove}
                                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
                            >
                                Approve Option
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <div className="mb-8">
                <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Self-Learning Review</h2>
                <p className="text-gray-500 text-sm mt-1">Review and promote new options discovered from user input.</p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
                {/* SIDEBAR TABS */}
                <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm h-fit">
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Review Types</h3>
                    <div className="space-y-1">
                        {TABS.map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === tab.id
                                    ? "bg-blue-50 text-blue-700 ring-1 ring-blue-100"
                                    : "text-gray-600 hover:bg-gray-50"
                                    }`}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* CONTENT AREA */}
                <div className="md:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden min-h-[400px]">
                    <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
                        <h3 className="font-bold text-gray-700 text-sm">
                            Pending <span className="text-blue-600 font-mono">{TABS.find(t => t.id === activeTab)?.label}</span>
                        </h3>
                        <button onClick={loadSuggestions} className="text-xs text-blue-600 hover:underline font-semibold">Refresh</button>
                    </div>

                    {loading ? (
                        <div className="p-12 text-center text-gray-300 animate-pulse">Loading suggestions...</div>
                    ) : (
                        <table className="w-full text-left">
                            <thead>
                                <tr className="bg-gray-50/50 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                    <th className="px-4 py-3">Suggested Option</th>
                                    <th className="px-4 py-3">Frequency</th>
                                    <th className="px-4 py-3 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {suggestions.map(s => (
                                    <tr key={s.id} className="hover:bg-gray-50 transition-colors group">
                                        <td className="px-4 py-3">
                                            <div className="font-medium text-gray-800 text-sm">{s.suggested_name}</div>
                                            <div className="text-[10px] text-gray-400 uppercase tracking-wider font-mono mt-0.5">Status: {s.status}</div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${s.count >= s.threshold ? "bg-green-50 text-green-700 ring-1 ring-green-600/20" : "bg-gray-100 text-gray-600"}`}>
                                                {s.count} / {s.threshold}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <div className="flex justify-end gap-2 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() => openApproveModal(s)}
                                                    className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 font-medium transition-colors"
                                                >
                                                    Approve
                                                </button>
                                                <button className="text-xs px-2 py-1 text-gray-400 hover:text-red-600 font-medium transition-colors">Dismiss</button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                {suggestions.length === 0 && (
                                    <tr>
                                        <td colSpan="3" className="px-6 py-12 text-center text-gray-400 text-sm">
                                            No pending suggestions found.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </div>
    );
}
