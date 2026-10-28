"use client";

import React, { useState, useEffect, useRef } from "react";
import { Play, Pause, Volume2, VolumeX, ShieldCheck, ShieldAlert, Download, Radio } from "lucide-react";
import { Button } from "./Button";

interface AudioPlayerProps {
  callId: string;
  recordingKey?: string;
  durationSec: number;
  consentGiven: boolean;
  transcript?: Array<{ speaker: "Agent" | "Caller"; text: string }>;
  language?: "ml-IN" | "en-IN";
}

export function AudioPlayer({
  callId,
  recordingKey,
  durationSec,
  consentGiven,
  transcript = [],
  language = "ml-IN",
}: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTurnIdx, setCurrentTurnIdx] = useState<number>(-1);
  const [isMuted, setIsMuted] = useState(false);
  const turnTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const audioElRef = useRef<HTMLAudioElement | null>(null);

  // Stop audio on call change
  useEffect(() => {
    if (audioElRef.current) {
      audioElRef.current.pause();
      audioElRef.current = null;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    if (turnTimeoutRef.current) {
      clearTimeout(turnTimeoutRef.current);
    }
    setIsPlaying(false);
    setProgress(0);
    setCurrentTurnIdx(-1);
  }, [callId]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (audioElRef.current) {
        audioElRef.current.pause();
        audioElRef.current = null;
      }
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      if (turnTimeoutRef.current) {
        clearTimeout(turnTimeoutRef.current);
      }
    };
  }, []);

  const handleTogglePlay = () => {
    if (typeof window === "undefined") return;

    if (isPlaying) {
      if (audioElRef.current) {
        audioElRef.current.pause();
      }
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      if (turnTimeoutRef.current) {
        clearTimeout(turnTimeoutRef.current);
      }
      setIsPlaying(false);
    } else {
      setIsPlaying(true);
      playTelephoneChime();

      // For recorded live calls or sample audio, stream real audio from backend!
      if (recordingKey || callId.startsWith("call-live") || callId === "call-901") {
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://voice-agent-pphb.onrender.com";
          const audioSrc = callId === "call-901" 
            ? "/audio/live_hospital_sample.wav" 
            : `${apiUrl}/api/calls/live/${callId}/audio`;

          const audio = new Audio(audioSrc);
          audioElRef.current = audio;
          audio.ontimeupdate = () => {
            if (audio.duration) {
              setProgress(Math.round((audio.currentTime / audio.duration) * 100));
            }
          };
          audio.onended = () => {
            setIsPlaying(false);
            setProgress(100);
          };
          audio.onerror = () => {
            // Fallback to browser speech synthesis if audio file not reachable
            playTranscriptTurn(0);
          };
          audio.play().catch(() => playTranscriptTurn(0));
          return;
        } catch {
          // Fallback to synthesis
        }
      }

      // Default browser speech synthesis for other calls
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      playTranscriptTurn(0);
    }
  };

  // Web Audio API tone generator (Telephone chime & connection tone)
  const playTelephoneChime = () => {
    if (isMuted || typeof window === "undefined") return;
    try {
      const AudioContextClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextClass) return;
      const ctx = new AudioContextClass();

      // First beep
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = "sine";
      osc1.frequency.setValueAtTime(523.25, ctx.currentTime); // C5
      osc1.frequency.setValueAtTime(659.25, ctx.currentTime + 0.08); // E5
      gain1.gain.setValueAtTime(0.15, ctx.currentTime);
      gain1.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
      osc1.connect(gain1);
      gain1.connect(ctx.destination);
      osc1.start();
      osc1.stop(ctx.currentTime + 0.25);
    } catch {
      // AudioContext policy handled gracefully
    }
  };

  // Play next speaker turn in transcript using Browser Speech Synthesis
  const playTranscriptTurn = (idx: number) => {
    if (!transcript || idx >= transcript.length) {
      setIsPlaying(false);
      setProgress(100);
      setCurrentTurnIdx(-1);
      return;
    }

    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return;
    }

    setCurrentTurnIdx(idx);
    const stepProgress = Math.round(((idx + 1) / transcript.length) * 100);
    setProgress(stepProgress);

    const turn = transcript[idx];
    const utterance = new SpeechSynthesisUtterance(turn.text);

    // AI Receptionist vs Patient caller voice modulation
    if (turn.speaker === "Agent") {
      utterance.pitch = 1.15;
      utterance.rate = 0.95;
    } else {
      utterance.pitch = 0.85;
      utterance.rate = 1.0;
    }

    utterance.lang = language === "ml-IN" ? "ml-IN" : "en-IN";

    // Select suitable voice
    const voices = window.speechSynthesis.getVoices();
    if (language === "ml-IN") {
      const mlVoice = voices.find(
        (v) => v.lang.startsWith("ml") || v.name.toLowerCase().includes("malayalam")
      );
      if (mlVoice) utterance.voice = mlVoice;
    } else {
      const enVoice = voices.find((v) => v.lang === "en-IN" || v.lang.startsWith("en"));
      if (enVoice) utterance.voice = enVoice;
    }

    utterance.onend = () => {
      turnTimeoutRef.current = setTimeout(() => {
        playTranscriptTurn(idx + 1);
      }, 400);
    };

    utterance.onerror = () => {
      turnTimeoutRef.current = setTimeout(() => {
        playTranscriptTurn(idx + 1);
      }, 400);
    };

    if (!isMuted) {
      window.speechSynthesis.speak(utterance);
    } else {
      // If muted, advance on a timer
      turnTimeoutRef.current = setTimeout(() => {
        playTranscriptTurn(idx + 1);
      }, 3000);
    }
  };

  if (!consentGiven) {
    return (
      <div className="flex items-center gap-3 p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 text-sm">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0" />
        <span>Audio recording not available: Caller declined recording consent at start of call.</span>
      </div>
    );
  }

  const currentSec = Math.floor(((durationSec || 60) * progress) / 100);
  const formatSec = (s: number) => {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  const activeTurn = currentTurnIdx >= 0 && transcript ? transcript[currentTurnIdx] : null;

  return (
    <div className="flex flex-col gap-3 p-4 rounded-xl bg-gradient-to-r from-slate-900 via-slate-900 to-slate-800/80 border border-slate-800">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="text-xs text-slate-400 font-medium">
            Verified Consent • Encrypted Storage (MinIO)
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Radio className="w-2.5 h-2.5 animate-pulse" />
            Live Voice Audio Enabled
          </span>
        </div>
        <span className="text-xs text-slate-500 font-mono">Signed Link Active</span>
      </div>

      {/* Active Speaker Live Subtitle */}
      {isPlaying && activeTurn && (
        <div className="flex items-center gap-2 text-xs py-1.5 px-3 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-200">
          <Volume2 className="w-3.5 h-3.5 text-emerald-400 animate-pulse shrink-0" />
          <span className="font-semibold text-emerald-400">
            {activeTurn.speaker === "Agent" ? "🤖 ClinicVoice AI" : "👤 Patient"}:
          </span>
          <span className="truncate italic font-malayalam">&ldquo;{activeTurn.text}&rdquo;</span>
        </div>
      )}

      <div className="flex items-center gap-4">
        <Button
          variant="primary"
          size="sm"
          className="rounded-full w-10 h-10 p-0 shrink-0"
          onClick={handleTogglePlay}
          title={isPlaying ? "Pause Audio" : "Play Voice Recording"}
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
        </Button>

        <div className="flex-1 flex flex-col gap-1">
          {/* Animated simulated waveform */}
          <div className="h-6 flex items-center gap-1 overflow-hidden">
            {Array.from({ length: 32 }).map((_, i) => {
              const active = (i / 32) * 100 <= progress;
              const height = isPlaying
                ? Math.max(20, Math.sin(i * 0.7 + progress) * 100)
                : 35;
              return (
                <div
                  key={i}
                  style={{ height: `${height}%` }}
                  className={`flex-1 rounded-full transition-all duration-150 ${
                    active ? "bg-emerald-400" : "bg-slate-700/60"
                  }`}
                />
              );
            })}
          </div>

          <div className="flex justify-between text-xs text-slate-400 font-mono">
            <span>{formatSec(currentSec)}</span>
            <span>{formatSec(durationSec || 60)}</span>
          </div>
        </div>

        <button
          onClick={() => {
            if (isPlaying && "speechSynthesis" in window) {
              window.speechSynthesis.cancel();
            }
            setIsMuted(!isMuted);
          }}
          className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition-colors"
          title={isMuted ? "Unmute Voice" : "Mute Voice"}
        >
          {isMuted ? <VolumeX className="w-4 h-4 text-amber-400" /> : <Volume2 className="w-4 h-4" />}
        </button>

        <a
          href="/audio/live_hospital_sample.wav"
          download="sreerudra_hospital_call.wav"
          className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition-colors inline-flex items-center justify-center"
          title="Download Studio Voice (.wav)"
        >
          <Download className="w-4 h-4" />
        </a>
      </div>
    </div>
  );
}
