"use client";

import { useEffect } from "react";
import Map from "@/components/Map";
import DriverDetails from "@/components/DriverDetails";
import { useDataStore } from "@/stores/useDataStore";

export default function Dashboard() {
  const setPositions = useDataStore((state) => state.setPositions);
  const setTelemetry = useDataStore((state) => state.setTelemetry);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:4000/ws");

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.pos) {
                setPositions(data.pos);
            }
            if (data.telemetry) {
                setTelemetry(data.telemetry);
            }
        } catch (e) {
            console.error("Parse error", e);
        }
    };

    return () => ws.close();
  }, [setPositions, setTelemetry]);

  return (
    <main className="flex h-screen flex-col bg-zinc-950 text-white overflow-hidden">
      <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900">
        <h1 className="text-2xl font-bold tracking-tight">F1 Live Replay</h1>
        <div className="text-xs text-zinc-500 font-mono">LIVE CONNECTED</div>
      </header>

      <div className="flex flex-1 overflow-hidden">
          <div className="flex-1 relative bg-zinc-900/50">
             <Map />
          </div>

          <DriverDetails />
      </div>
    </main>
  );
}
