"use client";

import React, { useState } from "react";
import { MessageSquare, Save, Check } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export function AgentGreetingSection() {
  const [greetingMl, setGreetingMl] = useState(
    "നമസ്കാരം! ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റലിലേക്ക് സ്വാഗതം. ഞാൻ ഒരു എ.ഐ അസിസ്റ്റന്റ് ആണ്. സേവന നിലവാരം ഉറപ്പുവരുത്തുന്നതിനായി ഈ കോൾ റെക്കോർഡ് ചെയ്തോട്ടെ?"
  );
  const [greetingEn, setGreetingEn] = useState(
    "Hello! Welcome to Sreerudra Ayurveda Hospital. How can I assist you today? May we record this call for quality purposes?"
  );
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>
          <MessageSquare className="w-5 h-5 text-emerald-400" />
          <span>Inbound Call Greetings & AI Disclosure</span>
        </CardTitle>
        <CardDescription>
          By law and clinic policy, every call states AI identity and requests recording consent upfront.
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-1.5">
            Malayalam Greeting (മലയാളം സ്വാഗതം):
          </label>
          <textarea
            value={greetingMl}
            onChange={(e) => setGreetingMl(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-white font-malayalam leading-relaxed h-24 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-1.5">
            English Greeting:
          </label>
          <textarea
            value={greetingEn}
            onChange={(e) => setGreetingEn(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-white leading-relaxed h-20 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-slate-500 font-mono">Changes take effect on the next incoming call.</span>
          <Button variant="primary" size="sm" type="submit">
            {saved ? <Check className="w-4 h-4 mr-1 text-white" /> : <Save className="w-4 h-4 mr-1" />}
            {saved ? "Saved & Deployed" : "Save Greeting"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
