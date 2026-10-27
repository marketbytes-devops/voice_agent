"use client";

import React from "react";
import { MessageSquare, Bot, User } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { CallRecord } from "@/lib/mockData";

export function TranscriptViewerSection({ call }: { call: CallRecord }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>
          <MessageSquare className="w-5 h-5 text-emerald-400" />
          <span>Full Call Transcript</span>
        </CardTitle>
        <CardDescription>
          Synchronized turn-by-turn audio transcript (Malayalam & English).
        </CardDescription>
      </CardHeader>

      <div className="space-y-3.5 max-h-[380px] overflow-y-auto pr-2">
        {call.transcript.map((item, idx) => {
          const isAgent = item.speaker === "Agent";
          return (
            <div
              key={idx}
              className={`flex gap-3 ${isAgent ? "items-start" : "items-start flex-row-reverse"}`}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                  isAgent ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-800 text-slate-300"
                }`}
              >
                {isAgent ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
              </div>

              <div
                className={`max-w-[80%] rounded-2xl p-3.5 text-sm leading-relaxed ${
                  isAgent
                    ? "bg-slate-900 border border-slate-800 text-slate-200"
                    : "bg-emerald-950/40 border border-emerald-500/30 text-emerald-100"
                }`}
              >
                <div className="text-[10px] font-semibold text-slate-500 mb-1">
                  {isAgent ? "ClinicVoice AI" : "Caller"}
                </div>
                <div className="font-malayalam">{item.text}</div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
