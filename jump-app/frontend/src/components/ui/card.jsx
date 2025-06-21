import React from "react";

export function Card({ children }) {
  return <div className="bg-white shadow-md rounded-xl p-4">{children}</div>;
}

export function CardContent({ children }) {
  return <div className="mt-2">{children}</div>;
}
