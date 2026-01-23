import React, { useEffect, useState } from "react";
import { apiGet } from "../api";

export default function AssetwiseEfficiencyChart() {
    const [days, setDays] = useState(7);
    const [data, setData] = useState(null);
    const [err, setErr] = useState("");
    const [loading, setLoading] = useState(true);

    const [expanded, setExpanded] = useState({});

    useEffect(() => {
        let mounted = true;
        setLoading(true);
        (async () => {
            try {
                const resp = await apiGet(`/ui/efficiency/by-asset?days=${days}`);
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
    }, [days]);

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

    const formatMetric = (val) => {
        if (val === undefined || val === null || isNaN(val)) return "-";
        return Math.round(val).toLocaleString();
    };

    const renderRow = (node, hierarchy = []) => {
        const isExp = expanded[node.asset_id];
        const hasChildren = node.children && node.children.length > 0;

        // Tree Guides using fixed width cells and SVGs
        const renderGuides = () => {
            return hierarchy.map((isLast, index) => {
                const isCurrent = index === hierarchy.length - 1;

                return (
                    <div key={index} className="w-8 h-auto flex-shrink-0 flex justify-center bg-transparent relative">
                        {!isCurrent ? (
                            // Ancestor Guide: Vertical line if ancestor is not last
                            !isLast && <div className="absolute top-0 bottom-0 w-px bg-gray-300 left-1/2 -ml-px"></div>
                        ) : (
                            // Current Node Connector
                            <>
                                {/* Vertical Line: Top to Bottom (if T) or Top to Middle (if L) */}
                                <div className={`absolute top-0 w-px bg-gray-300 left-1/2 -ml-px ${isLast ? 'h-1/2' : 'h-full'}`}></div>
                                {/* Horizontal Line: Middle to Right */}
                                <div className="absolute top-1/2 right-0 w-1/2 h-px bg-gray-300"></div>
                            </>
                        )}
                    </div>
                );
            });
        };

        return (
            <React.Fragment key={node.asset_id}>
                <tr className="hover:bg-gray-50 border-b border-gray-100 last:border-0 transition-colors">
                    <td className="p-0 pr-4 whitespace-nowrap">
                        <div className="flex items-stretch h-full min-h-[48px]">

                            {/* 1. Indentation Guides */}
                            {renderGuides()}

                            {/* 2. Expander / Leaf Icon Cell */}
                            <div className="w-8 h-auto flex-shrink-0 flex items-center justify-center relative">
                                {/* Connection to child line (Vertical tail if expanded and has children) */}
                                {/* Only draw tiny tail if I have children and am expanded, to connect to my first child */}
                                {hasChildren && isExp && (
                                    <div className="absolute bottom-0 top-1/2 w-px bg-gray-300 left-1/2 -ml-px"></div>
                                    // Note: top-1/2 essentially starts from center where the expander is
                                )}

                                {/* Connector adjustment for root nodes? 
                                    If I am a child (hierarchy > 0), the guide cell to my left drew a line to my center. 
                                    So the grid connects perfectly. 
                                */}

                                <div
                                    className={`w-5 h-5 flex items-center justify-center rounded-sm transition-colors cursor-pointer z-10 ${hasChildren ? 'hover:bg-gray-200 bg-gray-100 border border-gray-300' : ''}`}
                                    onClick={() => hasChildren && toggle(node.asset_id)}
                                >
                                    {hasChildren ? (
                                        <span className="text-[10px] text-gray-600 font-bold leading-none pb-0.5">
                                            {isExp ? "−" : "+"}
                                        </span>
                                    ) : (
                                        <span className="w-1.5 h-1.5 rounded-full bg-gray-300"></span>
                                    )}
                                </div>
                            </div>

                            {/* 3. Asset Name & Badge */}
                            <div className="flex flex-col justify-center py-3 pl-2 cursor-default" onClick={() => hasChildren && toggle(node.asset_id)}>
                                <div className="flex items-center gap-2">
                                    <span className={`text-sm ${node.is_parent ? 'font-bold text-gray-800' : 'font-medium text-gray-700'}`}>
                                        {node.asset_name || node.asset_code}
                                    </span>
                                    {node.is_critical && (
                                        <span className="px-1.5 py-0.5 text-[10px] uppercase font-bold text-red-600 bg-red-100 border border-red-200 rounded tracking-wider">
                                            Critical
                                        </span>
                                    )}
                                </div>
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
                    <td className="py-3 px-4 text-sm text-gray-500 whitespace-nowrap font-mono text-right">
                        {formatMetric(node.mttr_minutes)} <span className="text-xs text-gray-300">min</span>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-500 whitespace-nowrap font-mono text-right">
                        {formatMetric(node.mttf_minutes)} <span className="text-xs text-gray-300">min</span>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-500 whitespace-nowrap font-mono text-right">
                        {formatMetric(node.mtbf_minutes)} <span className="text-xs text-gray-300">min</span>
                    </td>
                </tr>
                {hasChildren && isExp && node.children.map((child, i) =>
                    renderRow(child, [...hierarchy, i === node.children.length - 1])
                )}
            </React.Fragment>
        );
    };

    return (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm mb-6">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-white">
                <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                    <span className="w-2 h-6 bg-gradient-to-b from-green-500 to-emerald-400 rounded-sm"></span>
                    Assetwise Efficiency
                </h3>
                <div className="flex items-center gap-2">
                    <select
                        value={days}
                        onChange={(e) => setDays(Number(e.target.value))}
                        className="text-sm border-gray-300 rounded-md shadow-sm focus:border-green-500 focus:ring-green-500"
                    >
                        <option value={1}>Last 24 Hours</option>
                        <option value={7}>Last 7 Days</option>
                        <option value={30}>Last 30 Days</option>
                        <option value={90}>Last 3 Months</option>
                    </select>
                </div>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider border-b border-gray-200 font-semibold">
                            <th className="py-3 px-4 pl-12 w-2/5">Asset</th>
                            <th className="py-3 px-4 w-1/5">Efficiency</th>
                            <th className="py-3 px-4 text-right w-1/5">Uptime</th>
                            <th className="py-3 px-4 text-right w-1/5">Downtime</th>
                            <th className="py-3 px-4 text-right w-1/12">MTTR</th>
                            <th className="py-3 px-4 text-right w-1/12">MTTF</th>
                            <th className="py-3 px-4 text-right w-1/12">MTBF</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tree.map(root => renderRow(root, []))}
                    </tbody>
                </table>
            </div>
            <div className="bg-gray-50 px-6 py-3 border-t border-gray-100 text-xs text-right text-gray-400 font-mono">
                Based on {data.total_minutes} minutes window
            </div>
        </div>
    );
}
