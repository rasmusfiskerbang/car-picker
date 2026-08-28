import { QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";

import { AppRouter } from "@/app-router";
import { catalogueQueryClient } from "@/catalogue-query";
import "@/styles.css";

createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={catalogueQueryClient}>
    <AppRouter />
  </QueryClientProvider>,
);
