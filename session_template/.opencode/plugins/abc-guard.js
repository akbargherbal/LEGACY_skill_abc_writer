import fs from "node:fs"
import path from "node:path"
import { Plugin } from "@opencode/plugin"

// The experiment pins one model and one per-call ceiling. A 32k reasoning
// burst cannot happen: the request is cut to 8k and the composer's step limit
// forces a tool call. The log makes the model in use auditable.
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
