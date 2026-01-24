import React, { useState, useEffect } from "react";
import { apiGet, apiPost } from "../../api";

export default function SuggestionsReview() {
    const [suggestions, setSuggestions] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadSuggestions();
    }, []);

    async function loadSuggestions() {
        setLoading(true);
        try {
            const res = await apiGet("/suggestions/list?status=pending");
            setSuggestions(res || []);
        } finally {
            setLoading(false);
        }
    }

    async function handleApprove(id, currentName) {
        const code = prompt("Enter a unique code for this reason (e.g. MECH_PUMP_FAIL):", currentName.toUpperCase().replace(/\s+/g, "_"));
        if (!code) return;
        try {
            await apiPost("/suggestions/approve", { suggestion_id: id, item_code: code });
            loadSuggestions();
        } catch (err) {
            alert("Error approving suggestion");
        }
    }

    return (
        <div className="max-w-5xl mx-auto">
            <div className="mb-8">
                <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Self-Learning Review</h2>
                <p className="text-gray-500 text-sm mt-1">Review reasons that have been used multiple times and promote them to the master list.</p>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                {loading ? (
                    <div className="p-12 text-center text-gray-400 animate-pulse">Loading suggestions...</div>
                ) : (
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                <th className="px-6 py-4">Suggested Reason</th>
                                <th className="px-6 py-4">Frequency</th>
                                <th className="px-6 py-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {suggestions.map(s => (
                                <tr key={s.id} className="hover:bg-blue-50/30 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="font-medium text-gray-800">{s.suggested_name}</div>
                                        <div className="text-xs text-gray-400 uppercase tracking-tighter">Status: {s.status}</div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`px-2 py-1 rounded-full text-xs font-bold ${s.count >= s.threshold ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}>
                                            {s.count} / {s.threshold}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-right space-x-3">
                                        <button
                                            onClick={() => handleApprove(s.id, s.suggested_name)}
                                            className="text-sm font-semibold text-blue-600 hover:text-blue-800"
                                        >
                                            Approve & Promote
                                        </button>
                                        <button className="text-sm font-semibold text-gray-400 hover:text-red-500">Dismiss</button>
                                    </td>
                                </tr>
                            ))}
                            {suggestions.length === 0 && (
                                <tr>
                                    <td colSpan="3" className="px-6 py-12 text-center text-gray-400 italic">No auto-promoted suggestions to review.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
