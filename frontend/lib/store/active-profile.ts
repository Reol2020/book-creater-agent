import { create } from "zustand";

import { settingsApi, type LlmProfile } from "@/lib/api/endpoints/settings";

interface ActiveProfileState {
  profile: LlmProfile | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export const useActiveProfile = create<ActiveProfileState>((set) => ({
  profile: null,
  loading: false,
  error: null,
  async refresh() {
    set({ loading: true, error: null });
    try {
      const p = await settingsApi.getActive();
      set({ profile: p, loading: false });
    } catch (e) {
      set({ loading: false, error: String(e) });
    }
  },
}));
