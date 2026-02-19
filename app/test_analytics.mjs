import { chromium } from 'playwright';

console.log('🚀 Starting browser test...');

const browser = await chromium.launch({ 
  headless: false,
  slowMo: 500 
});

const page = await browser.newPage();

// Monitor console
page.on('console', msg => {
  if (msg.type() === 'error') {
    console.log('❌ Browser console error:', msg.text());
  }
});

// Monitor network
page.on('response', response => {
  if (response.url().includes('analytics')) {
    console.log('📡 Analytics request:', response.url(), '-', response.status());
  }
});

console.log('📍 Navigating to http://localhost:4321/dashboard/map/');
await page.goto('http://localhost:4321/dashboard/map/', { waitUntil: 'networkidle' });

console.log('⏳ Waiting for React hydration...');
await page.waitForTimeout(3000);

// Take screenshot
await page.screenshot({ path: 'test_screenshots/01_initial.png', fullPage: true });
console.log('📸 Screenshot: test_screenshots/01_initial.png');

// Check for Analytics Layers text
const content = await page.textContent('body');
const hasAnalyticsLayers = content.includes('Analytics Layers');
console.log('🔍 "Analytics Layers" text found:', hasAnalyticsLayers ? '✅' : '❌');

// Look for checkboxes
const checkboxes = await page.$$('input[type="checkbox"]');
console.log(`📦 Checkboxes found: ${checkboxes.length}`);

if (checkboxes.length > 0) {
  console.log('🖱️  Clicking first analytics checkbox...');
  await checkboxes[0].click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'test_screenshots/02_layer_toggled.png' });
  console.log('📸 Screenshot: test_screenshots/02_layer_toggled.png');
}

// Check URL
const url = page.url();
console.log('🔗 URL:', url);
console.log('🔗 Has layers parameter:', url.includes('layers=') ? '✅' : '❌');

// Final screenshot
await page.screenshot({ path: 'test_screenshots/03_final.png', fullPage: true });
console.log('📸 Screenshot: test_screenshots/03_final.png');

console.log('✅ Test complete! Keeping browser open for 5 seconds...');
await page.waitForTimeout(5000);

await browser.close();
console.log('🎉 All done!');
