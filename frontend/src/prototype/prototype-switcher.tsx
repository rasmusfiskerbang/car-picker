import { ArrowLeft, ArrowRight } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export type PrototypeVariant<Key extends string> = {
  key: Key;
  name: string;
};

export function PrototypeSwitcher<Key extends string>({
  current,
  onChange,
  variants,
}: {
  current: Key;
  onChange: (variant: Key) => void;
  variants: readonly PrototypeVariant<Key>[];
}) {
  const currentIndex = variants.findIndex((variant) => variant.key === current);
  const safeIndex = currentIndex === -1 ? 0 : currentIndex;

  const cycle = (direction: -1 | 1) => {
    const next =
      variants[(safeIndex + direction + variants.length) % variants.length];
    onChange(next.key);
  };

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      const target = event.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        (target instanceof HTMLElement && target.isContentEditable)
      ) {
        return;
      }
      if (event.key === "ArrowLeft") cycle(-1);
      if (event.key === "ArrowRight") cycle(1);
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  });

  if (!import.meta.env.DEV) return null;

  const selected = variants[safeIndex];
  return (
    <nav
      aria-label="Skift prototypevariant"
      className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center rounded-full bg-foreground p-1.5 text-background shadow-2xl"
    >
      <Button
        aria-label="Forrige variant"
        className="rounded-full text-background hover:bg-background/15 hover:text-background"
        onClick={() => cycle(-1)}
        size="icon"
        variant="ghost"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
      </Button>
      <span className="min-w-48 px-3 text-center text-xs font-bold">
        {selected.key.toUpperCase()} · {selected.name}
      </span>
      <Button
        aria-label="Næste variant"
        className="rounded-full text-background hover:bg-background/15 hover:text-background"
        onClick={() => cycle(1)}
        size="icon"
        variant="ghost"
      >
        <ArrowRight aria-hidden="true" className="size-4" />
      </Button>
    </nav>
  );
}
