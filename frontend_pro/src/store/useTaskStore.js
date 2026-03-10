import { create } from "zustand";

export const useTaskStore = create((set) => ({
    selectedLeafIds: new Set(),
    addLeaf: (id) =>
        set((state) => {
            const next = new Set(state.selectedLeafIds);
            next.add(id);
            return { selectedLeafIds: next };
        }),
    removeLeaf: (id) =>
        set((state) => {
            const next = new Set(state.selectedLeafIds);
            next.delete(id);
            return { selectedLeafIds: next };
        }),
    clearAll: () => set({ selectedLeafIds: new Set() }),
}));
