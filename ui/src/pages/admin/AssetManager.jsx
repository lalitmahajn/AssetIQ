import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../api";

export default function AssetManager() {
    const [assets, setAssets] = useState([]);
    const [err, setErr] = useState("");
    const [form, setForm] = useState({ id: "", name: "", parent_id: "", asset_type: "MACHINE", description: "", is_critical: false });
    const [editing, setEditing] = useState(false);

    async function load() {
        try {
            const r = await apiGet("/master/assets/list");
            setAssets(r);
        } catch (e) {
            setErr(e.message);
        }
    }

    useEffect(() => { load(); }, []);

    async function save(e) {
        e.preventDefault();
        setErr("");
        const body = { ...form };
        if (!body.parent_id) delete body.parent_id;

        try {
            const url = editing ? "/master/assets/update" : "/master/assets/create";
            await apiPost(url, body);
            setForm({ id: "", name: "", parent_id: "", asset_type: "MACHINE", description: "", is_critical: false });
            setEditing(false);
            load();
        } catch (e) {
            setErr(e.message);
        }
    }

    function edit(a) {
        setForm({
            id: a.id,
            name: a.name,
            parent_id: a.parent_id || "",
            asset_type: a.asset_type,
            parent_id: a.parent_id || "",
            asset_type: a.asset_type,
            description: a.description || "",
            is_critical: a.is_critical || false
        });
        setEditing(true);
    }

    async function doDelete(assetId) {
        if (!confirm(`Are you sure you want to delete asset "${assetId}"?`)) return;
        setErr("");
        try {
            await apiPost(`/master/assets/delete?asset_id=${assetId}`, {});
            load();
        } catch (e) {
            setErr(e.message);
        }
    }

    return (
        <div className="space-y-6">
            <div className="bg-white p-4 rounded shadow">
                <h3 className="text-lg font-bold mb-4">{editing ? "Edit Asset" : "New Asset"}</h3>
                <form onSubmit={save} className="grid grid-cols-2 gap-4">
                    <input
                        className="border p-2 rounded"
                        placeholder="Asset Code (Unique)"
                        value={form.id}
                        onChange={e => setForm({ ...form, id: e.target.value })}
                        disabled={editing} // ID cannot change
                        required
                    />
                    <input
                        className="border p-2 rounded"
                        placeholder="Name"
                        value={form.name}
                        onChange={e => setForm({ ...form, name: e.target.value })}
                        required
                    />
                    <select
                        className="border p-2 rounded"
                        value={form.asset_type}
                        onChange={e => setForm({ ...form, asset_type: e.target.value })}
                    >
                        <option value="AREA">Area / Line</option>
                        <option value="MACHINE">Machine</option>
                        <option value="COMPONENT">Component</option>
                    </select>
                    <input
                        className="border p-2 rounded"
                        placeholder="Parent Asset ID (Optional)"
                        value={form.parent_id}
                        onChange={e => setForm({ ...form, parent_id: e.target.value })}
                    />
                    <input
                        className="border p-2 rounded col-span-2"
                        placeholder="Description"
                        value={form.description}
                        onChange={e => setForm({ ...form, description: e.target.value })}
                    />
                    <div className="col-span-2 flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="is_critical"
                            checked={form.is_critical}
                            onChange={e => setForm({ ...form, is_critical: e.target.checked })}
                            className="w-4 h-4 text-blue-600 rounded"
                        />
                        <label htmlFor="is_critical" className="text-gray-700 font-medium select-none">Mark as Critical Asset</label>
                    </div>
                    <div className="col-span-2 flex gap-2">
                        <button className="bg-blue-600 text-white px-4 py-2 rounded">{editing ? "Update" : "Create"}</button>
                        {editing && (
                            <button type="button" onClick={() => { setEditing(false); setForm({ id: "", name: "", parent_id: "", asset_type: "MACHINE", description: "", is_critical: false }) }} className="bg-gray-400 text-white px-4 py-2 rounded">Cancel</button>
                        )}
                    </div>
                </form>
                {err && <div className="text-red-500 mt-2">{err}</div>}
            </div>

            <div className="bg-white rounded shadow overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="p-3">Type</th>
                            <th className="p-3">Asset Code</th>
                            <th className="p-3">Name</th>
                            <th className="p-3">Parent</th>
                            <th className="p-3">Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y">
                        {assets.map(a => {
                            const parent = assets.find(p => p.id === a.parent_id);
                            return (
                                <tr key={a.id}>
                                    <td className="p-3 text-xs font-mono">{a.asset_type}</td>
                                    <td className="p-3 font-medium text-blue-600" title={a.id}>{a.asset_code || a.id}</td>
                                    <td className="p-3">{a.name}
                                        {a.is_critical && <span className="ml-2 bg-red-100 text-red-600 text-[10px] font-bold px-1.5 py-0.5 rounded uppercase">Critical</span>}
                                    </td>
                                    <td className="p-3 text-gray-500">
                                        {parent ? (
                                            <span title={a.parent_id}>{parent.asset_code || parent.id}</span>
                                        ) : (
                                            <span className="opacity-50">-</span>
                                        )}
                                    </td>
                                    <td className="p-3 space-x-2">
                                        <button onClick={() => edit(a)} className="text-blue-600 hover:underline">Edit</button>
                                        <button onClick={() => doDelete(a.id)} className="text-red-600 hover:underline">Delete</button>
                                    </td>
                                </tr>
                            );
                        })}
                        {assets.length === 0 && <tr><td colSpan={5} className="p-4 text-center text-gray-500">No assets defined.</td></tr>}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
