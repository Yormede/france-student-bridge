/**
 * get_jwt.js — Obtient un JWT France Student via Puppeteer SSO
 * 
 * Flow: Login WHMCS -> SSO -> IA portal -> GET /api/auth/api-token -> JWT
 * 
 * Env vars: FS_EMAIL, FS_PASSWORD
 * Output: JWT token sur stdout (une seule ligne)
 */
const puppeteer = require('puppeteer-core');

const EMAIL = process.env.FS_EMAIL;
const PASSWORD = process.env.FS_PASSWORD;

if (!EMAIL || !PASSWORD) {
    console.error('FS_EMAIL et FS_PASSWORD requis');
    process.exit(1);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getJWT() {
    const browser = await puppeteer.launch({
        headless: 'new',
        executablePath: process.env.CHROME_PATH || '/usr/bin/chromium',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--single-process',
        ],
    });

    try {
        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');

        // 1. Login WHMCS
        await page.goto('https://my.francestudent.org/login.php', {
            waitUntil: 'networkidle2',
            timeout: 30000,
        });
        await sleep(2000);

        // Accept cookies if present
        await page.evaluate(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const accept = btns.find(b => (b.textContent || '').toLowerCase().includes('tout accepter'));
            if (accept) accept.click();
        });
        await sleep(1000);

        await page.type('input[name="username"]', EMAIL);
        await page.type('input[name="password"]', PASSWORD);
        await page.click('#login');
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 });
        await sleep(2000);

        // 2. Go to IA portal (triggers SSO)
        let jwt = null;

        // Intercept the api-token response
        page.on('response', async resp => {
            if (resp.url().includes('/api/auth/api-token')) {
                try {
                    const data = await resp.json();
                    if (data.accessToken) jwt = data.accessToken;
                } catch (e) {}
            }
        });

        await page.goto('https://ia.francestudent.org/login', {
            waitUntil: 'networkidle2',
            timeout: 20000,
        });
        await sleep(2000);

        // Click "Sign in with France Student" button
        await page.evaluate(() => {
            const el = Array.from(document.querySelectorAll('button, a'))
                .find(x => (x.textContent || '').toLowerCase().includes('france student'));
            if (el) el.click();
        });

        // Wait for redirect chain to complete
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 30000 }).catch(() => {});
        await sleep(3000);

        // If JWT not captured from response, try fetching directly
        if (!jwt) {
            try {
                const resp = await page.evaluate(async () => {
                    const r = await fetch('/api/auth/api-token');
                    return r.json();
                });
                if (resp && resp.accessToken) jwt = resp.accessToken;
            } catch (e) {}
        }

        if (!jwt) {
            throw new Error('JWT non obtenu apres SSO');
        }

        // Output JWT on stdout (only the token, nothing else)
        process.stdout.write(jwt);
    } finally {
        await browser.close();
    }
}

getJWT().catch(e => {
    console.error(`[get_jwt] ERREUR: ${e.message}`);
    process.exit(1);
});
