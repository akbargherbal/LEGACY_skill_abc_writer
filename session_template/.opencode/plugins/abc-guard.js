import fs from "node:fs"
import path from "node:path"
import { Plugin } from "@opencode/plugin"

// The 1.0 loop writes a whole score per call and validates it with the
// scorecard. Pin one model/variant, cap output per request at 8k tokens so a
// 2-4k-token draft fits and a runaway burst is cut, and log the resolved model
// so a run can be audited.
const PIN = { providerID: "deepseek", id: "deepseek-flash", variant: "high" }
const MAX_TOKENS = 8000

export default Plugin.define({
  id: "abc-score.guard",
  async setup(ctx) {
    const logPath = path.join(ctx.location.directory, "abc-session.log")
    const log = (row) => {
      try {
        fs.appendFileSync(logPath, JSON.stringify(row) + "\n")
      } catch {
        // A read-only workspace must not break the session.
      }
    }

    await ctx.session.hook("experimental.model.resolve", (event) => {
      if (event.kind !== "primary") return
      const before = event.model
      event.model = { ...PIN }
      log({ at: Date.now(), sessionID: event.sessionID, agent: event.agent,
            kind: event.kind, before, after: event.model })
    })

    await ctx.session.hook("context", (event) => {
      if (event.options.maxTokens === undefined || event.options.maxTokens > MAX_TOKENS) {
        event.options.maxTokens = MAX_TOKENS
      }
    })
  },
})
