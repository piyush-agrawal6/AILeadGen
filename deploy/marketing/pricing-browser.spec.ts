import {test,expect} from '@playwright/test';
for(const width of [1440,1280,1024,768,390,320])test(`approved pricing remains usable at ${width}px`,async({page},info)=>{
 await page.setViewportSize({width,height:900});await page.goto('/pricing');
 await expect(page.locator('.family-pricing')).toHaveAttribute('data-catalog-version','2026-11-14.2');
 await expect(page.getByRole('row',{name:/Monthly searches/})).toContainText('100');
 await expect(page.getByRole('row',{name:/Shared reserved AI token capacity/})).toContainText('1,800,000');
 await expect(page.getByRole('row',{name:/Monthly monitoring checks/})).toContainText('60');
 await expect(page.getByRole('row',{name:/Monthly reports/})).toContainText('30');
 await expect(page.getByRole('row',{name:/Monitoring frequency/})).toContainText('Daily');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await expect(page.locator('.family-pricing')).not.toContainText('awaiting approval');
 await page.screenshot({path:info.outputPath('pricing-'+width+'.png'),fullPage:true});
});
