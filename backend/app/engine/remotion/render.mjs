#!/usr/bin/env node
/**
 * Remotion render entry point.
 * Called from Python: node render.mjs <manifest.json> <output.mp4>
 *
 * The manifest JSON contains everything needed:
 *   { videoSrc, zoomEntries, defaultZoom, durationFrames, fps, width, height }
 *
 * videoSrc must be an absolute filesystem path. This script copies the
 * file into the Webpack bundle's public/ directory so Remotion's
 * OffthreadVideo can access it via staticFile().
 */
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition, ensureBrowser } from "@remotion/renderer";
import { readFileSync, existsSync, copyFileSync, mkdirSync } from "fs";
import { resolve, dirname, basename, isAbsolute } from "path";
import { fileURLToPath } from "url";

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

// Prefer system Chromium (already in Docker image) over downloading.
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
console.log(`[REMOTION] Bundle at: ${bundleLocation}`);

// Copy the video file INTO the bundle's public/ directory so
// OffthreadVideo can load it via the bundle's HTTP server.
// Remotion docs: "you can add assets to the public folder that is
// inside the bundle after the fact" when using SSR APIs.
const videoFileName = basename(videoSrc);
const bundlePublic = resolve(bundleLocation, "public");
mkdirSync(bundlePublic, { recursive: true });
const videoDest = resolve(bundlePublic, videoFileName);
console.log(`[REMOTION] Copying video into bundle: ${videoSrc} -> ${videoDest}`);
copyFileSync(resolve(videoSrc), videoDest);

// The component receives the staticFile-style path (just the filename,
// served from the bundle's public/ root).
const videoUrl = videoFileName;
console.log(`[REMOTION] Video URL for composition: ${videoUrl}`);

const inputProps = { videoSrc: videoUrl, zoomEntries, defaultZoom };

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
