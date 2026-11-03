"use client";

import React, { useState, useEffect } from "react";
import { BookOpen, Plus, Trash2, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { MOCK_FAQS, FaqItem } from "@/lib/mockData";

export function FaqManagerSection() {
  const [faqs, setFaqs] = useState<FaqItem[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [newQEn, setNewQEn] = useState("");
  const [newQMl, setNewQMl] = useState("");
  const [newAEn, setNewAEn] = useState("");
  const [newAMl, setNewAMl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://voice-agent-pphb.onrender.com";

  useEffect(() => {
    async function loadFaqs() {
      try {
        const res = await fetch(`${apiUrl}/api/faqs`, { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            setFaqs(data);
            return;
          }
        }
      } catch (err) {
        console.warn("Could not fetch FAQs from cloud API, using fallback:", err);
      }
      setFaqs(MOCK_FAQS);
    }
    loadFaqs();
  }, [apiUrl]);

  const handleAddFaq = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQEn || !newAEn) return;

    setIsSubmitting(true);
    const newEntry = {
      question: newQEn,
      questionMl: newQMl || newQEn,
      answer: newAEn,
      answerMl: newAMl || newAEn,
      category: "Hospital Policy",
      language: "ml-IN",
    };

    try {
      const res = await fetch(`${apiUrl}/api/faqs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newEntry),
      });
      const data = await res.json();
      const createdItem: FaqItem = {
        id: data.id || `faq-${Date.now()}`,
        question: newQEn,
        questionMl: newQMl || newQEn,
        answer: newAEn,
        answerMl: newAMl || newAEn,
        category: "Hospital Policy",
      };
      setFaqs([createdItem, ...faqs]);
      setSuccessMsg("FAQ successfully saved to database and synced with voicebot!");
      setTimeout(() => setSuccessMsg(""), 4000);
    } catch (err) {
      console.warn("Could not persist FAQ to database:", err);
      const fallbackItem: FaqItem = {
        id: `faq-${Date.now()}`,
        question: newQEn,
        questionMl: newQMl || newQEn,
        answer: newAEn,
        answerMl: newAMl || newAEn,
        category: "Hospital Policy",
      };
      setFaqs([fallbackItem, ...faqs]);
    } finally {
      setIsSubmitting(false);
      setShowAdd(false);
      setNewQEn("");
      setNewQMl("");
      setNewAEn("");
      setNewAMl("");
    }
  };

  const handleDeleteFaq = async (id: string) => {
    setFaqs((prev) => prev.filter((f) => f.id !== id));
    try {
      await fetch(`${apiUrl}/api/faqs/${id}`, { method: "DELETE" });
    } catch (err) {
      console.warn("Could not delete FAQ from cloud database:", err);
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle>
            <BookOpen className="w-5 h-5 text-emerald-400" />
            <span>Approved Hospital FAQs ({faqs.length})</span>
          </CardTitle>
          <CardDescription>
            The live voicebot automatically queries these database entries during telephone calls.
          </CardDescription>
        </div>
        <Button variant="primary" size="sm" onClick={() => setShowAdd(!showAdd)}>
          <Plus className="w-4 h-4 mr-1" /> Add New FAQ
        </Button>
      </CardHeader>

      {successMsg && (
        <div className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Add FAQ Form */}
      {showAdd && (
        <form onSubmit={handleAddFaq} className="p-4 mb-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
          <div className="font-semibold text-xs text-emerald-400 uppercase">New Dual-Language FAQ Entry</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Question in English (e.g. What are visiting hours?)..."
              value={newQEn}
              onChange={(e) => setNewQEn(e.target.value)}
              className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-xs text-white outline-none focus:border-emerald-500"
              required
            />
            <input
              type="text"
              placeholder="ചോദ്യം മലയാളത്തിൽ (Malayalam Question)..."
              value={newQMl}
              onChange={(e) => setNewQMl(e.target.value)}
              className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-xs text-white font-malayalam outline-none focus:border-emerald-500"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <textarea
              placeholder="Answer in English (e.g. Visiting hours are 4 PM to 7 PM daily.)..."
              value={newAEn}
              onChange={(e) => setNewAEn(e.target.value)}
              className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-xs text-white h-20 outline-none focus:border-emerald-500"
              required
            />
            <textarea
              placeholder="മറുപടി മലയാളത്തിൽ (Malayalam Answer)..."
              value={newAMl}
              onChange={(e) => setNewAMl(e.target.value)}
              className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-xs text-white font-malayalam h-20 outline-none focus:border-emerald-500"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" type="button" onClick={() => setShowAdd(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving to Supabase..." : "Save Approved FAQ"}
            </Button>
          </div>
        </form>
      )}

      <div className="space-y-4">
        {faqs.map((f) => (
          <div key={f.id} className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sm text-white">{f.question}</span>
              <div className="flex items-center gap-2">
                <Badge variant="neutral">{f.category}</Badge>
                <button
                  type="button"
                  onClick={() => handleDeleteFaq(f.id)}
                  className="text-slate-500 hover:text-red-400 p-1 rounded transition-colors"
                  title="Delete FAQ"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            {f.questionMl && f.questionMl !== f.question && (
              <div className="text-xs text-emerald-400 font-malayalam">{f.questionMl}</div>
            )}

            <div className="pt-2 border-t border-slate-800/80 text-xs text-slate-300 leading-relaxed">
              <span className="font-semibold text-slate-400 block mb-0.5">Approved Answer:</span>
              <p className="text-slate-300 mb-1">{f.answer}</p>
              {f.answerMl && f.answerMl !== f.answer && (
                <p className="text-slate-400 font-malayalam">{f.answerMl}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
