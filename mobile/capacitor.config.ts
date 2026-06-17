import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.campus.lostfound",
  appName: "Digital Lost and Found",
  webDir: "dist",
  server: {
    androidScheme: "http",
    cleartext: true
  },
  plugins: {
    CapacitorHttp: {
      enabled: false
    }
  }
};

export default config;
