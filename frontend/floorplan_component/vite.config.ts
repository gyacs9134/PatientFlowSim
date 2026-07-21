import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "build",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("react-konva")) return "react-konva";
          if (id.includes("konva/lib/shapes")) return "konva-shapes";
          if (id.includes("node_modules/konva")) return "konva-core";
          if (id.includes("streamlit-component-lib")) return "streamlit";
          if (id.includes("node_modules/react") || id.includes("node_modules/react-dom")) return "react";
          return undefined;
        },
      },
    },
  },
});
