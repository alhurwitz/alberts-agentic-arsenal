import { existsSync, readdirSync, readFileSync } from "node:fs"
import { homedir } from "node:os"
import { basename, dirname, join, resolve, sep } from "node:path"

// Injects the second-brain project page for the session's directory into the system prompt.
// A page matches when the directory is inside one of its frontmatter `paths:` entries
// (longest match wins), else when a page is named after the directory or one of its ancestors.
// Pages are re-read on every request so vault edits apply immediately.
const VAULT = process.env.SECOND_BRAIN_DIR ?? join(homedir(), "Code", "second-brain")
const PROJECTS = join(VAULT, "projects")
const FRONTMATTER = /^---\n([\s\S]*?)\n---\n?/

type Page = { name: string; paths: string[]; body: string }

const expand = (path: string) => resolve(path.replace(/^~(?=$|\/)/, homedir()))
const inside = (dir: string, root: string) => dir === root || dir.startsWith(root + sep)

const loadPages = (): Page[] => {
  if (!existsSync(PROJECTS)) return []
  return readdirSync(PROJECTS)
    .filter((file) => file.endsWith(".md"))
    .map((file) => {
      const text = readFileSync(join(PROJECTS, file), "utf8")
      const front = text.match(FRONTMATTER)?.[1] ?? ""
      const list = front.match(/^paths:[ \t]*\n((?:[ \t]*-.*(?:\n|$))*)/m)?.[1] ?? ""
      const paths = [...list.matchAll(/^\s*-\s*["']?([^"'\n]+?)["']?\s*$/gm)].map((m) => expand(m[1]))
      return { name: file.slice(0, -3), paths, body: text.replace(FRONTMATTER, "").trim() }
    })
}

export const pageFor = (directory: string, pages: Page[]): Page | undefined => {
  const dir = resolve(directory)
  let best: { page: Page; length: number } | undefined
  for (const page of pages) {
    for (const root of page.paths) {
      if (inside(dir, root) && root.length > (best?.length ?? -1)) best = { page, length: root.length }
    }
  }
  if (best) return best.page
  for (let d = dir; dirname(d) !== d; d = dirname(d)) {
    const page = pages.find((p) => p.name === basename(d))
    if (page) return page
  }
}

const SecondBrain = {
  id: "second-brain",
  async setup(ctx) {
    const directory = ctx.location.directory

    await ctx.session.hook("context", (event) => {
      let page: Page | undefined
      try {
        page = pageFor(directory, loadPages())
      } catch {
        return
      }
      if (!page) return
      event.system.push({
        type: "text",
        text: `Second brain project page for this repo (${join(PROJECTS, page.name)}.md), already loaded:\n\n${page.body}`,
      })
    })
  },
}

export default SecondBrain
