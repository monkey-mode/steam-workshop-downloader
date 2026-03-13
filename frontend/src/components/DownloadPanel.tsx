"use client";

import { useRef, useState } from "react";
import { WorkshopItem, streamDownload, SseEvent } from "@/lib/api";
import { Download, X, Loader2, CheckCircle, AlertCircle, FolderOpen, Terminal, XCircle } from "lucide-react";

interface Props {
  selected: WorkshopItem[];
  onClear: () => void;
}

type Status = "idle" | "running" | "done" | "error";

export default function DownloadPanel({ selected, onClear }: Props) {
  const [outputDir, setOutputDir] = useState("./downloads");
  const [username, setUsername] = useState("anonymous");
  const [status, setStatus] = useState<Status>("idle");
  const [logs, setLogs] = useState<string[]>([]);
  const [resultPath, setResultPath] = useState("");
  const [showLog, setShowLog] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  if (selected.length === 0 && status === "idle") return null;

  const appendLog = (line: string) => {
    setLogs((prev) => [...prev, line]);
    setTimeout(() => logEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  };

  const handleDownload = async () => {
    if (selected.length === 0) return;
    const appId = selected[0].app_id;
    const ids = selected.map((i) => i.workshop_id);

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setStatus("running");
    setLogs([]);
    setResultPath("");
    setShowLog(true);

    try {
      await streamDownload(appId, ids, outputDir, username, (event: SseEvent) => {
        if (event.type === "log") {
          appendLog(event.line);
        } else if (event.type === "done") {
          setResultPath(event.path);
          setStatus("done");
          appendLog(`✓ Downloaded to: ${event.path}`);
        } else {
          appendLog(`✗ Error: ${event.line}`);
          setStatus("error");
        }
      }, ctrl.signal);
    } catch (e) {
      if (e instanceof Error && e.name !== "AbortError") {
        appendLog(`✗ ${e.message}`);
        setStatus("error");
      }
    }
  };

  const handleCancel = () => {
    abortRef.current?.abort();
    setStatus("idle");
  };

  const handleClose = () => {
    setStatus("idle");
    setLogs([]);
    setShowLog(false);
    onClear();
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-gray-700 bg-gray-900/95 backdrop-blur-sm">
      {/* Log terminal */}
      {showLog && logs.length > 0 && (
        <div className="max-w-6xl mx-auto px-4 pt-3">
          <div className="bg-gray-950 border border-gray-700 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-700 bg-gray-900">
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <Terminal className="w-3.5 h-3.5" />
                <span>SteamCMD output</span>
              </div>
              <button
                onClick={() => setShowLog(false)}
                className="text-gray-500 hover:text-gray-300 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="h-40 overflow-y-auto p-3 font-mono text-xs text-gray-300 space-y-0.5">
              {logs.map((line, i) => (
                <div
                  key={i}
                  className={
                    line.startsWith("✓")
                      ? "text-green-400"
                      : line.startsWith("✗")
                      ? "text-red-400"
                      : "text-gray-300"
                  }
                >
                  {line}
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        </div>
      )}

      {/* Controls bar */}
      <div className="max-w-6xl mx-auto px-4 py-3 flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="flex-1 min-w-0">
          {status === "idle" || status === "running" ? (
            <>
              <p className="text-sm font-medium text-white">
                {selected.length} item{selected.length !== 1 ? "s" : ""} selected
              </p>
              <p className="text-xs text-gray-400 truncate">
                {selected.map((i) => i.title).join(", ")}
              </p>
            </>
          ) : status === "done" ? (
            <p className="text-sm text-green-400 flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 shrink-0" />
              Download complete
            </p>
          ) : (
            <p className="text-sm text-red-400 flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4 shrink-0" />
              Download failed — see log above
            </p>
          )}
        </div>

        {/* Output dir + username — only shown when idle */}
        {status === "idle" && (
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
            <div className="flex items-center gap-2 w-full sm:w-52">
              <FolderOpen className="w-4 h-4 text-gray-400 shrink-0" />
              <input
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                placeholder="./downloads"
              />
            </div>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full sm:w-36 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              placeholder="Steam username"
              title="Use 'anonymous' for F2P games, or enter your Steam username for paid games"
            />
          </div>
        )}

        <div className="flex items-center gap-2">
          {/* Show log toggle if hidden */}
          {!showLog && logs.length > 0 && (
            <button
              onClick={() => setShowLog(true)}
              className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
              title="Show log"
            >
              <Terminal className="w-4 h-4" />
            </button>
          )}

          {status === "idle" && (
            <>
              <button
                onClick={onClear}
                className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
                title="Clear selection"
              >
                <X className="w-4 h-4" />
              </button>
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-sm transition-colors"
              >
                <Download className="w-4 h-4" />
                Download
              </button>
            </>
          )}

          {status === "running" && (
            <button
              onClick={handleCancel}
              className="flex items-center gap-2 px-4 py-2 bg-red-700 hover:bg-red-600 text-white rounded-lg font-medium text-sm transition-colors"
            >
              <XCircle className="w-4 h-4" />
              Cancel
            </button>
          )}

          {(status === "done" || status === "error") && (
            <button
              onClick={handleClose}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium text-sm transition-colors"
            >
              <X className="w-4 h-4" />
              Close
            </button>
          )}

          {status === "running" && (
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              Downloading...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
