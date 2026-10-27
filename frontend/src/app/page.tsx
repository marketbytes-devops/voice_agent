import React from "react";
import {
  QuickStatsSection,
  LiveAgentStatusSection,
  TodayAppointmentsSection,
  RecentCallsSection,
  CallbackTasksSection,
} from "@/components/pages/home";

export default function HomePage() {
  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* 1. Quick High-Level Metrics */}
      <QuickStatsSection />

      {/* 2. Live Agent Status & Quick Simulator */}
      <LiveAgentStatusSection />

      {/* 3 & 4. Today's Appointments & Recent Calls (Side by Side) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TodayAppointmentsSection />
        <RecentCallsSection />
      </div>

      {/* 5. Reception Callback Tasks */}
      <CallbackTasksSection />
    </div>
  );
}
