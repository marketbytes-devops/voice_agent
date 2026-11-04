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
  HelpCircle,
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

export default function TestCallPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [callState, setCallState] = useState<"idle" | "connecting" | "listening" | "transcribing" | "thinking" | "speaking">("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [transcripts, setTranscripts] = useState<TranscriptTurn[]>([]);
  const [currentSpeakerText, setCurrentSpeakerText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [volumeLevel, setVolumeLevel] = useState(0);

  const socketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const activeAudioRef = useRef<HTMLAudioElement | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll transcript to bottom
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts, currentSpeakerText]);

  // Clean up audio & websocket on unmount
  useEffect(() => {
    return () => {
      endCall();
    };
  }, []);

  // Visualizer loop: monitor mic volume levels
  const startVolumeMonitor = (stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      audioContextRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const checkVolume = () => {
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        setVolumeLevel(Math.min(100, Math.round(avg * 1.8)));
        animFrameRef.current = requestAnimationFrame(checkVolume);
      };
      checkVolume();
    } catch (e) {
      console.warn("Volume monitor init error:", e);
    }
  };

  const stopVolumeMonitor = () => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setVolumeLevel(0);
  };

  // Play audio WAV chunk received from Sarvam TTS
  const playAgentAudio = useCallback((base64Audio: string) => {
    if (!base64Audio) return;
    try {
      // If previous audio is playing, halt it immediately
      if (activeAudioRef.current) {
        activeAudioRef.current.pause();
        activeAudioRef.current = null;
      }

      const audioSrc = `data:audio/wav;base64,${base64Audio}`;
      const audio = new Audio(audioSrc);
      activeAudioRef.current = audio;
      setCallState("speaking");

      audio.onended = () => {
        setCallState("listening");
        activeAudioRef.current = null;
        startContinuousRecording();
      };

      audio.onerror = () => {
        setCallState("listening");
        activeAudioRef.current = null;
        startContinuousRecording();
      };

      audio.play().catch((err) => {
        console.warn("Audio autoplay blocked or interrupted:", err);
        setCallState("listening");
        startContinuousRecording();
      });
    } catch (e) {
      console.error("Error playing audio chunk:", e);
      setCallState("listening");
    }
  }, []);

  // Handle client-side barge-in (interruption): stop AI voice immediately when user talks
  const triggerBargeIn = () => {
    if (activeAudioRef.current && !activeAudioRef.current.paused) {
      console.log("Client-side barge-in triggered: stopping AI audio instantly.");
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ event: "user_interrupted" }));
      }
    }
  };

  // Start continuous audio slice recording from microphone
  const startContinuousRecording = async () => {
    if (!mediaRecorderRef.current || isRecording) return;
    try {
      audioChunksRef.current = [];
      mediaRecorderRef.current.start(200); // 200ms timeslices
      setIsRecording(true);
    } catch (e) {
      console.warn("Could not start MediaRecorder slice:", e);
    }
  };

  // Stop recording and send audio payload to backend
  const stopAndSendRecording = () => {
    if (!mediaRecorderRef.current || !isRecording) return;
    try {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    } catch (e) {
      console.warn("Could not stop MediaRecorder:", e);
    }
  };

  // Connect WebSocket & start live call
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

      startVolumeMonitor(stream);

      // Setup MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        if (audioChunksRef.current.length === 0) return;
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        audioChunksRef.current = [];

        // If audio blob is larger than 1.5KB (real speech), send to Sarvam STT
        if (audioBlob.size > 1500 && socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
          setCallState("transcribing");
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64Data = (reader.result as string).split(",")[1];
            socketRef.current?.send(
              JSON.stringify({
                event: "user_audio",
                audio_base64: base64Data,
              })
            );
          };
          reader.readAsDataURL(audioBlob);
        }
      };

      // 2. Connect WebSocket to backend
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
            setCurrentSpeakerText(replyText);
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
        setErrorMessage("Could not connect to voice server. Please verify backend is running.");
        endCall();
      };

      ws.onclose = () => {
        setIsConnected(false);
        setCallState("idle");
        stopVolumeMonitor();
      };
    } catch (err: unknown) {
      console.error("Microphone permission or connection failure:", err);
      const msg = err instanceof Error ? err.message : "Microphone permission denied.";
      setErrorMessage(`${msg}. Please allow microphone permissions in your browser.`);
      setCallState("idle");
    }
  };

  // End Call
  const endCall = () => {
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
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    stopVolumeMonitor();
    setIsConnected(false);
    setIsRecording(false);
    setCallState("idle");
  };

  // Push quick Malayalam test prompt via text
  const sendQuickPrompt = (promptText: string) => {
    triggerBargeIn();
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      setCallState("thinking");
      socketRef.current.send(
        JSON.stringify({
          event: "user_text",
          text: promptText,
        })
      );
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
              Live Microphone Mode
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Test natural Malayalam conversations, human-like barge-in, Dr. Manoj’s calendar, and booking flows directly from your browser.
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
            {/* Background Glow */}
            <div
              className={`absolute inset-0 bg-gradient-to-b transition-opacity duration-700 pointer-events-none ${
                callState === "speaking"
                  ? "from-blue-600/15 via-transparent to-transparent opacity-100"
                  : callState === "listening"
                  ? "from-emerald-600/15 via-transparent to-transparent opacity-100"
                  : callState === "thinking"
                  ? "from-amber-600/15 via-transparent to-transparent opacity-100"
                  : "opacity-0"
              }`}
            />

            {/* Central Animated Avatar */}
            <div className="relative my-6">
              <div
                className={`w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300 shadow-2xl ${
                  callState === "speaking"
                    ? "bg-blue-500 text-white shadow-blue-500/40 ring-8 ring-blue-500/20 scale-105"
                    : callState === "listening"
                    ? "bg-emerald-500 text-white shadow-emerald-500/40 ring-8 ring-emerald-500/20 scale-105"
                    : callState === "thinking"
                    ? "bg-amber-500 text-slate-950 shadow-amber-500/40 animate-pulse"
                    : "bg-slate-800 text-slate-400 border border-slate-700"
                }`}
              >
                {callState === "speaking" ? (
                  <Volume2 className="w-12 h-12 animate-pulse" />
                ) : callState === "listening" ? (
                  <Mic className="w-12 h-12" />
                ) : callState === "thinking" ? (
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
                    transform: `scale(${1 + volumeLevel / 120})`,
                    opacity: volumeLevel > 10 ? 0.8 : 0.1,
                  }}
                />
              )}
            </div>

            {/* Status Title */}
            <h3 className="text-lg font-bold text-white">
              {callState === "idle" && "Ready to Connect"}
              {callState === "connecting" && "Dialing Voice Engine..."}
              {callState === "speaking" && "AI Receptionist Speaking"}
              {callState === "listening" && "Listening to You..."}
              {callState === "transcribing" && "Transcribing Malayalam..."}
              {callState === "thinking" && "Checking Dr. Manoj's Calendar..."}
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-[240px]">
              {callState === "idle" && "Click Start Live Voice Call to open microphone."}
              {callState === "speaking" && "Tip: Start talking anytime to test instant barge-in interruption!"}
              {callState === "listening" && "Speak naturally in Malayalam or English into your microphone."}
              {callState === "transcribing" && "Processing audio via Sarvam Saaras v3."}
              {callState === "thinking" && "Executing tools & querying Supabase."}
            </p>

            {/* Interactive Speech Trigger Buttons */}
            {isConnected && (
              <div className="w-full mt-6 pt-6 border-t border-slate-800/80 space-y-3">
                <Button
                  onMouseDown={() => {
                    triggerBargeIn();
                    startContinuousRecording();
                  }}
                  onMouseUp={() => {
                    stopAndSendRecording();
                  }}
                  onTouchStart={() => {
                    triggerBargeIn();
                    startContinuousRecording();
                  }}
                  onTouchEnd={() => {
                    stopAndSendRecording();
                  }}
                  className={`w-full py-3.5 rounded-xl font-semibold gap-2 transition-all ${
                    isRecording
                      ? "bg-rose-600 hover:bg-rose-500 text-white ring-4 ring-rose-500/20 scale-95"
                      : "bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                  }`}
                >
                  <Mic className={`w-4 h-4 ${isRecording ? "animate-pulse text-white" : "text-emerald-400"}`} />
                  {isRecording ? "Release to Send Speech..." : "Hold to Speak (or Talk Freely)"}
                </Button>
                <p className="text-[11px] text-slate-500 text-center">
                  Microphone is active. Speak clearly or hold button.
                </p>
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
                  onClick={() => sendQuickPrompt(p.ml)}
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

        {/* Right Column: Live Turn-by-Turn Transcript & Telemetry */}
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

          {/* Footer Call Info */}
          <div className="p-3 bg-slate-950/60 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Full Medical Guardrails Active (No Prescriptions / Emergency Escalation Enforced)</span>
            </div>
            <div className="text-[11px] text-slate-500">
              Supabase DB: <span className="text-emerald-400 font-medium">Mumbai Connected</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
