const assert = require('node:assert/strict');
(async () => {
  const {readJourney, awardFuel, loadFuel, launch, land, FLIGHT_SECONDS} = await import('../web/ship-journey.js');
  for (const tier of ['normal', 'super']) {
    const game = readJourney();
    assert.equal(launch(game), false);
    assert.equal(loadFuel(game, tier), false);
    awardFuel(game, tier);
    assert.equal(loadFuel(game, tier), true);
    assert.equal(loadFuel(game, tier), false, 'double loading cannot spend fuel');
    assert.equal(game[tier], 0);
    assert.equal(launch(game), true);
    assert.equal(launch(game), false, 'double launch cannot start a second flight');
    const restored = readJourney(JSON.parse(JSON.stringify(game)));
    assert.equal(restored.flight, tier, 'interrupted flight survives reload');
    assert.equal(land(restored), true);
    assert.equal(land(restored), false, 'landing cannot be awarded twice');
    assert.equal(restored.progress, tier === 'normal' ? 1 : 2);
    awardFuel(restored, 'normal'); loadFuel(restored, 'normal'); launch(restored); land(restored);
    assert.equal(restored.progress, tier === 'normal' ? 1 : 2, 'regular replay cannot erase rainbow progress');
  }
  assert.deepEqual(FLIGHT_SECONDS, {normal: 3, super: 4});
  assert.deepEqual(readJourney({normal: -1, super: Infinity, loaded: 'bogus', progress: 999}), readJourney());
  assert.deepEqual(readJourney(null), readJourney());
  console.log('Ship journey: fuel accounting, guarded launch, recovery, both destinations and replay passed');
})().catch(error => {console.error(error); process.exitCode = 1;});
