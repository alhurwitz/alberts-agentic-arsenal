// Hierarchical agent teams. A root session calls army_mobilize, then delegates through the
// built-in `subagent` tool to `army-officer` / `army-soldier` agents. This plugin enforces the
// shape of the tree, tracks every child, and accounts per-team budgets.
// Rules (checked on every subagent call made inside an army):
//   - depth of root = 0; children may go at most maxDepth (<= 5) levels below root
//   - army-soldier never spawns; army-officer only spawns when the child is above the soldier level
//   - children must be army-officer or army-soldier; leaf level (depth == maxDepth) is soldier only
//   - a officer spawn needs `TROOPS: <n>` as the prompt's first line; it costs the parent 1 + n,
//     a soldier costs 1; a finished officer returns its unused allotment to its parent
//   - every new child also counts against the global maxAgents cap; follow-ups do not
import { execFileSync } from "node:child_process"
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

import { childrenOf, elapsed, renderTree } from "./army-tui/tree.ts"

const HARD_MAX_DEPTH = 5
const DEFAULT_MAX_AGENTS = 50
const MANAGER = "army-officer"
const IC = "army-soldier"
const STORE = join(homedir(), ".local", "share", "opencode", "army")
const BUDGET_LINE = /^\s*TROOPS:\s*(\d+)\s*$/
const EVENT_STATUS: Record<string, Status> = {
  "session.execution.started": "running",
  "session.execution.succeeded": "done",
  "session.execution.failed": "failed",
  "session.execution.interrupted": "interrupted",
}

type Status = "running" | "done" | "failed" | "interrupted"
type Node = {
  sessionID: string
  parentID: string
  agent: string
  description: string
  depth: number
  status: Status
  startedAt: number
  endedAt?: number
  budget: number
  used: number
}
type Army = {
  rootID: string
  maxDepth: number
  maxAgents: number
  spawned: number
  officers: number
  ics: number
  used: number
  nodes: Record<string, Node>
}
type Session = { id: string; agent?: string; parentID?: string }
type Located = { army?: Army; depth: number; agent?: string; node?: Node }

const parseBudget = (prompt: string) => {
  const [first, ...rest] = prompt.split("\n")
  const match = BUDGET_LINE.exec(first ?? "")
  if (!match) return { budget: undefined, prompt }
  return { budget: Number(match[1]), prompt: rest.join("\n").replace(/^\n+/, "") }
}

const remaining = (army: Army, node?: Node) => (node ? node.budget - node.used : army.maxAgents - army.used)

const spawnCost = (child: string, budget = 0) => (child === MANAGER ? 1 + budget : 1)

// Shrinks a finished officer's allotment to what it used and returns the rest to its parent.
const settle = (army: Army, node: Node) => {
  const unused = node.budget - node.used
  if (node.agent !== MANAGER || unused <= 0) return 0
  node.budget = node.used
  const parent = army.nodes[node.parentID]
  if (parent) parent.used -= unused
  else army.used -= unused
  return unused
}

const textOf = (result: any): string => {
  if (typeof result === "string") return result
  if (Array.isArray(result)) return result.map(textOf).join("\n")
  if (result && typeof result === "object") return typeof result.text === "string" ? result.text : JSON.stringify(result)
  return ""
}

const childSessionID = (result: any) => /sessionID:\s*(ses_[A-Za-z0-9]+)/.exec(textOf(result?.content ?? result))?.[1]

const orgWorktrees = (porcelain: string, worktree: string) => {
  const prefix = `${worktree.replace(/\/+$/, "")}/.army/`
  return porcelain
    .split("\n")
    .filter((line) => line.startsWith("worktree "))
    .map((line) => line.slice("worktree ".length))
    .filter((path) => path.startsWith(prefix))
}

const childBranches = (list: string, current: string) =>
  list
    .split("\n")
    .map((line) => line.replace(/^[*+]?\s*/, "").trim())
    .filter((name) => current && name.startsWith(`${current}-`))

const git = (cwd: string, ...args: string[]) => execFileSync("git", ["-C", cwd, ...args], { encoding: "utf8" })

const Army = {
  id: "army",
  logic: { parseBudget, remaining, spawnCost, settle, renderTree, childSessionID, orgWorktrees, childBranches },
  async setup(ctx) {
    const armies = new Map<string, Army>()
    const owners = new Map<string, Army>()
    const pending = new Map<string, { army: Army; child: string; parentID: string; depth: number; budget: number; cost: number }>()
    const waiters = new Set<() => void>()
    const spawnKey = (sessionID: string, input: any) => `${sessionID}\u0000${input.agent}\u0000${input.description}`

    const save = (army: Army) => {
      mkdirSync(STORE, { recursive: true })
      writeFileSync(join(STORE, `${army.rootID}.json`), JSON.stringify(army, null, 2))
      for (const waiter of waiters) waiter()
    }

    const register = (army: Army) => {
      armies.set(army.rootID, army)
      for (const id of Object.keys(army.nodes)) owners.set(id, army)
    }

    const load = () => {
      mkdirSync(STORE, { recursive: true })
      for (const file of readdirSync(STORE).filter((name) => name.endsWith(".json"))) {
        try {
          register({ used: 0, nodes: {}, ...JSON.parse(readFileSync(join(STORE, file), "utf8")) })
        } catch {}
      }
    }
    load()

    const getSession = async (id: string): Promise<Session | undefined> => {
      const result = await ctx.session.get({ sessionID: id }).catch(() => undefined)
      return result?.data ?? result
    }

    const known = (id: string): Located | undefined => {
      const root = armies.get(id)
      if (root) return { army: root, depth: 0 }
      const army = owners.get(id)
      const node = army?.nodes[id]
      return node ? { army, depth: node.depth, agent: node.agent, node } : undefined
    }

    // Tracked sessions resolve from the tree; others walk parentID up to a tracked ancestor.
    const locate = async (sessionID: string): Promise<Located> => {
      const caller = await getSession(sessionID)
      let current = caller
      for (let steps = 0; current && steps <= HARD_MAX_DEPTH + 1; steps++) {
        const hit = known(current.id)
        if (hit) return steps === 0 ? { ...hit, agent: hit.agent ?? caller?.agent } : { army: hit.army, depth: hit.depth + steps, agent: caller?.agent }
        if (!current.parentID) break
        current = await getSession(current.parentID)
      }
      return { army: undefined, depth: 0, agent: caller?.agent }
    }

    const onEvent = (type: string, data: any) => {
      const status = EVENT_STATUS[type]
      const army = status ? owners.get(data?.sessionID) : undefined
      const node = army?.nodes[data.sessionID]
      if (!army || !node || node.status === status) return
      node.status = status
      node.endedAt = status === "running" ? undefined : Date.now()
      if (status !== "running") settle(army, node)
      save(army)
    }

    const controller = new AbortController()
    void (async () => {
      try {
        for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
          onEvent(event?.type, event?.data ?? event?.properties)
        }
      } catch (error: any) {
        if (!controller.signal.aborted) console.warn("[army] event subscription failed:", error?.message)
      }
    })()

    const waitFor = (army: Army, callerID: string, mode: string, timeoutMs: number, signal?: AbortSignal) => {
      const watched = childrenOf(army, callerID).filter((node) => node.status === "running")
      const ended = () => watched.filter((node) => node.status !== "running")
      const satisfied = () => (mode === "all" ? ended().length === watched.length : ended().length > 0)
      return new Promise<{ watched: Node[]; timedOut: boolean }>((resolve) => {
        if (watched.length === 0 || satisfied()) return resolve({ watched, timedOut: false })
        const finish = (timedOut: boolean) => {
          waiters.delete(check)
          clearTimeout(timer)
          signal?.removeEventListener("abort", abort)
          resolve({ watched, timedOut })
        }
        const check = () => satisfied() && finish(false)
        const abort = () => finish(true)
        const timer = setTimeout(abort, timeoutMs)
        signal?.addEventListener("abort", abort)
        waiters.add(check)
      })
    }

    const describeWait = (watched: Node[], timedOut: boolean) => {
      if (watched.length === 0) return "No running children to wait for."
      const line = (node: Node) => `- ${node.sessionID} "${node.description}" ${node.status}`
      const ended = watched.filter((node) => node.status !== "running")
      const running = watched.filter((node) => node.status === "running")
      return [
        timedOut ? "Wait ended (timeout or abort)." : "Wait satisfied.",
        `Ended (${ended.length}):`,
        ...ended.map(line),
        `Still running (${running.length}):`,
        ...running.map(line),
      ].join("\n")
    }

    const statusText = async (sessionID: string) => {
      const { army, depth, node } = await locate(sessionID)
      if (!army) return "Not inside an army. Root session must call army_mobilize first."
      return `You are at depth ${depth}/${army.maxDepth}; your budget left: ${remaining(army, node)}.\n${renderTree(army)}`
    }

    const startOrg = async (input: any, sessionID: string) => {
      const { army: existing } = await locate(sessionID)
      if (existing && existing.rootID !== sessionID) {
        return `Not started: this session is already inside army ${existing.rootID}. Delegate within it.`
      }
      const maxDepth = Math.min(HARD_MAX_DEPTH, Math.max(1, Math.trunc(Number(input.maxDepth))))
      const maxAgents = Math.max(1, Math.trunc(Number(input.maxAgents ?? ctx.options?.maxAgents ?? DEFAULT_MAX_AGENTS)))
      const army: Army = existing
        ? Object.assign(existing, { maxDepth, maxAgents })
        : { rootID: sessionID, maxDepth, maxAgents, spawned: 0, officers: 0, ics: 0, used: 0, nodes: {} }
      register(army)
      save(army)
      return (
        `Army ${existing ? "updated" : "started"}: maxDepth=${maxDepth}, maxAgents=${maxAgents}, spawned=${army.spawned}. ` +
        `You are the General (depth 0): follow the army-officer playbook. ` +
        `Delegate with the subagent tool using agent "${maxDepth === 1 ? IC : `${MANAGER}" or "${IC}`}". ` +
        `A ${MANAGER} prompt must start with the line "TROOPS: <n>" (n = agents its subtree may spawn); it costs you 1 + n.`
      )
    }

    const checkWorktree = (worktree: string) => {
      const current = git(worktree, "branch", "--show-current").trim()
      const worktrees = orgWorktrees(git(worktree, "worktree", "list", "--porcelain"), worktree)
      const branches = childBranches(git(worktree, "branch", "--no-merged", "HEAD"), current)
      if (worktrees.length === 0 && branches.length === 0) return `Clean: no child worktrees under ${worktree}/.army/ and no unmerged ${current}-* branches.`
      return [
        `Child worktrees under .army/ (${worktrees.length}):`,
        ...worktrees.map((path) => `- ${path}`),
        `Unmerged ${current}-* branches (${branches.length}):`,
        ...branches.map((name) => `- ${name}`),
      ].join("\n")
    }

    await ctx.tool.transform((editor) => {
      editor.add({
        name: "army_mobilize",
        description:
          "Start a hierarchical team run rooted at this session. Call once before delegating to army-officer / army-soldier subagents. " +
          "Pick maxDepth (1-5) from the task size: 1 = root directs soldiers only; each extra level adds a officer layer. " +
          "maxAgents caps total spawned agents (default 50) unless the user asked for a different cap.",
        input: {
          type: "object",
          properties: {
            maxDepth: { type: "integer", minimum: 1, maximum: HARD_MAX_DEPTH, description: "Levels below the root, 1-5" },
            maxAgents: { type: "integer", minimum: 1, description: `Total agent budget, default ${DEFAULT_MAX_AGENTS}` },
          },
          required: ["maxDepth"],
          additionalProperties: false,
        },
        async execute(input: any, toolContext: any) {
          return { content: await startOrg(input, toolContext.sessionID) }
        },
      })
      editor.add({
        name: "army_status",
        description: "Show the army tree: every agent's role, task, status, elapsed time and budget used/allotted, plus totals.",
        input: { type: "object", properties: {}, additionalProperties: false },
        async execute(_input: any, toolContext: any) {
          return { content: await statusText(toolContext.sessionID) }
        },
      })
      editor.add({
        name: "army_wait",
        description:
          "Block until one (mode any) or all (mode all) of your running children finish, instead of idling. " +
          "Returns which children ended with their status and which are still running.",
        input: {
          type: "object",
          properties: {
            mode: { type: "string", enum: ["any", "all"], description: "any (default) or all" },
            timeoutMinutes: { type: "number", minimum: 0, description: "Give up after this long, default 30" },
          },
          additionalProperties: false,
        },
        async execute(input: any, toolContext: any) {
          const { army } = await locate(toolContext.sessionID)
          if (!army) return { content: "Not inside an army." }
          const timeoutMs = Number(input.timeoutMinutes ?? 30) * 60_000
          const { watched, timedOut } = await waitFor(army, toolContext.sessionID, input.mode ?? "any", timeoutMs, toolContext.signal)
          return { content: describeWait(watched, timedOut) }
        },
      })
      editor.add({
        name: "army_check",
        description:
          "Before reporting done: list git worktrees under <worktree>/.army/ and local <current branch>-* branches not merged into the current branch.",
        input: {
          type: "object",
          properties: { worktree: { type: "string", description: "Absolute path of your worktree" } },
          required: ["worktree"],
          additionalProperties: false,
        },
        async execute(input: any) {
          try {
            return { content: checkWorktree(String(input.worktree)) }
          } catch (error: any) {
            return { content: `army_check failed: ${error?.message ?? error}` }
          }
        },
      })
    })


    const validate = (located: Located, child: string) => {
      const { army, agent, depth } = located
      if (!army) return child === MANAGER || child === IC ? `call army_mobilize before delegating to ${child}.` : undefined
      if (agent === IC) return `army-soldier does not delegate. Do the work yourself and report to your officer.`
      if (child !== MANAGER && child !== IC) return depth === 0 ? undefined : `inside an army, delegate only to "${MANAGER}" or "${IC}" (got "${child}").`
      if (depth + 1 > army.maxDepth) return `depth limit ${army.maxDepth} reached. Do this work yourself or have a soldier at your level do it.`
      if (child === MANAGER && depth + 1 === army.maxDepth) return `depth ${depth + 1} is the soldier level (maxDepth ${army.maxDepth}); spawn "${IC}" instead.`
      return undefined
    }

    const validateBudget = (army: Army, node: Node | undefined, child: string, budget: number | undefined) => {
      if (child === MANAGER && budget === undefined) return `a ${MANAGER} prompt must start with the line "TROOPS: <n>" (agents its subtree may spawn).`
      const cost = spawnCost(child, budget)
      if (army.spawned >= army.maxAgents) return `global agent cap ${army.maxAgents} used up. Reuse existing children via sessionID or do the work yourself.`
      if (cost > remaining(army, node)) return `spawning this ${child} costs ${cost} but your budget has ${remaining(army, node)} left. Lower TROOPS, reuse children, or do the work yourself.`
      return undefined
    }

    const childPreamble = (army: Army, child: string, depth: number, budget: number) =>
      `[army] You are ${child} at depth ${depth}/${army.maxDepth}` +
      `${child === MANAGER ? `; your children may be ${depth + 1 === army.maxDepth ? `"${IC}" only` : `"${MANAGER}" or "${IC}"`}` : ""}. ` +
      `Budget left: ${budget}.\n\n`

    await ctx.tool.hook("execute.before", async (event) => {
      if (event.tool !== "subagent") return
      const input = event.input ?? {}
      const child = String(input.agent ?? "")
      const located = await locate(event.sessionID)
      const shapeError = located.army && input.sessionID && located.agent !== soldier ? undefined : validate(located, child)
      if (shapeError) throw new Error(`[army] BLOCKED: ${shapeError}`)
      const army = located.army
      if (!army || input.sessionID) return

      const parsed = parseBudget(String(input.prompt ?? ""))
      const budgetError = validateBudget(army, located.node, child, parsed.budget)
      if (budgetError) throw new Error(`[army] BLOCKED: ${budgetError}`)

      const budget = child === MANAGER ? (parsed.budget ?? 0) : 0
      const cost = spawnCost(child, budget)
      if (located.node) located.node.used += cost
      else army.used += cost
      army.spawned++
      if (child === MANAGER) army.officers++
      else army.ics++
      pending.set(spawnKey(event.sessionID, input), { army, child, parentID: event.sessionID, depth: located.depth + 1, budget, cost })
      input.prompt = childPreamble(army, child, located.depth + 1, budget) + parsed.prompt
      save(army)
    })

    const refund = (spawn: { army: Army; child: string; parentID: string; cost: number }) => {
      const parent = spawn.army.nodes[spawn.parentID]
      if (parent) parent.used -= spawn.cost
      else spawn.army.used -= spawn.cost
      spawn.army.spawned--
      if (spawn.child === MANAGER) spawn.army.officers--
      else spawn.army.ics--
    }

    await ctx.tool.hook("execute.after", async (event) => {
      if (event.tool !== "subagent") return
      const key = spawnKey(event.sessionID, event.input ?? {})
      const spawn = pending.get(key)
      if (!spawn) return
      pending.delete(key)
      const sessionID = event.status === "completed" ? childSessionID(event.result) : undefined
      if (!sessionID) {
        refund(spawn)
        return save(spawn.army)
      }
      spawn.army.nodes[sessionID] = {
        sessionID,
        parentID: spawn.parentID,
        agent: spawn.child,
        description: String(event.input?.description ?? ""),
        depth: spawn.depth,
        status: "running",
        startedAt: Date.now(),
        budget: spawn.budget,
        used: 0,
      }
      owners.set(sessionID, spawn.army)
      save(spawn.army)
    })

    return () => controller.abort()
  },
}

export default Army
