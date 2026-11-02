"use client";

import React, { useState, useEffect } from "react";
import { DoctorScheduleSection, CalendarGridSection } from "@/components/pages/appointments";
import { MOCK_APPOINTMENTS, MOCK_DOCTORS, AppointmentRecord, DoctorItem } from "@/lib/mockData";

export default function AppointmentsPage() {
  const [doctors, setDoctors] = useState<DoctorItem[]>(MOCK_DOCTORS);
  const [appointments, setAppointments] = useState<AppointmentRecord[]>(MOCK_APPOINTMENTS);
  const [isLive, setIsLive] = useState<boolean>(false);

  useEffect(() => {
    async function fetchLiveData() {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://voice-agent-pphb.onrender.com";
      try {
        const [docRes, apptRes] = await Promise.all([
          fetch(`${apiUrl}/api/doctors`, { cache: "no-store" }),
          fetch(`${apiUrl}/api/appointments`, { cache: "no-store" })
        ]);

        if (docRes.ok) {
          const docData = await docRes.json();
          if (Array.isArray(docData) && docData.length > 0) {
            setDoctors(docData);
            setIsLive(true);
          }
        }

        if (apptRes.ok) {
          const apptData = await apptRes.json();
          if (Array.isArray(apptData) && apptData.length > 0) {
            setAppointments(apptData);
            setIsLive(true);
          }
        }
      } catch (err) {
        console.warn("Could not fetch live doctors/appointments from cloud API, using fallback:", err);
      }
    }
    fetchLiveData();
  }, []);

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Doctor Timetables & Appointments</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time appointment schedule for Sreerudra Ayurveda Hospital physicians.
          </p>
        </div>
        {isLive && (
          <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-full">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-emerald-400 font-medium">Supabase Database Connected ({doctors.length} Doctors)</span>
          </div>
        )}
      </div>

      <DoctorScheduleSection doctors={doctors} />
      <CalendarGridSection appointments={appointments} doctors={doctors} />
    </div>
  );
}
