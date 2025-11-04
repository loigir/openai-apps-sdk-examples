import { memo, useMemo } from "react";
import { sanitizeText } from "../utils/sanitize";
import "./emergency-alert.css";

// Helper functions moved outside component
const getEmergencyIcon = (type) => {
  switch (type) {
    case "late":
      return "⏰";
    case "illness":
      return "🤒";
    case "cancel":
      return "❌";
    default:
      return "🚨";
  }
};

const getEmergencyTitle = (type) => {
  switch (type) {
    case "late":
      return "Retard signalé";
    case "illness":
      return "Maladie signalée";
    case "cancel":
      return "Ramassage annulé";
    default:
      return "Urgence déclarée";
  }
};

const EmergencyAlert = memo(function EmergencyAlert({ alert, onClose }) {
  const icon = useMemo(() => getEmergencyIcon(alert.type), [alert.type]);
  const title = useMemo(() => getEmergencyTitle(alert.type), [alert.type]);

  return (
    <div className={`emergency-alert type-${alert.type}`}>
      <div className="alert-icon">{icon}</div>
      <div className="alert-content">
        <div className="alert-title">{title}</div>
        <div className="alert-context">{sanitizeText(alert.context)}</div>
      </div>
      <button className="alert-close" onClick={onClose} aria-label="Fermer l'alerte">
        ×
      </button>
    </div>
  );
});

export default EmergencyAlert;
