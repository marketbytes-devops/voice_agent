"use client";

import React from "react";
import { UserCheck, Clock, Award, ShieldCheck } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { MOCK_DOCTORS } from "@/lib/mockData";

export function DoctorScheduleSection() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>
          <UserCheck className="w-5 h-5 text-emerald-400" />
          <span>Active Ayurvedic Physicians & Duty Schedules</span>
        </CardTitle>
        <CardDescription>
          Timetables synced with voice agent slot calculations. Breaks and leave are guarded automatically.
        </CardDescription>
      </CardHeader>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {MOCK_DOCTORS.map((doc) => (
          <div key={doc.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h4 className="font-bold text-white text-base">{doc.name}</h4>
                <div className="text-xs text-emerald-400 font-medium">{doc.qualification}</div>
              </div>
              <Badge variant="success">Active</Badge>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {doc.specialties.map((spec, i) => (
                <span key={i} className="text-[11px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded-md">
                  {spec}
                </span>
              ))}
            </div>

            <div className="text-xs text-slate-400 flex items-center gap-1.5 pt-2 border-t border-slate-800/80">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span>{doc.workingHours}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
