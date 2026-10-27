"use client";

import React, { useState } from "react";
import { Search, Phone, ShieldCheck, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { CallRecord } from "@/lib/mockData";

interface CallListSectionProps {
  calls: CallRecord[];
  selectedCallId: string;
  onSelectCall: (call: CallRecord) => void;
}

export function CallListSection({ calls, selectedCallId, onSelectCall }: CallListSectionProps) {
  const [search, setSearch] = useState("");

  const filtered = calls.filter(
    (c) =>
      c.callerNumber.includes(search) ||
      c.patientName.toLowerCase().includes(search.toLowerCase()) ||
      (c.patientNameMl && c.patientNameMl.includes(search))
  );

  return (
    <div className="flex flex-col h-full bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-slate-800 bg-slate-950/40">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search by phone, name (English/Malayalam)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60">
        {filtered.map((call) => {
          const isSelected = call.id === selectedCallId;
          return (
            <div
              key={call.id}
              onClick={() => onSelectCall(call)}
              className={`p-4 cursor-pointer transition-colors ${
                isSelected ? "bg-emerald-500/10 border-l-4 border-emerald-500" : "hover:bg-slate-800/40"
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-semibold text-sm text-slate-100">{call.patientName}</span>
                <span className="text-[11px] text-slate-500">{call.timestamp}</span>
              </div>

              {call.patientNameMl && (
                <div className="text-xs text-emerald-400 font-malayalam mb-1">{call.patientNameMl}</div>
              )}

              <div className="flex items-center justify-between mt-2 text-xs text-slate-400">
                <span className="font-mono">{call.callerNumber}</span>
                <div className="flex items-center gap-1.5">
                  <Badge variant={call.language === "ml-IN" ? "malayalam" : "info"}>
                    {call.language === "ml-IN" ? "മലയാളം" : "English"}
                  </Badge>
                  <Badge variant={call.outcome === "Booked" ? "success" : "neutral"}>
                    {call.outcome}
                  </Badge>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
