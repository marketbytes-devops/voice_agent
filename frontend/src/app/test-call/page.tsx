"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Mic,
  MicOff,
  PhoneCall,
  PhoneOff,
  Volume2,
  VolumeX,
  Bot,
  User,
  Sparkles,
  RotateCcw,
  ShieldCheck,
  CheckCircle2,
  Activity,
  AlertCircle,
  Send,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface TranscriptTurn {
  id: string;
  speaker: "Agent" | "Caller";
  text: string;
  turnType?: string;
  timestamp: string;
}

// 16kHz 16-bit Mono PCM WAV Encoder
function writeString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // Linear PCM
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return buffer;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

export default function TestCallPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [callState, setCallState] = useState<"idle" | "connecting" | "listening" | "transcribing" | "thinking" | "speaking">("idle");
  const [transcripts, setTranscripts] = useState<TranscriptTurn[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [volumeLevel, setVolumeLevel] = useState(0);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [textInput, setTextInput] = useState("");

  const socketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const activeAudioRef = useRef<HTMLAudioElement | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  // VAD and PCM recording refs
  const pcmChunksRef = useRef<Float32Array[]>([]);
  const isSpeakingRef = useRef(false);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isAgentSpeakingRef = useRef(false);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      endCall();
    };
  }, []);

  // Instant client-side barge-in: Stop AI audio immediately when user begins talking
  const triggerBargeIn = useCallback(() => {
    if (activeAudioRef.current && !activeAudioRef.current.paused) {
      console.log("Client-side barge-in: Halting AI audio playback instantly.");
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
      isAgentSpeakingRef.current = false;
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ event: "user_interrupted" }));
      }
    }
  }, []);

  // Play audio WAV chunk received from Sarvam TTS
  const playAgentAudio = useCallback((base64Audio: string) => {
    if (!base64Audio) return;
    try {
      if (activeAudioRef.current) {
        activeAudioRef.current.pause();
        activeAudioRef.current = null;
      }

      const audioSrc = `data:audio/wav;base64,${base64Audio}`;
      const audio = new Audio(audioSrc);
      activeAudioRef.current = audio;
      isAgentSpeakingRef.current = true;
      setCallState("speaking");

      audio.onended = () => {
        isAgentSpeakingRef.current = false;
        activeAudioRef.current = null;
        setCallState("listening");
      };

      audio.onerror = () => {
        isAgentSpeakingRef.current = false;
        activeAudioRef.current = null;
        setCallState("listening");
      };

      audio.play().catch((err) => {
        console.warn("Audio autoplay blocked or interrupted:", err);
        isAgentSpeakingRef.current = false;
        setCallState("listening");
      });
    } catch (e) {
      console.error("Error playing audio chunk:", e);
      isAgentSpeakingRef.current = false;
      setCallState("listening");
    }
  }, []);

  // Send collected user speech WAV to backend
  const sendRecordedUtterance = useCallback(() => {
    if (pcmChunksRef.current.length === 0) return;

    // Calculate total sample count
    let totalLength = 0;
    for (const chunk of pcmChunksRef.current) {
      totalLength += chunk.length;
    }

    // Ignore tiny audio blips (< 0.25 seconds at 16kHz)
    if (totalLength < 16000 * 0.25) {
      pcmChunksRef.current = [];
      return;
    }

    // Flatten chunks into a single Float32Array
    const mergedSamples = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of pcmChunksRef.current) {
      mergedSamples.set(chunk, offset);
      offset += chunk.length;
    }
    pcmChunksRef.current = [];

    // Encode to 16kHz 16-bit Mono WAV
    const wavBuffer = encodeWav(mergedSamples, 16000);
    const wavB64 = arrayBufferToBase64(wavBuffer);

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      setCallState("transcribing");
      socketRef.current.send(
        JSON.stringify({
          event: "user_audio",
          audio_base64: wavB64,
        })
      );
    }
  }, []);

  // Start Call & initialize Web Audio VAD
  const startCall = async () => {
    setErrorMessage(null);
    setCallState("connecting");
    setTranscripts([]);

    try {
      // 1. Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      // 2. Setup AudioContext and PCM VAD Processor
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);
      // 4096 buffer size = ~256ms audio slices at 16kHz
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);

        // Calculate Root Mean Square (RMS) volume
        let sumSquares = 0;
        for (let i = 0; i < input.length; i++) {
          sumSquares += input[i] * input[i];
        }
        const rms = Math.sqrt(sumSquares / input.length) * 100;
        setVolumeLevel(Math.min(100, Math.round(rms * 4.5)));

        const SPEECH_THRESHOLD = 2.2;
        const isLoud = rms >= SPEECH_THRESHOLD;

        // User is actively speaking
        if (isLoud) {
          // If agent was speaking, interrupt immediately!
          if (isAgentSpeakingRef.current) {
            triggerBargeIn();
          }

          if (!isSpeakingRef.current) {
            isSpeakingRef.current = true;
            setIsUserSpeaking(true);
            setCallState("listening");
          }

          // Buffer audio chunk
          pcmChunksRef.current.push(new Float32Array(input));

          // Cancel silence timer
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
          }
        } else if (isSpeakingRef.current) {
          // Caller paused: buffer chunk and monitor for end-of-speech silence (600ms)
          pcmChunksRef.current.push(new Float32Array(input));

          if (!silenceTimerRef.current) {
            silenceTimerRef.current = setTimeout(() => {
              isSpeakingRef.current = false;
              setIsUserSpeaking(false);
              silenceTimerRef.current = null;
              sendRecordedUtterance();
            }, 600); // 600ms pause indicates natural end of sentence
          }
        }
      };

      source.connect(processor);
      processor.connect(ctx.destination);

      // 3. Connect WebSocket to backend
      const wsUrl =
        typeof window !== "undefined" && window.location.hostname === "localhost"
          ? "ws://localhost:8000/api/voice/web-call"
          : "wss://voice-agent-pphb.onrender.com/api/voice/web-call";

      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setCallState("connecting");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const ev = data.event;

          if (ev === "status") {
            setCallState(data.state);
          } else if (ev === "user_transcript") {
            setTranscripts((prev) => [
              ...prev,
              {
                id: `user-${Date.now()}`,
                speaker: "Caller",
                text: data.text,
                timestamp: new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }),
              },
            ]);
            setCallState("thinking");
          } else if (ev === "agent_speech") {
            const replyText = data.text || "";
            setTranscripts((prev) => [
              ...prev,
              {
                id: `bot-${Date.now()}`,
                speaker: "Agent",
                text: replyText,
                turnType: data.turn_type,
                timestamp: new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }),
              },
            ]);

            if (data.audio_base64) {
              playAgentAudio(data.audio_base64);
            } else {
              setCallState("listening");
            }
          }
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        setErrorMessage("Could not connect to voice server. Verify backend is running.");
        endCall();
      };

      ws.onclose = () => {
        setIsConnected(false);
        setCallState("idle");
      };
    } catch (err: unknown) {
      console.error("Microphone permission or connection failure:", err);
      const msg = err instanceof Error ? err.message : "Microphone permission denied.";
      setErrorMessage(`${msg}. Please allow microphone permissions in your browser.`);
      setCallState("idle");
    }
  };

  // End Call & Cleanup
  const endCall = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    isSpeakingRef.current = false;
    isAgentSpeakingRef.current = false;
    pcmChunksRef.current = [];

    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
    }
    if (socketRef.current) {
      if (socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ event: "hangup" }));
      }
      socketRef.current.close();
      socketRef.current = null;
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setIsConnected(false);
    setIsUserSpeaking(false);
    setVolumeLevel(0);
    setCallState("idle");
  };

  // Push quick Malayalam test prompt via text
  const sendTextPrompt = (promptText: string) => {
    if (!promptText.trim()) return;
    triggerBargeIn();
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      setCallState("thinking");
      socketRef.current.send(
        JSON.stringify({
          event: "user_text",
          text: promptText.trim(),
        })
      );
      setTextInput("");
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">AI Voice Receptionist Live Tester</h1>
            <Badge variant="success" className="gap-1.5 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Automatic Voice Detection (VAD) Active
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Speak naturally in Malayalam into your microphone. The AI will listen, interrupt on speech, and answer like a human.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {!isConnected ? (
            <Button
              onClick={startCall}
              className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-6 py-2.5 rounded-xl shadow-lg shadow-emerald-600/20 gap-2 text-sm"
            >
              <PhoneCall className="w-4 h-4" />
              Start Live Voice Call
            </Button>
          ) : (
            <Button
              onClick={endCall}
              variant="danger"
              className="px-6 py-2.5 rounded-xl shadow-lg shadow-rose-600/20 gap-2 text-sm font-semibold"
            >
              <PhoneOff className="w-4 h-4" />
              End Call
            </Button>
          )}
        </div>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Main Interactive Stage */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Visual Call Pod & Mic Control */}
        <div className="lg:col-span-1 space-y-6">
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col items-center justify-center text-center relative overflow-hidden">
            {/* Central Animated Avatar */}
            <div className="relative my-6">
              <div
                className={`w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300 shadow-2xl ${
                  callState === "speaking"
                    ? "bg-blue-500 text-white shadow-blue-500/40 ring-8 ring-blue-500/20 scale-105"
                    : isUserSpeaking
                    ? "bg-emerald-500 text-white shadow-emerald-500/40 ring-8 ring-emerald-500/30 scale-110"
                    : callState === "listening"
                    ? "bg-slate-800 text-emerald-400 border border-emerald-500/30"
                    : callState === "transcribing" || callState === "thinking"
                    ? "bg-amber-500 text-slate-950 shadow-amber-500/40 animate-pulse"
                    : "bg-slate-800 text-slate-400 border border-slate-700"
                }`}
              >
                {callState === "speaking" ? (
                  <Volume2 className="w-12 h-12 animate-pulse" />
                ) : isUserSpeaking ? (
                  <Mic className="w-12 h-12 animate-bounce" />
                ) : callState === "transcribing" || callState === "thinking" ? (
                  <Activity className="w-12 h-12 animate-spin" />
                ) : (
                  <Bot className="w-12 h-12" />
                )}
              </div>

              {/* Pulsing Voice Activity Rings */}
              {isConnected && (
                <div
                  className="absolute inset-0 rounded-full border-2 border-emerald-400 pointer-events-none transition-all duration-75"
                  style={{
                    transform: `scale(${1 + volumeLevel / 90})`,
                    opacity: volumeLevel > 8 ? 0.9 : 0.1,
                  }}
                />
              )}
            </div>

            {/* Status Title */}
            <h3 className="text-lg font-bold text-white">
              {callState === "idle" && "Ready to Connect"}
              {callState === "connecting" && "Dialing Voice Engine..."}
              {callState === "speaking" && "AI Receptionist Speaking..."}
              {isUserSpeaking && "Listening to Your Voice..."}
              {!isUserSpeaking && callState === "listening" && "Listening (Speak Freely)"}
              {callState === "transcribing" && "Transcribing Malayalam (Sarvam STT)..."}
              {callState === "thinking" && "Checking Dr. Manoj's Calendar..."}
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-[240px]">
              {callState === "idle" && "Click Start Live Voice Call to open microphone."}
              {callState === "speaking" && "Tip: Start talking anytime to interrupt the AI immediately!"}
              {isUserSpeaking && "We detect your voice! Pause when you finish speaking."}
              {!isUserSpeaking && callState === "listening" && "Microphone is on. Speak naturally in Malayalam."}
              {callState === "transcribing" && "Processing your speech via Saaras v3."}
              {callState === "thinking" && "Querying Supabase doctors and appointments."}
            </p>

            {/* Live Volume Meter Bar */}
            {isConnected && (
              <div className="w-full mt-6 pt-4 border-t border-slate-800 space-y-2">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Microphone Input Level</span>
                  <span className={volumeLevel > 8 ? "text-emerald-400 font-semibold" : "text-slate-500"}>
                    {volumeLevel > 8 ? "Voice Detected" : "Quiet"}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-75 ${
                      volumeLevel > 8 ? "bg-emerald-400 shadow-sm shadow-emerald-400/50" : "bg-slate-600"
                    }`}
                    style={{ width: `${Math.min(100, volumeLevel * 1.5)}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Quick One-Click Malayalam Test Prompts */}
          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <span>Quick Test Prompts (1-Click Test)</span>
            </div>
            <p className="text-[11px] text-slate-400">Click any prompt to simulate patient speech immediately:</p>
            <div className="space-y-2">
              {[
                {
                  ml: "ഡോക്ടർ മനോജിന് നാളെ എന്തെങ്കിലും ഫ്രീ സമയം ഉണ്ടോ?",
                  en: "Does Dr. Manoj have free slots tomorrow?",
                },
                {
                  ml: "രാവിലെ 10:15 AM സ്ലോട്ട് ബുക്ക് ചെയ്തോളൂ. എന്റെ പേര് അക്ഷയ്.",
                  en: "Book 10:15 AM slot. My name is Akshay.",
                },
                {
                  ml: "ശ്രീരുദ്ര ഹോസ്പിറ്റലിൽ എന്തൊക്കെ പഞ്ചകർമ്മ ചികിത്സകൾ ഉണ്ട്?",
                  en: "What Panchakarma treatments do you offer?",
                },
                {
                  ml: "ഹലോ? ഞാൻ പറയുന്നത് കേൾക്കാമോ?",
                  en: "Hello? Can you hear me?",
                },
                {
                  ml: "നെഞ്ചുവേദനയുണ്ട്, അടിയന്തിരമാണ് സഹായിക്കാമോ?",
                  en: "Chest pain emergency! Please help.",
                },
              ].map((p, idx) => (
                <button
                  key={idx}
                  disabled={!isConnected}
                  onClick={() => sendTextPrompt(p.ml)}
                  className="w-full text-left p-2.5 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-emerald-500/40 text-xs transition-all disabled:opacity-40 disabled:cursor-not-allowed group"
                >
                  <div className="text-slate-200 font-medium group-hover:text-emerald-400 transition-colors">
                    {p.ml}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">{p.en}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Live Turn-by-Turn Transcript & Text Input */}
        <div className="lg:col-span-2 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col h-[650px] overflow-hidden">
          {/* Transcript Header */}
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold text-slate-200">Live Malayalam Conversation Transcript</span>
            </div>
            <div className="text-[11px] text-slate-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>Sreerudra Hospital Reception</span>
            </div>
          </div>

          {/* Transcript Messages Scroll Area */}
          <div className="flex-1 p-6 overflow-y-auto space-y-4">
            {transcripts.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-slate-800/60 border border-slate-700 flex items-center justify-center text-slate-400">
                  <PhoneCall className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-400">No active conversation yet</p>
                  <p className="text-xs text-slate-500 mt-1 max-w-sm">
                    Click &quot;Start Live Voice Call&quot; to begin. The AI will introduce itself in Malayalam and listen to your voice.
                  </p>
                </div>
              </div>
            ) : (
              transcripts.map((turn) => (
                <div
                  key={turn.id}
                  className={`flex gap-3 max-w-[85%] ${
                    turn.speaker === "Caller" ? "ml-auto flex-row-reverse" : "mr-auto"
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center text-xs font-semibold ${
                      turn.speaker === "Caller"
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                        : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    }`}
                  >
                    {turn.speaker === "Caller" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div className="space-y-1">
                    <div
                      className={`p-3.5 rounded-2xl text-sm leading-relaxed ${
                        turn.speaker === "Caller"
                          ? "bg-emerald-600 text-white rounded-tr-none shadow-md"
                          : "bg-slate-800 text-slate-100 rounded-tl-none border border-slate-700 shadow-sm"
                      }`}
                    >
                      {turn.text}
                    </div>

                    <div
                      className={`text-[10px] text-slate-500 flex items-center gap-1.5 ${
                        turn.speaker === "Caller" ? "justify-end" : "justify-start"
                      }`}
                    >
                      <span>{turn.speaker === "Caller" ? "You (Patient)" : "AI Receptionist"}</span>
                      <span>•</span>
                      <span>{turn.timestamp}</span>
                      {turn.turnType && (
                        <>
                          <span>•</span>
                          <span className="capitalize text-emerald-400">{turn.turnType}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
            <div ref={transcriptEndRef} />
          </div>

          {/* Text Input Fallback Bar */}
          <div className="p-3 bg-slate-950/80 border-t border-slate-800">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendTextPrompt(textInput);
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                disabled={!isConnected}
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder={isConnected ? "Or type your question in Malayalam/English..." : "Start call to talk or type..."}
                className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 disabled:opacity-40"
              />
              <Button
                type="submit"
                disabled={!isConnected || !textInput.trim()}
                className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2.5 rounded-xl text-xs gap-1.5 font-semibold disabled:opacity-40"
              >
                <Send className="w-3.5 h-3.5" />
                Send
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
