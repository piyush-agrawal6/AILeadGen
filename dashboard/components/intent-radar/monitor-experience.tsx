"use client";
import {RadarExport} from './RadarExport';

import {
  MonitorsDashboard,
  MonitorBuilderPage,
  MonitorDetailPage,
} from "./monitors/index";

export {
  MonitorsDashboard,
  MonitorBuilderPage,
  MonitorDetailPage,
};

export function MonitorsExperience({ route }: { route: string }) {
  if (route === "monitors/new") {
    return <MonitorBuilderPage />;
  }
  if (route.startsWith("monitors/") && route !== "monitors/new") {
    const id = route.split("/")[1];
    return <><MonitorDetailPage id={id} /><RadarExport selection={{dataset:'monitor',parent:id}}/></>;
  }
  return <MonitorsDashboard />;
}
