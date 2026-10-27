"use client";

import React, { useState } from "react";
import { Sliders, Volume2, ShieldCheck, PhoneForwarded } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export function VoiceModelSection() {
  const [speaker, setSpeaker] = useState("meera");
  const [vadDuration, setVadDuration] = useState(250);
  const [fallbackPhone, setFallbackPhone] = useState("+91 477 225 1234");

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>
          <Sliders className="w-5 h-5 text-teal-400" />
          <span>Telephony & Voice Provider Configuration</span>
        </CardTitle>
        <CardDescription>
          Fine-tune voice timbre, speech interruption threshold, and human receptionist fallback number.
        </CardDescription>
      </CardHeader>

      <div className="space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">
              Malayalam Voice Model (Sarvam Bulbul):
            </label>
            <select
              value={speaker}
              onChange={(e) => setSpeaker(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-xs text-white outline-none focus:border-emerald-500"
            >
              <option value="meera">Meera (Warm, Professional Kerala Female Voice)</option>
              <option value="ananya">Ananya (Clear, Modern Multilingual Voice)</option>
              <option value="arvind">Arvind (Calm Kerala Male Voice)</option>
            </select>
            <span className="text-[11px] text-slate-500 mt-1 block">Default voice selected for Sreerudra callers.</span>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">
              Human Reception Fallback Phone (E.164):
            </label>
            <input
              type="text"
              value={fallbackPhone}
              onChange={(e) => setFallbackPhone(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-xs text-white font-mono outline-none focus:border-emerald-500"
            />
            <span className="text-[11px] text-slate-500 mt-1 block">Calls are transferred here if agent encounters errors or caller insists on human.</span>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs font-semibold text-slate-300">
              Interruption VAD Sensitivity: {vadDuration}ms
            </label>
            <span className="text-xs text-emerald-400 font-mono">Recommended: 250ms</span>
          </div>
          <input
            type="range"
            min={150}
            max={600}
            step={25}
            value={vadDuration}
            onChange={(e) => setVadDuration(Number(e.target.value))}
            className="w-full accent-emerald-500"
          />
          <div className="flex justify-between text-[11px] text-slate-500 mt-1">
            <span>Fast Barge-in (150ms)</span>
            <span>Balanced (250ms)</span>
            <span>Filters Coughs/Hum (600ms)</span>
          </div>
        </div>
      </div>
    </Card>
  );
}
