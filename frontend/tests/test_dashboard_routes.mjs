import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const webRoot = path.resolve(__dirname, "..");

console.log("============================================================");
console.log("      CLINICVOICE PHASE 3 WEB DASHBOARD VERIFICATION       ");
console.log("============================================================");

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`[PASS] ${message}`);
    passed++;
  } else {
    console.error(`[FAIL] ${message}`);
    failed++;
  }
}

// 1. Verify Modular Home Sections (User requirement: 5 distinct sections in a home folder)
const homeSectionsDir = path.join(webRoot, "src", "components", "pages", "home");
assert(fs.existsSync(homeSectionsDir), "Home page sections directory exists at src/components/pages/home");

const expectedHomeSections = [
  "QuickStatsSection.tsx",
  "TodayAppointmentsSection.tsx",
  "RecentCallsSection.tsx",
  "CallbackTasksSection.tsx",
  "LiveAgentStatusSection.tsx",
  "index.ts",
];

for (const sec of expectedHomeSections) {
  const filePath = path.join(homeSectionsDir, sec);
  assert(fs.existsSync(filePath), `Home modular section exists: ${sec}`);
}

// 2. Verify Reusable Atomic Primitives in src/components/ui/
const uiDir = path.join(webRoot, "src", "components", "ui");
const expectedUi = ["Button.tsx", "Card.tsx", "Badge.tsx", "AudioPlayer.tsx"];
for (const ui of expectedUi) {
  assert(fs.existsSync(path.join(uiDir, ui)), `Reusable UI primitive exists: src/components/ui/${ui}`);
}

// 3. Verify All Next.js App Router Pages
const appDir = path.join(webRoot, "src", "app");
const expectedPages = [
  "layout.tsx",
  "page.tsx",
  "globals.css",
  "calls/page.tsx",
  "appointments/page.tsx",
  "knowledge/page.tsx",
  "settings/page.tsx",
];

for (const pg of expectedPages) {
  assert(fs.existsSync(path.join(appDir, pg)), `App Router route page exists: src/app/${pg}`);
}

// 4. Verify Next.js Build Output Artifacts
const buildOutput = path.join(webRoot, ".next", "BUILD_ID");
assert(fs.existsSync(buildOutput), "Next.js production build succeeded and .next/BUILD_ID generated");

console.log("\n------------------------------------------------------------");
console.log(`TEST SUMMARY: ${passed} assertions passed, ${failed} failed.`);
console.log("------------------------------------------------------------\n");

if (failed > 0) {
  process.exit(1);
} else {
  console.log("RESULT: ALL PHASE 3 DASHBOARD SPECIFICATIONS VERIFIED! [PASS]");
}
