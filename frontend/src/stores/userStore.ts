import { create } from "zustand";

interface UserState {
  username: string | null;
  token: string | null;
  login: (username: string, token: string) => void;
  logout: () => void;
  isAuthed: () => boolean;
}

export const useUserStore = create<UserState>((set, get) => ({
  username: localStorage.getItem("carsoul_username") || null,
  token: localStorage.getItem("carsoul_token") || null,
  login: (username, token) => {
    localStorage.setItem("carsoul_username", username);
    localStorage.setItem("carsoul_token", token);
    set({ username, token });
  },
  logout: () => {
    localStorage.removeItem("carsoul_username");
    localStorage.removeItem("carsoul_token");
    set({ username: null, token: null });
  },
  isAuthed: () => !!get().token,
}));
