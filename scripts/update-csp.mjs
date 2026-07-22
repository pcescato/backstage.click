import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

const ENV_FILE_PATH = path.join(process.cwd(), '.env.deploy');
const DIST_DIR = path.join(process.cwd(), 'dist');
const REQUIRED_ENV_VARS = ['CF_ZONE_ID', 'CF_RULESET_ID', 'CF_RULE_ID', 'CF_API_TOKEN'];

function loadEnvFile(filePath) {
  let envFile;

  try {
    envFile = readFileSync(filePath, 'utf8');
  } catch (error) {
    if (error && typeof error === 'object' && 'code' in error && error.code === 'ENOENT') {
      return;
    }

    throw error;
  }

  envFile.split('\n').forEach((line) => {
    const match = line.match(/^([^#=]+)=(.*)$/);

    if (!match) {
      return;
    }

    const key = match[1].trim();
    const value = match[2].trim();

    if (!key) {
      return;
    }

    process.env[key] = (process.env[key] ?? value).replace(/\r/g, '');
  });
}

loadEnvFile(ENV_FILE_PATH);

function getRequiredEnv(name) {
  const value = process.env[name];

  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value;
}

async function getHtmlFiles(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const nestedFiles = await Promise.all(
    entries.map(async (entry) => {
      const fullPath = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        return getHtmlFiles(fullPath);
      }

      return path.extname(entry.name) === '.html' ? [fullPath] : [];
    }),
  );

  return nestedFiles.flat();
}

function isJsMimeType(mime) {
  if (!mime) return true;
  const jsMimes = [
    'text/javascript',
    'application/javascript',
    'application/ecmascript',
    'text/ecmascript',
    'module',
  ];
  return jsMimes.includes(mime.trim().toLowerCase());
}

function extractInlineScripts(html) {
  const scripts = [];
  const scriptTagPattern = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;

  for (const match of html.matchAll(scriptTagPattern)) {
    const attributes = match[1] ?? '';
    const content = match[2] ?? '';

    if (/\bsrc\s*=/.test(attributes)) {
      continue;
    }

    const typeMatch = attributes.match(/\btype\s*=\s*["']([^"']+)["']/);
    const type = typeMatch ? typeMatch[1] : null;

    if (!isJsMimeType(type)) {
      continue;
    }

    if (!content.trim()) {
      continue;
    }

    scripts.push(content);
  }

  return scripts;
}

function toCspHash(scriptContent) {
  const digest = createHash('sha256').update(scriptContent).digest('base64');
  return `'sha256-${digest}'`;
}

const CLOUDFLARE_HEADER_VALUE_LIMIT = 4000;

function buildCspHeader(hashes) {
  const hashSegment = hashes.length > 0 ? ` ${hashes.join(' ')}` : '';

  const directives = [
    "default-src 'self'",
    `script-src 'self'${hashSegment} https://assets.calendly.com`,
    'frame-src https://assets.calendly.com https://calendly.com',
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self' data: https://fonts.googleapis.com https://fonts.gstatic.com",
    "img-src 'self' data: https:",
    "connect-src 'self'",
    "base-uri 'self'",
    "form-action 'self'",
  ];

  const csp = directives.join('; ');

  if (csp.length > CLOUDFLARE_HEADER_VALUE_LIMIT) {
    throw new Error(
      `CSP header (${csp.length} chars) exceeds Cloudflare ${CLOUDFLARE_HEADER_VALUE_LIMIT} char limit. ` +
      'Reduce inline scripts or move them to external files.',
    );
  }

  return csp;
}

async function fetchRule(endpoint, apiToken, ruleId) {
  const response = await fetch(endpoint, {
    headers: {
      Authorization: `Bearer ${apiToken}`,
      'Content-Type': 'application/json',
    },
  });

  const data = await response.json();

  if (!response.ok || !data.success || !data.result) {
    const errorText = data?.errors?.map((error) => error.message).join('; ') || response.statusText;
    throw new Error(`Failed to fetch Cloudflare rule: ${errorText}`);
  }

  const currentRule = data.result.rules?.find((rule) => rule.id === ruleId);

  if (!currentRule) {
    throw new Error(`Failed to fetch Cloudflare rule: Rule ${ruleId} not found in ruleset.`);
  }

  return currentRule;
}

async function updateRule(endpoint, apiToken, payload) {
  const response = await fetch(endpoint, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${apiToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok || !data.success) {
    const errorText = data?.errors?.map((error) => error.message).join('; ') || response.statusText;
    throw new Error(`Failed to update Cloudflare rule: ${errorText}`);
  }
}

async function main() {
  for (const envVar of REQUIRED_ENV_VARS) {
    getRequiredEnv(envVar);
  }

  const zoneId = getRequiredEnv('CF_ZONE_ID');
  const rulesetId = getRequiredEnv('CF_RULESET_ID');
  const ruleId = getRequiredEnv('CF_RULE_ID');
  const apiToken = getRequiredEnv('CF_API_TOKEN');

  const htmlFiles = await getHtmlFiles(DIST_DIR);

  if (htmlFiles.length === 0) {
    throw new Error(`No HTML files found in ${DIST_DIR}. Run the build before updating CSP.`);
  }

  const scriptContents = (
    await Promise.all(
      htmlFiles.map(async (filePath) => {
        const html = await readFile(filePath, 'utf8');
        return extractInlineScripts(html);
      }),
    )
  ).flat();

  const hashes = [...new Set(scriptContents.map(toCspHash))].sort();
  const cspHeader = buildCspHeader(hashes);
  const rulesetEndpoint = `https://api.cloudflare.com/client/v4/zones/${zoneId}/rulesets/${rulesetId}`;
  const ruleEndpoint = `${rulesetEndpoint}/rules/${ruleId}`;
  const currentRule = await fetchRule(rulesetEndpoint, apiToken, ruleId);
  const existingHeaders =
    currentRule.action_parameters?.headers &&
    typeof currentRule.action_parameters.headers === 'object' &&
    !Array.isArray(currentRule.action_parameters.headers)
      ? currentRule.action_parameters.headers
      : {};
  const updatedHeaders = {
    ...existingHeaders,
    'Content-Security-Policy': {
      operation: 'set',
      value: cspHeader,
    },
  };

  const payload = {
    action: currentRule.action,
    expression: currentRule.expression,
    description: currentRule.description,
    enabled: currentRule.enabled,
    ...(currentRule.ref ? { ref: currentRule.ref } : {}),
    action_parameters: {
      ...currentRule.action_parameters,
      headers: updatedHeaders,
    },
  };

  await updateRule(ruleEndpoint, apiToken, payload);

  console.log(
    `Updated Cloudflare CSP rule with ${hashes.length} hash${hashes.length === 1 ? '' : 'es'}.`,
  );
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
