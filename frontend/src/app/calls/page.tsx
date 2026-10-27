"use client";

import React, { useState } from "react";
import {
  CallListSection,
  CallDetailPlayerSection,
  TranscriptViewerSection,
} from "@/components/pages/calls";
import { MOCK_CALLS, CallRecord } from "@/lib/mockData";

export default function CallsPage() {
  const [selectedCall, setSelectedCall] = useState<CallRecord>(MOCK_CALLS[0]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Call History, Audio & Transcripts</h1>
        <p className="text-sm text-slate-400 mt-1">
          Review patient calls, inspect bilingual transcripts, and verify recording consent logs.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[680px]">
        {/* Left Column: Call List (4 cols) */}
        <div className="lg:col-span-4 h-full">
          <CallListSection
            calls={MOCK_CALLS}
            selectedCallId={selectedCall.id}
            onSelectCall={(call) => setSelectedCall(call)}
          />
        </div>

        {/* Right Column: Audio Playback & Full Transcript (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          <CallDetailPlayerSection call={selectedCall} />
          <TranscriptViewerSection call={selectedCall} />
        </div>
      </div>
    </div>
  );
}
