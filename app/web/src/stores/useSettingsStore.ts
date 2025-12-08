import { create } from 'zustand';

interface SettingsState {
  showCornerNumbers: boolean;
  favoriteDrivers: string[];
  useSafetyCarColors: boolean;
  speedUnit: 'metric' | 'imperial';
}

export const useSettingsStore = create<SettingsState>((set) => ({
  showCornerNumbers: true,
  favoriteDrivers: [],
  useSafetyCarColors: true,
  speedUnit: 'metric',
}));
