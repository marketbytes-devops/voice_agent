"use client";

import React, { useState, useEffect } from "react";
import { CheckCircle2, Clock, Phone } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { CallbackTaskItem } from "@/lib/mockData";

export function CallbackTasksSection() {
  const [tasks, setTasks] = useState<CallbackTaskItem[]>([]);
  const [isLoaded, setIsLoaded] = useState<boolean>(false);

  useEffect(() => {
    async function fetchCallbacks() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://voice-agent-pphb.onrender.com";
        const res = await fetch(`${apiUrl}/api/callbacks`, { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            setTasks(data);
          }
        }
      } catch (err) {
        console.warn("Could not fetch callback tasks:", err);
      } finally {
        setIsLoaded(true);
      }
    }
    fetchCallbacks();
  }, []);

  const resolveTask = async (id: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://voice-agent-pphb.onrender.com";
      await fetch(`${apiUrl}/api/callbacks/${id}/resolve`, { method: "POST" });
    } catch (err) {
      console.warn("Failed to resolve callback in backend:", err);
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle>
            <Clock className="w-5 h-5 text-amber-400" />
            <span>Reception Callback Tasks ({tasks.length})</span>
          </CardTitle>
          <CardDescription>
            Tasks dispatched by AI when callers request human staff or detailed billing queries.
          </CardDescription>
        </div>
      </CardHeader>

      {tasks.length === 0 ? (
        <div className="py-8 text-center text-sm text-slate-500">
          <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-400/60" />
          All callback tasks have been resolved!
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-white">{task.patientName}</span>
                  <span className="text-xs text-amber-400 font-mono font-medium">{task.phone}</span>
                  <Badge variant="warning">{task.preferredTime}</Badge>
                </div>
                <p className="text-xs text-slate-300 mt-1">{task.reason}</p>
                <span className="text-[11px] text-slate-500 mt-1 block">Created {task.createdAt}</span>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Button variant="secondary" size="sm" onClick={() => window.open(`tel:${task.phone}`)}>
                  <Phone className="w-3.5 h-3.5 mr-1 text-emerald-400" /> Call Patient
                </Button>
                <Button variant="primary" size="sm" onClick={() => resolveTask(task.id)}>
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Mark Resolved
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
