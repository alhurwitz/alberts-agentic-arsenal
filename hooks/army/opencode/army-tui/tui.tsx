/** @jsxImportSource @opentui/solid */
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"
import { renderTree, type TreeOrg } from "./tree.ts"

// V2 TUI plugin: default export { id, setup }. Commands are registered from an "app" slot,
// the same way the built-in /stats command does it. @opentui/solid is supplied by the host.
const DIR = join(homedir(), ".local/share/opencode/army")

const loadOrgs = (): TreeOrg[] =>
  existsSync(DIR)
    ? readdirSync(DIR)
        .filter((file) => file.endsWith(".json"))
        .map((file) => join(DIR, file))
        .sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs)
        .map((file) => JSON.parse(readFileSync(file, "utf8")))
    : []

// Prefer the army this session belongs to (as root or member); fall back to the latest run.
const statusText = (sessionID: string | undefined) => {
  const armies = loadOrgs()
  const army = armies.find((o) => o.rootID === sessionID || (sessionID && o.nodes?.[sessionID])) ?? armies[0]
  return army ? renderTree(army) : "No army runs yet. Start one with /alberts-army <task>."
}

export default {
  id: "army-tui",
  setup(t: any) {
    t.ui.slot({
      append: "app",
      render() {
        t.keymap.layer(() => ({
          mode: "global",
          commands: [
            {
              id: "army.status",
              title: "Army status",
              description: "Show the agent team tree without a model request",
              group: "Army",
              slash: { name: "alberts-army-status" },
              palette: true,
              run() {
                let text: string
                try {
                  text = statusText(t.ui.router.current()?.sessionID)
                } catch (e) {
                  text = `Army status failed: ${e instanceof Error ? e.message : e}`
                }
                t.ui.dialog.show(() => (
                  <box flexDirection="column" paddingLeft={2} paddingRight={2} paddingBottom={1}>
                    <text>Army Status</text>
                    <text>{text}</text>
                  </box>
                ))
                t.ui.dialog.set?.({ size: "large" })
              },
            },
          ],
        }))
        return null
      },
    })
  },
}
