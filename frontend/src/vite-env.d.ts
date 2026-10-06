/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Public URL of the POLTRACKER API for production builds. Unset in development (uses the /api proxy). */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
