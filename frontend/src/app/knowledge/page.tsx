"use client";

import React from "react";
import { FaqManagerSection, TreatmentsSection } from "@/components/pages/knowledge";

export default function KnowledgeBasePage() {
  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Hospital Knowledge Base</h1>
        <p className="text-sm text-slate-400 mt-1">
          Manage approved Ayurvedic treatments, therapy packages, and dual-language FAQs.
        </p>
      </div>

      <TreatmentsSection />
      <FaqManagerSection />
    </div>
  );
}
