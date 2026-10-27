"use client";

import React from "react";
import { DoctorScheduleSection, CalendarGridSection } from "@/components/pages/appointments";

export default function AppointmentsPage() {
  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Doctor Timetables & Appointments</h1>
        <p className="text-sm text-slate-400 mt-1">
          Real-time appointment schedule for Sreerudra Ayurveda Hospital physicians.
        </p>
      </div>

      <DoctorScheduleSection />
      <CalendarGridSection />
    </div>
  );
}
