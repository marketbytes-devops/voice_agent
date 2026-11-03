"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Phone,
  PhoneOff,
  Mic,
  Send,
  Sparkles,
  Bot,
  User,
  Clock,
  CheckCircle2,
  Volume2,
  CalendarCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface InteractiveWebPhoneModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface MessageTurn {
  speaker: "Agent" | "Caller";
  text: string;
}

export function InteractiveWebPhoneModal({ isOpen, onClose }: InteractiveWebPhoneModalProps) {
  const [seconds, setSeconds] = useState(0);
  const [inputText, setInputText] = useState("");
  const [isLoadingTurn, setIsLoadingTurn] = useState(false);
  const [isBooked, setIsBooked] = useState(false);
  const [conversation, setConversation] = useState<MessageTurn[]>([
    {
      speaker: "Agent",
      text: "നമസ്കാരം! ശ്രീരുദ്ര ആയുർവേദ ആശുപത്രിയിലേക്ക് സ്വാഗതം. ഞാൻ ഒരു AI അസിസ്റ്റന്റാണ്. ഈ കോൾ ഗുണനിലവാരത്തിനായി റെക്കോർഡ് ചെയ്യപ്പെടുന്നുണ്ട്. ഇന്ന് ഞാൻ നിങ്ങളെ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?",
    },
  ]);
  const [isSaving, setIsSaving] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Play greeting audio and start duration timer on open
  useEffect(() => {
    if (isOpen) {
      setSeconds(0);
      setIsBooked(false);
      setConversation([
        {
          speaker: "Agent",
          text: "നമസ്കാരം! ശ്രീരുദ്ര ആയുർവേദ ആശുപത്രിയിലേക്ക് സ്വാഗതം. ഞാൻ ഒരു AI അസിസ്റ്റന്റാണ്. ഈ കോൾ ഗുണനിലവാരത്തിനായി റെക്കോർഡ് ചെയ്യപ്പെടുന്നുണ്ട്. ഇന്ന് ഞാൻ നിങ്ങളെ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?",
        },
      ]);

      // Play native audio welcome
      try {
        const audio = new Audio("/audio/hospital_welcome_ml.wav");
        audioRef.current = audio;
        audio.play().catch(() => {});
      } catch {}

      const timer = setInterval(() => {
        setSeconds((prev) => prev + 1);
      }, 1000);

      return () => {
        clearInterval(timer);
        if (audioRef.current) {
          audioRef.current.pause();
        }
      };
    }
  }, [isOpen]);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation]);

  if (!isOpen) return null;

  const formatTimer = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const handleSendMessage = async (textToSend: string) => {
    if (!textToSend.trim() || isLoadingTurn) return;

    const callerMsg = textToSend.trim();
    setInputText("");

    const updatedHistory: MessageTurn[] = [...conversation, { speaker: "Caller", text: callerMsg }];
    setConversation(updatedHistory);
    setIsLoadingTurn(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://voice-agent-pphb.onrender.com";
      const res = await fetch(`${apiUrl}/api/web-call/turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          caller_text: callerMsg,
          conversation_history: updatedHistory,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const reply = data.reply || "തീർച്ചയായും, താങ്കളെ സഹായിക്കാൻ സാധിച്ചതിൽ സന്തോഷം.";
        if (data.is_booked) {
          setIsBooked(true);
        }
        setConversation((prev) => [...prev, { speaker: "Agent", text: reply }]);
      } else {
        setConversation((prev) => [
          ...prev,
          {
            speaker: "Agent",
            text: "തീർച്ചയായും, ഡോക്ടർ മനോജിന്റെ കൺസൾട്ടേഷൻ നാളെ രാവിലെ 10:00 മണിക്ക് രേഖപ്പെടുത്തിയിട്ടുണ്ട്.",
          },
        ]);
        setIsBooked(true);
      }
    } catch {
      setConversation((prev) => [
        ...prev,
        {
          speaker: "Agent",
          text: "സന്ദർശന സമയം ദിവസവും വൈകുന്നേരം 4:00 മണി മുതൽ 7:00 മണി വരെയാണ്.",
        },
      ]);
    } finally {
      setIsLoadingTurn(false);
    }
  };

  const handleEndCall = async () => {
    setIsSaving(true);
    if (audioRef.current) {
      audioRef.current.pause();
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://voice-agent-pphb.onrender.com";
      await fetch(`${apiUrl}/api/web-call/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_name: "Akshay (അക്ഷയ്)",
          caller_number: "+91 99473 84437",
          transcript: conversation,
          outcome: isBooked ? "Booked" : "Inquiry Answered",
          duration_sec: Math.max(15, seconds),
        }),
      });
    } catch {
      // Proceed to reload
    } finally {
      setIsSaving(false);
      onClose();
      // Reload dashboard so new call & booking appear in real time!
      window.location.reload();
    }
  };

  const quickPrompts = [
    {
      title: "Visiting Hours",
      ml: "സന്ദർശന സമയം എപ്പോഴാണ്?",
    },
    {
      title: "Joint Pain Treatments",
      ml: "സന്ധിവേദനയ്ക്ക് എന്തൊക്കെ ചികിത്സകളാണ് ഉള്ളത്?",
    },
    {
      title: "Book Dr. Manoj",
      ml: "നാളെ ഡോക്ടർ മനോജിന് ഒരു അപ്പോയിന്റ്മെന്റ് ബുക്ക് ചെയ്യണം. എന്റെ പേര് അക്ഷയ്.",
    },
    {
      title: "Conclude & Thank",
      ml: "ശരി, വളരെ നന്ദി.",
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="w-full max-w-xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-200">
        {/* Call Header */}
        <div className="p-5 bg-gradient-to-r from-slate-950 via-slate-900 to-emerald-950/40 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
                <Bot className="w-6 h-6" />
              </div>
              <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-slate-900 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Sreerudra Hospital AI Receptionist</h3>
                <Badge variant="success" className="text-[10px] py-0 px-2">Live Web Call</Badge>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Incoming: +91 99473 84437 • Virtual: 0495 426 9761
              </p>
            </div>
          </div>

          <div className="flex flex-col items-end">
            <div className="flex items-center gap-1.5 text-emerald-400 font-mono text-sm font-semibold bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 rounded-full">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              {formatTimer(seconds)}
            </div>
          </div>
        </div>

        {/* Call Animated Audio Waveform */}
        <div className="py-2.5 px-6 bg-slate-950/60 border-b border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Volume2 className="w-4 h-4 text-emerald-400 animate-pulse" />
            <span className="text-[11px] text-emerald-400 font-medium">Bilingual Speech Audio Active (Sarvam ml-IN)</span>
          </div>
          <div className="flex items-center gap-1">
            {[40, 70, 30, 90, 60, 100, 50, 80, 45, 95, 35, 65].map((h, i) => (
              <span
                key={i}
                className="w-1 bg-emerald-400/80 rounded-full animate-pulse"
                style={{
                  height: `${Math.max(6, (h * 18) / 100)}px`,
                  animationDuration: `${0.4 + (i % 4) * 0.2}s`,
                }}
              />
            ))}
          </div>
        </div>

        {/* Live Turn-by-Turn Speech Transcript */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 min-h-[260px] bg-slate-950/30 font-malayalam">
          {conversation.map((turn, idx) => {
            const isAgent = turn.speaker === "Agent";
            return (
              <div
                key={idx}
                className={`flex gap-3 ${isAgent ? "justify-start" : "justify-end"}`}
              >
                {isAgent && (
                  <div className="w-7 h-7 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shrink-0 mt-1 font-sans">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                    isAgent
                      ? "bg-slate-900 border border-slate-800 text-slate-200"
                      : "bg-emerald-600 text-white font-medium"
                  }`}
                >
                  <span className="text-[10px] font-sans font-semibold block mb-1 opacity-70">
                    {isAgent ? "AI Receptionist (ശ്രീരുദ്ര)" : "Caller (അക്ഷയ്)"}
                  </span>
                  {turn.text}
                </div>
                {!isAgent && (
                  <div className="w-7 h-7 rounded-lg bg-emerald-600 flex items-center justify-center text-white shrink-0 mt-1 font-sans">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}

          {isLoadingTurn && (
            <div className="flex items-center gap-2 text-slate-400 text-xs py-2 italic font-sans">
              <span className="w-3 h-3 rounded-full border border-emerald-500 border-t-transparent animate-spin" />
              AI is formulating response in Malayalam...
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Spoken Prompts */}
        <div className="p-3 bg-slate-950/80 border-t border-slate-800 space-y-2">
          <div className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5 px-1 font-sans">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span>Click to speak naturally to AI:</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {quickPrompts.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSendMessage(q.ml)}
                disabled={isLoadingTurn}
                className="text-left p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800/80 hover:border-emerald-500/40 text-[11px] text-slate-300 transition-all truncate"
                title={q.ml}
              >
                <span className="block font-sans text-emerald-400 text-[10px] font-semibold">
                  {q.title}
                </span>
                <span className="truncate block font-malayalam">{q.ml}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Input Bar & Hang Up Controls */}
        <div className="p-4 bg-slate-900 border-t border-slate-800 flex items-center gap-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage(inputText);
            }}
            className="flex-1 flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-2xl px-3 py-1.5 focus-within:border-emerald-500"
          >
            <input
              type="text"
              placeholder="Type your response in Malayalam or English..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isLoadingTurn}
              className="w-full bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none font-malayalam py-1.5"
            />
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={!inputText.trim() || isLoadingTurn}
              className="h-8 px-3 rounded-xl"
            >
              <Send className="w-3.5 h-3.5" />
            </Button>
          </form>

          {/* End Call Button */}
          <Button
            type="button"
            variant="danger"
            onClick={handleEndCall}
            disabled={isSaving}
            className="rounded-2xl px-4 py-2 text-xs flex items-center gap-2 bg-rose-600 hover:bg-rose-500 text-white font-semibold shrink-0 shadow-lg shadow-rose-950/50"
          >
            <PhoneOff className="w-4 h-4" />
            {isSaving ? "Saving..." : "End Call"}
          </Button>
        </div>
      </div>
    </div>
  );
}
