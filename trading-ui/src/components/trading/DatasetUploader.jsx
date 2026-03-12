import { useCallback, useMemo, useState } from "react";
import { CheckCircle, UploadCloud } from "lucide-react";
import toast from "react-hot-toast";

import StatusMessageCard from "../ui/StatusMessageCard";
import {
    apiGet,
    apiPostForm,
    buildApiErrorState,
} from "../../lib/api";
import { previewCsvHeaders } from "../../lib/candleData";

const UPLOAD_TIMEOUT_MS = 15000;
const DATASET_LOAD_TIMEOUT_MS = 30000;

export default function DatasetUploader({
    onUploadSuccess,
    appearance = "default",
    showSuccessToast = true,
}) {
    const [isDragging, setIsDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [datasetInfo, setDatasetInfo] = useState(null);
    const [errorState, setErrorState] = useState(null);
    const [lastFile, setLastFile] = useState(null);
    const [lastDatasetId, setLastDatasetId] = useState("");
    const [lastFileName, setLastFileName] = useState("");
    const isMonochrome = appearance === "monochrome";

    const handleDragEvent = useCallback((event) => {
        event.preventDefault();
        event.stopPropagation();
        if (event.type === "dragenter" || event.type === "dragover") {
            setIsDragging(true);
        } else if (event.type === "dragleave") {
            setIsDragging(false);
        }
    }, []);

    const updateSelectedAsset = useCallback((datasetId, fileName, rows = 0) => {
        if (!onUploadSuccess) {
            return;
        }

        onUploadSuccess({
            id: datasetId,
            symbol: fileName.replace(/\.csv$/i, "").toUpperCase(),
            market: "Custom Dataset",
            broker: "local",
            rows,
        });
    }, [onUploadSuccess]);

    const fetchDatasetInfo = useCallback(async (datasetId, fileName) => {
        setLastDatasetId(datasetId);
        setLastFileName(fileName);

        try {
            const info = await apiGet(`/dataset/${datasetId}`, {
                timeout: DATASET_LOAD_TIMEOUT_MS,
            });
            setDatasetInfo((current) => ({
                ...(current || {}),
                ...info,
                filename: info.filename || fileName,
                status: info.status || "ready",
            }));
            setErrorState(null);
            updateSelectedAsset(datasetId, fileName, info.rows || 0);
        } catch (error) {
            setErrorState({
                ...buildApiErrorState(error, "Dataset not loaded", "Unable to load dataset details."),
                action: "load",
            });
            console.error(error);
        }
    }, [updateSelectedAsset]);

    const handleFileSelect = useCallback(async (file) => {
        setLastFile(file);
        setErrorState(null);

        try {
            if (!file.name.toLowerCase().endsWith(".csv")) {
                throw new Error("Only CSV files are allowed.");
            }

            const headerPreview = await file.slice(0, 64 * 1024).text();
            previewCsvHeaders(headerPreview);

            setUploading(true);
            const formData = new FormData();
            formData.append("file", file);

            const uploadResponse = await apiPostForm("/upload-dataset", formData, {
                timeout: UPLOAD_TIMEOUT_MS,
            });
            const datasetId = uploadResponse?.dataset_id || uploadResponse?.id;

            if (!datasetId) {
                throw new Error("Upload completed, but the dataset id was missing.");
            }

            setLastDatasetId(datasetId);
            setLastFileName(file.name);
            setDatasetInfo({
                id: datasetId,
                dataset_id: datasetId,
                filename: uploadResponse.filename || file.name,
                rows: 0,
                start: null,
                end: null,
                status: uploadResponse.status || "uploaded",
            });
            updateSelectedAsset(datasetId, file.name, 0);
            if (showSuccessToast) {
                toast.success("Dataset uploaded successfully.");
            }
            void fetchDatasetInfo(datasetId, file.name);
        } catch (error) {
            setErrorState({
                ...buildApiErrorState(error, "Upload failed — retry", "Unable to upload dataset."),
                action: "upload",
            });
            console.error(error);
        } finally {
            setUploading(false);
        }
    }, [fetchDatasetInfo, updateSelectedAsset]);

    const handleDrop = useCallback((event) => {
        event.preventDefault();
        event.stopPropagation();
        setIsDragging(false);

        const file = event.dataTransfer.files?.[0];
        if (file) {
            void handleFileSelect(file);
        }
    }, [handleFileSelect]);

    const retryUpload = useCallback(() => {
        if (errorState?.action === "load" && lastDatasetId) {
            void fetchDatasetInfo(lastDatasetId, lastFileName || lastFile?.name || `${lastDatasetId}.csv`);
            return;
        }

        if (lastFile) {
            void handleFileSelect(lastFile);
        }
    }, [errorState?.action, fetchDatasetInfo, handleFileSelect, lastDatasetId, lastFile, lastFileName]);

    const handleReset = useCallback(() => {
        setDatasetInfo(null);
        setErrorState(null);
        setLastDatasetId("");
        setLastFileName("");
        if (onUploadSuccess) {
            onUploadSuccess(null);
        }
    }, [onUploadSuccess]);

    const errorCard = useMemo(() => {
        if (!errorState) {
            return null;
        }

        return (
            <StatusMessageCard
                title={errorState.title}
                description={errorState.description}
                actionLabel={errorState.action === "load" ? "Retry Load" : "Retry Upload"}
                onAction={retryUpload}
                tone={isMonochrome ? "neutral" : "error"}
            />
        );
    }, [errorState, isMonochrome, retryUpload]);

    if (datasetInfo) {
        return (
            <div className="space-y-3">
                <div
                    className={`group relative flex flex-col gap-3 rounded-xl border p-4 ${
                        isMonochrome
                            ? "border-[#2a2a2a] bg-[#111111]"
                            : "border-emerald-500/20 bg-emerald-500/5"
                    }`}
                >
                    <button
                        type="button"
                        onClick={handleReset}
                        className={`absolute top-2 right-2 p-1 opacity-0 transition-colors group-hover:opacity-100 hover:text-white ${
                            isMonochrome ? "text-white/45" : "text-textSecondary"
                        }`}
                        title="Remove dataset"
                    >
                        ×
                    </button>
                    <div className="flex items-center gap-3">
                        <div
                            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                                isMonochrome ? "bg-white/10 text-white" : "bg-emerald-500/20 text-emerald-500"
                            }`}
                        >
                            <CheckCircle size={16} />
                        </div>
                        <div>
                            <span className="block text-sm font-bold text-white">{datasetInfo.filename}</span>
                            <span className={`text-xs ${isMonochrome ? "text-white/70" : "text-emerald-400"}`}>
                                {datasetInfo.rows > 0
                                    ? `${datasetInfo.rows.toLocaleString()} rows dataset loaded`
                                    : "Dataset uploaded"}
                            </span>
                        </div>
                    </div>
                    <div className={`mt-1 flex gap-4 border-t pt-3 ${isMonochrome ? "border-white/10" : "border-emerald-500/10"}`}>
                        <div className="flex-1">
                            <span className={`mb-0.5 block text-[10px] ${isMonochrome ? "text-white/45" : "text-textSecondary"}`}>Start</span>
                            <span className="text-[11px] font-mono text-white/80">{datasetInfo.start?.split("T")[0] || "Loading"}</span>
                        </div>
                        <div className="flex-1">
                            <span className={`mb-0.5 block text-[10px] ${isMonochrome ? "text-white/45" : "text-textSecondary"}`}>End</span>
                            <span className="text-[11px] font-mono text-white/80">{datasetInfo.end?.split("T")[0] || "Loading"}</span>
                        </div>
                    </div>
                </div>
                {errorCard}
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {errorCard}
            <div
                onDragEnter={handleDragEvent}
                onDragLeave={handleDragEvent}
                onDragOver={handleDragEvent}
                onDrop={handleDrop}
                className={`
                    flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-all duration-200
                    ${isDragging
                        ? (isMonochrome ? "border-white bg-[#111111]" : "border-emerald-500 bg-emerald-500/5")
                        : (isMonochrome ? "border-[#2a2a2a] bg-[#111111] hover:border-white/30 hover:bg-[#151515]" : "border-white/10 bg-black/20 hover:border-white/20 hover:bg-black/40")
                    }
                    ${uploading ? "pointer-events-none opacity-50" : ""}
                `}
            >
                <input
                    type="file"
                    accept=".csv"
                    className="hidden"
                    id="dataset-upload"
                    onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) {
                            void handleFileSelect(file);
                        }
                    }}
                />

                <label htmlFor="dataset-upload" className="flex w-full cursor-pointer flex-col items-center">
                    <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-full transition-colors ${
                        isDragging
                            ? (isMonochrome ? "bg-white text-black" : "bg-emerald-500 text-black")
                            : (isMonochrome ? "bg-white/5 text-white/55" : "bg-white/5 text-textSecondary")
                    }`}>
                        {uploading ? <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" /> : <UploadCloud size={20} />}
                    </div>

                    <h4 className="mb-2 text-sm font-bold text-white">
                        {uploading ? "Uploading Dataset..." : "Upload CSV Dataset"}
                    </h4>

                    <p className={`mb-4 max-w-[220px] text-[11px] ${isMonochrome ? "text-white/55" : "text-textSecondary"}`}>
                        Drag and drop historical pricing data, or click to browse.
                    </p>

                    <div className={`flex flex-wrap items-center justify-center gap-2 font-mono text-[9px] ${isMonochrome ? "text-white/45" : "text-textSecondary/70"}`}>
                        <span className="rounded bg-white/5 px-2 py-0.5">timestamp</span>
                        <span className="rounded bg-white/5 px-2 py-0.5">open</span>
                        <span className="rounded bg-white/5 px-2 py-0.5">high</span>
                        <span className="rounded bg-white/5 px-2 py-0.5">low</span>
                        <span className="rounded bg-white/5 px-2 py-0.5">close</span>
                        <span className="rounded bg-white/5 px-2 py-0.5">volume</span>
                    </div>
                </label>
            </div>
        </div>
    );
}
