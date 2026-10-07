async page => {
  const baseUrl = new URL(page.url()).origin;
  const artifactDirectory = 'output/viz-server-tests';
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const original = await (await page.request.get(baseUrl + '/api/state')).json();
  await page.locator('.export-menu > summary').click();
  const downloads = [];
  for (const [scope, title] of [['schema', 'T-box 스키마 Cypher'], ['data', 'A-box 데이터 Cypher'], ['model', '전체 모델 Cypher']]) {
    const downloadEvent = page.waitForEvent('download');
    const responseEvent = page.waitForResponse(response => response.url().includes('/api/export/cypher?scope=' + scope));
    await page.getByRole('button', {name: title, exact: true}).click();
    const downloaded = await downloadEvent;
    const response = await responseEvent;
    const payload = await response.json();
    await downloaded.saveAs(artifactDirectory + '/cypher-downloads/' + downloaded.suggestedFilename());
    if (await downloaded.failure() || !response.ok() || payload.scope !== scope || payload.revision !== original.revision) throw new Error('Invalid download: ' + scope);
    downloads.push({scope, filename: downloaded.suggestedFilename(), statements: payload.statement_count});
  }
  await page.getByRole('checkbox', {name: '가맹점', exact: true}).uncheck();
  const responseEvent = page.waitForResponse(response => response.url().includes('/api/export/cypher?scope=schema'));
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', {name: 'T-box 스키마 Cypher', exact: true}).click();
  await downloadEvent;
  const filtered = await (await responseEvent).json();
  if (!filtered.content.includes('CREATE NODE TABLE `Merchant`')) throw new Error('Visible filter removed schema from export');
  await page.getByRole('checkbox', {name: '가맹점', exact: true}).check();
  const current = await (await page.request.get(baseUrl + '/api/state')).json();
  if (current.document_revision !== original.document_revision) throw new Error('Export changed published model');
  if (errors.length) throw new Error(errors.join('\n'));
  await page.screenshot({path: artifactDirectory + '/cypher-export-menu.png', fullPage: true});
  return {downloads, ignoresViewFilters: true, modelUnchanged: true, javascriptErrors: errors};
}
