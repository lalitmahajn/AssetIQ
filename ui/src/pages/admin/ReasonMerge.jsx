import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../api";

export default function ReasonMerge() {
    const [reasons, setReasons] = useState([]);
    const [sourceId, setSourceId] = useState("");
    const [targetId, setTargetId] = useState("");
    const [msg, setMsg] = useState("");
    const [err, setErr] = useState("");

    async function load() {
        try {
            const r = await apiGet("/master/reasons/list");
            setReasons(r);
        } catch (e) {
            setErr(e.message);
        }
    }

    useEffect(() => { load(); }, []);

    async function doMerge() {
        setErr("");
        setMsg("");
        if (!sourceId || !targetId) {
            setErr("Please select both reasons");
            return;
        }
        if (sourceId === targetId) {
            setErr("Source and Target cannot be the same");
            return;
        }

        try {
            await apiPost("/master/reasons/merge", { source_id: parseInt(sourceId), target_id: parseInt(targetId) });
            setMsg("Merge successful! Source reason deactivated.");
            setSourceId("");
            setTargetId("");
            load();
        } catch (e) {
            setErr(e.message);
        }
    }

    return (
        <div className="max-w-2xl bg-white p-6 rounded shadow">
            <h3 className="text-xl font-bold mb-4 text-gray-800">Clean-up Tool: Merge Reasons</h3>
            <p className="text-gray-500 mb-6 text-sm">
                Use this tool to fix duplicates or typos.
                Select the "Bad" reason (Source) and the "Correct" reason (Target).
                The Source reason will be deactivated, and future reports can be aliased (feature pending).
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
                <div>
                    <label className="block text-sm font-semibold text-red-600 mb-1">Source (Bad Reason)</label>
                    <select
                        className="w-full border border-red-200 bg-red-50 p-3 rounded"
                        value={sourceId} onChange={e => setSourceId(e.target.value)}
                    >
                        <option value="">-- Select Reason to Remove --</option>
                        {reasons.map(r => (
                            <option key={r.id} value={r.id}>{r.text} ({r.category})</option>
                        ))}
                    </select>
                </div>

                <div className="flex justify-center pb-3">
                    <span className="text-2xl text-gray-400">➔</span>
                </div>

                <div>
                    <label className="block text-sm font-semibold text-green-600 mb-1">Target (Good Reason)</label>
                    <select
                        className="w-full border border-green-200 bg-green-50 p-3 rounded"
                        value={targetId} onChange={e => setTargetId(e.target.value)}
                    >
                        <option value="">-- Select Correct Reason --</option>
                        {reasons.map(r => (
                            <option key={r.id} value={r.id}>{r.text} ({r.category})</option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="mt-8">
                <button
                    onClick={doMerge}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded transition-colors"
                >
                    Merge & Deactivate Source
                </button>
            </div>

            {msg && <div className="mt-4 p-3 bg-green-100 text-green-700 rounded text-center">{msg}</div>}
            {err && <div className="mt-4 p-3 bg-red-100 text-red-700 rounded text-center">{err}</div>}
        </div>
    );
}
