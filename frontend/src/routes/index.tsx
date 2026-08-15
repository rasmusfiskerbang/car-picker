import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  beforeLoad: () => {
    throw redirect({
      to: "/catalogue",
      search: {
        form: "all",
        power: "all",
        provider: "all",
        q: "",
        selected: [],
        sort: "source",
        variant: "a",
      },
    });
  },
});
