// Generated catalog is synchronized from planebyte-leadgen; no local price list.
import catalog from './intent-radar-catalog.json' with {type:'json'};
export const pricing=catalog;
export type Plan=typeof pricing.plans[number];
export type Tier=Plan['code'];
