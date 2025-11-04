import { memo, useMemo } from "react";
import { sanitizeText } from "../utils/sanitize";
import "./pickup-card.css";

// Helper functions moved outside component to avoid recreation
const formatTime = (date) => {
  return date.toLocaleTimeString("fr-CA", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

const getStatusColor = (pickup, minutesUntilPickup) => {
  if (pickup.status === "completed") return "green";
  if (pickup.status === "cancelled") return "gray";
  if (pickup.delay && pickup.delay > 0) return "orange";
  if (minutesUntilPickup < 5) return "red";
  if (minutesUntilPickup < 15) return "yellow";
  return "blue";
};

const getTimeLabel = (minutesUntilPickup) => {
  if (minutesUntilPickup < 0) return "En retard";
  if (minutesUntilPickup === 0) return "Maintenant";
  if (minutesUntilPickup < 60) return `Dans ${minutesUntilPickup} min`;
  const hours = Math.floor(minutesUntilPickup / 60);
  const mins = minutesUntilPickup % 60;
  return `Dans ${hours}h${mins > 0 ? mins.toString().padStart(2, "0") : ""}`;
};

const PickupCard = memo(function PickupCard({ pickup, currentTime }) {
  const scheduledTime = useMemo(() => new Date(pickup.scheduled_time), [pickup.scheduled_time]);
  const minutesUntilPickup = useMemo(
    () => Math.floor((scheduledTime - currentTime) / 1000 / 60),
    [scheduledTime, currentTime]
  );

  const statusColor = useMemo(
    () => getStatusColor(pickup, minutesUntilPickup),
    [pickup, minutesUntilPickup]
  );

  const timeLabel = useMemo(() => getTimeLabel(minutesUntilPickup), [minutesUntilPickup]);
  const formattedTime = useMemo(() => formatTime(scheduledTime), [scheduledTime]);

  return (
    <div className={`pickup-card status-${statusColor}`}>
      <div className="pickup-time-badge">
        <div className="scheduled-time">{formattedTime}</div>
        <div className="time-until">{timeLabel}</div>
      </div>

      <div className="pickup-details">
        <div className="child-info">
          <div className="child-name">{sanitizeText(pickup.child?.name) || "Enfant inconnu"}</div>
          {pickup.child?.grade && <div className="child-grade">{sanitizeText(pickup.child.grade)}</div>}
        </div>

        <div className="pickup-person-info">
          <div className="person-icon">👤</div>
          <div className="person-name">{sanitizeText(pickup.pickup_person?.name) || "Personne inconnue"}</div>
        </div>

        {pickup.eta && (
          <div className="eta-info">
            <span className="eta-icon">🚗</span>
            <span className="eta-time">ETA: {pickup.eta}</span>
            {pickup.delay > 0 && <span className="delay-badge">+{pickup.delay} min</span>}
          </div>
        )}

        {pickup.notes && (
          <div className="pickup-notes">
            <span className="notes-icon">📝</span>
            {sanitizeText(pickup.notes)}
          </div>
        )}
      </div>

      <div className="pickup-status">
        <span className={`status-badge ${pickup.status}`}>
          {pickup.status === "pending" && "En attente"}
          {pickup.status === "in_progress" && "En cours"}
          {pickup.status === "completed" && "Complété"}
          {pickup.status === "cancelled" && "Annulé"}
        </span>
      </div>
    </div>
  );
});

export default PickupCard;
