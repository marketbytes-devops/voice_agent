"use client";

import React from "react";
import Link from "next/link";
import { PhoneCall, ShieldCheck, ShieldAlert, ArrowUpRight } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { MOCK_CALLS } from "@/lib/mockData";

export function RecentCallsSection() {
  return (
    <Card className="flex-1">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle>
            <PhoneCall className="w-5 h-5 text-teal-400" />
            <span>Recent Inbound Calls</span>
          </CardTitle>
          <CardDescription>
            Live call recordings, language detection, and AI outcomes.
          </CardDescription>
        </div>
        <Link
          href="/calls"
          className="text-xs text-teal-400 hover:text-teal-300 font-semibold flex items-center gap-1 transition-colors"
        >
          All Calls & Audio <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </CardHeader>

      <div className="divide-y divide-slate-800/80">
        {MOCK_CALLS.map((call) => (
          <div key={call.id} className="py-3.5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-teal-400 font-semibold shrink-0">
                <PhoneCall className="w-4 h-4" />
              </div>
              <div>
                <div className="font-semibold text-sm text-slate-100 flex items-center gap-2">
                  <span>{call.patientName}</span>
                  {call.patientNameMl && (
                    <span className="text-xs text-teal-400 font-malayalam">({call.patientNameMl})</span>
                  )}
                </div>
                <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-2">
                  <span>{call.callerNumber}</span>
                  <span>•</span>
                  <span>{call.durationSec}s</span>
                  <span>•</span>
                  <span>{call.timestamp}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2.5 shrink-0">
              <Badge variant={call.language === "ml-IN" ? "malayalam" : "info"}>
                {call.language === "ml-IN" ? "മലയാളം (ml)" : "English (en)"}
              </Badge>
              <Badge variant={call.outcome === "Booked" ? "success" : "neutral"}>
                {call.outcome}
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
