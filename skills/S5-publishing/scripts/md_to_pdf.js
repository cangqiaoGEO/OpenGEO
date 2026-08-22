const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

function loadDependencies() {
  try {
    return {
      MarkdownIt: require('markdown-it'),
      puppeteer: require('puppeteer'),
    };
  } catch (error) {
    console.error('Missing dependency. Install markdown-it and puppeteer in this workspace.');
    console.error(error.message);
    process.exit(2);
  }
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function findChrome() {
  const configured = process.env.CHROME_PATH || process.env.PUPPETEER_EXECUTABLE_PATH;
  const candidates = [
    configured,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate));
}

function printUsage() {
  console.log('Usage: node md_to_pdf.js <input.md> [output.pdf] [custom-style.css]');
  process.exit(1);
}

const args = process.argv.slice(2);
if (args.length < 1) {
  printUsage();
}

const mdPath = path.resolve(args[0]);
if (!fs.existsSync(mdPath)) {
  console.error('Error: Markdown file not found:', mdPath);
  process.exit(1);
}
if (path.extname(mdPath).toLowerCase() !== '.md') {
  console.error('Error: Input must be a .md file:', mdPath);
  process.exit(1);
}

const defaultPdfPath = mdPath.replace(/\.md$/i, '.pdf');
const pdfPath = args[1] ? path.resolve(args[1]) : defaultPdfPath;
const customCssPath = args[2] ? path.resolve(args[2]) : null;
if (pdfPath === mdPath) {
  console.error('Error: Output PDF must not overwrite the Markdown input.');
  process.exit(1);
}

if (!fs.existsSync(path.dirname(pdfPath))) {
  console.error('Error: Output directory does not exist:', path.dirname(pdfPath));
  process.exit(1);
}

const { MarkdownIt, puppeteer } = loadDependencies();

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  typographer: false,
});

const mdContent = fs.readFileSync(mdPath, 'utf-8');
const htmlBody = md.render(mdContent);
const documentTitle = escapeHtml(path.basename(mdPath, path.extname(mdPath)));

const defaultCss = `
@page {
  size: A4;
  margin: 20mm 18mm 25mm 18mm;
}

body {
  font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', sans-serif;
  font-size: 11pt;
  line-height: 1.8;
  color: #222;
}

h1 {
  font-size: 24pt;
  color: #1a1a2e;
  text-align: center;
  margin-top: 4cm;
  margin-bottom: 0.5cm;
  font-weight: 700;
}

h2 {
  font-size: 16pt;
  color: #1a1a2e;
  border-bottom: 2px solid #e94560;
  padding-bottom: 8px;
  margin-top: 1.2cm;
  margin-bottom: 0.5cm;
  page-break-after: avoid;
}

h3 {
  font-size: 13pt;
  color: #16213e;
  margin-top: 0.8cm;
  margin-bottom: 0.3cm;
  page-break-after: avoid;
}

h4 {
  font-size: 11.5pt;
  color: #333;
  margin-top: 0.6cm;
  margin-bottom: 0.2cm;
  page-break-after: avoid;
}

p {
  margin: 0.3cm 0;
  text-align: justify;
}

blockquote {
  border-left: 4px solid #e94560;
  margin: 0.5cm 0;
  padding: 0.3cm 0.6cm;
  background: #f8f9fa;
  color: #555;
  font-style: italic;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5cm 0;
  font-size: 10pt;
  page-break-inside: avoid;
}

th {
  background: #1a1a2e;
  color: white;
  padding: 8px 10px;
  text-align: left;
  font-weight: 600;
  border: 1px solid #1a1a2e;
}

td {
  padding: 7px 10px;
  border: 1px solid #ddd;
  vertical-align: top;
}

tr:nth-child(even) {
  background: #f8f9fa;
}

ul, ol {
  margin: 0.3cm 0;
  padding-left: 1cm;
}

li {
  margin: 0.1cm 0;
}

strong {
  color: #1a1a2e;
  font-weight: 700;
}

hr {
  border: none;
  border-top: 1px solid #ddd;
  margin: 0.8cm 0;
}

code {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  background: #f4f4f4;
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 10pt;
}

pre {
  background: #f4f4f4;
  padding: 10px;
  border-radius: 5px;
  overflow-x: auto;
  font-size: 10pt;
}
`;

let cssContent = defaultCss;
if (customCssPath) {
  if (!fs.existsSync(customCssPath)) {
    console.error('Error: Custom CSS file not found:', customCssPath);
    process.exit(1);
  }
  cssContent = fs.readFileSync(customCssPath, 'utf-8');
}

const fullHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>${documentTitle}</title>
    <style>
        ${cssContent}
    </style>
</head>
<body class="markdown-body">
    ${htmlBody}
</body>
</html>`;

const htmlPath = path.join(
  path.dirname(mdPath),
  `.opengeo-md-to-pdf-${process.pid}-${Date.now()}.html`,
);
fs.writeFileSync(htmlPath, fullHtml, { encoding: 'utf-8', flag: 'wx' });

(async () => {
  let browser;
  try {
    const executablePath = findChrome();
    const launchOptions = {
      headless: 'new',
    };
    if (executablePath) launchOptions.executablePath = executablePath;
    if (process.env.PUPPETEER_NO_SANDBOX === '1') {
      launchOptions.args = ['--no-sandbox', '--disable-setuid-sandbox'];
    }
    browser = await puppeteer.launch(launchOptions);

    const page = await browser.newPage();
    await page.setJavaScriptEnabled(false);
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'networkidle0' });

    await page.pdf({
      path: pdfPath,
      format: 'A4',
      printBackground: true,
      margin: {
        top: '20mm',
        right: '18mm',
        bottom: '25mm',
        left: '18mm',
      },
      displayHeaderFooter: true,
      headerTemplate: `<div style="font-size:9px; color:#999; width:100%; text-align:center; padding-top:10px; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;">${documentTitle}</div>`,
      footerTemplate: `<div style="font-size:9px; color:#999; width:100%; text-align:center; padding-bottom:10px; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>`,
    });

    console.log('PDF generated:', pdfPath);
  } catch (err) {
    console.error('Error generating PDF:', err.message);
    process.exit(1);
  } finally {
    if (browser) await browser.close();
    try {
      fs.unlinkSync(htmlPath);
    } catch (cleanupError) {
      console.error('Warning: Could not remove temporary HTML:', cleanupError.message);
    }
  }
})();
