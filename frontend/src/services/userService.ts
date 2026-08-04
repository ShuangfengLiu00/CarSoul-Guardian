import { post } from "@/utils/request";
import type { Token, UserOut } from "./types";

export interface RegisterBody {
  username: string;
  password: string;
  email: string;
}
export interface LoginBody {
  username: string;
  password: string;
}

export const userService = {
  register: (body: RegisterBody) => post<UserOut>("/api/user/register", body),
  login: (body: LoginBody) => post<Token>("/api/user/login", body),
};
