"use client";

import React, { useState, useEffect } from "react";
import { Calendar, User, Clock, ArrowUpRight } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { MOCK_APPOINTMENTS, AppointmentRecord } from "@/lib/mockData";
import Link from "next/link";

export function TodayAppointmentsSection() {
  const [appointments, setAppointments] = useState<AppointmentRecord[]>(MOCK_APPOINTMENTS.slice(0, 4));

  useEffect(() => {
    async function fetchTodayAppointments() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://voice-agent-pphb.onrender.com";
        const res = await fetch(`${apiUrl}/api/appointments`, { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            setAppointments(data.slice(0, 4));
          }
        }
      } catch (err) {
        console.warn("Could not fetch today appointments from cloud API:", err);
      }
    }
    fetchTodayAppointments();
  }, []);

  return (
    <Card className="flex-1">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle>
            <Calendar className="w-5 h-5 text-emerald-400" />
            <span>Today's Verified Appointments</span>
          </CardTitle>
          <CardDescription>
            Appointments booked by AI voice receptionist against doctor schedules.
          </CardDescription>
        </div>
        <Link
          href="/appointments"
          className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1 transition-colors"
        >
          View Calendar <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </CardHeader>

      <div className="divide-y divide-slate-800/80">
        {appointments.map((appt) => (
          <div key={appt.id} className="py-3.5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-slate-300 font-semibold text-xs shrink-0">
                <Clock className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <div className="font-semibold text-sm text-slate-100 flex items-center gap-2">
                  <span>{appt.patientName}</span>
                  <span className="text-xs text-slate-500 font-normal">({appt.patientPhone})</span>
                </div>
                <div className="text-xs text-slate-400 mt-0.5">
                  <span className="text-emerald-400 font-medium">{appt.doctorName}</span> • {appt.treatmentName}
                </div>
              </div>
            </div>

            <div className="text-right shrink-0">
              <div className="text-sm font-bold text-slate-200">{appt.timeStr}</div>
              <Badge variant={appt.status === "confirmed" ? "success" : "warning"} className="mt-1">
                {appt.status.toUpperCase()}
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
