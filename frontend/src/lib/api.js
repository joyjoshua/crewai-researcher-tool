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

  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

export default api;
