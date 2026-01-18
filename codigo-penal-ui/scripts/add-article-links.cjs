#!/usr/bin/env node
/**
 * Script para agregar enlaces automáticos a referencias de artículos del Código Penal
 *
 * Patrones a enlazar:
 * - "artículo X" o "artículos X, Y, Z"
 * - "artículo X-A" (con sufijo de letra)
 *
 * Patrones a EXCLUIR:
 * - label="Artículo X.-" (es el label del propio artículo)
 * - "artículo X de la Ley N°..." (referencia a ley externa)
 * - "artículo X del Decreto..." (referencia a decreto externo)
 * - "artículo X de la Constitución..." (referencia a constitución)
 * - Referencias ya enlazadas (<a href=...)
 */

const fs = require('fs');
const path = require('path');

// Directorio de artículos
const articulosDir = path.join(__dirname, '../src/components/articulos');

// Cargar todos los IDs de artículos existentes
function getExistingArticleIds() {
  const files = fs.readdirSync(articulosDir).filter(f => f.endsWith('.astro'));
  const ids = new Set();

  for (const file of files) {
    const content = fs.readFileSync(path.join(articulosDir, file), 'utf-8');
    const match = content.match(/id="(articulo-[^"]+)"/);
    if (match) {
      ids.add(match[1]);
    }
  }
  return ids;
}

// Convertir número de artículo a ID
function articleNumToId(num) {
  // Normalizar: "108-B" -> "articulo-108-B", "36" -> "articulo-36"
  const normalized = num.trim().replace(/\s+/g, '-');
  return `articulo-${normalized}`;
}

// Verificar si una referencia debe ser excluida
function shouldExclude(textBefore, textAfter, fullMatch) {
  // Excluir si es un label o heading
  if (textBefore.includes('label="') || textBefore.includes('heading="')) return true;

  // Excluir si ya está enlazado
  if (textBefore.includes('<a href=') || textBefore.includes('href="#articulo')) return true;
  if (textBefore.match(/<a[^>]*>$/)) return true;

  // Excluir referencias a leyes/decretos/códigos externos
  const externalPatterns = [
    /^[\s,)]*de la Ley/i,
    /^[\s,)]*del Decreto/i,
    /^[\s,)]*de la Constitución/i,
    /^[\s,)]*de la Convención/i,
    /^[\s,)]*del Código Procesal/i,
    /^[\s,)]*del Nuevo Código Procesal/i,
    /^[\s,)]*del Código Civil/i,
    /^[\s,)]*del Código de los Niños/i,
    /^[\s,)]*del Código Tributario/i,
    /^[\s,)]*de la Ley Orgánica/i,
    /^[\s,)]*del Reglamento/i,
    /^[\s,)]*del Estatuto/i,
    /^[\s,)]*del Tratado/i,
  ];

  for (const pattern of externalPatterns) {
    if (pattern.test(textAfter)) return true;
  }

  // Excluir notas de modificación: (*) Artículo modificado por el artículo X de...
  if (textBefore.includes('(*) Artículo') || textBefore.includes('(*) Numeral') || textBefore.includes('(*) Inciso') || textBefore.includes('(*) Párrafo') || textBefore.includes('(*) Literal')) {
    if (/^[\s\d,-A-Za-z]*de la |^[\s\d,-A-Za-z]*del /i.test(textAfter)) return true;
  }

  // Excluir si está después de "modificado por el", "incorporado por el"
  if (textBefore.match(/(?:modificado|incorporado|derogado)\s+por\s+(?:el\s+)?$/i)) {
    return true;
  }

  // Excluir si el texto después contiene referencia a código externo en contexto cercano
  // Ej: "artículo 288 o del artículo 290 del Nuevo Código Procesal Penal"
  if (textAfter.match(/^[^.]*del Nuevo Código Procesal/i)) {
    return true;
  }
  if (textAfter.match(/^[^.]*del Código Procesal Penal/i)) {
    return true;
  }

  return false;
}

// Procesar un archivo
function processFile(filePath, existingIds, dryRun = true) {
  let content = fs.readFileSync(filePath, 'utf-8');
  const fileName = path.basename(filePath);
  let changes = [];

  // Patrón para encontrar referencias a artículos
  // Matches: "artículo 36", "artículos 107, 108", "artículo 108-B", etc.
  const pattern = /\b(artículos?)\s+([\d]+(?:-[A-Za-zÑñ])?(?:\s*(?:,|y|º)\s*[\d]+(?:-[A-Za-zÑñ])?)*)/gi;

  let match;
  const replacements = [];

  while ((match = pattern.exec(content)) !== null) {
    const fullMatch = match[0];
    const prefix = match[1]; // "artículo" o "artículos"
    const numbers = match[2]; // "36" o "107, 108, 108-A"

    const startIdx = match.index;
    const endIdx = startIdx + fullMatch.length;

    // Contexto antes y después
    const textBefore = content.substring(Math.max(0, startIdx - 100), startIdx);
    const textAfter = content.substring(endIdx, Math.min(content.length, endIdx + 50));

    if (shouldExclude(textBefore, textAfter, fullMatch)) {
      continue;
    }

    // Parsear los números de artículos
    const articleNums = numbers.split(/\s*(?:,|y|º)\s*/).map(n => n.trim()).filter(n => n);

    // Construir el reemplazo con enlaces
    let replacement = prefix + ' ';
    const linkedParts = [];

    for (let i = 0; i < articleNums.length; i++) {
      const num = articleNums[i];
      const id = articleNumToId(num);

      // Verificar si el artículo existe
      if (existingIds.has(id) || existingIds.has(id.toLowerCase())) {
        // Buscar el ID correcto (puede tener diferente case)
        let correctId = id;
        for (const existingId of existingIds) {
          if (existingId.toLowerCase() === id.toLowerCase()) {
            correctId = existingId;
            break;
          }
        }
        linkedParts.push(`<a href="#${correctId}">${num}</a>`);
      } else {
        // Artículo no existe, dejarlo sin enlace
        linkedParts.push(num);
      }
    }

    // Reconstruir con separadores originales
    let rebuilt = prefix + ' ';
    const separators = numbers.match(/\s*(?:,|y|º)\s*/g) || [];
    for (let i = 0; i < linkedParts.length; i++) {
      rebuilt += linkedParts[i];
      if (i < separators.length) {
        rebuilt += separators[i];
      }
    }

    if (rebuilt !== fullMatch) {
      replacements.push({
        start: startIdx,
        end: endIdx,
        original: fullMatch,
        replacement: rebuilt,
        context: textBefore.slice(-30) + '[HERE]' + textAfter.slice(0, 30)
      });
    }
  }

  // Aplicar reemplazos de atrás hacia adelante para no afectar los índices
  if (!dryRun && replacements.length > 0) {
    replacements.reverse();
    for (const r of replacements) {
      content = content.substring(0, r.start) + r.replacement + content.substring(r.end);
    }
    fs.writeFileSync(filePath, content);
  }

  return replacements;
}

// Main
const existingIds = getExistingArticleIds();
console.log(`Found ${existingIds.size} existing article IDs\n`);

const files = fs.readdirSync(articulosDir)
  .filter(f => f.endsWith('.astro'))
  .sort();

const dryRun = process.argv.includes('--dry-run') || !process.argv.includes('--apply');
console.log(dryRun ? '=== DRY RUN (use --apply to make changes) ===' : '=== APPLYING CHANGES ===');
console.log('');

let totalChanges = 0;
for (const file of files) {
  const filePath = path.join(articulosDir, file);
  const changes = processFile(filePath, existingIds, dryRun);

  if (changes.length > 0) {
    console.log(`\n${file}: ${changes.length} changes`);
    for (const c of changes) {
      console.log(`  "${c.original}" -> "${c.replacement}"`);
      console.log(`    Context: ...${c.context}...`);
    }
    totalChanges += changes.length;
  }
}

console.log(`\n=== Total: ${totalChanges} changes ===`);
