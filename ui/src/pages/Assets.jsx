import { memo, useEffect, useState } from "react";
import { apiGet } from "../api";
import AssetHistoryView from "../components/AssetHistoryView";

export default function Assets() {
    const [view, setView] = useState("list"); // list, tree, history
    const [assets, setAssets] = useState([]);
    const [selectedAsset, setSelectedAsset] = useState(null);
    const [tree, setTree] = useState([]);
    const [loading, setLoading] = useState(false);
    const [search, setSearch] = useState("");
    const [debouncedSearch, setDebouncedSearch] = useState("");
    const [expandCommand, setExpandCommand] = useState({ action: null, key: 0 }); // action: 'expand' | 'collapse' | null

    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(search);
        }, 300);
        return () => clearTimeout(timer);
    }, [search]);

    // AUTO-SWITCH TO LIST VIEW ON SEARCH
    useEffect(() => {
        if (search.trim().length > 0 && view !== "list") {
            setView("list");
        }
    }, [search]);

    async function loadData() {
        setLoading(true);
        try {
            if (view === "list") {
                const res = await apiGet(`/assets/list${debouncedSearch ? `?q=${encodeURIComponent(debouncedSearch)}` : ""}`);
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
    }, [view, debouncedSearch]);

    function CategoryIcon({ category, className }) {
        const cat = String(category || "").toLowerCase();
        if (cat.includes("area") || cat.includes("hall")) {
            return <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>;
        }
        if (cat.includes("machine") || cat.includes("reactor") || cat.includes("centrifuge")) {
            return <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" /></svg>;
        }
        return <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>;
    }

    const RenderNode = memo(({ node, level = 0, expandCommand }) => {
        const [isExpanded, setIsExpanded] = useState(true);
        const hasChildren = node.children && node.children.length > 0;
        const isRoot = level === 0;

        // Sync with global controls
        useEffect(() => {
            if (expandCommand.action === 'expand') setIsExpanded(true);
            if (expandCommand.action === 'collapse') setIsExpanded(false);
        }, [expandCommand.key]);

        return (
            <div className={`${!isRoot ? 'ml-6 border-l-2 border-blue-50 pl-4' : ''} py-1.5`}>
                <div className="flex items-center gap-2">
                    {hasChildren ? (
                        <button 
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="p-1 hover:bg-blue-50 rounded text-blue-400 transition-colors mr-1"
                            title={isExpanded ? "Collapse" : "Expand"}
                        >
                            <svg className={`w-3.5 h-3.5 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M9 5l7 7-7 7" /></svg>
                        </button>
                    ) : (
                        !isRoot && <span className="text-gray-300 mr-1 font-light">↳</span>
                    )}
                    
                    <span className="font-bold text-gray-800 tracking-tight text-sm font-mono">{node.asset_code}</span>
                    <span className="text-gray-300">-</span>
                    <span className="text-sm text-gray-600 font-medium">{node.name}</span>
                    <span className="text-[10px] bg-gray-50 border border-gray-100 px-2 py-0.5 rounded text-gray-400 font-bold uppercase tracking-wider ml-1">
                        {node.category}
                    </span>
                </div>
                
                {hasChildren && isExpanded && (
                    <div className="animate-fade-in">
                        {node.children.map(child => <RenderNode key={child.id} node={child} level={level + 1} expandCommand={expandCommand} />)}
                    </div>
                )}
            </div>
        );
    });

    return (
        <div className="max-w-6xl mx-auto py-6 px-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Asset Registry</h2>
                    <p className="text-gray-500 text-sm mt-1">Manage industrial assets and their hierarchies.</p>
                </div>
                
                <div className="flex items-center gap-3">
                    {view === "tree" && (
                        <div className="flex bg-white border border-gray-200 rounded-lg p-1 mr-2 shadow-sm">
                            <button
                                onClick={() => setExpandCommand({ action: 'expand', key: Date.now() })}
                                className="px-3 py-1 text-xs font-bold text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            >
                                Expand All
                            </button>
                            <div className="w-px bg-gray-200 mx-1"></div>
                            <button
                                onClick={() => setExpandCommand({ action: 'collapse', key: Date.now() })}
                                className="px-3 py-1 text-xs font-bold text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            >
                                Collapse All
                            </button>
                        </div>
                    )}
                    <div className="flex bg-gray-100 p-1 rounded-lg shadow-sm border border-gray-200">
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
            </div>

            {view === "history" && selectedAsset && (
                <div className="max-w-4xl mx-auto">
                    <AssetHistoryView 
                        assetId={selectedAsset} 
                        onBack={() => { setView("list"); setSelectedAsset(null); }} 
                    />
                </div>
            )}

            {view === "list" && (
                <div className="mb-6 max-w-2xl animate-fade-in">
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="Search assets by name or code..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full bg-white border border-gray-200 rounded-xl pl-11 pr-10 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all shadow-sm"
                        />
                        <div className="absolute left-4 top-3.5 text-gray-400">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                        </div>
                        {search && (
                            <button 
                                onClick={() => setSearch("")}
                                className="absolute right-3.5 top-3.5 p-0.5 text-gray-400 hover:text-gray-600 transition-colors bg-gray-50 rounded-full"
                            >
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" /></svg>
                            </button>
                        )}
                    </div>
                </div>
            )}

            {view !== "history" && (
            <div className="bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden min-h-[400px]">
                {loading ? (
                    <div className="p-20 text-center flex flex-col items-center">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent mb-4"></div>
                        <div className="text-gray-400 text-sm font-medium">Updating registry...</div>
                    </div>
                ) : view === "list" ? (
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-bold text-gray-400 uppercase tracking-widest">
                                <th className="px-6 py-4">Asset Code</th>
                                <th className="px-6 py-4">Name</th>
                                <th className="px-6 py-4">Category</th>
                                <th className="px-6 py-4">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {assets.map(a => (
                                <tr key={a.id} className="hover:bg-blue-50/30 transition-colors group">
                                    <td className="px-6 py-4 font-mono text-blue-600 text-sm font-semibold">{a.asset_code}</td>
                                    <td className="px-6 py-4 text-gray-700 font-medium group-hover:text-blue-700">
                                        {a.name}
                                        {a.is_critical && <span className="ml-2 bg-red-100 text-red-600 text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider">Critical</span>}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <span className="bg-gray-100 text-gray-500 px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider group-hover:bg-blue-100 group-hover:text-blue-600 transition-colors">
                                                {a.category}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <button 
                                            onClick={() => { setSelectedAsset(a.id); setView("history"); }}
                                            className="text-blue-600 hover:text-blue-800 text-xs font-bold uppercase tracking-wide flex items-center gap-1 hover:underline"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                            History
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {assets.length === 0 && (
                                <tr>
                                    <td colSpan="3" className="px-6 py-20 text-center bg-gray-50/50">
                                        <div className="flex flex-col items-center">
                                            <div className="p-4 bg-white rounded-full shadow-sm mb-4">
                                                <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                                            </div>
                                            <p className="text-lg font-semibold text-gray-600 mb-1">No assets found</p>
                                            <p className="text-sm text-gray-400 mb-6">We couldn't find any results matching "{debouncedSearch}"</p>
                                            <button 
                                                onClick={() => setSearch("")}
                                                className="bg-blue-600 text-white px-6 py-2.5 rounded-lg text-sm font-bold hover:bg-blue-700 transition-all shadow-lg shadow-blue-200 active:scale-95"
                                            >
                                                Clear All Filters
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                ) : (
                    <div className="p-8 bg-gray-50/20">
                        <div className="space-y-1">
                            {tree.map(node => <RenderNode key={node.id} node={node} expandCommand={expandCommand} />)}
                            {tree.length === 0 && (
                                <div className="text-center py-20 bg-white rounded-lg border border-dashed border-gray-300">
                                    <p className="text-gray-400 italic">No root assets found in the registry.</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
            )}
        </div>
    );
}
