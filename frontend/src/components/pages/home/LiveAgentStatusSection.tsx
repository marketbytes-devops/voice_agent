"use client";

import React, { useState } from "react";
import { Bot, PhoneForwarded, Radio, Sparkles, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { MOCK_CLINIC } from "@/lib/mockData";

export function LiveAgentStatusSection() {
  const [testingCall, setTestingCall] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const handleTestCall = () => {
    setTestingCall(true);
    setTestResult(null);
    setTimeout(() => {
      setTestingCall(false);
      setTestResult("Simulated inbound call connected! Audio streaming in Malayalam (ml-IN) & English (en-IN).");
    }, 1200);
  };

  return (
    <Card className="border-emerald-500/30 bg-gradient-to-r from-slate-900 via-slate-900 to-emerald-950/20">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">AI Voice Receptionist (Live)</h3>
                <Badge variant="success" className="animate-pulse">Active 24/7</Badge>
              </div>
              <p className="text-xs text-slate-400">
                Connected to Exotel Virtual Trunk • LiveKit Audio Worker • Sarvam AI Malayalam Engine
              </p>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-300 font-malayalam leading-relaxed">
            <span className="text-emerald-400 font-sans font-semibold text-[11px] block mb-1">
              Active Bilingual Greeting:
            </span>
            "നമസ്കാരം! ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റലിലേക്ക് സ്വാഗതം. ഞാൻ ഒരു എ.ഐ അസിസ്റ്റന്റ് ആണ്. Hello! Welcome to Sreerudra Ayurveda Hospital."
          </div>

          {testResult && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              <span>{testResult}</span>
            </div>
          )}
        </div>

        <div className="flex flex-col sm:flex-row lg:flex-col gap-3 shrink-0">
          <Button
            variant="primary"
            onClick={handleTestCall}
            disabled={testingCall}
            className="w-full sm:w-auto"
          >
            <Radio className="w-4 h-4 mr-2 text-white animate-pulse" />
            {testingCall ? "Connecting Voice Session..." : "Simulate Test Call Now"}
          </Button>

          <div className="text-[11px] text-slate-500 text-center lg:text-right font-mono">
            Fallback Number: +91 477 225 1234
          </div>
        </div>
      </div>
    </Card>
  );
}
