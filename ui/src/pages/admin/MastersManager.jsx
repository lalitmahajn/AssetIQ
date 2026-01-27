import React, { useState, useEffect } from "react";
import { apiGet, apiPost } from "../../api";

export default function MastersManager() {
    const [types, setTypes] = useState([]);
    const [selectedType, setSelectedType] = useState("");
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);

    // Modal State
    const [showModal, setShowModal] = useState(false);
    const [newName, setNewName] = useState("");
    const [newCode, setNewCode] = useState("");
    const [isCodeManual, setIsCodeManual] = useState(false);

    useEffect(() => {
        loadTypes();
    }, []);

    async function loadTypes() {
        const res = await apiGet("/masters-dynamic/types");
        setTypes(res || []);
        if (res && res.length > 0) setSelectedType(res[0].type_code);
    }

    useEffect(() => {
        if (selectedType) loadItems();
    }, [selectedType]);

    async function loadItems() {
        setLoading(true);
        try {
            const res = await apiGet(`/masters-dynamic/items?type_code=${selectedType}`);
            setItems(res || []);
        } finally {
            setLoading(false);
        }
    }

    function openAddModal() {
        setNewName("");
        setNewCode("");
        setIsCodeManual(false);
        setShowModal(true);
    }

    async function handleAddOption() {
        if (!newName.trim()) return;
        const code = newCode.trim() || newName.toUpperCase().replace(/\s+/g, "_");

        try {
            await apiPost("/masters-dynamic/items/create", {
                type_code: selectedType,
                item_code: code,
                item_name: newName.trim()
            });
            setShowModal(false);
            loadItems();
        } catch (err) {
            alert("Error creating item: " + err.message);
        }
    }

    async function handleDisable(id) {
        if (!confirm("Are you sure you want to disable this option? It will be hidden from dropdowns.")) return;
        try {
            await apiPost("/masters-dynamic/items/toggle", { item_id: id, is_active: false });
            loadItems();
        } catch (err) {
            alert("Error: " + err.message);
        }
    }

    return (
        <div className="max-w-4xl mx-auto">
            {/* ADD OPTION MODAL */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4">
                        <h3 className="text-lg font-bold text-gray-900 mb-4">
                            Add New Option
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
                                    onKeyDown={e => { if (e.key === "Enter") handleAddOption(); }}
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
                                onClick={handleAddOption}
                                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
                            >
                                Add Option
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <div className="mb-8">
                <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Dynamic Masters</h2>
                <p className="text-gray-500 text-sm mt-1">Configure drop-down options and system categories.</p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
                <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm h-fit">
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Master Types</h3>
                    <div className="space-y-1">
                        {types.map(t => (
                            <button
                                key={t.type_code}
                                onClick={() => setSelectedType(t.type_code)}
                                className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all ${selectedType === t.type_code ? "bg-blue-50 text-blue-700 ring-1 ring-blue-100" : "text-gray-600 hover:bg-gray-50"}`}
                            >
                                {t.name}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="md:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
                        <h3 className="text-sm font-bold text-gray-700">Options for: <span className="text-blue-600 font-mono">{selectedType}</span></h3>
                        <button
                            onClick={openAddModal}
                            className="text-xs text-blue-600 font-semibold hover:underline"
                        >
                            + Add Option
                        </button>
                    </div>
                    <div className="divide-y divide-gray-100 min-h-[300px]">
                        {loading ? (
                            <div className="p-12 text-center text-gray-300 animate-pulse">Loading options...</div>
                        ) : items.map(item => (
                            <div key={item.id} className="p-4 flex justify-between items-center hover:bg-gray-50 transition-colors">
                                <div>
                                    <div className="text-sm font-bold text-gray-800">{item.item_name}</div>
                                    <div className="text-xs font-mono text-gray-400 uppercase tracking-tighter">{item.item_code}</div>
                                </div>
                                <button
                                    onClick={() => handleDisable(item.id)}
                                    className="text-xs text-red-500 hover:text-red-700 font-medium transition-colors"
                                >
                                    Disable
                                </button>
                            </div>
                        ))}
                        {items.length === 0 && !loading && (
                            <div className="p-12 text-center text-gray-400 italic">No options defined for this type.</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
