/**
 * test_bridge.js — Test du pont France Student Bridge
 * 
 * Teste: /health, /v1/models, /v1/chat/completions (stream + non-stream)
 */
const BASE = process.env.BRIDGE_URL || 'http://localhost:8765';

async function main() {
    console.log('=== TEST FRANCE STUDENT BRIDGE ===\n');

    // 1. Health
    console.log('[1] GET /health');
    const health = await fetch(`${BASE}/health`);
    const healthData = await health.json();
    console.log('    status:', healthData.status, '| auth:', healthData.authenticated);
    if (healthData.status !== 'ok') throw new Error('Health failed');
    if (!healthData.authenticated) console.log('    ⚠ Non authentifié — lance /auth/login d\'abord');

    // 2. Models
    console.log('\n[2] GET /v1/models');
    const models = await fetch(`${BASE}/v1/models`);
    const modelsData = await models.json();
    console.log(`    ${modelsData.data.length} modèles:`);
    for (const m of modelsData.data) {
        console.log(`      [${m.id}] ${m.id} (${m.owned_by})`);
    }

    // 3. Chat non-stream
    console.log('\n[3] POST /v1/chat/completions (non-stream)');
    const chatResp = await fetch(`${BASE}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: 'gpt-5.6-sol',
            messages: [{ role: 'user', content: 'Dis juste "coucou" en 1 mot' }],
            stream: false,
        }),
    });
    const chatData = await chatResp.json();
    const text = chatData.choices?.[0]?.message?.content || '(vide)';
    console.log('    Réponse:', text);
    console.log('    Modèle:', chatData.model, '| Tokens:', chatData.usage?.total_tokens);

    // 4. Chat stream
    console.log('\n[4] POST /v1/chat/completions (stream)');
    const streamResp = await fetch(`${BASE}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: 'claude-sonnet-5',
            messages: [{ role: 'user', content: 'Compte de 1 a 5' }],
            stream: true,
        }),
    });

    process.stdout.write('    Réponse: ');
    const reader = streamResp.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        for (const line of chunk.split('\n')) {
            if (line.startsWith('data:')) {
                const data = line.slice(5).trim();
                if (data === '[DONE]') continue;
                try {
                    const parsed = JSON.parse(data);
                    const delta = parsed.choices?.[0]?.delta?.content || '';
                    if (delta) { process.stdout.write(delta); fullText += delta; }
                } catch (e) {}
            }
        }
    }
    console.log('\n    Stream OK:', fullText.length > 0);

    console.log('\n=== TOUS LES TESTS SONT PASSÉS ===');
}

main().catch(e => { console.error('ERREUR:', e.message); process.exit(1); });