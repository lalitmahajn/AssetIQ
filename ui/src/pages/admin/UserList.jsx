import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../api";

export default function UserList() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [err, setErr] = useState("");
    const [showForm, setShowForm] = useState(false);
    const [isEditing, setIsEditing] = useState(false);

    // Form State
    const [username, setUsername] = useState("");
    const [pin, setPin] = useState("");
    const [roles, setRoles] = useState("maintenance");

    async function load() {
        setLoading(true);
        try {
            const data = await apiGet("/master/users/list");
            setUsers(data);
        } catch (e) {
            setErr(String(e));
        } finally {
            setLoading(false);
        }
    }

    async function save(e) {
        e.preventDefault();
        setErr("");
        try {
            if (isEditing) {
                // Update
                const body = { username };
                if (pin) body.pin = pin;
                if (roles) body.roles = roles;
                await apiPost("/master/users/update", body);
            } else {
                // Create
                await apiPost("/master/users/create", { username, pin, roles });
            }

            resetForm();
            await load();
        } catch (e) {
            setErr(String(e?.message || e));
        }
    }

    async function remove(u) {
        if (!window.confirm(`Delete user ${u.id}?`)) return;
        setErr("");
        try {
            await apiPost(`/master/users/delete?username=${u.id}`, {}); // Query param or body? 
            // Endpoint def: delete_user(username: str). FastAPI usually expects query param for singular primitives unless Body is used.
            // Let's assume query param based on definition: def delete_user(username: str...
            await load();
        } catch (e) {
            setErr(String(e?.message || e));
        }
    }

    function edit(u) {
        setUsername(u.id);
        setRoles(u.roles);
        setPin(""); // Don't show old pin, just empty to keep or new to change
        setIsEditing(true);
        setShowForm(true);
    }

    function resetForm() {
        setShowForm(false);
        setIsEditing(false);
        setUsername("");
        setPin("");
        setRoles("maintenance");
        setErr("");
    }

    useEffect(() => { load(); }, []);

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-gray-800">User Management</h3>
                {!showForm && (
                    <button
                        onClick={() => setShowForm(true)}
                        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                    >
                        + New User
                    </button>
                )}
            </div>

            {err && <div className="text-red-600 mb-4 bg-red-50 p-2 rounded">{err}</div>}

            {showForm && (
                <form onSubmit={save} className="mb-6 bg-gray-50 p-4 rounded border border-gray-200">
                    <h4 className="font-semibold mb-3">{isEditing ? "Edit User" : "Create New User"}</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <input
                            placeholder="Username / Email"
                            className="border p-2 rounded bg-white disabled:bg-gray-100"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            required
                            disabled={isEditing} // Cannot change ID on edit
                        />
                        <input
                            placeholder={isEditing ? "New PIN (blank to keep)" : "PIN (min 6 digits)"}
                            className="border p-2 rounded"
                            type="password"
                            value={pin} onChange={e => setPin(e.target.value)}
                            required={!isEditing}
                        />
                        <input
                            placeholder="Roles (comma sep)"
                            className="border p-2 rounded"
                            value={roles} onChange={e => setRoles(e.target.value)}
                        />
                    </div>
                    <div className="mt-3 flex gap-2">
                        <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                            {isEditing ? "Update User" : "Create User"}
                        </button>
                        <button
                            type="button"
                            onClick={resetForm}
                            className="bg-gray-400 text-white px-4 py-2 rounded hover:bg-gray-500"
                        >
                            Cancel
                        </button>
                    </div>
                </form>
            )}

            <table className="w-full text-left">
                <thead>
                    <tr className="border-b">
                        <th className="py-2">User ID / Email</th>
                        <th className="py-2">Roles</th>
                        <th className="py-2">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {loading ? (
                        <tr><td colSpan={3} className="py-4 text-center">Loading...</td></tr>
                    ) : users.map(u => (
                        <tr key={u.id} className="border-b last:border-0 hover:bg-gray-50">
                            <td className="py-2 font-medium">{u.id}</td>
                            <td className="py-2">
                                {u.roles.split(",").map(r => {
                                    const role = r.trim().toLowerCase();
                                    let badgeClass = "bg-gray-200 text-gray-700";
                                    if (role === "admin") badgeClass = "bg-purple-100 text-purple-800";
                                    else if (role === "supervisor") badgeClass = "bg-blue-100 text-blue-800";
                                    else if (role === "maintenance") badgeClass = "bg-green-100 text-green-800";
                                    else if (role === "operator") badgeClass = "bg-orange-100 text-orange-800";

                                    return (
                                        <span key={r} className={`inline-block rounded px-2 py-0.5 text-xs mr-1 font-medium ${badgeClass}`}>
                                            {r.trim()}
                                        </span>
                                    );
                                })}
                            </td>
                            <td className="py-2 flex gap-3">
                                <button onClick={() => edit(u)} className="text-blue-600 hover:underline">Edit</button>
                                <button onClick={() => remove(u)} className="text-red-600 hover:underline">Delete</button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
