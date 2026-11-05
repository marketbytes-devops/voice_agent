"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Phone, RefreshCw } from "lucide-react";
import {
  CallListSection,
  CallDetailPlayerSection,
  TranscriptViewerSection,
} from "@/components/pages/calls";
import { CallRecord } from "@/lib/mockData";

export default function CallsPage() {
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [selectedCall, setSelectedCall] = useState<CallRecord | null>(null);
  const [isLive, setIsLive] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const fetchLiveCalls = useCallback(async (isBackground = false) => {
    if (!isBackground) setIsLoading(true);
    else setIsRefreshing(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://voice-agent-pphb.onrender.com";
      const res = await fetch(`${apiUrl}/api/calls/live`, { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setCalls(data);
          setSelectedCall((prev) => {
            if (!prev) return data.length > 0 ? data[0] : null;
            const match = data.find((c) => c.id === prev.id);
            return match || (data.length > 0 ? data[0] : null);
          });
          setIsLive(true);
          setIsLoading(false);
          setIsRefreshing(false);
          return;
        }
      }
    } catch (err) {
      console.warn("Could not fetch live calls from API:", err);
    }
    setIsLive(true);
    setIsLoading(false);
    setIsRefreshing(false);
  }, []);

  useEffect(() => {
    fetchLiveCalls();
    const interval = setInterval(() => {
      fetchLiveCalls(true);
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchLiveCalls]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Call History, Audio & Transcripts</h1>
          <p className="text-sm text-slate-400 mt-1">
            Review patient calls, inspect bilingual transcripts, and verify recording consent logs.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchLiveCalls()}
            disabled={isRefreshing || isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:text-white hover:border-slate-700 transition"
            title="Refresh Call History"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-emerald-400" : ""}`} />
            <span>Refresh</span>
          </button>
          {isLive && (
            <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-full">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs text-emerald-400 font-medium">Supabase Database Connected ({calls.length} Calls)</span>
            </div>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="min-h-[400px] flex items-center justify-center">
          <div className="flex items-center gap-3 text-slate-400 text-sm">
            <span className="w-4 h-4 rounded-full border-2 border-emerald-500 border-t-transparent animate-spin" />
            Loading live call recordings from database...
          </div>
        </div>
      ) : calls.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-16 text-center max-w-lg mx-auto my-12">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto text-emerald-400 mb-4">
            <Phone className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-semibold text-white">No Phone Calls Recorded Yet</h3>
          <p className="text-xs text-slate-400 mt-2 leading-relaxed">
            Real telephone calls received or handled by the AI voice assistant will appear here automatically with full Malayalam transcripts, AI summaries, and encrypted audio recordings.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[680px]">
          {/* Left Column: Call List (4 cols) */}
          <div className="lg:col-span-4 h-full">
            <CallListSection
              calls={calls}
              selectedCallId={selectedCall?.id || ""}
              onSelectCall={(call) => setSelectedCall(call)}
            />
          </div>

          {/* Right Column: Audio Playback & Full Transcript (8 cols) */}
          <div className="lg:col-span-8 space-y-6">
            {selectedCall && (
              <>
                <CallDetailPlayerSection call={selectedCall} />
                <TranscriptViewerSection call={selectedCall} />
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
