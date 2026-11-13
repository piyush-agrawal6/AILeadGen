/** Inert selection only. The backend independently owns pricing and billing. */
export const planCodes=['starter','growth','scale','enterprise'] as const;
export type PlanCode=typeof planCodes[number];
export function approvedPlan(value:unknown):PlanCode|null{return typeof value==='string'&&(planCodes as readonly string[]).includes(value)?value as PlanCode:null;}
export function planDestination(product:unknown,plan:unknown):string|null{const code=approvedPlan(plan);return product==='intent-radar'&&code?'/billing?plan='+code:null;}
