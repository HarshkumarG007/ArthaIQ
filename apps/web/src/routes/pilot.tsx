import React from "react";
import { PilotDashboard } from "../components/career/PilotDashboard";

interface PilotRouteProps {
  onNavigateToCareer?: () => void;
  onNavigateToCompensation?: () => void;
}

export function PilotRoute({
  onNavigateToCareer,
  onNavigateToCompensation,
}: PilotRouteProps): React.JSX.Element {
  return (
    <div className="space-y-6">
      <PilotDashboard
        onNavigateToCareer={onNavigateToCareer}
        onNavigateToCompensation={onNavigateToCompensation}
      />
    </div>
  );
}

export default PilotRoute;
