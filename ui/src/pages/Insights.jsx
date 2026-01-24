
import { useEffect, useState } from "react";
import { apiGet } from "../api";
import AssetwiseEfficiencyChart from "../components/AssetwiseEfficiencyChart";

function severityRank(s) {
  if (s === "HIGH") return 3;
  if (s === "MEDIUM") return 2;
  return 1;
}

export default function Insights({ plantName }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [dismissed, setDismissed] = useState({});
  const [selectedInsight, setSelectedInsight] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const resp = await apiGet("/ui/insights/overview");
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
  // Filter out dismissed items
  const activeItems = items.filter(x => !dismissed[x.title + x.site_code]);

  const global = activeItems.filter(x => !x.site_code);
  const perPlant = activeItems.filter(x => x.site_code);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800 p-6">
      <div className="max-w-7xl mx-auto">

        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Plant Insights</h2>
          <p className="text-gray-500 text-sm">
            Real-time asset performance metrics and automated system intelligence.
          </p>
        </div>

        {/* 1. System Alerts / Plant Insights (Moved to Top) */}
        <div className="mb-10">
          <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
            <span className="w-2 h-6 bg-gradient-to-b from-red-500 to-orange-400 rounded-sm"></span>
            System Alerts & Concerns
            <span className="ml-2 px-2.5 py-0.5 rounded-full bg-gray-200 text-gray-600 text-xs font-bold">
              {perPlant.length} Active
            </span>
          </h3>

          {perPlant.length === 0 ? (
            <div className="bg-white border border-green-200 rounded-lg p-8 text-center shadow-sm">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-100 text-green-600 mb-4">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
              </div>
              <h4 className="text-lg font-medium text-gray-900">System Healthy</h4>
              <p className="text-gray-500 mt-1">No critical patterns or anomalies detected in the analysis window.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {perPlant.map((x, idx) => {
                const isHigh = x.severity === 'HIGH';
                const isMed = x.severity === 'MEDIUM';
                const borderClass = isHigh ? 'border-l-4 border-l-red-500' : (isMed ? 'border-l-4 border-l-yellow-500' : 'border-l-4 border-l-blue-400');
                const bgClass = isHigh ? 'bg-red-50' : (isMed ? 'bg-yellow-50' : 'bg-blue-50');

                return (
                  <div key={idx} className={`bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow relative overflow-hidden ${borderClass}`}>
                    <div className="p-5">
                      <div className="flex justify-between items-start mb-3">
                        <span className={`
                          px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider
                          ${isHigh ? 'bg-red-100 text-red-700' : (isMed ? 'bg-yellow-100 text-yellow-700' : 'bg-blue-100 text-blue-700')}
                        `}>
                          {x.severity} Priority
                        </span>
                        <div className="flex gap-2">
                          {/* Actions */}
                          <button
                            onClick={() => setDismissed(prev => ({ ...prev, [x.title + x.site_code]: true }))}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                            title="Dismiss Alert"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                          </button>
                        </div>
                      </div>

                      <h4 className="font-bold text-gray-900 mb-2 leading-tight">
                        {x.title}
                      </h4>

                      <div className="text-sm text-gray-600 mb-4 bg-white/50 p-2 rounded border border-gray-100/50">
                        {x.detail?.note || "System detected anomaly based on recent data patterns."}
                      </div>

                      <div className="flex items-center justify-between mt-4 border-t border-gray-100 pt-3">
                        <span className="text-[10px] font-black text-blue-600/40 uppercase tracking-tighter">
                          {plantName || x.site_code}
                        </span>
                        <span className="text-[10px] text-gray-400 font-mono italic">
                          {x.detail?.window_days || 14}d Window
                        </span>
                        <button
                          onClick={() => setSelectedInsight(x)}
                          className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
                        >
                          View Analysis →
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 2. Asset Efficiency Chart */}
        <AssetwiseEfficiencyChart />

        {/* 3. Global Patterns (Optional/Secondary) */}
        {global.length > 0 && (
          <div className="mt-8">
            <h3 className="text-lg font-semibold text-gray-700 mb-4">HQ Global Observations</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {global.map((x, idx) => (
                <div key={idx} className="bg-gray-50 border border-gray-200 rounded-md p-4 flex items-center justify-between">
                  <div className="font-medium text-gray-800">{x.title}</div>
                  <span className="text-xs text-gray-500 uppercase">{x.severity}</span>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* Analysis Detail Modal */}
      {selectedInsight && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={() => setSelectedInsight(null)}>
          <div
            className="bg-white rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden transform transition-all"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className={`px-6 py-5 border-b border-gray-100 flex justify-between items-start 
                    ${selectedInsight.severity === 'HIGH' ? 'bg-red-50/50' :
                selectedInsight.severity === 'MEDIUM' ? 'bg-yellow-50/50' : 'bg-blue-50/50'}`}>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border
                                ${selectedInsight.severity === 'HIGH' ? 'bg-red-100 text-red-700 border-red-200' :
                      selectedInsight.severity === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700 border-yellow-200' : 'bg-blue-100 text-blue-700 border-blue-200'}`}>
                    {selectedInsight.severity} PRIORITY
                  </span>
                  <span className="text-[10px] font-black text-blue-600 uppercase tracking-tighter">
                    {plantName || selectedInsight.site_code}
                  </span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 leading-tight pr-4">
                  {selectedInsight.title}
                </h3>
              </div>
              <button
                onClick={() => setSelectedInsight(null)}
                className="text-gray-400 hover:text-gray-600 p-1 hover:bg-black/5 rounded-full transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-8">
              {/* Render Specific Content based on content shape */}
              {(() => {
                const d = selectedInsight.detail || {};

                // 1. Repeated Stop Patterns
                if (d.reason_code && d.total_stops) {
                  return (
                    <div className="space-y-6">
                      <div className="grid grid-cols-3 gap-4">
                        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 text-center">
                          <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Problem</div>
                          <div className="font-bold text-gray-800 text-sm">{d.reason_code}</div>
                        </div>
                        <div className="bg-red-50 p-4 rounded-lg border border-red-100 text-center">
                          <div className="text-xs text-red-500 uppercase font-semibold mb-1">Frequency</div>
                          <div className="text-2xl font-bold text-red-700">{d.total_stops} <span className="text-sm font-normal text-red-600">stops</span></div>
                        </div>
                        <div className="bg-orange-50 p-4 rounded-lg border border-orange-100 text-center">
                          <div className="text-xs text-orange-500 uppercase font-semibold mb-1">Total Impact</div>
                          <div className="text-2xl font-bold text-orange-700">{d.downtime_minutes} <span className="text-sm font-normal text-orange-600">min</span></div>
                        </div>
                      </div>

                      <div className="p-4 bg-blue-50 rounded-lg border border-blue-100 flex items-start gap-4">
                        <div className="p-2 bg-blue-100 rounded-full text-blue-600">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </div>
                        <div>
                          <h4 className="font-bold text-blue-900 text-sm">System Analysis</h4>
                          <p className="text-sm text-blue-800 mt-1">
                            This issue has persisted across <strong>{d.days_affected} different days</strong> within the last {d.window_days} days.
                            Chronic recurrence suggests a maintenance intervention is required rather than just operational resets.
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                }

                // 2. Top Downtime
                if (d.top && Array.isArray(d.top)) {
                  return (
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                        Downtime Distribution (Top 5)
                      </h4>
                      <div className="overflow-hidden border border-gray-200 rounded-lg">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reason</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Stops</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Lost Time</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {d.top.map((item, i) => (
                              <tr key={i} className={i === 0 ? "bg-red-50/30" : ""}>
                                <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{item.reason_code}</td>
                                <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-500 text-right">{item.stops}</td>
                                <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-900 font-bold text-right">{item.downtime_minutes} min</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <p className="mt-4 text-xs text-gray-500 bg-gray-50 p-3 rounded border border-gray-200">
                        <strong>Insight:</strong> The top contributor accounts for a significant portion of total downtime in the {d.window_days} day window.
                      </p>
                    </div>
                  );
                }

                // 3. SLA Trends
                if (d.direction && d.recent_breaches !== undefined) {
                  return (
                    <div className="space-y-6">
                      <div className="flex items-center justify-center py-6">
                        <div className={`text-5xl font-bold ${d.direction === 'up' ? 'text-red-500' : (d.direction === 'down' ? 'text-green-500' : 'text-gray-400')}`}>
                          {d.direction === 'up' ? '↗' : (d.direction === 'down' ? '↘' : '→')}
                        </div>
                        <div className="ml-4">
                          <div className="text-lg font-bold text-gray-900">
                            Trend is {d.direction.toUpperCase()}
                          </div>
                          <p className="text-gray-500 text-sm">Comparing last {d.recent_days} days to prior period</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm text-center">
                          <div className="text-xs text-gray-400 uppercase font-bold">Recent Breaches</div>
                          <div className="text-3xl font-bold text-gray-800 mt-1">{d.recent_breaches}</div>
                        </div>
                        <div className="bg-gray-50 border border-gray-200 p-4 rounded-lg text-center opacity-75">
                          <div className="text-xs text-gray-400 uppercase font-bold">Previous Breaches</div>
                          <div className="text-3xl font-bold text-gray-600 mt-1">{d.previous_breaches}</div>
                        </div>
                      </div>
                    </div>
                  );
                }

                // Fallback Generic
                return (
                  <div>
                    <h4 className="text-sm font-bold text-gray-900 mb-2 uppercase tracking-wider">Raw Detail Data</h4>
                    <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-xs overflow-auto max-h-60 border border-gray-700">
                      {JSON.stringify(d, null, 2)}
                    </pre>
                  </div>
                );
              })()}
            </div>

            {/* Modal Footer */}
            <div className="px-8 py-4 bg-gray-50 border-t border-gray-200 flex justify-between items-center text-xs text-gray-500">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                Verified by Intelligence Engine
              </div>
              <button
                onClick={() => setSelectedInsight(null)}
                className="px-6 py-2.5 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 hover:text-gray-900 font-medium transition-all shadow-sm"
              >
                Close Analysis
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
