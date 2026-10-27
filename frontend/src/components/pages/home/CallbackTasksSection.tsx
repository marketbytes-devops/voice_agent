"use client";

import React, { useState } from "react";
import { CheckCircle2, Clock, Phone, AlertCircle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { MOCK_CALLBACKS, CallbackTaskItem } from "@/lib/mockData";

export function CallbackTasksSection() {
  const [tasks, setTasks] = useState<CallbackTaskItem[]>(MOCK_CALLBACKS);

  const resolveTask = (id: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
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
