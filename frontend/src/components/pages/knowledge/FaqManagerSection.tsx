"use client";

import React, { useState } from "react";
import { BookOpen, Plus, Globe } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { MOCK_FAQS, FaqItem } from "@/lib/mockData";

export function FaqManagerSection() {
  const [faqs, setFaqs] = useState<FaqItem[]>(MOCK_FAQS);
  const [showAdd, setShowAdd] = useState(false);
  const [newQEn, setNewQEn] = useState("");
  const [newQMl, setNewQMl] = useState("");
  const [newAEn, setNewAEn] = useState("");
  const [newAMl, setNewAMl] = useState("");

  const handleAddFaq = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQEn || !newAEn) return;

    const created: FaqItem = {
      id: `faq-${Date.now()}`,
      question: newQEn,
      questionMl: newQMl || newQEn,
      answer: newAEn,
      answerMl: newAMl || newAEn,
      category: "General",
    };
    setFaqs([created, ...faqs]);
    setShowAdd(false);
    setNewQEn("");
    setNewQMl("");
    setNewAEn("");
    setNewAMl("");
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle>
            <BookOpen className="w-5 h-5 text-emerald-400" />
            <span>Approved Hospital FAQs (English & Malayalam)</span>
          </CardTitle>
          <CardDescription>
            The voice agent ONLY answers questions from these approved entries. It never hallucinates policies.
          </CardDescription>
        </div>
        <Button variant="primary" size="sm" onClick={() => setShowAdd(!showAdd)}>
          <Plus className="w-4 h-4 mr-1" /> Add New FAQ
        </Button>
      </CardHeader>

      {/* Add FAQ Form */}
      {showAdd && (
        <form onSubmit={handleAddFaq} className="p-4 mb-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
          <div className="font-semibold text-xs text-emerald-400 uppercase">New Dual-Language FAQ Entry</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Question in English..."
              value={newQEn}
              onChange={(e) => setNewQEn(e.target.value)}
              className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-xs text-white"
              required
            />
            <input
              type="text"
              placeholder="ചോദ്യം മലയാളത്തിൽ (Malayalam Question)..."
              value={newQMl}
              onChange={(e) => setNewQMl(e.target.value)}
              className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-xs text-white font-malayalam"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <textarea
              placeholder="Answer in English..."
              value={newAEn}
              onChange={(e) => setNewAEn(e.target.value)}
              className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-xs text-white h-20"
              required
            />
            <textarea
              placeholder="മറുപടി മലയാളത്തിൽ (Malayalam Answer)..."
              value={newAMl}
              onChange={(e) => setNewAMl(e.target.value)}
              className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-xs text-white font-malayalam h-20"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" type="button" onClick={() => setShowAdd(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Save Approved FAQ
            </Button>
          </div>
        </form>
      )}

      <div className="space-y-4">
        {faqs.map((f) => (
          <div key={f.id} className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sm text-white">{f.question}</span>
              <Badge variant="neutral">{f.category}</Badge>
            </div>
            <div className="text-xs text-emerald-400 font-malayalam">{f.questionMl}</div>

            <div className="pt-2 border-t border-slate-800/80 text-xs text-slate-300 leading-relaxed">
              <span className="font-semibold text-slate-400 block mb-0.5">Approved Answer:</span>
              <p className="text-slate-300 mb-1">{f.answer}</p>
              <p className="text-slate-400 font-malayalam">{f.answerMl}</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
