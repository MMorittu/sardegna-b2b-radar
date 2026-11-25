"use client";

import { useEffect } from "react";

export function ReactGrabDev() {
  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      void import("react-grab").then((rg) => {
        if (typeof rg.init === "function") {
          rg.init();
        }
      });
    }
  }, []);

  return null;
}

