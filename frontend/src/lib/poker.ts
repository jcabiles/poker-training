export const RANK_ORDER = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];

const IDX: Record<string, number> = Object.fromEntries(
  "23456789TJQKA".split("").map((r, i) => [r, i]),
);

/** ('Ah','Ks') -> 'AKo'; ('Ah','Kh') -> 'AKs'; ('7c','7d') -> '77'. */
export function handClass(c1: string, c2: string): string {
  let r1 = c1[0];
  let s1 = c1[1];
  let r2 = c2[0];
  let s2 = c2[1];
  if (r1 === r2) return r1 + r2;
  if (IDX[r1] < IDX[r2]) {
    [r1, r2, s1, s2] = [r2, r1, s2, s1];
  }
  return r1 + r2 + (s1 === s2 ? "s" : "o");
}
