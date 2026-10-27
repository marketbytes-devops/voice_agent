"use client";

import React from "react";
import { Phone, Clock, FileText, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { AudioPlayer } from "@/components/ui/AudioPlayer";
import { CallRecord } from "@/lib/mockData";

export function CallDetailPlayerSection({ call }: { call: CallRecord }) {
  return (
    <div className="space-y-6">
      {/* Overview Card */}
      <Card>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-white">{call.patientName}</h2>
              {call.patientNameMl && (
                <span className="text-sm text-emerald-400 font-malayalam font-medium">({call.patientNameMl})</span>
              )}
            </div>
            <div className="text-xs text-slate-400 font-mono mt-1">
              Caller ID: {call.callerNumber} • Duration: {call.durationSec}s • {call.timestamp}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant={call.language === "ml-IN" ? "malayalam" : "info"}>
              {call.language === "ml-IN" ? "മലയാളം (ml-IN)" : "English (en-IN)"}
            </Badge>
            <Badge variant={call.outcome === "Booked" ? "success" : "neutral"}>
              {call.outcome}
            </Badge>
          </div>
        </div>

        {/* AI Structured Summary */}
        <div className="mt-4">
          <div className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-emerald-400" /> AI Generated Summary & Booking Outcome:
          </div>
          <p className="text-sm text-slate-200 leading-relaxed bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
            {call.summary}
          </p>
        </div>

        {/* Audio Player */}
        <div className="mt-5">
          <div className="text-xs font-semibold text-slate-400 mb-2">Encrypted Audio Recording Playback:</div>
          <AudioPlayer
            callId={call.id}
            recordingKey={call.recordingKey}
            durationSec={call.durationSec}
            consentGiven={call.consentGiven}
            transcript={call.transcript}
            language={call.language}
          />
        </div>
      </Card>
    </div>
  );
}
