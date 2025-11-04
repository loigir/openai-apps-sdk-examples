import "./emergency-alert.css";

export default function EmergencyAlert({ alert, onClose }) {
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

  return (
    <div className={`emergency-alert type-${alert.type}`}>
      <div className="alert-icon">{getEmergencyIcon(alert.type)}</div>
      <div className="alert-content">
        <div className="alert-title">{getEmergencyTitle(alert.type)}</div>
        <div className="alert-context">{alert.context}</div>
      </div>
      <button className="alert-close" onClick={onClose} aria-label="Fermer l'alerte">
        ×
      </button>
    </div>
  );
}
