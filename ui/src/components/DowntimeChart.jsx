import React, { useEffect, useState } from "react";
import { apiGet } from "../api";

export default function DowntimeChart() {
    const [data, setData] = useState(null);
    const [err, setErr] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let mounted = true;
        (async () => {
            try {
                const resp = await apiGet("/hq/compare/downtime");
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

    if (loading) return <div className="p-4 text-gray-500 animate-pulse">Loading chart...</div>;
    if (err) return <div className="p-4 text-red-600">Failed to load chart: {err}</div>;
    if (!data?.items?.length) return <div className="p-4 text-gray-500">No downtime data available for comparison.</div>;

    // Find max for scaling
    const maxVal = Math.max(...data.items.map(i => i.downtime_minutes)) || 1;

    return (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 shadow-sm">
            <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="w-2 h-6 bg-blue-600 rounded-sm"></span>
                Global Downtime Comparison <span className="text-gray-400 font-normal text-sm">(Minutes)</span>
            </h3>
            <div className="space-y-4">
                {data.items.map((item, idx) => {
                    const widthPct = Math.max(2, (item.downtime_minutes / maxVal) * 100);
                    return (
                        <div key={item.site_code} className="group">
                            <div className="flex justify-between text-sm text-gray-600 mb-1 group-hover:text-blue-700 transition-colors">
                                <span className="font-semibold tracking-wide">{item.site_code}</span>
                                <span className="font-mono font-medium">{item.downtime_minutes} min</span>
                            </div>
                            <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden border border-gray-100">
                                <div
                                    className="h-full rounded-full bg-gradient-to-r from-blue-600 to-cyan-500 shadow-sm transition-all duration-1000 ease-out group-hover:from-blue-500 group-hover:to-cyan-400"
                                    style={{ width: `${widthPct}%` }}
                                />
                            </div>
                        </div>
                    );
                })}
            </div>
            <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-right text-gray-400 font-mono">
                UTC Day: {data.day_utc}
            </div>
        </div>
    );
}
