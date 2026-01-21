
import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost, apiPut } from "../api";

export default function PLCConfiguration() {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // null = list, {} = new, {id...} = edit
  const [error, setError] = useState("");

  const [activeTab, setActiveTab] = useState("CONFIG"); // CONFIG | TAGS

  useEffect(() => {
    loadConfigs();
  }, []);

  async function loadConfigs() {
    setLoading(true);
    try {
      const data = await apiGet("/plc/configs");
      setConfigs(data || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveConfig(cfg) {
    try {
      if (cfg.id) {
        await apiPut(`/plc/configs/${cfg.id}`, cfg);
      } else {
        await apiPost("/plc/configs", { ...cfg, site_code: "P01" }); // Default site code
      }
      setEditing(null);
      loadConfigs();
    } catch (e) {
      alert(e.message);
    }
  }

  async function handleDeleteConfig(id) {
    if (!confirm("Delete this PLC config?")) return;
    try {
      await apiDelete(`/plc/configs/${id}`);
      loadConfigs();
    } catch (e) {
      alert(e.message);
    }
  }
  
  async function handleTestConnection(cfg) {
     try {
       const res = await apiPost("/plc/test-connection", cfg);
       if(res.ok) alert("Connection Successful!");
       else alert("Connection Failed: " + res.error);
     } catch(e) {
       alert("Error: " + e.message);
     }
  }

  if (editing) {
     if(activeTab === 'TAGS' && editing.id) {
         return <PLCTagEditor plc={editing} onBack={() => setEditing(null)} />;
     }
     return (
        <PLCConfigForm 
            initialValues={editing} 
            onSave={handleSaveConfig} 
            onCancel={() => setEditing(null)} 
            onTest={handleTestConnection}
            onManageTags={() => setActiveTab('TAGS')}
        />
     );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">PLC Configuration</h1>
        <button
          onClick={() => { setEditing({}); setActiveTab('CONFIG'); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Add PLC
        </button>
      </div>

      {error && <div className="text-red-600 mb-4">{error}</div>}

      <div className="bg-white rounded shadow overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-100 border-b">
              <th className="p-4 font-semibold text-gray-600">Name</th>
              <th className="p-4 font-semibold text-gray-600">Protocol</th>
              <th className="p-4 font-semibold text-gray-600">Connection</th>
              <th className="p-4 font-semibold text-gray-600">Status</th>
              <th className="p-4 font-semibold text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody>
            {configs.map((c) => (
              <tr key={c.id} className="border-b hover:bg-gray-50">
                <td className="p-4">{c.name}</td>
                <td className="p-4">{c.protocol}</td>
                <td className="p-4">
                  {c.protocol === "MODBUS_TCP"
                    ? `${c.ip_address}:${c.port}`
                    : `${c.serial_port} @ ${c.baud_rate}`}
                </td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded text-xs ${c.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                    {c.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="p-4">
                  <button
                    onClick={() => { setEditing(c); setActiveTab('CONFIG'); }}
                    className="text-blue-600 hover:underline mr-4"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => { setEditing(c); setActiveTab('TAGS'); }}
                     className="text-purple-600 hover:underline mr-4"
                  >
                    Tags
                  </button>
                  <button
                    onClick={() => handleDeleteConfig(c.id)}
                    className="text-red-600 hover:underline"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {configs.length === 0 && !loading && (
              <tr>
                <td colSpan="5" className="p-4 text-center text-gray-500">
                  No PLCs configured.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PLCConfigForm({ initialValues, onSave, onCancel, onTest, onManageTags }) {
  const [form, setForm] = useState({
    site_code: "P01",
    name: "",
    protocol: "MODBUS_TCP",
    ip_address: "127.0.0.1",
    port: 502,
    serial_port: "COM1",
    baud_rate: 9600,
    slave_id: 1,
    scan_interval_sec: 5,
    is_active: true,
    ...initialValues,
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({
      ...form,
      [name]: type === "checkbox" ? checked : value,
    });
  };

  return (
    <div className="p-6 max-w-2xl mx-auto bg-white rounded shadow">
      <h2 className="text-xl font-bold mb-4">
        {initialValues.id ? "Edit PLC" : "New PLC"}
      </h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Name</label>
          <input
             name="name"
             value={form.name} 
             onChange={handleChange}
             className="mt-1 block w-full border border-gray-300 rounded p-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Protocol</label>
          <select
             name="protocol"
             value={form.protocol}
             onChange={handleChange}
             className="mt-1 block w-full border border-gray-300 rounded p-2"
          >
            <option value="MODBUS_TCP">Modbus TCP</option>
            <option value="MODBUS_RTU">Modbus RTU</option>
          </select>
        </div>

        {form.protocol === "MODBUS_TCP" ? (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">IP Address</label>
              <input
                 name="ip_address"
                 value={form.ip_address}
                 onChange={handleChange}
                 className="mt-1 block w-full border border-gray-300 rounded p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Port</label>
              <input
                 name="port"
                 type="number"
                 value={form.port}
                 onChange={handleChange}
                 className="mt-1 block w-full border border-gray-300 rounded p-2"
              />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
             <div>
              <label className="block text-sm font-medium text-gray-700">Serial Port</label>
              <input
                 name="serial_port"
                 value={form.serial_port}
                 onChange={handleChange}
                 className="mt-1 block w-full border border-gray-300 rounded p-2"
                 placeholder="e.g. COM3 or /dev/ttyUSB0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Baud Rate</label>
              <input
                 name="baud_rate"
                 type="number"
                 value={form.baud_rate}
                 onChange={handleChange}
                 className="mt-1 block w-full border border-gray-300 rounded p-2"
              />
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
             <div>
              <label className="block text-sm font-medium text-gray-700">Slave ID</label>
              <input
                 name="slave_id"
                 type="number"
                 value={form.slave_id}
                 onChange={handleChange}
                 className="mt-1 block w-full border border-gray-300 rounded p-2"
              />
            </div>
             <div>
              <label className="block text-sm font-medium text-gray-700">Scan Interval (sec)</label>
              <input
                 name="scan_interval_sec"
                 type="number"
                 value={form.scan_interval_sec}
                 onChange={handleChange}
                 className="mt-1 block w-full border border-gray-300 rounded p-2"
              />
            </div>
        </div>

        <div className="flex items-center">
            <input
                type="checkbox"
                name="is_active"
                checked={form.is_active}
                onChange={handleChange}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label className="ml-2 block text-sm text-gray-900">
                Active
            </label>
        </div>

      </div>

      <div className="mt-6 flex justify-between">
         <div>
            <button
                onClick={() => onTest(form)}
                className="bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600 mr-2"
            >
                Test Connection
            </button>
            {initialValues.id && (
                 <button
                    onClick={onManageTags}
                    className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
                >
                    Manage Tags
                </button>
            )}
         </div>
         <div>
            <button
                onClick={onCancel}
                className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300 mr-2"
            >
                Cancel
            </button>
             <button
                onClick={() => onSave(form)}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
                Save
            </button>
         </div>
      </div>
    </div>
  );
}

function PLCTagEditor({ plc, onBack }) {
    const [tags, setTags] = useState([]);
    const [loading, setLoading] = useState(true);
    const [formTag, setFormTag] = useState(getEmptyTag(plc.id));
    const [liveValues, setLiveValues] = useState({});

    useEffect(() => { loadTags(); }, [plc.id]);

    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const vals = await apiGet(`/plc/values/${plc.id}`);
                setLiveValues(vals || {});
            } catch(e) { console.error("Poll error", e); }
        }, 2000);
        return () => clearInterval(interval);
    }, [plc.id]);
    
    function getEmptyTag(plcId) {
        return {
            plc_id: plcId,
            tag_name: "",
            address: "", // default to empty string for input
            data_type: "BOOL",
            multiplier: 1.0,
            is_stop_trigger: false,
            trigger_value: 1.0,
            stop_reason_template: "",
            asset_id: ""
        };
    }

    async function loadTags() {
        setLoading(true);
        try { 
            const d = await apiGet(`/plc/tags/${plc.id}`);
            setTags(d || []);
        } catch(e) { alert(e.message); }
        finally { setLoading(false); }
    }

    async function handleSaveTag() {
        if(!formTag.tag_name) return alert("Tag Name required");
        
        // Parse numbers safely
        const payload = {
            ...formTag,
            address: parseInt(formTag.address),
            multiplier: parseFloat(formTag.multiplier),
            trigger_value: parseFloat(formTag.trigger_value)
        };
        
        if (isNaN(payload.address)) return alert("Address must be a valid number");

        try {
            if (formTag.id) {
                // Update
                await apiPut(`/plc/tags/${formTag.id}`, payload);
            } else {
                // Create
                await apiPost("/plc/tags", payload);
            }
            loadTags();
            setFormTag(getEmptyTag(plc.id));
        } catch(e) { alert(e.message); }
    }

    function handleEditTag(tag) {
        setFormTag({ ...tag });
    }

    function handleCancelEdit() {
        setFormTag(getEmptyTag(plc.id));
    }

    async function handleDeleteTag(id) {
        if(!confirm("Remove this tag?")) return;
        try {
            await apiDelete(`/plc/tags/${id}`);
            // If deleting the tag currently being edited, reset form
            if (formTag.id === id) {
                setFormTag(getEmptyTag(plc.id));
            }
            loadTags();
        } catch(e) { alert(e.message); }
    }

    return (
        <div className="p-6">
             <div className="flex items-center mb-6">
                <button onClick={onBack} className="text-blue-600 hover:underline mr-4">← Back</button>
                <h1 className="text-2xl font-bold text-gray-800">Tags for {plc.name}</h1>
             </div>

             <div className="mb-6 bg-gray-50 p-4 rounded border">
                <div className="flex justify-between items-center mb-2">
                    <h3 className="font-semibold">{formTag.id ? "Edit Tag" : "Add New Tag"}</h3>
                    {formTag.id && (
                        <button onClick={handleCancelEdit} className="text-xs text-red-600 hover:underline">Cancel Edit</button>
                    )}
                </div>
                
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <input placeholder="Tag Name" className="border p-2 rounded" value={formTag.tag_name} onChange={e => setFormTag({...formTag, tag_name: e.target.value})} />
                    <input type="number" placeholder="Address (e.g. 40001)" className="border p-2 rounded" value={formTag.address} onChange={e => setFormTag({...formTag, address: e.target.value})} />
                    <select className="border p-2 rounded" value={formTag.data_type} onChange={e => setFormTag({...formTag, data_type: e.target.value})}>
                        <option value="BOOL">BOOL</option>
                        <option value="INT16">INT16</option>
                        <option value="FLOAT32">FLOAT32</option>
                    </select>
                     <input type="number" placeholder="Multiplier" className="border p-2 rounded" value={formTag.multiplier} onChange={e => setFormTag({...formTag, multiplier: e.target.value})} />
                </div>
                <div className="mt-4 border-t pt-4">
                     <label className="flex items-center space-x-2">
                        <input type="checkbox" checked={formTag.is_stop_trigger} onChange={e => setFormTag({...formTag, is_stop_trigger: e.target.checked})} />
                        <span className="font-medium">Is Stop Trigger?</span>
                     </label>
                     
                     {formTag.is_stop_trigger && (
                        <div className="mt-2 grid grid-cols-1 lg:grid-cols-3 gap-4">
                            <input type="number" placeholder="Trigger Value" className="border p-2 rounded" value={formTag.trigger_value} onChange={e => setFormTag({...formTag, trigger_value: e.target.value})} />
                            <input placeholder="Asset ID" className="border p-2 rounded" value={formTag.asset_id || ""} onChange={e => setFormTag({...formTag, asset_id: e.target.value})} />
                            <input placeholder="Reason Template (Use $TagName)" className="border p-2 rounded" value={formTag.stop_reason_template || ""} onChange={e => setFormTag({...formTag, stop_reason_template: e.target.value})} />
                        </div>
                     )}
                </div>
                <button 
                    onClick={handleSaveTag} 
                    className={`mt-4 px-4 py-2 rounded text-white ${formTag.id ? "bg-purple-600 hover:bg-purple-700" : "bg-green-600 hover:bg-green-700"}`}
                >
                    {formTag.id ? "Update Tag" : "Add Tag"}
                </button>
             </div>

             <div className="bg-white rounded shadow text-sm">
                <table className="w-full text-left">
                    <thead className="bg-gray-100 border-b">
                        <tr>
                            <th className="p-3">Name</th>
                            <th className="p-3">Address</th>
                            <th className="p-3">Type</th>
                            <th className="p-3">Multiplier</th>
                            <th className="p-3">Trigger Info</th>
                            <th className="p-3">Live Value</th>
                            <th className="p-3">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tags.map(t => (
                            <tr key={t.id} className={`border-b ${formTag.id === t.id ? "bg-purple-50" : ""}`}>
                                <td className="p-3 font-medium">{t.tag_name}</td>
                                <td className="p-3">{t.address}</td>
                                <td className="p-3">{t.data_type}</td>
                                <td className="p-3">{t.multiplier}</td>
                                <td className="p-3">
                                    {t.is_stop_trigger ? (
                                        <div className="text-xs">
                                            <span className="font-bold text-orange-700 block">Trigger @ {t.trigger_value}</span>
                                            <span className="block text-gray-600">Asset: {t.asset_id || "-"}</span>
                                            <span className="block text-gray-500 italic">"{t.stop_reason_template}"</span>
                                        </div>
                                    ) : (
                                        <span className="text-gray-400 text-xs">Data Only</span>
                                    )}
                                </td>
                                <td className="p-3 font-mono font-bold text-blue-700">
                                    {liveValues[t.tag_name] !== undefined ? liveValues[t.tag_name] : "-"}
                                </td>
                                <td className="p-3">
                                    <button onClick={() => handleEditTag(t)} className="text-blue-600 hover:underline mr-3">Edit</button>
                                    <button onClick={() => handleDeleteTag(t.id)} className="text-red-600 hover:underline">Delete</button>
                                </td>
                            </tr>
                        ))}
                         {tags.length === 0 && <tr><td colSpan="6" className="p-4 text-center">No tags defined</td></tr>}
                    </tbody>
                </table>
             </div>
        </div>
    );
}
