// Local game progression only. Distances and wormholes are story mechanics.
export const FLIGHT_SECONDS = {normal: 3, super: 4};
export function readJourney(value = {}) {
  const count = n => Number.isInteger(n) && n >= 0 && n <= 999 ? n : 0;
  const tier = n => ['normal', 'super'].includes(n) ? n : 'none';
  return {
    normal: count(value?.normal), super: count(value?.super), loaded: tier(value?.loaded),
    flight: tier(value?.flight), progress: [0, 1, 2].includes(value?.progress) ? value.progress : 0,
    encounterSeen: value?.encounterSeen === true,
  };
}
export function awardFuel(journey, tier) {
  if (Object.hasOwn(FLIGHT_SECONDS, tier)) journey[tier] = Math.min(999, journey[tier] + 1);
}
export function loadFuel(journey, tier) {
  if (!(Object.hasOwn(FLIGHT_SECONDS, tier)) || journey[tier] < 1 || journey.loaded !== 'none' || journey.flight !== 'none') return false;
  journey[tier]--; journey.loaded = tier; return true;
}
export function launch(journey) {
  if (!(Object.hasOwn(FLIGHT_SECONDS, journey.loaded)) || journey.flight !== 'none') return false;
  journey.flight = journey.loaded; journey.loaded = 'none'; return true;
}
export function land(journey) {
  if (!(Object.hasOwn(FLIGHT_SECONDS, journey.flight))) return false;
  journey.progress = Math.max(journey.progress, journey.flight === 'super' ? 2 : 1);
  journey.flight = 'none'; return true;
}
