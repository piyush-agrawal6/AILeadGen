import puppeteer from 'puppeteer-core';
const [url,output,proxy]=process.argv.slice(2);
const restricted=u=>/\/(?:login|signin|sign-in|admin|account|checkout|dashboard)(?:\/|$)/i.test(new URL(u).pathname);
if(restricted(url))process.exit(2);
const browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage',`--proxy-server=${proxy}`,'--proxy-bypass-list=<-loopback>','--disable-quic','--force-webrtc-ip-handling-policy=disable_non_proxied_udp','--disable-background-networking','--disable-extensions']});
try {
 const context=await browser.createBrowserContext(),page=await context.newPage();
 await page.setViewport({width:1440,height:900,deviceScaleFactor:1});
 await page.setRequestInterception(true);let requests=0;
 page.on('request',req=>{let allowed=false;try{const u=new URL(req.url());allowed=['http:','https:'].includes(u.protocol)&&req.method()==='GET'&&!restricted(u.href)&&++requests<=80;}catch{}if(allowed)req.continue();else req.abort();});
 page.on('dialog',d=>d.dismiss());
 const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:12000});
 if(!response||response.status()>=400||restricted(page.url()))process.exitCode=2;
 else if(await page.$('input[type="password"]'))process.exitCode=2;
 else {await page.screenshot({path:output,type:'webp',quality:75,fullPage:false});}
} finally {await browser.close();}
