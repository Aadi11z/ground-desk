import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("authentication entry", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        supabase_url: "https://example.supabase.co",
        supabase_publishable_key: "publishable-key",
      }),
    }));
  });

  afterEach(() => vi.unstubAllGlobals());

  it("shows a single organization sign-in entry point", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Sign in to your organization" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Continue" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Create organization" })).not.toBeInTheDocument();
  });
});
