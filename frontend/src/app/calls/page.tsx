"use client";

import React, { useState, useEffect } from "react";
import {
  CallListSection,
  CallDetailPlayerSection,
  TranscriptViewerSection,
} from "@/components/pages/calls";
import { MOCK_CALLS, CallRecord } from "@/lib/mockData";

export default function CallsPage() {
  const [calls, setCalls] = useState<CallRecord[]>(MOCK_CALLS);
  const [selectedCall, setSelectedCall] = useState<CallRecord>(MOCK_CALLS[0]);
  const [isLive, setIsLive] = useState<boolean>(false);

  useEffect(() => {
    async function fetchLiveCalls() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://voice-agent-pphb.onrender.com";
        const res = await fetch(`${apiUrl}/api/calls/live`, { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            setCalls(data);
            setSelectedCall(data[0]);
            setIsLive(true);
          }
        }
      } catch (err) {
        console.warn("Could not fetch live calls from cloud API, using fallback:", err);
      }
    }
    fetchLiveCalls();
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Call History, Audio & Transcripts</h1>
          <p className="text-sm text-slate-400 mt-1">
            Review patient calls, inspect bilingual transcripts, and verify recording consent logs.
          </p>
        </div>
        {isLive && (
          <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-full">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-emerald-400 font-medium">Live Connected ({calls.length} Calls)</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[680px]">
        {/* Left Column: Call List (4 cols) */}
        <div className="lg:col-span-4 h-full">
          <CallListSection
            calls={calls}
            selectedCallId={selectedCall?.id}
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
    </div>
  );
}
