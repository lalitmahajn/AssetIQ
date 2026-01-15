import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../api";

export default function ReasonEditor() {
    const [reasons, setReasons] = useState([]);
    const [loading, setLoading] = useState(true);
    const [err, setErr] = useState("");
    const [showForm, setShowForm] = useState(false);

    const [newText, setNewText] = useState("");
    const [newCat, setNewCat] = useState("Operational");

    async function load() {
        setLoading(true);
        try {
            const data = await apiGet("/master/reasons/list");
            setReasons(data);
        } catch (e) {
            setErr(String(e));
        } finally {
            setLoading(false);
        }
    }

    async function handleAdd(e) {
        e.preventDefault();
        setErr("");
        try {
            await apiPost("/master/reasons/create", { text: newText, category: newCat });
            setShowForm(false);
            setNewText("");
            await load();
        } catch (e) {
            setErr(String(e?.message || e));
        }
    }

    async function handleDelete(id) {
        if (!confirm("Are you sure you want to delete this reason?")) return;
        try {
            await apiPost(`/master/reasons/delete?id=${id}`);
            await load();
        } catch (e) {
            alert("Failed to delete: " + e);
        }
    }

    useEffect(() => { load(); }, []);

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-gray-800">Stop Reasons (Symptoms)</h3>
                <button
                    onClick={() => setShowForm(!showForm)}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                >
                    {showForm ? "Cancel" : "+ Add Reason"}
                </button>
            </div>

            {err && <div className="text-red-600 mb-4 bg-red-50 p-2 rounded">{err}</div>}

            {showForm && (
                <form onSubmit={handleAdd} className="mb-6 bg-blue-50 p-4 rounded border border-blue-200">
                    <h4 className="font-semibold mb-3">Add Standard Reason</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <input
                            placeholder="Reason Text (e.g. Broken Belt)"
                            className="border p-2 rounded w-full"
                            value={newText} onChange={e => setNewText(e.target.value)} required
                        />
                        <select
                            className="border p-2 rounded w-full"
                            value={newCat} onChange={e => setNewCat(e.target.value)}
                        >
                            <option value="Operational">Operational</option>
                            <option value="Mechanical">Mechanical</option>
                            <option value="Electrical">Electrical</option>
                            <option value="Quality">Quality</option>
                        </select>
                    </div>
                    <button className="mt-3 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Save</button>
                </form>
            )}

            <table className="w-full text-left">
                <thead>
                    <tr className="border-b">
                        <th className="py-2">Category</th>
                        <th className="py-2">Reason Text</th>
                        <th className="py-2 text-right">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {loading ? (
                        <tr><td colSpan={3} className="py-4 text-center">Loading...</td></tr>
                    ) : reasons.length === 0 ? (
                        <tr><td colSpan={3} className="py-4 text-center text-gray-500">No reasons found.</td></tr>
                    ) : reasons.map(r => (
                        <tr key={r.id} className="border-b last:border-0 hover:bg-gray-50">
                            <td className="py-2 text-gray-600">
                                <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${r.category === 'Mechanical' ? 'bg-red-100 text-red-800' :
                                        r.category === 'Electrical' ? 'bg-yellow-100 text-yellow-800' :
                                            'bg-gray-100 text-gray-800'
                                    }`}>
                                    {r.category}
                                </span>
                            </td>
                            <td className="py-2 font-medium">{r.text}</td>
                            <td className="py-2 text-right">
                                <button
                                    onClick={() => handleDelete(r.id)}
                                    className="text-red-600 hover:text-red-800 hover:underline text-sm"
                                >
                                    Delete
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
