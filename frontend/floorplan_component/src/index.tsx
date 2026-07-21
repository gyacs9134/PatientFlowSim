import React from "react";
import ReactDOM from "react-dom/client";
import { Streamlit, withStreamlitConnection, type ComponentProps } from "streamlit-component-lib";
import { FloorPlan } from "./FloorPlan";
import type { ComponentArgs } from "./types";
import "./styles.css";

function App({ args }: ComponentProps) {
  return <FloorPlan {...(args as unknown as ComponentArgs)} />;
}

const ConnectedApp = withStreamlitConnection(App);
ReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><ConnectedApp /></React.StrictMode>);
Streamlit.setComponentReady();
