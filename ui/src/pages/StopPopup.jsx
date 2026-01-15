
import React, { useEffect, useState } from "react";
import { connectStopSSE } from "../sse";

export default function StopPopup() {
  const [last, setLast] = useState(null);

  useEffect(() => {
    const close = connectStopSSE((d) => {
      console.log("SSE Event:", d);
      setLast(d);
      // Auto-hide after 5 seconds
      setTimeout(() => setLast(null), 5000);
    });
    return () => close();
  }, []);

  if (!last) return null;

  const isResolved = last.type === "STOP_RESOLVED";
  const isOpen = last.type === "STOP_OPEN";
  const title = isResolved ? "Stop Resolved" : (isOpen ? "New Stop Alert" : "System Alert");
  const colorClass = isResolved ? "bg-green-50 border-green-500 text-green-900" : "bg-red-50 border-red-500 text-red-900";
  const borderClass = isResolved ? "border-l-4 border-green-500" : "border-l-4 border-red-500";

  // Parse details
  let details = "";
  if (isResolved) {
    // In resolved event we might only get ID, or we get what the backend sent.
    // Backend (ui_stop_queue.py) sends {"type":"STOP_RESOLVED", "stop_queue_id": sq.id}
    details = `Stop ID: ${last.stop_queue_id || 'Unknown'}`;
  } else if (isOpen) {
    // Backend (ingest.py/services.py) sends {"type":"STOP_OPEN","stop_id":...,"asset_id":...,"reason":...}
    details = `${last.asset_id || 'Asset'}: ${last.reason || 'Stop Event'}`;
  } else {
    details = typeof last === "object" ? JSON.stringify(last).slice(0, 100) : String(last);
  }

  return (
    <div className={`fixed bottom-4 right-4 z-50 w-80 shadow-lg rounded-lg overflow-hidden bg-white ${borderClass} animate-bounce-in`}>
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {isResolved ? (
              <svg className="h-6 w-6 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            )}
          </div>
          <div className="ml-3 w-0 flex-1 pt-0.5">
            <p className="text-sm font-medium text-gray-900">{title}</p>
            <p className="mt-1 text-sm text-gray-500 break-words">{details}</p>
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              className="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none"
              onClick={() => setLast(null)}
            >
              <span className="sr-only">Close</span>
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
