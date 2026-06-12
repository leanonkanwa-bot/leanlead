import puppeteer from 'puppeteer';
import { readFileSync, unlinkSync } from 'fs';
import { execSync } from 'child_process';

const [,, htmlPath, outputPath, durationStr, widthStr, heightStr, fpsStr] = process.argv;
const duration = parseFloat(durationStr) || 2.0;
const width = parseInt(widthStr) || 1080;
const height = parseInt(heightStr) || 1920;
const fps = parseInt(fpsStr) || 30;

const browser = await puppeteer.launch({
    headless: true,
    args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=' + width + ',' + height,
    ]
});

const page = await browser.newPage();
await page.setViewport({ width, height });

const html = readFileSync(htmlPath, 'utf8');
await page.setContent(html, { waitUntil: 'networkidle0' });

// Wait for animations to settle
await page.waitForTimeout(parseInt(duration * 1000 * 0.7));

// Take screenshot
const screenshotPath = outputPath.replace('.mp4', '_frame.png');
await page.screenshot({ path: screenshotPath, fullPage: false });

await browser.close();

// Convert screenshot to video with FFmpeg
const ffmpeg = process.env.FFMPEG_PATH || 'ffmpeg';
execSync(`${ffmpeg} -y -loglevel error -loop 1 -i "${screenshotPath}" -t ${duration} -vf "scale=${width}:${height}" -c:v libx264 -preset ultrafast -pix_fmt yuv420p -an "${outputPath}"`);

// Cleanup
try { unlinkSync(screenshotPath); } catch(e) {}

console.log('rendered:' + outputPath);
