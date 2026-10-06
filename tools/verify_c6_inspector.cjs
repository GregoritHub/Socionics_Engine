/* Local static artifact QA; no remote page or authentication. */
const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const modules=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
const {chromium}=require(modules?path.join(modules,'playwright'):'playwright');
(async()=>{
 const input=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:1000},deviceScaleFactor:1});const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(pathToFileURL(input).href);await page.screenshot({path:path.join(out,'inspector-desktop.png'),fullPage:true});
 const total=await page.locator('.cell').count();if(total!==32)throw Error('wrong cell count');
 await page.locator('#filter').fill('Embody');const filtered=await page.locator('.cell:visible').count();if(filtered!==2)throw Error('filter failed');
 await page.locator('.cell:visible').first().locator('summary').first().click();await page.screenshot({path:path.join(out,'inspector-filtered.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.locator('#filter').fill('');
 await page.screenshot({path:path.join(out,'inspector-mobile.png'),fullPage:true});
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);if(overflow)throw Error('mobile body overflow');
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify({passed:true,total,filtered,mobile_body_overflow:overflow,page_errors:errors},null,2));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
