declare module "jalaali-js" {
  interface JalaaliResult {
    jy: number;
    jm: number;
    jd: number;
  }
  const jalaali: {
    toJalaali(gy: number, gm: number, gd: number): JalaaliResult;
    toGregorian(jy: number, jm: number, jd: number): { gy: number; gm: number; gd: number };
    jalaaliMonthLength(jy: number, jm: number): number;
    isValidJalaaliDate(jy: number, jm: number, jd: number): boolean;
  };
  export default jalaali;
}
