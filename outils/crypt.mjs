// Chiffre / déchiffre les données de la carte (AES-256-GCM, clé PBKDF2-SHA256).
// Usage : CARTE_MDP='...' node crypt.mjs enc ventes.json ventes.enc.json
//         CARTE_MDP='...' node crypt.mjs dec ventes.enc.json ventes.json
import { readFileSync, writeFileSync } from 'node:fs';
const [mode, src, dst] = process.argv.slice(2);
const pw = process.env.CARTE_MDP;
if (!pw || !['enc','dec'].includes(mode) || !src || !dst) { console.error('usage: CARTE_MDP=... node crypt.mjs enc|dec in out'); process.exit(2); }
const { subtle } = globalThis.crypto;
const getRandomValues = a => globalThis.crypto.getRandomValues(a);
const b64 = u => Buffer.from(u).toString('base64');
const ub64 = s => new Uint8Array(Buffer.from(s, 'base64'));
async function key(salt, it, usage) {
  const km = await subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey']);
  return subtle.deriveKey({ name: 'PBKDF2', salt, iterations: it, hash: 'SHA-256' }, km, { name: 'AES-GCM', length: 256 }, false, [usage]);
}
if (mode === 'enc') {
  const data = readFileSync(src);
  JSON.parse(data); // vérifie que c'est du JSON valide
  const salt = getRandomValues(new Uint8Array(16)), iv = getRandomValues(new Uint8Array(12)), it = 600000;
  const ct = await subtle.encrypt({ name: 'AES-GCM', iv }, await key(salt, it, 'encrypt'), data);
  writeFileSync(dst, JSON.stringify({ v: 1, it, salt: b64(salt), iv: b64(iv), ct: b64(new Uint8Array(ct)) }));
  console.log('chiffré', data.length, 'octets ->', dst);
} else {
  const e = JSON.parse(readFileSync(src, 'utf8'));
  const pt = await subtle.decrypt({ name: 'AES-GCM', iv: ub64(e.iv) }, await key(ub64(e.salt), e.it, 'decrypt'), ub64(e.ct));
  writeFileSync(dst, Buffer.from(pt));
  console.log('déchiffré ->', dst);
}
