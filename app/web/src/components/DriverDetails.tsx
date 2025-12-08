"use client";

import { useDataStore } from "@/stores/useDataStore";
import { motion } from "motion/react";

export default function DriverDetails() {
  const telemetry = useDataStore((state) => state.telemetry);
  const driverList = useDataStore((state) => state.driverList);

  if (!telemetry || Object.keys(telemetry).length === 0) {
      return <div className="p-4 text-zinc-500">Waiting for live data...</div>;
  }

  // Just show first 3 drivers for now or all
  const driversToShow = Object.values(telemetry).slice(0, 5);

  return (
    <div className="flex flex-col gap-4 p-4 w-80 h-full overflow-y-auto border-l border-zinc-800 bg-zinc-950/50">
      <h2 className="text-xl font-bold mb-2 text-zinc-100">Live Telemetry</h2>
      {driversToShow.map((data: any) => {
        const driver = driverList[data.driver_number] || { tla: "UNK", teamColour: "fff" };

        return (
          <div key={data.driver_number} className="bg-zinc-900 rounded-lg p-3 border border-zinc-800">
             <div className="flex justify-between items-center mb-2">
                <span className="font-bold text-2xl" style={{ color: `#${driver.teamColour}` }}>{driver.tla}</span>
                <span className="text-zinc-400">#{data.driver_number}</span>
             </div>

             <div className="grid grid-cols-2 gap-2 text-sm font-mono">
                 <div className="flex flex-col">
                     <span className="text-zinc-500">SPD</span>
                     <span className="text-lg">{data.speed} <span className="text-xs">km/h</span></span>
                 </div>
                 <div className="flex flex-col">
                     <span className="text-zinc-500">GEAR</span>
                     <span className="text-lg">{data.gear}</span>
                 </div>
                 <div className="flex flex-col col-span-2">
                     <span className="text-zinc-500">RPM</span>
                     <div className="w-full bg-zinc-800 h-2 rounded-full mt-1">
                         <motion.div
                            className="bg-blue-500 h-full rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${(data.rpm / 15000) * 100}%` }}
                         />
                     </div>
                     <span className="text-xs text-right mt-1">{data.rpm}</span>
                 </div>
             </div>
          </div>
        );
      })}
    </div>
  );
}
