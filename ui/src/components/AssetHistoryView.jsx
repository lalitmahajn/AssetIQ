import { useEffect, useState } from "react";
import { apiGet } from "../api";

export default function AssetHistoryView({ assetId, onBack }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const h = await apiGet(`/ui/assets/${assetId}/history?limit=20`);
        setHistory(h || []);
      } catch (e) { }
      finally { setLoading(false); }
    };
    load();
  }, [assetId]);

  const renderPayload = (payload) => {
    if (!payload) return null;
    return (
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs bg-gray-50 p-2 rounded border border-gray-100">
        {Object.entries(payload).map(([key, val]) => (
          <div key={key} className="flex flex-col">
            <span className="text-gray-400 uppercase font-bold text-[10px]">{key.replace(/_/g, ' ')}</span>
            <span className="text-gray-700 font-medium">{String(val)}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={onBack} className="text-blue-600 hover:text-blue-800 flex items-center gap-1 text-sm font-medium mb-1">
            &larr; Back
          </button>
          <h2 className="text-2xl font-bold text-gray-800">Asset History: <span className="text-blue-600">{assetId}</span></h2>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <span className="text-sm font-bold text-gray-500 uppercase">Recent Activity Log</span>
          <span className="text-xs text-gray-400">{history.length} events found</span>
        </div>

        <div className="divide-y divide-gray-100">
          {loading && <div className="p-12 text-center text-gray-500">Loading comprehensive history...</div>}
          {!loading && history.length === 0 && <div className="p-12 text-center text-gray-500 italic">No historical events recorded for this asset.</div>}

          {history.map(h => (
            <div key={h.id} className="p-6 hover:bg-gray-50 transition-colors">
              <div className="flex items-start gap-4">
                <div className={`mt-1 w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-lg
                  ${h.type.includes('STOP') ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'}`}>
                  {h.type.includes('STOP') ? 'S' : 'T'}
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-bold text-gray-900 text-lg uppercase tracking-tight">{h.type.replace(/_/g, ' ')}</h4>
                      <p className="text-sm text-gray-500 font-medium">{new Date(h.occurred_at).toLocaleDateString()} &bull; {new Date(h.occurred_at).toLocaleTimeString()}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest
                      ${h.type.includes('STOP') ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'}`}>
                      {h.type.split('_')[0]}
                    </span>
                  </div>

                  <div className="mt-3 text-gray-700 font-medium">
                    {h.payload.title || h.payload.reason || "Automatic System Log"}
                  </div>

                  {renderPayload(h.payload)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
