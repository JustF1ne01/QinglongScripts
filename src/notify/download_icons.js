const sharp = require('sharp');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const TARGET_DIR = __dirname;
const ICON_SIZE = 256;

function download(url) {
    return new Promise((resolve, reject) => {
        const client = url.startsWith('https') ? https : http;
        const req = client.get(url, {
            headers: { 'User-Agent': 'Mozilla/5.0' },
            timeout: 15000
        }, (res) => {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                download(res.headers.location).then(resolve).catch(reject);
                return;
            }
            const chunks = [];
            res.on('data', chunk => chunks.push(chunk));
            res.on('end', () => {
                if (res.statusCode === 200) {
                    resolve(Buffer.concat(chunks));
                } else {
                    reject(new Error(`HTTP ${res.statusCode}`));
                }
            });
        });
        req.on('error', reject);
        req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
    });
}

async function downloadAndSave(name, url, isSvg = false) {
    const output = path.join(TARGET_DIR, `${name}.png`);
    try {
        console.log(`[${name}] Downloading from: ${url}`);
        const data = await download(url);

        if (isSvg || url.includes('simpleicons.org')) {
            // Convert SVG to PNG with white background
            const pngBuffer = await sharp(data)
                .resize(ICON_SIZE, ICON_SIZE, { fit: 'contain', background: { r: 255, g: 255, b: 255, alpha: 0 } })
                .png()
                .toBuffer();
            fs.writeFileSync(output, pngBuffer);
        } else {
            // Convert any image to PNG at target size
            const pngBuffer = await sharp(data)
                .resize(ICON_SIZE, ICON_SIZE, { fit: 'contain', background: { r: 255, g: 255, b: 255, alpha: 0 } })
                .png()
                .toBuffer();
            fs.writeFileSync(output, pngBuffer);
        }
        console.log(`  OK: ${name}.png (${(data.length / 1024).toFixed(1)} KB)`);
        return true;
    } catch (err) {
        console.log(`  FAIL: ${name} - ${err.message}`);
        return false;
    }
}

// Generate a placeholder icon with text
function generatePlaceholder(name, text, bgColor, textColor = '#FFFFFF') {
    const output = path.join(TARGET_DIR, `${name}.png`);
    const svg = `
    <svg width="${ICON_SIZE}" height="${ICON_SIZE}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${ICON_SIZE}" height="${ICON_SIZE}" rx="40" fill="${bgColor}"/>
        <text x="50%" y="50%" dominant-baseline="central" text-anchor="middle"
              font-family="Arial, sans-serif" font-size="${ICON_SIZE / 4}" font-weight="bold" fill="${textColor}">
            ${text}
        </text>
    </svg>`;

    return sharp(Buffer.from(svg))
        .resize(ICON_SIZE, ICON_SIZE)
        .png()
        .toFile(output)
        .then(() => {
            console.log(`  OK: ${name}.png (generated placeholder)`);
            return true;
        })
        .catch(err => {
            console.log(`  FAIL placeholder: ${name} - ${err.message}`);
            return false;
        });
}

async function main() {
    console.log('Downloading notification channel icons...\n');

    // Simple Icons CDN sources (SVG)
    const simpleIconSources = {
        'telegram': 'telegram',
        'smtp': 'gmail',
        'synology': 'synology',
        'go-cqhttp': 'qq',
        'wechat-work': 'wechat',
        'ntfy': 'ntfy',
        'console': 'gnometerminal',
    };

    // GitHub and other PNG sources
    const pngSources = {
        'gotify': 'https://raw.githubusercontent.com/gotify/logo/master/gotify-logo.png',
        'bark': 'https://raw.githubusercontent.com/Finb/Bark/master/Bark/Assets.xcassets/AppIcon.appiconset/1024.png',
        'ntfy_alt': 'https://raw.githubusercontent.com/binwiederhier/ntfy/main/.github/images/logo.png',
    };

    // Download Simple Icons
    for (const [name, slug] of Object.entries(simpleIconSources)) {
        const url = `https://cdn.simpleicons.org/${slug}`;
        const success = await downloadAndSave(name, url, true);
        if (!success) {
            // Try fallback for ntfy
            if (name === 'ntfy' && pngSources.ntfy_alt) {
                await downloadAndSave(name, pngSources.ntfy_alt, false);
            }
        }
        await new Promise(r => setTimeout(r, 500)); // Rate limit
    }

    // Download PNG sources
    for (const [name, url] of Object.entries(pngSources)) {
        if (name === 'ntfy_alt') continue; // Already tried as fallback
        await downloadAndSave(name, url, false);
        await new Promise(r => setTimeout(r, 500));
    }

    // Generate placeholders for missing icons
    const placeholders = {
        'bark': { text: 'Bark', bg: '#FF6B6B' },
        'dingtalk': { text: 'DD', bg: '#0089FF' },
        'feishu': { text: 'FS', bg: '#3370FF' },
        'igot': { text: 'iG', bg: '#FF4757' },
        'serverchan': { text: 'SC', bg: '#FF6B81' },
        'pushdeer': { text: 'PD', bg: '#2ED573' },
        'pushplus': { text: 'P+', bg: '#1E90FF' },
        'weplusbot': { text: 'WB', bg: '#07C160' },
        'qmsg': { text: 'QM', bg: '#FFA502' },
        'aibotk': { text: 'AI', bg: '#8B5CF6' },
        'pushme': { text: 'PM', bg: '#10B981' },
        'chronocat': { text: 'CC', bg: '#F59E0B' },
        'webhook': { text: 'WH', bg: '#6366F1' },
        'wxpusher': { text: 'WP', bg: '#07C160' },
    };

    console.log('\nGenerating placeholder icons for remaining channels...\n');
    for (const [name, config] of Object.entries(placeholders)) {
        const output = path.join(TARGET_DIR, `${name}.png`);
        if (!fs.existsSync(output)) {
            await generatePlaceholder(name, config.text, config.bg);
        }
    }

    console.log('\nDone!');
}

main().catch(console.error);
