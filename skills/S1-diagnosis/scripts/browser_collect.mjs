#!/usr/bin/env node
/** Collect one consumer-product answer through a visible, human-authorized browser session */

import crypto from "node:crypto"
import fs from "node:fs/promises"
import path from "node:path"
import process from "node:process"
import readline from "node:readline/promises"
import { fileURLToPath } from "node:url"
import { chromium } from "playwright"

const MODULE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")

const PRODUCTS = {
  doubao: "https://www.doubao.com/chat/",
  qwen: "https://www.qianwen.com/",
  deepseek: "https://chat.deepseek.com/",
}

function parseArgs(argv) {
  const values = {}
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index]
    if (!key?.startsWith("--") || argv[index + 1] === undefined) {
      throw new Error(`参数必须使用 --name value 形式，收到 ${key ?? "<empty>"}`)
    }
    values[key.slice(2)] = argv[index + 1]
  }
  for (const required of ["request", "output", "input-selector", "answer-selector"]) {
    if (!values[required]) throw new Error(`缺少 --${required}`)
  }
  return values
}

function fingerprint(request) {
  const canonical = JSON.stringify(sortObject(request))
  return crypto.createHash("sha256").update(canonical, "utf8").digest("hex")
}

function sortObject(value) {
  if (Array.isArray(value)) return value.map(sortObject)
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, sortObject(value[key])]))
  }
  return value
}

async function waitForStableText(locator, timeoutMs) {
  const deadline = Date.now() + timeoutMs
  let previous = ""
  let stableRounds = 0
  while (Date.now() < deadline) {
    const current = (await locator.last().innerText()).trim()
    if (current && current === previous) stableRounds += 1
    else stableRounds = 0
    if (stableRounds >= 3) return current
    previous = current
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error(`回答在 ${timeoutMs}ms 内未稳定`)
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  const request = JSON.parse(await fs.readFile(args.request, "utf8"))
  if (request.channel !== "official_app_browser") throw new Error("请求通道必须为 official_app_browser")
  const product = request.consumer_product
  const url = args.url ?? PRODUCTS[product]
  if (!url) throw new Error(`不支持的平台 ${product}`)

  const root = path.join(MODULE_ROOT, "work")
  const profileDir = path.join(root, "browser-profiles", product)
  const artifactDir = path.join(root, "browser-artifacts")
  await fs.mkdir(profileDir, { recursive: true })
  await fs.mkdir(artifactDir, { recursive: true })

  const context = await chromium.launchPersistentContext(profileDir, { headless: args.headless === "true" })
  const page = context.pages()[0] ?? await context.newPage()
  await page.goto(url, { waitUntil: "domcontentloaded" })

  const terminal = readline.createInterface({ input: process.stdin, output: process.stdout })
  if (args["skip-auth-wait"] !== "true") {
    await terminal.question("请本人完成登录、验证码和权限操作，并确认页面可提问后按 Enter，未完成请用 Ctrl+C 退出：")
  }
  await page.locator(args["input-selector"]).fill(request.query)
  if (args["send-selector"]) await page.locator(args["send-selector"]).click()
  else await page.locator(args["input-selector"]).press(args["submit-key"] ?? "Enter")
  const answerLocator = page.locator(args["answer-selector"])
  await answerLocator.last().waitFor({ state: "visible", timeout: Number(args.timeout ?? 120000) })
  const rawText = await waitForStableText(answerLocator, Number(args.timeout ?? 120000))

  const citations = []
  if (args["citation-selector"]) {
    for (const anchor of await page.locator(args["citation-selector"]).all()) {
      const href = await anchor.getAttribute("href")
      if (href?.startsWith("http://") || href?.startsWith("https://")) {
        citations.push({ url: href, title: (await anchor.innerText()).trim() || null })
      }
    }
  }
  const inlineCitationTitles = args["inline-citation-selector"]
    ? (await page.locator(args["inline-citation-selector"]).allTextContents()).map((item) => item.trim()).filter(Boolean)
    : []
  let searchExecuted = request.configuration.search_mode === "none" ? false : null
  if (args["search-evidence-selector"] && args["search-evidence-text"]) {
    const evidenceText = await page.locator(args["search-evidence-selector"]).innerText()
    searchExecuted = evidenceText.includes(args["search-evidence-text"])
  } else if (citations.length) {
    searchExecuted = true
  }
  const stamp = new Date().toISOString().replaceAll(":", "-")
  const screenshotPath = path.join(artifactDir, `${request.request_id}-${stamp}.png`)
  await page.screenshot({ path: screenshotPath, fullPage: true })

  const response = {
    schema_version: "1.0.0",
    response_id: `response-${request.request_id.slice("request-".length)}`,
    request_id: request.request_id,
    protocol_id: request.protocol_id,
    query_id: request.query_id,
    consumer_product: product,
    provider: "consumer_web",
    channel: "official_app_browser",
    status: "completed",
    collected_at: new Date().toISOString(),
    model_requested: null,
    model_reported: null,
    search_requested: request.configuration.search_mode === "native",
    search_executed: searchExecuted,
    citation_mode: citations.length ? "structured" : inlineCitationTitles.length ? "inline_only" : "unknown",
    raw_text: rawText,
    citations,
    raw_payload: { page_url: page.url(), title: await page.title(), inline_citation_titles: inlineCitationTitles },
    request_fingerprint: fingerprint(request),
    platform_request_id: null,
    screenshot_path: screenshotPath,
    error: null,
  }
  await fs.mkdir(path.dirname(path.resolve(args.output)), { recursive: true })
  await fs.writeFile(args.output, `${JSON.stringify(response, null, 2)}\n`, "utf8")
  if (args["auto-close"] !== "true") {
    await terminal.question(`已保存 ${args.output}，检查完成后按 Enter 关闭浏览器：`)
  }
  terminal.close()
  await context.close()
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`)
  process.exitCode = 1
})
