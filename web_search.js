/**
 * web_search.js — Web search anti-detect via Puppeteer (Obscura-style)
 * Usage: node web_search.js "<query>" [max_results]
 * Output: JSON sur stdout
 */
const puppeteer = require('puppeteer-core');

const query = process.argv[2];
const maxResults = parseInt(process.argv[3] || '5', 10);

if (!query) { process.exit(1); }

async function search() {
    const browser = await puppeteer.launch({
        headless: 'new',
        executablePath: process.env.CHROME_PATH || '/usr/bin/chromium',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
        ],
    });

    try {
        const page = await browser.newPage();
        await page.setUserAgent(
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        );

        // DuckDuckGo HTML
        const url = 'https://html.duckduckgo.com/html/?q=' + encodeURIComponent(query);
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 15000 });

        const results = await page.evaluate((max) => {
            const items = [];
            const els = document.querySelectorAll('.result');
            for (let i = 0; i < els.length && i < max; i++) {
                const titleEl = els[i].querySelector('.result__title a, .result__a');
                const snippetEl = els[i].querySelector('.result__snippet');
                const urlEl = els[i].querySelector('.result__url');
                items.push({
                    title: (titleEl?.textContent || '').trim(),
                    url: (urlEl?.textContent || titleEl?.href || '').trim(),
                    snippet: (snippetEl?.textContent || '').trim(),
                });
            }
            return items;
        }, maxResults);

        process.stdout.write(JSON.stringify({ query, results }));
    } finally {
        await browser.close();
    }
}

search().catch(e => {
    process.stdout.write(JSON.stringify({ error: e.message, query }));
    process.exit(1);
});
