import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('landing, authentication and project workspace meet automated WCAG checks',async({page})=>{
 const scan=async()=>{const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();expect(result.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))).toEqual([])};
 await page.goto('/');await scan();await page.getByRole('button',{name:'Start an investigation'}).click();await scan();
 await page.getByLabel('Name',{exact:true}).fill('Accessibility Engineer');await page.getByLabel('Email',{exact:true}).fill(`a11y-${Date.now()}@example.test`);await page.getByLabel('Password',{exact:true}).fill('accessibility-test-passphrase');await page.getByRole('button',{name:'Create account',exact:true}).click();await expect(page.getByRole('heading',{name:'Your projects'})).toBeVisible();await scan();
 await page.setViewportSize({width:390,height:844});await scan();
});
