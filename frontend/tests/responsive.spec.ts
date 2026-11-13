import {test,expect} from '@playwright/test';
import path from 'node:path';
test('responsive views, navigation focus, reduced motion and empty state',async({page})=>{
 await page.goto('/');await expect(page.getByRole('heading',{name:/Career direction/})).toBeVisible();
 await expect(page.getByRole('status')).toHaveCount(0);
 for(const width of [1440,1024,768,390,320]){
  await page.setViewportSize({width,height:900});
  await page.goto('/#Overview');
  await expect(page.getByRole('heading',{name:/Career direction/})).toBeVisible();
  await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(350);
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  if(width===390){await expect(page.getByRole('button',{name:'Profile',exact:true})).not.toBeVisible();await page.getByRole('button',{name:'Toggle navigation'}).click();await expect(page.getByRole('button',{name:'Profile',exact:true})).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Profile',exact:true})).not.toBeVisible();await expect(page.getByRole('button',{name:'Toggle navigation'})).toBeFocused();await page.locator('h1').click();}
  await page.screenshot({path:path.resolve(`../.build/simplified-ui/overview-${width}.png`),fullPage:true});
 }
 await page.setViewportSize({width:1440,height:1000});await page.getByRole('button',{name:'Careers',exact:true}).click();await page.getByRole('textbox',{name:'Filter careers'}).fill('no-such-occupation');await expect(page.getByRole('heading',{name:/No careers match/})).toBeVisible();await page.getByRole('button',{name:'Clear filter'}).click();await expect(page.locator('.career')).toHaveCount(5);
 await page.emulateMedia({reducedMotion:'reduce'});await page.goto('/#Overview');await expect.poll(()=>page.locator('.hero-copy').evaluate(el=>getComputedStyle(el).animationName)).toBe('none');
});
test('every workspace view fits a phone',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 for(const name of ['Profile','Careers','Skill gaps','Knowledge graph','Learning roadmap']){
  await page.goto('/#'+encodeURIComponent(name));await expect(page.locator('h1')).toBeVisible();await expect(page.getByRole('status')).toHaveCount(0);await expect(page.getByRole('alert')).toHaveCount(0);
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 }
});
test('new profile protects saved skills, graph edges are accessible, latest selection wins',async({page,request})=>{
 const students=await (await request.get('http://127.0.0.1:8000/api/students')).json();const [a,b]=students.filter((s:any)=>s.demo);
 await page.goto('/#Profile');await expect(page.getByRole('status')).toHaveCount(0);await page.getByRole('button',{name:'New student'}).click();await expect(page.getByText('Save this new profile to add its skills.')).toBeVisible();await expect(page.getByRole('button',{name:'Add skill',exact:true})).toHaveCount(0);
 const saved=await (await request.get(`http://127.0.0.1:8000/api/students/${a.id}`)).json();expect(saved.skills).toEqual(a.skills);
 await page.goto('/#Knowledge%20graph');await expect(page.locator('.graph canvas').first()).toBeVisible();await page.getByText('Browse graph nodes and relationships with the keyboard',{exact:true}).click();const edge=page.locator('.graph-node-list button').filter({hasText:'→'}).first();await expect(edge).toBeVisible();await edge.focus();await page.keyboard.press('Enter');await expect(page.locator('dt').filter({hasText:/^source$/})).toBeVisible();
 await page.route(`**/api/students/${b.id}/recommendations`,async route=>{const response=await route.fetch();await new Promise(r=>setTimeout(r,500));await route.fulfill({response})});
 await page.getByRole('combobox',{name:'Select student'}).selectOption(String(b.id));await page.getByRole('combobox',{name:'Select student'}).selectOption(String(a.id));await expect(page.getByRole('status')).toHaveCount(0);await expect(page.getByRole('combobox',{name:'Select student'})).toHaveValue(String(a.id));
 await page.getByRole('button',{name:'Profile',exact:true}).click();await expect(page.getByRole('textbox',{name:'Name or anonymous identifier'})).toHaveValue(a.name);
 await page.getByRole('button',{name:'Profile',exact:true}).click();await page.route(`**/api/students/${a.id}`,async route=>{if(route.request().method()==='PUT'){const response=await route.fetch();await new Promise(r=>setTimeout(r,400));await route.fulfill({response})}else await route.continue()});
 await page.getByRole('textbox',{name:'Projects and experience'}).fill('Delayed save selection test');await page.getByRole('button',{name:'Save profile',exact:true}).click();await page.getByRole('combobox',{name:'Select student'}).selectOption(String(b.id));await expect(page.getByRole('status')).toHaveCount(0);await expect(page.getByRole('combobox',{name:'Select student'})).toHaveValue(String(b.id));
});
