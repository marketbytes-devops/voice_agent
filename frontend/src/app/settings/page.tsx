"use client";

import React from "react";
import { AgentGreetingSection, VoiceModelSection } from "@/components/pages/settings";

export default function SettingsPage() {
  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">AI Receptionist Settings</h1>
        <p className="text-sm text-slate-400 mt-1">
          Configure bilingual greetings, AI disclosures, voice timbres, and interruption sensitivity.
        </p>
      </div>

      <AgentGreetingSection />
      <VoiceModelSection />
    </div>
  );
}
