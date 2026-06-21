import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC = join(__dirname, '..', 'assets', 'icon.svg');
const OUT = join(__dirname, '..', 'public', 'icons');

const SIZES = [
  { name: 'icon-192.png', size: 192 },
  { name: 'icon-256.png', size: 256 },
  { name: 'icon-384.png', size: 384 },
  { name: 'icon-512.png', size: 512 },
  { name: 'apple-touch-icon.png', size: 180 },
  { name: 'favicon-32.png', size: 32 },
];

async function main() {
  const svg = await readFile(SRC);
  await mkdir(OUT, { recursive: true });
  for (const { name, size } of SIZES) {
    const png = await sharp(svg).resize(size, size).png().toBuffer();
    await writeFile(join(OUT, name), png);
    console.log(`  ✓ ${name} (${size}×${size})`);
  }
  console.log(`Icons generated in ${OUT}`);
}

main().catch((err) => {
  console.error('Icon generation failed:', err);
  process.exit(1);
});
