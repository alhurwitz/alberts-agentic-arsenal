import { Plugin } from "@opencode/plugin/tui"

type Hit = { title: string; value: number; category: string; description?: string }
type Entry = { label: string; text: string; message: number }

const MAX_RESULTS = 200
const SNIPPET = 110

function entries(messages: ReadonlyArray<any>): Entry[] {
  const out: Entry[] = []
  messages.forEach((m, i) => {
    const n = i + 1
    if (typeof m.text === "string" && m.text.trim()) out.push({ label: `#${n} ${m.type}`, text: m.text, message: i })
    for (const p of m.content ?? []) {
      if (p.type === "text" && p.text?.trim()) out.push({ label: `#${n} ${m.type}`, text: p.text, message: i })
      else if (p.type === "reasoning" && p.text?.trim()) out.push({ label: `#${n} thinking`, text: p.text, message: i })
      else if (p.type === "tool") {
        const input = typeof p.state?.input === "string" ? p.state.input : JSON.stringify(p.state?.input ?? {})
        const output = (p.state?.content ?? [])
          .filter((c: any) => c.type === "text")
          .map((c: any) => c.text)
          .join("\n")
        out.push({ label: `#${n} tool ${p.name}`, text: `${input}\n${output}`, message: i })
      }
    }
  })
  return out
}

function lines(all: Entry[]): Hit[] {
  return all.flatMap((e, idx) =>
    e.text
      .split("\n")
      .map((l) => l.replace(/\s+/g, " ").trim())
      .filter(Boolean)
      .map((l) => ({ title: l, value: idx, category: e.label })),
  )
}

function snippet(line: string, q: string): string {
  const at = Math.max(0, line.toLowerCase().indexOf(q))
  const start = Math.max(0, at - 30)
  return (start > 0 ? "…" : "") + line.slice(start, start + SNIPPET) + (start + SNIPPET < line.length ? "…" : "")
}

function search(options: Hit[], query: string): Hit[] {
  const q = query.trim().toLowerCase()
  if (!q) return []
  const hits: Hit[] = []
  for (const o of options) {
    if (hits.length >= MAX_RESULTS) break
    if (o.title.toLowerCase().includes(q)) hits.push({ ...o, title: snippet(o.title, q) })
  }
  return hits
}

export default Plugin.define({
  id: "albert.find",
  setup(context) {
    const find = async (initial?: string) => {
      const route = context.ui.router.current() as { type: string; sessionID?: string }
      if (route.type !== "session" || !route.sessionID) {
        context.ui.toast.show({ message: "Open a session first", variant: "warning" })
        return
      }
      await context.data.session.message.sync(route.sessionID)
      const messages = context.data.session.message.list(route.sessionID) ?? []
      const all = entries(messages)
      const seed = initial?.trim() ?? ""
      const pick = await context.ui.dialog.select<number>({
        title: seed ? `Find: ${seed}` : "Find in session (type to search)",
        options: lines(all),
        search: (query, options) => search(options as Hit[], query || seed),
      })
      if (pick === undefined) return
      jump(messages, all[pick].message)
    }

    // Plugins can't scroll to a message directly, so step back from the bottom
    // through user messages until we reach the turn that holds the hit.
    const jump = (messages: ReadonlyArray<any>, index: number) => {
      let turn = index
      while (turn > 0 && messages[turn].type !== "user") turn--
      const steps = messages.slice(turn).filter((m) => m.type === "user").length
      context.keymap.dispatch("session.last")
      for (let i = 0; i < steps; i++) context.keymap.dispatch("session.message.user.previous")
      context.ui.toast.show({ message: "Jumped to match · /bottom to return", variant: "info", duration: 2500 })
    }

    context.keymap.layer(() => ({
      mode: "global",
      commands: [
        {
          id: "albert.find",
          title: "Find in session",
          group: "Session",
          palette: true,
          slash: { name: "find", aliases: ["search"], arguments: true },
          run: (input?: string) => find(input),
        },
        {
          id: "albert.find.bottom",
          title: "Jump to bottom",
          group: "Session",
          palette: true,
          slash: { name: "bottom", aliases: ["latest"] },
          run: () => context.keymap.dispatch("session.last"),
        },
      ],
    }))
  },
})
