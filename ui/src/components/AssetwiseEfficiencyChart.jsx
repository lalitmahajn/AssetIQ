import React, { useEffect, useState } from "react";
import { apiGet } from "../api";

export default function AssetwiseEfficiencyChart() {
    const [data, setData] = useState(null);
    const [err, setErr] = useState("");
    const [loading, setLoading] = useState(true);

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

    if (loading) return <div className="p-4 text-gray-500 animate-pulse">Loading efficiency chart...</div>;
    if (err) return <div className="p-4 text-red-600">Failed to load efficiency chart: {err}</div>;
    if (!data?.items?.length) return <div className="p-4 text-gray-500">No assets found. Create assets to see efficiency data.</div>;

    const getBarColor = (pct) => {
        if (pct >= 90) return "from-green-500 to-emerald-400";
        if (pct >= 70) return "from-yellow-500 to-amber-400";
        return "from-red-500 to-rose-400";
    };

    const getBadgeColor = (pct) => {
        if (pct >= 90) return "bg-green-100 text-green-700 border-green-200";
        if (pct >= 70) return "bg-yellow-100 text-yellow-700 border-yellow-200";
        return "bg-red-100 text-red-700 border-red-200";
    };

    return (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 shadow-sm">
            <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="w-2 h-6 bg-gradient-to-b from-green-500 to-emerald-400 rounded-sm"></span>
                Assetwise Efficiency <span className="text-gray-400 font-normal text-sm">(Last {data.window_days} Days)</span>
            </h3>
            <div className="space-y-4">
                {data.items.map((item, idx) => {
                    const widthPct = Math.max(5, item.efficiency_pct);
                    return (
                        <div key={item.asset_id} className="group">
                            <div className="flex justify-between text-sm text-gray-600 mb-1 group-hover:text-gray-800 transition-colors">
                                <span className="font-semibold tracking-wide">{item.asset_code}</span>
                                <span className={`px-2 py-0.5 text-xs font-bold rounded border ${getBadgeColor(item.efficiency_pct)}`}>
                                    {item.efficiency_pct}%
                                </span>
                            </div>
                            <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden border border-gray-100">
                                <div
                                    className={`h-full rounded-full bg-gradient-to-r ${getBarColor(item.efficiency_pct)} shadow-sm transition-all duration-1000 ease-out`}
                                    style={{ width: `${widthPct}%` }}
                                />
                            </div>
                            <div className="mt-1 text-xs text-gray-400 flex gap-4">
                                <span>Uptime: {item.uptime_minutes} min</span>
                                <span>Downtime: {item.downtime_minutes} min</span>
                            </div>
                        </div>
                    );
                })}
            </div>
            <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-right text-gray-400 font-mono">
                Based on {data.total_minutes} minutes window
            </div>
        </div>
    );
}
