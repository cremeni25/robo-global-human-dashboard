/** Endereço único da API do Robô Global (defina VITE_API_URL no deploy). */
export const API_URL = ((import.meta.env.VITE_API_URL as string | undefined)?.trim() || "https://robo-global-api-v2.onrender.com").replace(/\/$/, "");
