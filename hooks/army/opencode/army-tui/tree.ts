// Shared by the army server plugin and the army-tui terminal plugin. Keep dependency-free.
export type TreeNode = {
  sessionID: string
  parentID: string
  agent?: string
  description: string
  status: string
  startedAt: number
  endedAt?: number
  budget: number
  used: number
}
export type TreeOrg = {
  rootID: string
  maxDepth: number
  maxAgents: number
  spawned: number
  managers: number
  ics: number
  used: number
  nodes: Record<string, TreeNode>
}

const MANAGER = "army-officer"
type Node = TreeNode
type Army = TreeOrg

export const elapsed = (node: Node, now: number) => {
  const seconds = Math.max(0, Math.round(((node.endedAt ?? now) - node.startedAt) / 1000))
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m${String(seconds % 60).padStart(2, "0")}s`
}

export const childrenOf = (army: Army, parentID: string) =>
  Object.values(army.nodes)
    .filter((node) => node.parentID === parentID)
    .sort((a, b) => a.startedAt - b.startedAt)

const renderNode = (army: Army, node: Node, now: number, indent: string): string[] => {
  const role = node.agent === MANAGER ? "officer" : "soldier"
  const budget = node.agent === MANAGER ? `, budget ${node.used}/${node.budget}` : ""
  const line = `${indent}- ${role} "${node.description}" ${node.status} ${elapsed(node, now)}${budget} [${node.sessionID}]`
  return [line, ...childrenOf(army, node.sessionID).flatMap((child) => renderNode(army, child, now, `${indent}  `))]
}

export const renderTree = (army: Army, now = Date.now()) => {
  const nodes = Object.values(army.nodes)
  const running = nodes.filter((node) => node.status === "running").length
  return [
    `General ${army.rootID} (maxDepth ${army.maxDepth}): root budget ${army.used}/${army.maxAgents}`,
    ...childrenOf(army, army.rootID).flatMap((child) => renderNode(army, child, now, "  ")),
    `Totals: spawned ${army.spawned}/${army.maxAgents} (officers ${army.managers}, soldiers ${army.ics}); running ${running}.`,
  ].join("\n")
}

