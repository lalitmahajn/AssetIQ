import React, { useState, useEffect } from "react";
import { apiGet, apiPost } from "../api";

export default function Assets() {
    const [view, setView] = useState("list"); // list or tree
    const [assets, setAssets] = useState([]);
    const [tree, setTree] = useState([]);
    const [loading, setLoading] = useState(false);

    async function loadData() {
        setLoading(true);
        try {
            if (view === "list") {
                const res = await apiGet("/assets/list");
                setAssets(res || []);
            } else {
                const res = await apiGet("/assets/tree");
                setTree(res.children || []);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadData();
    }, [view]);

    function RenderNode({ node, level = 0 }) {
        return (
            <div className="ml-4 border-l-2 border-blue-100 pl-4 py-1">
                <div className="flex items-center gap-2">
                    <span className="text-gray-400">↳</span>
                    <span className="font-medium text-gray-800">{node.asset_code}</span>
                    <span className="text-sm text-gray-500">- {node.name}</span>
                    <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-400 capitalize">{node.category}</span>
                </div>
                {node.children && node.children.map(child => <RenderNode key={child.id} node={child} level={level + 1} />)}
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto py-6">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Asset Registry</h2>
                    <p className="text-gray-500 text-sm mt-1">Manage industrial assets and their hierarchies.</p>
                </div>
                <div className="flex bg-gray-100 p-1 rounded-lg">
                    <button
                        onClick={() => setView("list")}
                        className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${view === "list" ? "bg-white shadow-sm text-blue-600" : "text-gray-500 hover:text-gray-700"}`}
                    >
                        List View
                    </button>
                    <button
                        onClick={() => setView("tree")}
                        className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${view === "tree" ? "bg-white shadow-sm text-blue-600" : "text-gray-500 hover:text-gray-700"}`}
                    >
                        Tree View
                    </button>
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                {loading ? (
                    <div className="p-12 text-center text-gray-400 animate-pulse">Loading assets...</div>
                ) : view === "list" ? (
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                <th className="px-6 py-4">Asset Code</th>
                                <th className="px-6 py-4">Name</th>
                                <th className="px-6 py-4">Category</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {assets.map(a => (
                                <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                                    <td className="px-6 py-4 font-mono text-blue-600 text-sm">{a.asset_code}</td>
                                    <td className="px-6 py-4 text-gray-700 font-medium">{a.name}</td>
                                    <td className="px-6 py-4">
                                        <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded-full text-xs font-medium uppercase tracking-tighter">
                                            {a.category}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                            {assets.length === 0 && (
                                <tr>
                                    <td colSpan="3" className="px-6 py-12 text-center text-gray-400 italic">No assets registered yet.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                ) : (
                    <div className="p-8">
                        <div className="space-y-2">
                            {tree.map(node => <RenderNode key={node.id} node={node} />)}
                            {tree.length === 0 && <div className="text-center text-gray-400 py-12 italic">No root assets found.</div>}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
