#!/usr/bin/env node
/**
 * Remotion render entry point.
 * Called from Python: node render.mjs <manifest.json> <output.mp4>
 *
 * The manifest JSON contains everything needed:
 *   { videoSrc, zoomEntries, defaultZoom, durationFrames, fps, width, height }
 *
 * videoSrc must be an absolute filesystem path. This script converts it
 * to a file:// URL for Remotion's OffthreadVideo component.
 */
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition, ensureBrowser } from "@remotion/renderer";
import { readFileSync, existsSync } from "fs";
import { resolve, dirname, isAbsolute } from "path";
import { fileURLToPath, pathToFileURL } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const [manifestPath, outputPath] = process.argv.slice(2);
if (!manifestPath || !outputPath) {
  console.error("Usage: node render.mjs <manifest.json> <output.mp4>");
  process.exit(1);
}

const manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
let {
  videoSrc,
  zoomEntries,
  defaultZoom,
  durationFrames,
  fps = 30,
  width = 1920,
  height = 1080,
} = manifest;

// Convert filesystem path to file:// URL for OffthreadVideo
if (isAbsolute(videoSrc) && !videoSrc.startsWith("file://")) {
  videoSrc = pathToFileURL(resolve(videoSrc)).href;
}
console.log(`[REMOTION] videoSrc: ${videoSrc}`);

// Prefer system Chromium (already in Docker image) over downloading a new one.
const CHROMIUM_PATHS = [
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
  "/usr/bin/google-chrome",
];
let browserExe = CHROMIUM_PATHS.find((p) => existsSync(p)) || null;
if (browserExe) {
  console.log(`[REMOTION] Using system browser: ${browserExe}`);
} else {
  console.log(`[REMOTION] No system browser found, ensuring Remotion browser...`);
  await ensureBrowser();
}

console.log(`[REMOTION] Bundling composition...`);
const bundleLocation = await bundle({
  entryPoint: resolve(__dirname, "src/index.ts"),
  webpackOverride: (config) => config,
});

const inputProps = { videoSrc, zoomEntries, defaultZoom };

const chromiumOpts = {
  disableWebSecurity: true,
  gl: "angle",
};
const browserOpts = browserExe ? { browserExecutable: browserExe } : {};

console.log(`[REMOTION] Selecting composition ZoomSegment...`);
const composition = await selectComposition({
  serveUrl: bundleLocation,
  id: "ZoomSegment",
  inputProps,
  chromiumOptions: chromiumOpts,
  ...browserOpts,
});

composition.durationInFrames = durationFrames;
composition.fps = fps;
composition.width = width;
composition.height = height;

console.log(`[REMOTION] Rendering ${durationFrames} frames at ${fps}fps (${width}x${height})...`);
await renderMedia({
  composition,
  serveUrl: bundleLocation,
  codec: "h264",
  outputLocation: resolve(outputPath),
  inputProps,
  chromiumOptions: chromiumOpts,
  ...browserOpts,
  onProgress: ({ progress }) => {
    if (Math.round(progress * 100) % 10 === 0) {
      process.stdout.write(`\r[REMOTION] Progress: ${Math.round(progress * 100)}%`);
    }
  },
});

console.log(`\n[REMOTION] Done: ${outputPath}`);
