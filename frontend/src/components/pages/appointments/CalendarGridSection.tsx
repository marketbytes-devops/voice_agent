"use client";

import React, { useState } from "react";
import { Calendar as CalendarIcon, Filter, CalendarX2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { AppointmentRecord, DoctorItem } from "@/lib/mockData";

interface CalendarGridSectionProps {
  appointments?: AppointmentRecord[];
  doctors?: DoctorItem[];
}

export function CalendarGridSection({
  appointments = [],
  doctors = [],
}: CalendarGridSectionProps) {
  const [selectedDoctor, setSelectedDoctor] = useState<string>("all");

  const displayAppointments = appointments;
  const displayDoctors = doctors;

  const filtered = selectedDoctor === "all"
    ? displayAppointments
    : displayAppointments.filter((a) => a.doctorName.toLowerCase().includes(selectedDoctor.toLowerCase()));

  return (
    <Card>
      <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4">
        <div>
          <CardTitle>
            <CalendarIcon className="w-5 h-5 text-emerald-400" />
            <span>Consultation Timetable Calendar</span>
          </CardTitle>
          <CardDescription>
            Live appointments booked by AI. Double bookings are protected via DB row locks.
          </CardDescription>
        </div>

        {/* Doctor Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={selectedDoctor}
            onChange={(e) => setSelectedDoctor(e.target.value)}
            className="bg-slate-900 border border-slate-800 text-xs text-white rounded-xl px-3 py-2 outline-none focus:border-emerald-500"
          >
            <option value="all">All Doctors</option>
            {displayDoctors.map((doc) => (
              <option key={doc.id} value={doc.name.toLowerCase()}>{doc.name}</option>
            ))}
          </select>
        </div>
      </CardHeader>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-950/60 text-xs text-slate-400 uppercase font-semibold border-b border-slate-800">
            <tr>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Patient</th>
              <th className="px-4 py-3">Phone</th>
              <th className="px-4 py-3">Doctor</th>
              <th className="px-4 py-3">Treatment</th>
              <th className="px-4 py-3 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                  <div className="flex flex-col items-center justify-center">
                    <CalendarX2 className="w-8 h-8 text-slate-600 mb-2" />
                    <p className="text-sm font-medium text-slate-400">No scheduled appointments found</p>
                    <p className="text-xs text-slate-500 mt-1">
                      Live bookings confirmed during phone calls will appear on this calendar grid.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map((appt) => (
                <tr key={appt.id} className="hover:bg-slate-900/40 transition-colors">
                  <td className="px-4 py-3.5 font-bold font-mono text-emerald-400 whitespace-nowrap">
                    {appt.timeStr}
                  </td>
                  <td className="px-4 py-3.5 font-semibold text-white">
                    {appt.patientName}
                  </td>
                  <td className="px-4 py-3.5 text-xs text-slate-400 font-mono">
                    {appt.patientPhone}
                  </td>
                  <td className="px-4 py-3.5 text-xs text-slate-300">
                    {appt.doctorName}
                  </td>
                  <td className="px-4 py-3.5 text-xs text-slate-400">
                    {appt.treatmentName}
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <Badge variant={appt.status === "confirmed" || appt.status === "booked" ? "success" : "warning"}>
                      {appt.status.toUpperCase()}
                    </Badge>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
