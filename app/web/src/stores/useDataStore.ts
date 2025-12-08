import { create } from 'zustand';

interface Position {
  x: number;
  y: number;
  z: number;
}

interface DriverData {
  driver_number: number;
  position: Position;
  speed: number;
  gear: number;
  rpm: number;
  throttle: number;
  brake: number;
}

interface AppState {
  positions: Record<string, { X: number; Y: number; Z: number }>;
  driverList: Record<string, any>;
  timingData: any;
  trackStatus: any;
  raceControlMessages: any;
  sessionInfo: any;

  setPositions: (pos: Record<string, Position>) => void;
  setTelemetry: (tel: Record<string, DriverData>) => void;
}

export const useDataStore = create<AppState>((set) => ({
  positions: {},
  driverList: {
     // Mock Driver List
     "1": { racingNumber: "1", tla: "VER", teamColour: "1e41ff" },
     "11": { racingNumber: "11", tla: "PER", teamColour: "1e41ff" },
     "16": { racingNumber: "16", tla: "LEC", teamColour: "ef1a2d" },
     "55": { racingNumber: "55", tla: "SAI", teamColour: "ef1a2d" },
     "44": { racingNumber: "44", tla: "HAM", teamColour: "27f4d2" },
     "63": { racingNumber: "63", tla: "RUS", teamColour: "27f4d2" },
     "4": { racingNumber: "4", tla: "NOR", teamColour: "ff8700" },
     "81": { racingNumber: "81", tla: "PIA", teamColour: "ff8700" },
  },
  timingData: null,
  trackStatus: { status: "1" },
  raceControlMessages: { messages: [] },
  sessionInfo: { meeting: { circuit: { key: 7 } } },
  telemetry: {},

  setPositions: (pos) => set((state) => {
      const newPos: Record<string, {X: number, Y: number, Z: number}> = {};
      for (const [key, val] of Object.entries(pos)) {
          newPos[key] = { X: val.x, Y: val.y, Z: val.z };
      }
      return { positions: newPos };
  }),
  setTelemetry: (tel) => set((state) => ({
      telemetry: tel
  })),
}));

export const usePositionStore = useDataStore; // Alias for compatibility with Map.tsx
