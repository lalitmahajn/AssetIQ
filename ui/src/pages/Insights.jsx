
import React, { useEffect, useState } from "react";
import { apiGet } from "../api";
import DowntimeChart from "../components/DowntimeChart";

function severityRank(s) {
  if (s === "HIGH") return 3;
  if (s === "MEDIUM") return 2;
  return 1;
}

export default function Insights() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const resp = await apiGet("/hq/insights/overview");
        if (mounted) setData(resp);
      } catch (e) {
        if (mounted) setErr(String(e?.message || e));
      }
    })();
    return () => { mounted = false; };
  }, []);

  if (err) {
    return (
      <div className="min-h-screen bg-gray-50 text-red-600 p-8">
        <div className="max-w-7xl mx-auto bg-white border border-red-200 rounded-lg p-6 shadow-sm">
          <h2 className="text-xl font-bold mb-2">Error Loading Insights</h2>
          <p>{err}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 p-8 flex items-center justify-center">
        <div className="text-gray-400 animate-pulse text-lg">Loading insights data...</div>
      </div>
    );
  }

  const items = (data.items || []).slice().sort((a, b) => severityRank(b.severity) - severityRank(a.severity));
  const global = items.filter(x => !x.site_code);
  const perPlant = items.filter(x => x.site_code);

  const maxGlobal = 4;
  const maxPerPlant = 10;

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800 p-6">
      <div className="max-w-7xl mx-auto">

        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Plant Insights</h2>
          <p className="text-gray-500 text-sm">
            Historical patterns and analysis. Read-only view provided by HQ Intelligence.
          </p>
        </div>

        {items.length === 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-8 text-center text-gray-500 mb-8 shadow-sm">
            Not enough data yet. Insights will appear after daily rollups and ticket history accumulate.
          </div>
        )}

        <DowntimeChart />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left Col: HQ Summary */}
          {global.length > 0 && (
            <div className="lg:col-span-1 space-y-4">
              <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                HQ Global Patterns
                <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-bold">New</span>
              </h3>
              {global.slice(0, maxGlobal).map((x, idx) => (
                <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
                  <div className="font-semibold text-gray-900 mb-1">{x.title}</div>
                  <div className="text-xs text-gray-500 flex flex-wrap gap-2 items-center">
                    <span className={`px-2 py-0.5 rounded-full bg-gray-100 border border-gray-200 text-gray-600 uppercase font-bold tracking-wider`}>
                      {x.severity}
                    </span>
                    <span>Window: {x.detail?.window_days ?? "-"} days</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Right Col: Plant Specific */}
          {perPlant.length > 0 && (
            <div className="lg:col-span-2">
              <h3 className="text-xl font-semibold text-gray-800 mb-4">Plant-Specific Insights</h3>
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-50 text-gray-500 uppercase text-xs font-semibold border-b border-gray-200">
                    <tr>
                      <th className="px-6 py-3">Plant</th>
                      <th className="px-6 py-3">Severity</th>
                      <th className="px-6 py-3">Insight Title</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {perPlant.slice(0, maxPerPlant).map((x, idx) => (
                      <tr key={idx} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 font-medium text-gray-900">{x.site_code}</td>
                        <td className="px-6 py-4">
                          <span className={`
                                                px-2 py-1 rounded-full text-xs font-bold border
                                                ${x.severity === 'HIGH' ? 'bg-red-50 text-red-700 border-red-100' :
                              x.severity === 'MEDIUM' ? 'bg-yellow-50 text-yellow-700 border-yellow-100' :
                                'bg-gray-100 text-gray-600 border-gray-200'}
                                            `}>
                            {x.severity}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-gray-600">{x.title}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500 text-right">
                  Showing top {maxPerPlant} active insights
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
