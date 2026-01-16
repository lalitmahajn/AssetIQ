import React, { useEffect, useState } from "react";
import { apiGet } from "../api";

export default function AssetwiseEfficiencyChart() {
    const [data, setData] = useState(null);
    const [err, setErr] = useState("");
    const [loading, setLoading] = useState(true);

    const [expanded, setExpanded] = useState({});

    useEffect(() => {
        let mounted = true;
        (async () => {
            try {
                const resp = await apiGet("/ui/efficiency/by-asset?days=7");
                if (mounted) {
                    setData(resp);
                    setLoading(false);
                }
            } catch (e) {
                if (mounted) {
                    setErr(String(e?.message || e));
                    setLoading(false);
                }
            }
        })();
        return () => { mounted = false; };
    }, []);

    const toggle = (id) => {
        setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
    };

    if (loading) return <div className="p-4 text-gray-500 animate-pulse">Loading efficiency chart...</div>;
    if (err) return <div className="p-4 text-red-600">Failed to load efficiency chart: {err}</div>;
    if (!data?.items?.length) return <div className="p-4 text-gray-500">No assets found. Create assets to see efficiency data.</div>;

    // Helper: Build Tree
    const buildTree = (items) => {
        const map = {};
        const roots = [];
        items.forEach(item => {
            map[item.asset_id] = { ...item, children: [] };
        });
        items.forEach(item => {
            if (item.parent_id && map[item.parent_id]) {
                map[item.parent_id].children.push(map[item.asset_id]);
            } else {
                roots.push(map[item.asset_id]);
            }
        });
        return roots;
    };

    const tree = buildTree(data.items);



    const getBadgeColor = (pct) => {
        if (pct >= 90) return "bg-green-100 text-green-700 border-green-200";
        if (pct >= 75) return "bg-yellow-100 text-yellow-700 border-yellow-200";
        return "bg-red-100 text-red-700 border-red-200";
    };

    const renderRow = (node) => {
        const isExp = expanded[node.asset_id];
        const hasChildren = node.children && node.children.length > 0;
        
        return (
            <React.Fragment key={node.asset_id}>
                <tr className="hover:bg-gray-50 border-b border-gray-100 last:border-0 transition-colors">
                    <td className="py-3 pr-4 pl-4 whitespace-nowrap">
                        <div 
                            className={`flex items-center gap-2 ${hasChildren ? 'cursor-pointer select-none text-gray-800' : 'text-gray-600'}`}
                            onClick={() => hasChildren && toggle(node.asset_id)}
                            style={{ paddingLeft: `${node.level * 24}px` }} 
                        >
                            <span className="w-4 h-4 flex items-center justify-center text-gray-400">
                                {hasChildren && (
                                    <span className="text-[10px] transform transition-transform duration-200">
                                        {isExp ? "▼" : "▶"}
                                    </span>
                                )}
                            </span>
                            <div className="flex flex-col">
                                <span className={`text-sm ${node.is_parent ? 'font-bold' : 'font-medium'}`}>
                                    {node.asset_name || node.asset_code}
                                </span>
                                {node.asset_name && node.asset_name !== node.asset_code && (
                                    <span className="text-[10px] text-gray-400">{node.asset_code}</span>
                                )}
                            </div>
                        </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                        <span className={`inline-flex px-2.5 py-1 text-xs font-bold rounded-full border ${getBadgeColor(node.efficiency_pct)}`}>
                            {node.efficiency_pct}%
                        </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-500 whitespace-nowrap font-mono text-right">
                        {node.uptime_minutes.toLocaleString()} <span className="text-xs text-gray-300">min</span>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-500 whitespace-nowrap font-mono text-right">
                        {node.downtime_minutes.toLocaleString()} <span className="text-xs text-gray-300">min</span>
                    </td>
                </tr>
                {hasChildren && isExp && node.children.map(child => renderRow(child))}
            </React.Fragment>
        );
    };

    return (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm mb-6">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-white">
                <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                    <span className="w-2 h-6 bg-gradient-to-b from-green-500 to-emerald-400 rounded-sm"></span>
                    Assetwise Efficiency 
                    <span className="text-gray-400 font-normal text-sm ml-1">(Last {data.window_days} Days)</span>
                </h3>
            </div>
            
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider border-b border-gray-200 font-semibold">
                            <th className="py-3 px-4 pl-12 w-2/5">Asset</th>
                            <th className="py-3 px-4 w-1/5">Efficiency</th>
                            <th className="py-3 px-4 text-right w-1/5">Uptime</th>
                            <th className="py-3 px-4 text-right w-1/5">Downtime</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tree.map(root => renderRow(root))}
                    </tbody>
                </table>
            </div>
            <div className="bg-gray-50 px-6 py-3 border-t border-gray-100 text-xs text-right text-gray-400 font-mono">
                Based on {data.total_minutes} minutes window
            </div>
        </div>
    );
}
