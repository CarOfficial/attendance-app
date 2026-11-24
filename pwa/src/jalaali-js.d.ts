declare module "jalaali-js" {
  interface JalaaliResult {
    jy: number;
    jm: number;
    jd: number;
  }
  const jalaali: {
    toJalaali(gy: number, gm: number, gd: number): JalaaliResult;
    toGregorian(jy: number, jm: number, jd: number): { gy: number; gm: number; gd: number };
  };
  export default jalaali;
}
