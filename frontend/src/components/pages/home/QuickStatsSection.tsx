"use client";

import React from "react";
import { PhoneCall, CalendarCheck, Clock, Award } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { MOCK_CLINIC } from "@/lib/mockData";

export function QuickStatsSection() {
  const stats = [
    {
      label: "Calls Handled Today",
      value: MOCK_CLINIC.todayCallsCount,
      subtext: "100% Inbound 24/7 Answering",
      icon: PhoneCall,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
    },
    {
      label: "Appointments Booked",
      value: MOCK_CLINIC.todayAppointmentsCount,
      subtext: "Validated in DB Transaction",
      icon: CalendarCheck,
      color: "text-teal-400",
      bg: "bg-teal-500/10",
      border: "border-teal-500/20",
    },
    {
      label: "Pending Callback Tasks",
      value: MOCK_CLINIC.pendingCallbacksCount,
      subtext: "Created by Agent for Staff",
      icon: Clock,
      color: "text-amber-400",
      bg: "bg-amber-500/10",
      border: "border-amber-500/20",
    },
    {
      label: "AI Tool Precision",
      value: `${MOCK_CLINIC.agentAccuracy}%`,
      subtext: "0 Medical Hallucinations",
      icon: Award,
      color: "text-sky-400",
      bg: "bg-sky-500/10",
      border: "border-sky-500/20",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((s, i) => {
        const Icon = s.icon;
        return (
          <Card key={i} className={`p-5 flex items-center gap-4 ${s.border}`}>
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${s.bg}`}>
              <Icon className={`w-6 h-6 ${s.color}`} />
            </div>
            <div>
              <div className="text-2xl font-bold text-white tracking-tight">{s.value}</div>
              <div className="text-xs font-semibold text-slate-300">{s.label}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">{s.subtext}</div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
