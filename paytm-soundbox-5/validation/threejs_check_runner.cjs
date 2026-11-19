const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  p.on('console', m => { if (m.type() === 'error') console.log('console error:', m.text()); });
  for (const f of ['paytm-soundbox-5-ar.glb', 'paytm-soundbox-5-hero.glb']) {
    for (const [az, el] of [[35, 15], [150, 25], [-90, 5]]) {
      await p.goto(`http://localhost:8765/index.html?f=${f}&az=${az}&el=${el}`);
      await p.waitForFunction(() => window.RESULT, null, { timeout: 60000 });
      const res = await p.evaluate(() => window.RESULT);
      if (az === 35) console.log(f, JSON.stringify(res));
      await p.screenshot({ path: `${f.replace('.glb','')}_${az}.png` });
    }
  }
  await b.close();
})();
