/**
 * CreateSessionModal.jsx  (FXReplay MVP)
 * ----------------------------------------
 * Modal for creating a new trading session.
 *
 * Fields:
 *   - Session name
 *   - Account balance
 *   - Asset selector (BrokerAssetSelector — market → broker → symbol)
 *   - Start date
 *   - End date
 *
 * On submit: POST /sessions → navigate to /session/{id}
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { X, Calendar, DollarSign, FileText, ChevronRight } from "lucide-react";
import toast from "react-hot-toast";
import {
    apiPost,
    getApiErrorMessage,
    getConnectivityMessage,
    isServerUnavailableError,
} from "../../lib/api";
import DatasetUploader from "../trading/DatasetUploader";

export default function CreateSessionModal({ isOpen, onClose, onSessionCreated }) {
    const navigate = useNavigate();

    const [name,      setName]      = useState("");
    const [balance,   setBalance]   = useState(10000);
    const [startDate, setStartDate] = useState("2022-01-01");
    const [endDate,   setEndDate]   = useState("2024-12-31");
    const [loading,   setLoading]   = useState(false);

    // selectedAsset: { id, symbol, broker, market, rows } | null
    const [selectedAsset, setSelectedAsset] = useState(null);

    const canSubmit = selectedAsset && name.trim() && !loading;

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!selectedAsset) { toast.error("Select an asset first."); return; }

        setLoading(true);
        const t = toast.loading("Creating session...");
        try {
            const payload = {
                session_name: name.trim() || `${selectedAsset.symbol} Session`,
                broker:       selectedAsset.broker,
                symbol:       selectedAsset.id, // using dataset ID
                balance:      Number(balance),
                start_date:   startDate ? new Date(startDate).toISOString() : null,
                end_date:     endDate   ? new Date(endDate).toISOString()   : null,
            };
            const res = await apiPost("/sessions", payload);
            toast.dismiss(t);
            toast.success("Session created!");
            onSessionCreated?.(res);
            onClose();
            navigate(`/session/${res.id}`);
        } catch (err) {
            toast.dismiss(t);
            toast.error(
                isServerUnavailableError(err)
                    ? getConnectivityMessage()
                    : getApiErrorMessage(err, "Failed to create session."),
            );
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm">
            <div className="bg-[#111] border border-white/8 rounded-2xl w-full max-w-lg shadow-2xl flex flex-col overflow-hidden">

                {/* Header */}
                <div className="px-6 py-5 border-b border-white/5 flex items-center justify-between bg-[#141414]">
                    <div>
                        <h2 className="text-sm font-bold text-white tracking-tight">New Trading Session</h2>
                        <p className="text-[11px] text-textSecondary mt-0.5">Select an asset and configure your session parameters</p>
                    </div>
                    <button onClick={onClose} className="text-textSecondary hover:text-white transition-colors p-1">
                        <X size={16} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-6 overflow-y-auto max-h-[80vh] custom-scrollbar">

                    {/* Asset Selector */}
                    <div>
                        <h3 className="text-[10px] font-bold text-textSecondary uppercase tracking-widest mb-3">Upload Dataset</h3>
                        <DatasetUploader onUploadSuccess={setSelectedAsset} />
                    </div>

                    {/* Selected asset info */}
                    {selectedAsset && (
                        <div className="flex items-center gap-3 px-4 py-3 bg-emerald-500/5 border border-emerald-500/20 rounded-xl">
                            <div className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                            <div>
                                <span className="text-sm font-bold text-white">{selectedAsset.symbol}</span>
                                <span className="text-xs text-emerald-400 ml-2">— DATASET</span>
                            </div>
                        </div>
                    )}

                    {/* Session name */}
                    <div>
                        <label className="text-[10px] font-bold text-textSecondary uppercase tracking-widest mb-2 flex items-center gap-1.5 block">
                            <FileText size={10} /> Session Name
                        </label>
                        <input
                            type="text"
                            value={name}
                            onChange={e => setName(e.target.value)}
                            placeholder={selectedAsset ? `${selectedAsset.symbol} Research` : "e.g. Q1 2024 EURUSD Study"}
                            className="w-full bg-[#0a0a0a] border border-white/8 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-emerald-500/40 transition-colors"
                        />
                    </div>

                    {/* Balance */}
                    <div>
                        <label className="text-[10px] font-bold text-textSecondary uppercase tracking-widest mb-2 flex items-center gap-1.5 block">
                            <DollarSign size={10} /> Starting Balance
                        </label>
                        <div className="relative">
                            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-textSecondary text-sm">$</span>
                            <input
                                type="number" min={100} step={100}
                                value={balance} onChange={e => setBalance(e.target.value)}
                                className="w-full bg-[#0a0a0a] border border-white/8 rounded-xl pl-8 pr-4 py-3 text-sm text-white focus:outline-none focus:border-emerald-500/40 transition-colors"
                            />
                        </div>
                    </div>

                    {/* Date range */}
                    <div>
                        <label className="text-[10px] font-bold text-textSecondary uppercase tracking-widest mb-2 flex items-center gap-1.5 block">
                            <Calendar size={10} /> Historical Range
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <span className="text-[10px] text-textSecondary mb-1 block">Start Date</span>
                                <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}
                                    className="w-full bg-[#0a0a0a] border border-white/8 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500/40 transition-colors" />
                            </div>
                            <div>
                                <span className="text-[10px] text-textSecondary mb-1 block">End Date</span>
                                <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
                                    className="w-full bg-[#0a0a0a] border border-white/8 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500/40 transition-colors" />
                            </div>
                        </div>
                    </div>

                    {/* Submit */}
                    <div className="flex items-center justify-end gap-3 pt-2 border-t border-white/5">
                        <button type="button" onClick={onClose}
                            className="px-4 py-2 text-xs font-bold text-textSecondary hover:text-white transition-colors">
                            CANCEL
                        </button>
                        <button type="submit" disabled={!canSubmit}
                            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold tracking-wide transition-all duration-150 ${
                                canSubmit
                                ? "bg-emerald-500 text-black hover:bg-emerald-400"
                                : "bg-white/5 text-textSecondary cursor-not-allowed"
                            }`}>
                            {loading ? "Creating..." : "Start Session"}
                            {!loading && <ChevronRight size={13} />}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
