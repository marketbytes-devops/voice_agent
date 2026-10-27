"use client";

import React from "react";
import { Sparkles, Clock, Check } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export function TreatmentsSection() {
  const treatments = [
    {
      name: "Panchakarma Detox Therapy",
      nameMl: "പഞ്ചകർമ്മ ചികിത്സ",
      duration: "7 - 21 Days",
      desc: "Complete biological cleansing through Vamana, Virechana, Vasthi, Nasya, and Raktamokshana.",
      needsDoctorReview: true,
    },
    {
      name: "Shirodhara Relaxation",
      nameMl: "ശിരോധാര",
      duration: "45 Minutes",
      desc: "Continuous pouring of medicated herbal oils on the forehead for anxiety, insomnia, and migraines.",
      needsDoctorReview: false,
    },
    {
      name: "Njavarakizhi (Shashtika Sali Pinda Sweda)",
      nameMl: "ഞവരക്കിഴി",
      duration: "60 Minutes",
      desc: "Fermentation with medicated rice boluses for muscle wasting, rheumatism, and neurological issues.",
      needsDoctorReview: false,
    },
    {
      name: "Abhyangam Full Body Herbal Massage",
      nameMl: "അഭ്യംഗം",
      duration: "60 Minutes",
      desc: "Traditional Kerala full-body warm herbal oil therapy improving circulation and cellular vitality.",
      needsDoctorReview: false,
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>
          <Sparkles className="w-5 h-5 text-teal-400" />
          <span>Authorized Ayurvedic Treatments & Therapies</span>
        </CardTitle>
        <CardDescription>
          Treatments the AI agent can discuss with callers and schedule preliminary evaluations for.
        </CardDescription>
      </CardHeader>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {treatments.map((t, i) => (
          <div key={i} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2.5">
            <div className="flex items-start justify-between">
              <div>
                <h4 className="font-bold text-white text-sm">{t.name}</h4>
                <div className="text-xs text-teal-400 font-malayalam font-medium">{t.nameMl}</div>
              </div>
              <Badge variant="info" className="gap-1">
                <Clock className="w-3 h-3" /> {t.duration}
              </Badge>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">{t.desc}</p>

            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
              <span>{t.needsDoctorReview ? "Requires Doctor Consultation first" : "Directly Schedulable"}</span>
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <Check className="w-3.5 h-3.5" /> Approved
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
