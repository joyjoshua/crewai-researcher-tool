import axios from "axios";
import { supabase } from "./supabase";

/**
 * Axios instance that auto-attaches the Supabase JWT to every request.
 */
const api = axios.create();

api.interceptors.request.use(async (config) => {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const token = session?.access_token;
  if (token) {
    // Axios 1.x: set() works with AxiosHeaders reliably in the browser.
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

export default api;
