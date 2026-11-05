"use client";

import React from "react";
import Link from "next/link";
import { Bell, Mic, Search, ShieldCheck, UserCheck } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { MOCK_CLINIC } from "@/lib/mockData";

export function Topbar() {
  return (
    <header className="h-16 border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-xl px-8 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-4">
        <div>
          <span className="text-sm font-semibold text-white">{MOCK_CLINIC.name}</span>
          <span className="text-xs text-slate-400 ml-2">({MOCK_CLINIC.location})</span>
        </div>
        <Badge variant="success" className="gap-1.5 hidden sm:inline-flex">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          Active Reception Line: {MOCK_CLINIC.virtualNumber}
        </Badge>
      </div>

      <div className="flex items-center gap-4">
        <Link
          href="/test-call"
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-400 text-xs font-semibold shadow-sm transition-all"
        >
          <Mic className="w-3.5 h-3.5 animate-pulse text-emerald-400" />
          <span>Test AI Voice Call</span>
        </Link>

        <div className="flex items-center gap-2 pl-3 border-l border-slate-800">
          <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-semibold text-emerald-400">
            SR
          </div>
          <div className="text-left hidden md:block">
            <div className="text-xs font-semibold text-slate-200">Reception Desk</div>
            <div className="text-[10px] text-slate-400">Role: Receptionist</div>
          </div>
        </div>
      </div>
    </header>
  );
}
